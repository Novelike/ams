# app/routers/registration.py

import os
import uuid
import asyncio
import json
import csv
import re
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Body, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from PIL import Image

from app.models.schemas import (
	FileUploadResponse,
	SegmentationRequest,
	SegmentationResponse,
	OCRRequest,
	OCRResponse,
	AssetRegistrationRequest,
	Asset,
	ChatResponse,
	JobResponse,
	JobStatus,
	JobStage,
	JobStatusEvent
)
from app.utils.sse import push_sse, sse_response
from app.utils.logging import registration_logger

import novelike.seg as segmod
import novelike.ocr as ocrmod
import novelike.chatbot as chatmod  # 예: chatmod.suggest_specs()

# 새로운 서비스 임포트
from app.services.enhanced_asset_matcher import EnhancedAssetMatcher, AssetMatcherConfig
from app.services.fuzzy_matcher import FuzzyMatcher
from app.services.confidence_evaluator import ConfidenceEvaluator, ConfidenceThresholds
# Phase 2 서비스 임포트
from app.services.confidence_ml import ConfidenceMLModel, FeedbackData
from app.services.dynamic_thresholds import DynamicThresholdManager, PerformanceMetrics
# 새로 추가된 서비스 임포트
from app.services.search_engine import get_search_engine
from app.services.realtime_learning import get_learning_pipeline
from app.services.ab_testing import get_ab_testing_framework
from app.middleware.performance_monitor import get_performance_monitor
# Phase 3 GPU OCR 서비스 임포트
from app.services.gpu_manager import get_gpu_manager
from app.services.batch_ocr_engine import get_batch_ocr_engine, BatchOCRRequest
from app.services.ocr_scheduler import get_ocr_scheduler, OCRJobRequest

router = APIRouter(
	prefix="/api/registration",
	tags=["registration"],
	responses={404: {"description": "Not found"}},
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 전역 서비스 인스턴스 초기화
asset_matcher = None
confidence_evaluator = None
fuzzy_matcher = None

async def initialize_services(force_reset: bool = False):
    """서비스 인스턴스 초기화"""
    global asset_matcher, confidence_evaluator, fuzzy_matcher

    # 강제 리셋이 요청된 경우 모든 서비스를 None으로 설정
    if force_reset:
        registration_logger.info("서비스 강제 리셋 중...")
        asset_matcher = None
        confidence_evaluator = None
        fuzzy_matcher = None

    if asset_matcher is None:
        registration_logger.info("자산 매칭 서비스 초기화 중...")
        try:
            config = AssetMatcherConfig(
                cache_ttl=3600,
                max_workers=4,
                enable_cache=True,
                data_dir="data/assets"
            )
            asset_matcher = EnhancedAssetMatcher(config)
            await asset_matcher.initialize()
            registration_logger.info("자산 매칭 서비스 초기화 완료")
        except Exception as e:
            registration_logger.error(f"자산 매칭 서비스 초기화 실패: {str(e)}")
            asset_matcher = None

    if confidence_evaluator is None:
        registration_logger.info("신뢰도 평가 서비스 초기화 중...")
        try:
            thresholds = ConfidenceThresholds(
                high=0.85,
                medium=0.65,
                low=0.45,
                very_low=0.25
            )
            confidence_evaluator = ConfidenceEvaluator(thresholds)
            registration_logger.info("신뢰도 평가 서비스 초기화 완료")
        except Exception as e:
            registration_logger.error(f"신뢰도 평가 서비스 초기화 실패: {str(e)}")
            confidence_evaluator = None

    if fuzzy_matcher is None:
        registration_logger.info("퍼지 매칭 서비스 초기화 중...")
        try:
            fuzzy_matcher = FuzzyMatcher()
            registration_logger.info("퍼지 매칭 서비스 초기화 완료")
        except Exception as e:
            registration_logger.error(f"퍼지 매칭 서비스 초기화 실패: {str(e)}")
            fuzzy_matcher = None

    registration_logger.info("모든 검증 서비스 초기화 완료")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_image(file: UploadFile = File(...)):
	registration_logger.info(f"이미지 업로드 요청 수신: {file.filename}")

	if not file.content_type.startswith("image/"):
		registration_logger.warning(f"잘못된 파일 형식: {file.content_type}")
		raise HTTPException(400, "이미지 파일만 업로드할 수 있습니다.")

	registration_logger.debug("파일 데이터 읽는 중...")
	data = await file.read()
	registration_logger.debug(f"파일 크기: {len(data)} 바이트")

	filename, ext = os.path.splitext(file.filename)
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	new_filename = f"{filename}_{timestamp}{ext}"
	path = os.path.join(UPLOAD_DIR, new_filename)

	registration_logger.debug(f"파일 저장 중: {path}")
	with open(path, "wb") as f:
		f.write(data)

	registration_logger.info(f"이미지 업로드 완료: {path}")
	return FileUploadResponse(
		filename=file.filename,
		size=len(data),
		content_type=file.content_type,
		upload_time=datetime.utcnow(),
		file_path=path,
	)


async def _segment_image_task(job_id: str, image_path: str):
	"""
	세그멘테이션 작업을 백그라운드에서 실행하고 SSE 이벤트를 전송하는 비동기 함수
	"""
	registration_logger.info(f"작업 ID '{job_id}'에 대한 세그멘테이션 작업 시작")
	registration_logger.debug(f"세그멘테이션 대상 이미지: {image_path}")

	# SSE 연결 시간 확보를 위한 짧은 지연
	registration_logger.debug("SSE 연결 시간 확보를 위해 0.5초 대기 중...")
	await asyncio.sleep(0.5)

	try:
		# 세그멘테이션 시작 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 세그멘테이션 시작 이벤트 전송 중")
		await push_sse(job_id, {
			"stage": JobStage.SEGMENT_START,
			"message": "세그멘테이션 시작",
			"timestamp": datetime.utcnow().isoformat()
		})

		# 세그멘테이션 수행
		registration_logger.info(f"YOLOv8 세그멘테이션 모델 호출 중...")
		results = segmod.segment_image(image_path)
		registration_logger.info(f"세그멘테이션 완료, 결과 처리 중")

		segments: Dict[str, Any] = {}

		# None 체크 및 안전한 처리 추가
		if results:
			registration_logger.debug(f"세그멘테이션 결과 객체 처리 중")
			for i, r in enumerate(results):
				registration_logger.debug(f"결과 {i+1} 처리 중")
				# r.masks가 None이 아니고 data 속성이 존재하는지 확인
				if r.masks is not None and hasattr(r.masks, 'data') and r.masks.data is not None:
					registration_logger.debug(f"마스크 데이터 발견됨, 변환 중")
					for name, mask in r.masks.data.items():
						registration_logger.debug(f"마스크 '{name}' 처리 중")
						segments[name] = mask.tolist()
				else:
					# 세그멘테이션 결과가 없는 경우 로그 또는 기본값 처리
					registration_logger.warning(f"결과 {i+1}에 대한 마스크 데이터를 찾을 수 없음: {r}")
		else:
			registration_logger.warning("세그멘테이션 결과가 없거나 비어 있음")

		# 세그멘테이션 완료 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 세그멘테이션 완료 이벤트 전송 중")
		await push_sse(job_id, {
			"stage": JobStage.SEGMENT_DONE,
			"message": "세그멘테이션 완료",
			"timestamp": datetime.utcnow().isoformat(),
			"result": {
				"segments": segments,
				"image_path": image_path
			}
		})

		registration_logger.info(f"작업 ID '{job_id}'에 대한 세그멘테이션 작업 완료")
		return SegmentationResponse(
			segments=segments,
			image_path=image_path,
		)
	except Exception as e:
		# 오류 발생 시 이벤트 전송
		registration_logger.error(f"세그멘테이션 중 오류 발생: {str(e)}")
		await push_sse(job_id, {
			"stage": "error",
			"message": f"세그멘테이션 오류: {str(e)}",
			"timestamp": datetime.utcnow().isoformat()
		})
		raise e


@router.post("/segment", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def segment_image(request: SegmentationRequest, background_tasks: BackgroundTasks):
	"""
	이미지 세그멘테이션 작업을 시작하고 작업 ID를 반환
	"""
	registration_logger.info(f"세그멘테이션 요청 수신: {request.image_path}")

	if not os.path.exists(request.image_path):
		registration_logger.error(f"이미지 파일을 찾을 수 없음: {request.image_path}")
		raise HTTPException(404, "이미지 파일을 찾을 수 없습니다.")

	# 작업 ID 생성
	job_id = str(uuid.uuid4())
	registration_logger.info(f"세그멘테이션 작업 ID 생성됨: {job_id}")

	# 백그라운드 작업 시작
	registration_logger.debug(f"백그라운드 세그멘테이션 작업 시작 중...")
	background_tasks.add_task(_segment_image_task, job_id, request.image_path)

	# 작업 ID와 상태 반환
	registration_logger.info(f"세그멘테이션 작업 {job_id} 대기열에 추가됨")
	return JobResponse(job_id=job_id, status=JobStatus.QUEUED)


def post_process_ocr_text(text: str) -> dict:
	"""OCR 텍스트 후처리 및 값 추출"""
	if not text or not isinstance(text, str):
		return {"category": "other", "value": text, "confidence": 0.0}

	text = text.strip()

	# 패턴 1: "제목: 내용" 형태
	colon_pattern = r'^([^:]+):\s*(.+)$'
	colon_match = re.match(colon_pattern, text)

	if colon_match:
		title = colon_match.group(1).strip()
		content = colon_match.group(2).strip()

		category = categorize_from_title(title)
		value = clean_content(content)

		return {"category": category, "value": value, "confidence": 0.9}

	# 패턴 2: "제목 내용" 형태 (공백으로 구분)
	space_pattern = r'^(모델명|제조사|시리얼번호|시리얼|제조자|제조업체|상호명|기자재|명칭|제품명칭)\s+(.+)$'
	space_match = re.match(space_pattern, text)

	if space_match:
		title = space_match.group(1).strip()
		content = space_match.group(2).strip()

		category = categorize_from_title(title)
		value = clean_content(content)

		return {"category": category, "value": value, "confidence": 0.8}

	# 기본값 반환
	return {"category": "other", "value": text, "confidence": 0.5}

def categorize_from_title(title: str) -> str:
	"""제목에서 카테고리 분류"""
	title_lower = title.lower()

	if any(keyword in title_lower for keyword in ['모델', 'model', '기자재', '명칭', '제품명칭']):
		return 'model'
	elif any(keyword in title_lower for keyword in ['제조', 'manufacturer', '상호명', '제조업체', '제조자']):
		return 'manufacturer'
	elif any(keyword in title_lower for keyword in ['시리얼', 'serial', 's/n', 'sn']):
		return 'serial'
	elif any(keyword in title_lower for keyword in ['전압', 'voltage', '정격', '스펙']):
		return 'spec'

	return 'other'

def clean_content(content: str) -> str:
	"""내용 텍스트 정리"""
	if not content:
		return ''

	# 괄호 제거
	content = re.sub(r'\([^)]*\)', '', content).strip()
	content = re.sub(r'\[[^\]]*\]', '', content).strip()

	# 불필요한 접두사 제거 (더 정확한 패턴 사용)
	# "기자재의 명칭제품명칭" -> "명칭제품명칭"
	# "상호명제조업체명" -> "제조업체명"
	unnecessary_patterns = [
		r'^기자재의\s*',
		r'^제품의\s*',
		r'^상품의\s*',
		r'^장비의\s*',
		r'^상호명(?=\S)',  # 상호명 뒤에 공백이 없는 경우만
		r'^제조자\s+',     # 제조자 뒤에 공백이 있는 경우만
		r'^제조국가\s*'
	]

	for pattern in unnecessary_patterns:
		content = re.sub(pattern, '', content, flags=re.IGNORECASE).strip()

	# 연속된 공백 정리
	content = re.sub(r'\s+', ' ', content).strip()

	return content

def process_ocr_result(ocr_result):
	"""OCR 결과를 안전하게 처리하는 헬퍼 함수"""
	registration_logger.debug(f"OCR 결과 처리 중: {type(ocr_result)}")
	try:
		# EasyOCR의 일반적인 반환 형식: [([[x1, y1], [x2, y2], [x3, y3], [x4, y4]], 'text', confidence)]
		if isinstance(ocr_result, (list, tuple)) and len(ocr_result) >= 3:
			# 튜플/리스트 형식: (bbox, text, confidence)
			bbox, text, conf = ocr_result[0], ocr_result[1], ocr_result[2]
			registration_logger.debug(f"리스트/튜플 형식 OCR 결과 처리: '{text}' (신뢰도: {conf:.2f})")

			# 텍스트 후처리 적용
			processed = post_process_ocr_text(text)

			return {
				"text": processed["value"],
				"original_text": text,
				"category": processed["category"],
				"conf": conf
			}
		elif isinstance(ocr_result, dict):
			# 딕셔너리 형식
			if "text" in ocr_result and "conf" in ocr_result:
				registration_logger.debug(f"딕셔너리 형식 OCR 결과 처리 (conf): '{ocr_result['text']}' (신뢰도: {ocr_result['conf']:.2f})")
				processed = post_process_ocr_text(ocr_result["text"])
				return {
					"text": processed["value"],
					"original_text": ocr_result["text"],
					"category": processed["category"],
					"conf": ocr_result["conf"]
				}
			elif "text" in ocr_result and "confidence" in ocr_result:
				registration_logger.debug(f"딕셔너리 형식 OCR 결과 처리 (confidence): '{ocr_result['text']}' (신뢰도: {ocr_result['confidence']:.2f})")
				processed = post_process_ocr_text(ocr_result["text"])
				return {
					"text": processed["value"],
					"original_text": ocr_result["text"],
					"category": processed["category"],
					"conf": ocr_result["confidence"]
				}

		# 기본값 반환
		registration_logger.warning(f"알 수 없는 OCR 결과 형식, 기본값으로 변환: {ocr_result}")
		return {"text": str(ocr_result), "conf": 0.0}
	except Exception as e:
		registration_logger.error(f"OCR 결과 처리 중 오류 발생: {e}")
		return {"text": "", "conf": 0.0}


async def _perform_ocr_task(job_id: str, image_path: str, segments: Optional[Dict[str, Any]] = None):
	"""
	OCR 작업을 백그라운드에서 실행하고 SSE 이벤트를 전송하는 비동기 함수
	"""
	registration_logger.info(f"작업 ID '{job_id}'에 대한 OCR 작업 시작")
	registration_logger.debug(f"OCR 대상 이미지: {image_path}")
	registration_logger.debug(f"세그멘테이션 정보 제공 여부: {segments is not None}")

	# 진행 상황 콜백 함수 정의
	async def progress_callback(stage: str, message: str, progress: float):
		stage_mapping = {
			"preprocessing": JobStage.OCR_PREPROCESSING,
			"detection": JobStage.OCR_DETECTION,
			"recognition": JobStage.OCR_RECOGNITION,
			"postprocessing": JobStage.OCR_POSTPROCESSING,
			"error": "error"
		}

		# "completed" 단계는 별도로 처리하지 않음 (실제 OCR 완료 이벤트는 따로 전송)
		if stage == "completed":
			registration_logger.debug(f"OCR 진행 상황 완료 단계 도달, 별도 완료 이벤트에서 처리됨")
			return

		mapped_stage = stage_mapping.get(stage, f"ocr_{stage}")
		await push_sse(job_id, {
			"stage": mapped_stage,
			"message": message,
			"progress": progress,
			"timestamp": datetime.utcnow().isoformat()
		})

	# SSE 연결 시간 확보를 위한 짧은 지연
	registration_logger.debug("SSE 연결 시간 확보를 위해 0.5초 대기 중...")
	await asyncio.sleep(0.5)

	try:
		# OCR 시작 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 OCR 시작 이벤트 전송 중")
		await push_sse(job_id, {
			"stage": JobStage.OCR_START,
			"message": "텍스트 인식 시작",
			"timestamp": datetime.utcnow().isoformat()
		})

		if not os.path.exists(image_path):
			registration_logger.error(f"이미지 파일을 찾을 수 없음: {image_path}")
			raise HTTPException(404, "이미지 파일을 찾을 수 없습니다.")

		registration_logger.debug(f"이미지 로드 중: {image_path}")
		img = Image.open(image_path).convert("RGB")
		registration_logger.debug(f"이미지 크기: {img.width}x{img.height} 픽셀")

		results: Dict[str, str] = {}
		confidence: Dict[str, float] = {}

		# 1) 세그멘테이션 bbox 가 있으면 해당 영역에 대해 EasyOCR 수행
		if segments:
			registration_logger.info(f"세그멘테이션 영역별 OCR 수행 시작 (영역 수: {len(segments)})")
			for field, bbox in segments.items():
				registration_logger.debug(f"영역 '{field}' OCR 처리 중")
				try:
					# 다양한 bbox 형식을 지원하도록 수정
					if isinstance(bbox, dict):
						registration_logger.debug(f"딕셔너리 형식 bbox 처리 중: {bbox}")
						# 표준 형식: x, y, width, height
						if all(key in bbox for key in ['x', 'y', 'width', 'height']):
							x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
							registration_logger.debug(f"표준 형식 bbox: x={x}, y={y}, width={w}, height={h}")
						# 대체 형식: x, y, w, h
						elif all(key in bbox for key in ['x', 'y', 'w', 'h']):
							x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
							registration_logger.debug(f"대체 형식 bbox: x={x}, y={y}, w={w}, h={h}")
						# 좌표 형식: x1, y1, x2, y2
						elif all(key in bbox for key in ['x1', 'y1', 'x2', 'y2']):
							x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
							x, y, w, h = x1, y1, x2 - x1, y2 - y1
							registration_logger.debug(f"좌표 형식 bbox: x1={x1}, y1={y1}, x2={x2}, y2={y2} -> x={x}, y={y}, w={w}, h={h}")
						else:
							registration_logger.warning(f"지원되지 않는 bbox 형식: {bbox}")
							continue
					elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
						# 리스트/튜플 형식: [x, y, w, h] 또는 [x1, y1, x2, y2]
						x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
						registration_logger.debug(f"리스트/튜플 형식 bbox: x={x}, y={y}, w={w}, h={h}")
					else:
						registration_logger.warning(f"잘못된 bbox 형식: {bbox}")
						continue

					# 음수 좌표나 크기 값 검증
					if x < 0 or y < 0 or w <= 0 or h <= 0:
						registration_logger.warning(f"잘못된 bbox 값: x={x}, y={y}, w={w}, h={h}")
						continue

					# 이미지 크롭 후 EasyOCR 수행
					registration_logger.debug(f"이미지 영역 크롭 중: x={x}, y={y}, w={w}, h={h}")
					crop = img.crop((x, y, x + w, y + h))
					registration_logger.debug(f"크롭된 이미지 크기: {crop.width}x{crop.height} 픽셀")

					buf = BytesIO()
					crop.save(buf, format="JPEG")
					registration_logger.debug(f"EasyOCR 호출 중 (영역 '{field}')")
					ocrs = await ocrmod.ocr_easy_with_progress(buf.getvalue(), progress_callback)

					if ocrs and len(ocrs) > 0:
						registration_logger.info(f"영역 '{field}'에서 {len(ocrs)}개 텍스트 감지됨")
						processed_result = process_ocr_result(ocrs[0])
						results[field] = processed_result["text"]
						confidence[field] = processed_result["conf"]
						registration_logger.info(f"영역 '{field}' OCR 결과: '{processed_result['text']}' (신뢰도: {processed_result['conf']:.2f})")
					else:
						registration_logger.warning(f"영역 '{field}'에서 텍스트가 감지되지 않음")

				except (KeyError, ValueError, TypeError) as e:
					registration_logger.error(f"영역 '{field}' bbox 처리 중 오류 발생: {e}")
					continue

		# 2) 세그멘테이션이 없거나 영역 OCR 결과가 없으면 전체 이미지에 대해 EasyOCR 수행
		if not results:
			registration_logger.info("세그멘테이션 영역 OCR 결과가 없음, 전체 이미지 OCR 수행 중")
			try:
				# 전체 이미지를 바이트로 변환
				registration_logger.debug("전체 이미지를 바이트로 변환 중")
				buf = BytesIO()
				img.save(buf, format="JPEG")
				registration_logger.debug("전체 이미지에 대해 EasyOCR 호출 중")
				ocrs = await ocrmod.ocr_easy_with_progress(buf.getvalue(), progress_callback)

				if ocrs and len(ocrs) > 0:
					registration_logger.info(f"전체 이미지에서 {len(ocrs)}개 텍스트 영역 감지됨")
					# 모든 검출된 텍스트를 처리
					full_texts = []
					total_confidence = 0.0

					for i, ocr_result in enumerate(ocrs):
						registration_logger.debug(f"텍스트 영역 {i+1}/{len(ocrs)} 처리 중")
						processed_result = process_ocr_result(ocr_result)
						field_name = f"text_{i + 1}" if len(ocrs) > 1 else "full_text"
						results[field_name] = processed_result["text"]
						confidence[field_name] = processed_result["conf"]
						full_texts.append(processed_result["text"])
						total_confidence += processed_result["conf"]
						registration_logger.debug(f"텍스트 영역 {i+1} 결과: '{processed_result['text']}' (신뢰도: {processed_result['conf']:.2f})")

					# 전체 텍스트도 함께 제공
					if len(ocrs) > 1:
						combined_text = " ".join(full_texts)
						avg_confidence = total_confidence / len(ocrs)
						results["combined_text"] = combined_text
						confidence["combined_text"] = avg_confidence
						registration_logger.info(f"결합된 전체 텍스트: '{combined_text}' (평균 신뢰도: {avg_confidence:.2f})")
				else:
					# OCR 결과가 없는 경우
					registration_logger.warning("전체 이미지에서 텍스트가 감지되지 않음")
					results["full_text"] = ""
					confidence["full_text"] = 0.0

			except Exception as e:
				registration_logger.error(f"전체 이미지 OCR 중 오류 발생: {e}")
				results["error"] = "OCR 처리 중 오류가 발생했습니다."
				confidence["error"] = 0.0

		# OCR 완료 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 OCR 완료 이벤트 전송 중")
		registration_logger.info(f"OCR 결과 요약: {len(results)}개 키, 결과 키들: {list(results.keys())}")
		registration_logger.debug(f"OCR 결과 상세: {results}")
		registration_logger.debug(f"OCR 신뢰도 상세: {confidence}")

		ocr_event_data = {
			"stage": JobStage.OCR_DONE,
			"message": "텍스트 인식 완료",
			"timestamp": datetime.utcnow().isoformat(),
			"result": {
				"results": results,
				"confidence": confidence
			}
		}

		registration_logger.info(f"전송할 OCR 완료 이벤트 데이터: stage={ocr_event_data['stage']}, result 키 개수={len(ocr_event_data['result']['results'])}")
		await push_sse(job_id, ocr_event_data)

		registration_logger.info(f"작업 ID '{job_id}'에 대한 OCR 작업 완료 (결과 수: {len(results)})")
		return OCRResponse(results=results, confidence=confidence)
	except Exception as e:
		# 오류 발생 시 이벤트 전송
		registration_logger.error(f"OCR 작업 중 오류 발생: {str(e)}")
		await push_sse(job_id, {
			"stage": "error",
			"message": f"OCR 오류: {str(e)}",
			"timestamp": datetime.utcnow().isoformat()
		})
		raise e


@router.post("/ocr", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def perform_ocr(request: OCRRequest, background_tasks: BackgroundTasks):
	"""
	OCR 작업을 시작하고 작업 ID를 반환
	"""
	registration_logger.info(f"OCR 요청 수신: {request.image_path}")
	registration_logger.debug(f"세그멘테이션 정보 제공 여부: {request.segments is not None}")

	if not os.path.exists(request.image_path):
		registration_logger.error(f"이미지 파일을 찾을 수 없음: {request.image_path}")
		raise HTTPException(404, "이미지 파일을 찾을 수 없습니다.")

	# 작업 ID 생성
	job_id = str(uuid.uuid4())
	registration_logger.info(f"OCR 작업 ID 생성됨: {job_id}")

	# 백그라운드 작업 시작
	registration_logger.debug(f"백그라운드 OCR 작업 시작 중...")
	background_tasks.add_task(_perform_ocr_task, job_id, request.image_path, request.segments)

	# 작업 ID와 상태 반환
	registration_logger.info(f"OCR 작업 {job_id} 대기열에 추가됨")
	return JobResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.post("/chatbot-assist", response_model=ChatResponse)
async def chatbot_assist(
		model_name: str = Body(..., embed=True),
		serial_number: str | None = Body(None, embed=True),
):
	registration_logger.info(f"챗봇 지원 요청 수신: 모델명={model_name}")
	if serial_number:
		registration_logger.debug(f"시리얼 번호 제공됨: {serial_number}")

	registration_logger.debug(f"모델명 '{model_name}'에 대한 스펙 추천 요청 중")
	specs_text = chatmod.suggest_specs(model_name)
	registration_logger.debug(f"추천된 스펙: {specs_text[:50]}...")

	year = datetime.utcnow().year
	asset_number = f"AMS-{year}-{str(uuid.uuid4())[:8]}"
	registration_logger.info(f"자산 번호 생성됨: {asset_number}")

	registration_logger.info(f"챗봇 지원 응답 생성 완료")
	return ChatResponse(
		message=specs_text,
		suggestions=[f"Suggested asset number: {asset_number}"],
		asset_info={"asset_number": asset_number},
	)


async def _register_asset_task(job_id: str, request: AssetRegistrationRequest):
	"""
	자산 등록 작업을 백그라운드에서 실행하고 SSE 이벤트를 전송하는 비동기 함수
	"""
	registration_logger.info(f"작업 ID '{job_id}'에 대한 자산 등록 작업 시작")
	registration_logger.debug(f"모델명: {request.model_name}, 시리얼 번호: {request.serial_number}")

	# SSE 연결 시간 확보를 위한 짧은 지연
	registration_logger.debug("SSE 연결 시간 확보를 위해 0.5초 대기 중...")
	await asyncio.sleep(0.5)

	try:
		# 자산 등록 시작 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 자산 등록 시작 이벤트 전송 중")
		await push_sse(job_id, {
			"stage": JobStage.REGISTER_START,
			"message": "자산 등록 시작",
			"timestamp": datetime.utcnow().isoformat()
		})

		# 자산 등록 처리
		registration_logger.debug("자산 정보 생성 중...")
		asset_id = str(uuid.uuid4())
		asset_number = f"AMS-{datetime.utcnow().year}-{str(uuid.uuid4())[:8]}"
		registration_logger.info(f"새 자산 ID 생성됨: {asset_id}")
		registration_logger.info(f"새 자산 번호 생성됨: {asset_number}")

		asset = Asset(
			id=asset_id,
			asset_number=asset_number,
			model_name=request.model_name,
			detailed_model=request.detailed_model,
			serial_number=request.serial_number,
			manufacturer=request.manufacturer,
			site=request.site,
			asset_type=request.asset_type,
			user=request.user,
			registration_date=datetime.utcnow(),
			image_path=request.image_path,
			ocr_results=request.ocr_results,
			segmentation_results=request.segmentation_results,
			specs=request.specs,
			metadata=request.metadata,
		)

		registration_logger.debug("자산 객체 생성 완료")
		registration_logger.debug(f"자산 정보: 제조사={request.manufacturer}, 사이트={request.site}, 유형={request.asset_type}")

		# 자산 등록 완료 이벤트 전송
		registration_logger.debug(f"작업 ID '{job_id}'에 대한 자산 등록 완료 이벤트 전송 중")
		await push_sse(job_id, {
			"stage": JobStage.REGISTER_DONE,
			"message": "자산 등록 완료",
			"timestamp": datetime.utcnow().isoformat(),
			"data": {"asset_id": asset.id, "asset_number": asset.asset_number}
		})

		registration_logger.info(f"작업 ID '{job_id}'에 대한 자산 등록 작업 완료")
		return asset
	except Exception as e:
		# 오류 발생 시 이벤트 전송
		registration_logger.error(f"자산 등록 중 오류 발생: {str(e)}")
		await push_sse(job_id, {
			"stage": "error",
			"message": f"자산 등록 오류: {str(e)}",
			"timestamp": datetime.utcnow().isoformat()
		})
		raise e


@router.post("/register", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def register_asset(request: AssetRegistrationRequest, background_tasks: BackgroundTasks):
	"""
	자산 등록 작업을 시작하고 작업 ID를 반환
	"""
	registration_logger.info(f"자산 등록 요청 수신: {request.model_name}")
	registration_logger.debug(f"시리얼 번호: {request.serial_number}, 제조사: {request.manufacturer}")

	# 작업 ID 생성
	job_id = str(uuid.uuid4())
	registration_logger.info(f"자산 등록 작업 ID 생성됨: {job_id}")

	# 백그라운드 작업 시작
	registration_logger.debug(f"백그라운드 자산 등록 작업 시작 중...")
	background_tasks.add_task(_register_asset_task, job_id, request)

	# 작업 ID와 상태 반환
	registration_logger.info(f"자산 등록 작업 {job_id} 대기열에 추가됨")
	return JobResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
	"""
	SSE 엔드포인트: 특정 작업의 상태 업데이트를 실시간으로 스트리밍
	"""
	registration_logger.info(f"작업 ID '{job_id}'에 대한 상태 스트리밍 요청 수신")
	return sse_response(job_id)


@router.post("/save-asset-data")
async def save_asset_data(request: AssetRegistrationRequest):
	"""
	자산 데이터를 CSV와 JSON 형태로 저장
	"""
	registration_logger.info(f"자산 데이터 저장 요청 수신: {request.model_name}")

	try:
		# 자산 번호 생성
		asset_number = f"AMS-{datetime.utcnow().year}-{str(uuid.uuid4())[:8]}"
		registration_logger.info(f"새 자산 번호 생성됨: {asset_number}")

		# CSV 저장용 데이터 (자산 목록 조회용)
		csv_data = {
			'asset_number': asset_number,
			'model_name': request.model_name or '',
			'serial_number': request.serial_number or '',
			'manufacturer': request.manufacturer or '',
			'site': request.site or '',
			'asset_type': request.asset_type.value if request.asset_type else '',
			'user': request.user or '',
			'registration_date': datetime.utcnow().isoformat()
		}

		# CSV 파일 경로 설정
		csv_file_path = Path("data/assets/assets_list.csv")
		csv_file_path.parent.mkdir(parents=True, exist_ok=True)

		# CSV 파일에 추가 (헤더가 없으면 헤더도 추가)
		file_exists = csv_file_path.exists() and csv_file_path.stat().st_size > 0

		with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=csv_data.keys())
			if not file_exists:
				writer.writeheader()
			writer.writerow(csv_data)

		registration_logger.info(f"CSV 파일에 자산 데이터 저장 완료: {csv_file_path}")

		# JSON 저장용 데이터 (상세 정보용)
		json_data = {
			'basic_info': csv_data,
			'specs': request.specs or {},
			'ocr_results': request.ocr_results or {},
			'metadata': {
				'image_path': request.image_path,
				'segmentation_results': request.segmentation_results,
				'processing_timestamp': datetime.utcnow().isoformat()
			}
		}

		# JSON 파일 경로 설정
		json_file_path = Path(f"data/assets/details/{asset_number}.json")
		json_file_path.parent.mkdir(parents=True, exist_ok=True)

		# JSON 파일 저장
		with open(json_file_path, 'w', encoding='utf-8') as jsonfile:
			json.dump(json_data, jsonfile, ensure_ascii=False, indent=2)

		registration_logger.info(f"JSON 파일에 자산 상세 데이터 저장 완료: {json_file_path}")

		return {
			"message": "자산 데이터 저장 완료",
			"asset_number": asset_number,
			"csv_path": str(csv_file_path),
			"json_path": str(json_file_path)
		}

	except Exception as e:
		registration_logger.error(f"자산 데이터 저장 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자산 데이터 저장 실패: {str(e)}"
		)


@router.get("/assets/list")
async def get_assets_list(
	page: int = 1,
	page_size: int = 20,
	search: Optional[str] = None,
	asset_type: Optional[str] = None,
	site: Optional[str] = None,
	manufacturer: Optional[str] = None
):
	"""
	CSV 파일에서 자산 목록 조회 (페이징, 검색, 필터링 지원)
	"""
	registration_logger.info(f"자산 목록 조회 요청: page={page}, page_size={page_size}, search={search}")

	try:
		csv_file_path = Path("data/assets/assets_list.csv")

		if not csv_file_path.exists():
			registration_logger.warning("자산 목록 CSV 파일이 존재하지 않음")
			return {
				"items": [],
				"total": 0,
				"page": page,
				"page_size": page_size,
				"total_pages": 0
			}

		assets = []

		# CSV 파일 읽기
		with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
			reader = csv.DictReader(csvfile)
			for row in reader:
				# 검색 필터 적용
				if search and search.lower() not in (
					row.get('model_name', '').lower() + 
					row.get('serial_number', '').lower() + 
					row.get('manufacturer', '').lower() +
					row.get('asset_number', '').lower()
				):
					continue

				# 자산 유형 필터 적용
				if asset_type and row.get('asset_type', '') != asset_type:
					continue

				# 지점 필터 적용
				if site and row.get('site', '') != site:
					continue

				# 제조사 필터 적용
				if manufacturer and row.get('manufacturer', '') != manufacturer:
					continue

				assets.append(row)

		registration_logger.info(f"필터링된 자산 수: {len(assets)}")

		# 페이징 처리
		total = len(assets)
		total_pages = (total + page_size - 1) // page_size
		start = (page - 1) * page_size
		end = start + page_size

		paginated_assets = assets[start:end]

		registration_logger.info(f"페이징 결과: {len(paginated_assets)}개 항목 반환")

		return {
			"items": paginated_assets,
			"total": total,
			"page": page,
			"page_size": page_size,
			"total_pages": total_pages
		}

	except Exception as e:
		registration_logger.error(f"자산 목록 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자산 목록 조회 실패: {str(e)}"
		)


@router.get("/assets/{asset_number}")
async def get_asset_detail(asset_number: str):
	"""
	특정 자산의 상세 정보 조회 (JSON 파일에서)
	"""
	registration_logger.info(f"자산 상세 정보 조회 요청: {asset_number}")

	try:
		json_file_path = Path(f"data/assets/details/{asset_number}.json")

		if not json_file_path.exists():
			registration_logger.warning(f"자산 상세 정보 파일이 존재하지 않음: {asset_number}")
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail=f"자산 번호 '{asset_number}'에 대한 상세 정보를 찾을 수 없습니다"
			)

		# JSON 파일 읽기
		with open(json_file_path, 'r', encoding='utf-8') as jsonfile:
			asset_detail = json.load(jsonfile)

		registration_logger.info(f"자산 상세 정보 조회 완료: {asset_number}")
		return asset_detail

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"자산 상세 정보 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자산 상세 정보 조회 실패: {str(e)}"
		)


@router.post("/verify-single")
async def verify_single_item(request: Dict[str, Any]):
	"""
	단일 OCR 항목 검증
	"""
	registration_logger.info("단일 항목 검증 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		text = request.get('text', '')
		category = request.get('category', 'other')
		confidence = request.get('confidence', 0.0)

		registration_logger.debug(f"검증 대상: {text} (카테고리: {category}, 신뢰도: {confidence})")

		# OCR 데이터 구성
		ocr_data = {
			'text': text,
			'confidence': confidence,
			'category': category
		}

		# DB 검증 수행
		verification_result = None
		if text and category in ['model', 'serial', 'manufacturer']:
			field_data = {f'{category}_name' if category == 'model' else 
						 f'{category}_number' if category == 'serial' else category: text}
			verification_result = await asset_matcher.verify_ocr_result_async(field_data)
			verification_result = verification_result.get(f'{category}_name' if category == 'model' else 
														f'{category}_number' if category == 'serial' else category)

		# 신뢰도 평가
		evaluation = confidence_evaluator.evaluate_ocr_result(ocr_data, verification_result)

		# 자동완성 제안 생성
		suggestions = []
		if text and len(text) >= 2:
			field_type = 'model_name' if category == 'model' else \
						'serial_number' if category == 'serial' else category
			suggestions = await asset_matcher.get_suggestions(field_type, text, limit=5)

		return {
			"verification": evaluation,
			"suggestions": suggestions,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"단일 항목 검증 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"검증 실패: {str(e)}"
		)


@router.post("/verify-ocr")
async def verify_ocr_batch(request: Dict[str, Any]):
	"""
	OCR 결과 일괄 검증
	"""
	registration_logger.info("OCR 일괄 검증 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		ocr_data_list = request.get('ocr_data', [])
		registration_logger.debug(f"검증할 항목 수: {len(ocr_data_list)}")

		# 각 항목별 검증 수행
		verification_results = {}
		suggestions = {}

		for item in ocr_data_list:
			item_id = item.get('id', '')
			text = item.get('text', '')
			category = item.get('category', 'other')
			confidence = item.get('confidence', 0.0)

			# OCR 데이터 구성
			ocr_data = {
				'text': text,
				'confidence': confidence,
				'category': category
			}

			# DB 검증 수행
			verification_result = None
			if text and category in ['model', 'serial', 'manufacturer']:
				field_data = {f'{category}_name' if category == 'model' else 
							 f'{category}_number' if category == 'serial' else category: text}
				db_result = await asset_matcher.verify_ocr_result_async(field_data)
				verification_result = db_result.get(f'{category}_name' if category == 'model' else 
													f'{category}_number' if category == 'serial' else category)

			# 신뢰도 평가
			evaluation = confidence_evaluator.evaluate_ocr_result(ocr_data, verification_result)
			verification_results[item_id] = evaluation

			# 자동완성 제안 생성
			item_suggestions = []
			if text and len(text) >= 2:
				field_type = 'model_name' if category == 'model' else \
							'serial_number' if category == 'serial' else category
				item_suggestions = await asset_matcher.get_suggestions(field_type, text, limit=5)
			suggestions[item_id] = item_suggestions

		# 전체 통계 계산
		batch_evaluation = confidence_evaluator.batch_evaluate(ocr_data_list, verification_results)

		return {
			"verification": verification_results,
			"suggestions": suggestions,
			"summary": batch_evaluation['summary'],
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"OCR 일괄 검증 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"일괄 검증 실패: {str(e)}"
		)


@router.get("/suggestions/{field_type}")
async def get_suggestions(field_type: str, q: str = "", limit: int = 10):
	"""
	자동완성 제안 조회
	"""
	registration_logger.info(f"자동완성 제안 요청: {field_type}, 쿼리: {q}")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		if not q or len(q) < 2:
			return {"suggestions": [], "status": "success"}

		# 자동완성 제안 생성
		suggestions = await asset_matcher.get_suggestions(field_type, q, limit)

		return {
			"suggestions": suggestions,
			"query": q,
			"field_type": field_type,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"자동완성 제안 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자동완성 조회 실패: {str(e)}"
		)


@router.get("/verification/stats")
async def get_verification_stats():
	"""
	검증 시스템 통계 조회 (Phase 2: 확장)
	"""
	registration_logger.info("검증 시스템 통계 요청 수신")

	try:
		# 서비스 초기화 확인 (강제 리셋으로 새로 초기화)
		await initialize_services(force_reset=True)

		# 각 서비스의 통계 수집
		matcher_stats = {}
		evaluator_stats = {}
		fuzzy_stats = {}

		if asset_matcher:
			try:
				matcher_stats = asset_matcher.get_stats()
			except Exception as e:
				registration_logger.warning(f"자산 매처 통계 수집 실패: {str(e)}")
				matcher_stats = {"error": str(e)}

		if confidence_evaluator:
			try:
				evaluator_stats = confidence_evaluator.get_stats()
			except Exception as e:
				registration_logger.warning(f"신뢰도 평가기 통계 수집 실패: {str(e)}")
				evaluator_stats = {"error": str(e)}

		if fuzzy_matcher:
			try:
				fuzzy_stats = fuzzy_matcher.get_cache_stats()
			except Exception as e:
				registration_logger.warning(f"퍼지 매처 통계 수집 실패: {str(e)}")
				fuzzy_stats = {"error": str(e)}

		return {
			"asset_matcher": matcher_stats,
			"confidence_evaluator": evaluator_stats,
			"fuzzy_matcher": fuzzy_stats,
			"services_initialized": {
				"asset_matcher": asset_matcher is not None,
				"confidence_evaluator": confidence_evaluator is not None,
				"fuzzy_matcher": fuzzy_matcher is not None
			},
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"검증 시스템 통계 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"통계 조회 실패: {str(e)}"
		)


# Phase 2: 새로운 엔드포인트들 추가

@router.post("/feedback/collect")
async def collect_user_feedback(request: Dict[str, Any]):
	"""
	사용자 피드백 수집 (Phase 2: ML 학습용)
	"""
	registration_logger.info("사용자 피드백 수집 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		ocr_data = request.get('ocr_data', {})
		verification_result = request.get('verification_result')
		user_accepted = request.get('user_accepted', True)
		corrected_text = request.get('corrected_text')

		# 피드백 수집
		await confidence_evaluator.collect_user_feedback(
			ocr_data=ocr_data,
			verification_result=verification_result,
			user_accepted=user_accepted,
			corrected_text=corrected_text
		)

		return {
			"message": "피드백 수집 완료",
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"피드백 수집 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"피드백 수집 실패: {str(e)}"
		)


@router.post("/performance/update")
async def update_performance_metrics(request: Dict[str, Any]):
	"""
	성능 지표 업데이트 및 임계값 자동 조정 (Phase 2)
	"""
	registration_logger.info("성능 지표 업데이트 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		# 성능 지표 생성
		metrics = PerformanceMetrics(
			true_positives=request.get('true_positives', 0),
			false_positives=request.get('false_positives', 0),
			true_negatives=request.get('true_negatives', 0),
			false_negatives=request.get('false_negatives', 0),
			total_predictions=request.get('total_predictions', 0)
		)

		# 임계값 조정
		adjustment_result = await confidence_evaluator.update_performance_metrics(metrics)

		return {
			"metrics": {
				"precision": metrics.precision,
				"recall": metrics.recall,
				"f1_score": metrics.f1_score,
				"accuracy": metrics.accuracy
			},
			"adjustment": adjustment_result,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"성능 지표 업데이트 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"성능 지표 업데이트 실패: {str(e)}"
		)


@router.get("/ml-model/info")
async def get_ml_model_info():
	"""
	ML 모델 정보 조회 (Phase 2)
	"""
	registration_logger.info("ML 모델 정보 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		model_info = confidence_evaluator.get_ml_model_info()
		threshold_info = confidence_evaluator.get_threshold_info()

		return {
			"ml_model": model_info,
			"thresholds": threshold_info,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"ML 모델 정보 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"ML 모델 정보 조회 실패: {str(e)}"
		)


@router.post("/thresholds/manual-override")
async def manual_threshold_override(request: Dict[str, Any]):
	"""
	수동 임계값 설정 (Phase 2)
	"""
	registration_logger.info("수동 임계값 설정 요청 수신")

	try:
		# 서비스 초기화 확인
		await initialize_services()

		new_thresholds = request.get('thresholds', {})
		reason = request.get('reason', 'manual_override')

		# 임계값 검증
		required_keys = ['high', 'medium', 'low', 'very_low']
		if not all(key in new_thresholds for key in required_keys):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"필수 임계값이 누락되었습니다: {required_keys}"
			)

		# 임계값 범위 검증
		for key, value in new_thresholds.items():
			if not 0.0 <= value <= 1.0:
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=f"임계값은 0.0과 1.0 사이여야 합니다: {key}={value}"
				)

		# 임계값 순서 검증 (high > medium > low > very_low)
		if not (new_thresholds['high'] > new_thresholds['medium'] > 
				new_thresholds['low'] > new_thresholds['very_low']):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="임계값은 high > medium > low > very_low 순서여야 합니다"
			)

		# 수동 설정 적용
		confidence_evaluator.threshold_manager.manual_threshold_override(new_thresholds, reason)

		return {
			"message": "임계값 수동 설정 완료",
			"new_thresholds": new_thresholds,
			"reason": reason,
			"status": "success"
		}

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"수동 임계값 설정 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"임계값 설정 실패: {str(e)}"
		)


# ==================== 새로 추가된 API 엔드포인트 ====================

@router.get("/search/assets")
async def search_assets(query: str, field: str = "content", limit: int = 10):
	"""
	자산 검색 (Whoosh 기반 퍼지 검색)
	"""
	registration_logger.info(f"자산 검색 요청: query={query}, field={field}")

	try:
		search_engine = await get_search_engine()
		results = await search_engine.fuzzy_search(query, field, limit)

		return {
			"query": query,
			"field": field,
			"results": results,
			"count": len(results),
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"자산 검색 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자산 검색 실패: {str(e)}"
		)


@router.get("/search/suggestions")
async def get_search_suggestions(field: str, partial_text: str, limit: int = 5):
	"""
	검색 자동완성 제안
	"""
	registration_logger.info(f"자동완성 요청: field={field}, text={partial_text}")

	try:
		search_engine = await get_search_engine()
		suggestions = await search_engine.suggest_completions(field, partial_text, limit)

		return {
			"field": field,
			"partial_text": partial_text,
			"suggestions": suggestions,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"자동완성 제안 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"자동완성 제안 실패: {str(e)}"
		)


@router.get("/search/stats")
async def get_search_stats():
	"""
	검색 엔진 통계
	"""
	registration_logger.info("검색 엔진 통계 요청")

	try:
		search_engine = await get_search_engine()
		stats = await search_engine.get_stats()

		return {
			"stats": stats,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"검색 통계 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"검색 통계 조회 실패: {str(e)}"
		)


@router.get("/learning/status")
async def get_learning_status():
	"""
	실시간 학습 상태 조회
	"""
	registration_logger.info("실시간 학습 상태 요청")

	try:
		learning_pipeline = await get_learning_pipeline()
		status_info = await learning_pipeline.get_learning_status()

		return {
			"learning_status": status_info,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"학습 상태 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"학습 상태 조회 실패: {str(e)}"
		)


@router.get("/learning/performance")
async def get_learning_performance(days: int = 7):
	"""
	학습 성능 메트릭 조회
	"""
	registration_logger.info(f"학습 성능 메트릭 요청: {days}일")

	try:
		learning_pipeline = await get_learning_pipeline()
		metrics = await learning_pipeline.get_performance_metrics(days)

		return {
			"performance_metrics": metrics,
			"days": days,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"성능 메트릭 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"성능 메트릭 조회 실패: {str(e)}"
		)


@router.get("/monitoring/request-stats")
async def get_request_stats(hours: int = 24):
	"""
	요청 통계 조회
	"""
	registration_logger.info(f"요청 통계 조회: {hours}시간")

	try:
		monitor = await get_performance_monitor()
		stats = await monitor.get_request_stats(hours)

		return {
			"request_stats": stats,
			"hours": hours,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"요청 통계 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"요청 통계 조회 실패: {str(e)}"
		)


@router.get("/monitoring/system-stats")
async def get_system_stats(hours: int = 24):
	"""
	시스템 통계 조회
	"""
	registration_logger.info(f"시스템 통계 조회: {hours}시간")

	try:
		monitor = await get_performance_monitor()
		stats = await monitor.get_system_stats(hours)

		return {
			"system_stats": stats,
			"hours": hours,
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"시스템 통계 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"시스템 통계 조회 실패: {str(e)}"
		)


@router.get("/monitoring/alerts")
async def get_performance_alerts(hours: int = 24, severity: str = None):
	"""
	성능 알림 조회
	"""
	registration_logger.info(f"성능 알림 조회: {hours}시간, severity={severity}")

	try:
		monitor = await get_performance_monitor()
		alerts = await monitor.get_alerts(hours, severity)

		return {
			"alerts": alerts,
			"hours": hours,
			"severity": severity,
			"count": len(alerts),
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"성능 알림 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"성능 알림 조회 실패: {str(e)}"
		)


@router.post("/ab-test/create")
async def create_ab_test(request: Dict[str, Any]):
	"""
	A/B 테스트 생성
	"""
	registration_logger.info("A/B 테스트 생성 요청")

	try:
		from app.services.ab_testing import ABTestConfig, TestVariant, TestStatus
		from datetime import datetime

		# 요청 데이터 검증
		config_data = request.get('config', {})
		variants_data = request.get('variants', [])

		if not config_data or not variants_data:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="config와 variants가 필요합니다"
			)

		# 테스트 설정 생성
		config = ABTestConfig(
			test_id=config_data['test_id'],
			name=config_data['name'],
			description=config_data['description'],
			status=TestStatus.DRAFT,
			traffic_split=config_data['traffic_split'],
			start_date=datetime.fromisoformat(config_data['start_date']),
			end_date=datetime.fromisoformat(config_data['end_date']),
			success_metric=config_data['success_metric'],
			minimum_sample_size=config_data['minimum_sample_size'],
			confidence_level=config_data['confidence_level'],
			created_by=config_data.get('created_by', 'system'),
			created_at=datetime.utcnow(),
			updated_at=datetime.utcnow()
		)

		# 테스트 변형 생성
		variants = [TestVariant(**variant_data) for variant_data in variants_data]

		# A/B 테스트 생성
		ab_framework = await get_ab_testing_framework()
		success = await ab_framework.create_test(config, variants)

		if success:
			return {
				"message": "A/B 테스트가 성공적으로 생성되었습니다",
				"test_id": config.test_id,
				"status": "success"
			}
		else:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="A/B 테스트 생성에 실패했습니다"
			)

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"A/B 테스트 생성 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"A/B 테스트 생성 실패: {str(e)}"
		)


@router.get("/ab-test/{test_id}/status")
async def get_ab_test_status(test_id: str):
	"""
	A/B 테스트 상태 조회
	"""
	registration_logger.info(f"A/B 테스트 상태 조회: {test_id}")

	try:
		ab_framework = await get_ab_testing_framework()
		test_status = await ab_framework.get_test_status(test_id)

		if test_status:
			return {
				"test_status": test_status,
				"status": "success"
			}
		else:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail=f"테스트를 찾을 수 없습니다: {test_id}"
			)

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"A/B 테스트 상태 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"A/B 테스트 상태 조회 실패: {str(e)}"
		)


@router.post("/ab-test/{test_id}/conversion")
async def record_ab_test_conversion(test_id: str, request: Dict[str, Any]):
	"""
	A/B 테스트 전환 이벤트 기록
	"""
	registration_logger.info(f"A/B 테스트 전환 기록: {test_id}")

	try:
		user_id = request.get('user_id')
		conversion_data = request.get('conversion_data', {})

		if not user_id:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="user_id가 필요합니다"
			)

		ab_framework = await get_ab_testing_framework()
		success = await ab_framework.record_conversion(test_id, user_id, conversion_data)

		if success:
			return {
				"message": "전환 이벤트가 기록되었습니다",
				"test_id": test_id,
				"user_id": user_id,
				"status": "success"
			}
		else:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="전환 이벤트 기록에 실패했습니다"
			)

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"A/B 테스트 전환 기록 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"전환 이벤트 기록 실패: {str(e)}"
		)


# ==================== GPU OCR API 엔드포인트 ====================

@router.post("/gpu-ocr/batch")
async def process_batch_gpu_ocr(files: List[UploadFile] = File(...)):
	"""
	GPU 최적화 배치 OCR 처리
	"""
	registration_logger.info(f"GPU 배치 OCR 요청 수신: {len(files)}개 파일")

	try:
		# GPU 환경 확인
		gpu_manager = await get_gpu_manager()
		if not gpu_manager.is_gpu_available():
			registration_logger.warning("GPU를 사용할 수 없어 CPU로 처리합니다")

		# 이미지 파일 검증
		image_data = []
		for file in files:
			if not file.content_type.startswith("image/"):
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=f"잘못된 파일 형식: {file.filename}"
				)

			data = await file.read()
			image_data.append({
				"filename": file.filename,
				"data": data,
				"content_type": file.content_type
			})

		# 배치 OCR 엔진으로 처리
		batch_engine = await get_batch_ocr_engine()

		# BatchOCRRequest 생성
		batch_request = BatchOCRRequest(
			images=image_data,
			use_gpu=gpu_manager.is_gpu_available(),
			batch_size=await gpu_manager.get_optimal_batch_size() if gpu_manager.is_gpu_available() else 4
		)

		# 배치 처리 실행
		results = await batch_engine.process_batch(batch_request)

		registration_logger.info(f"GPU 배치 OCR 처리 완료: {len(results.results)}개 결과")

		return {
			"message": "GPU 배치 OCR 처리가 완료되었습니다",
			"total_images": len(files),
			"processed_images": len(results.results),
			"processing_time": results.processing_time,
			"gpu_used": results.gpu_used,
			"results": [
				{
					"filename": result.filename,
					"text": result.text,
					"confidence": result.confidence,
					"processing_time": result.processing_time,
					"bounding_boxes": result.bounding_boxes
				}
				for result in results.results
			],
			"performance_stats": {
				"total_time": results.processing_time,
				"average_time_per_image": results.processing_time / len(results.results) if results.results else 0,
				"gpu_memory_used": results.gpu_memory_used,
				"cpu_usage": results.cpu_usage
			},
			"status": "success"
		}

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"GPU 배치 OCR 처리 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"GPU 배치 OCR 처리 실패: {str(e)}"
		)


@router.get("/gpu-ocr/stats")
async def get_gpu_ocr_stats():
	"""
	GPU OCR 시스템 통계 조회
	"""
	registration_logger.info("GPU OCR 통계 요청 수신")

	try:
		gpu_manager = await get_gpu_manager()
		batch_engine = await get_batch_ocr_engine()

		# GPU 상태 정보
		gpu_stats = await gpu_manager.get_gpu_stats()

		# 배치 엔진 통계
		engine_stats = await batch_engine.get_performance_stats()

		return {
			"gpu_info": {
				"available": gpu_manager.is_gpu_available(),
				"device_count": gpu_stats.get("device_count", 0),
				"current_device": gpu_stats.get("current_device", "cpu"),
				"memory_info": gpu_stats.get("memory_info", {}),
				"utilization": gpu_stats.get("utilization", {})
			},
			"performance_stats": {
				"total_processed": engine_stats.get("total_processed", 0),
				"average_processing_time": engine_stats.get("average_processing_time", 0),
				"gpu_acceleration_ratio": engine_stats.get("gpu_acceleration_ratio", 1.0),
				"memory_efficiency": engine_stats.get("memory_efficiency", 0),
				"error_rate": engine_stats.get("error_rate", 0)
			},
			"system_health": {
				"status": "healthy" if gpu_stats.get("healthy", True) else "warning",
				"last_updated": datetime.utcnow().isoformat(),
				"uptime": gpu_stats.get("uptime", 0)
			},
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"GPU OCR 통계 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"GPU OCR 통계 조회 실패: {str(e)}"
		)


@router.get("/gpu-ocr/scheduler/status")
async def get_scheduler_status():
	"""
	OCR 스케줄러 상태 조회
	"""
	registration_logger.info("OCR 스케줄러 상태 요청 수신")

	try:
		scheduler = await get_ocr_scheduler()
		status_info = await scheduler.get_status()

		return {
			"scheduler_status": status_info,
			"queue_info": {
				"pending_jobs": status_info.get("pending_jobs", 0),
				"running_jobs": status_info.get("running_jobs", 0),
				"completed_jobs": status_info.get("completed_jobs", 0),
				"failed_jobs": status_info.get("failed_jobs", 0)
			},
			"resource_usage": {
				"gpu_utilization": status_info.get("gpu_utilization", 0),
				"memory_usage": status_info.get("memory_usage", 0),
				"cpu_usage": status_info.get("cpu_usage", 0)
			},
			"performance_metrics": {
				"average_job_time": status_info.get("average_job_time", 0),
				"throughput": status_info.get("throughput", 0),
				"success_rate": status_info.get("success_rate", 100)
			},
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"스케줄러 상태 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"스케줄러 상태 조회 실패: {str(e)}"
		)


@router.post("/gpu-ocr/scheduler/job")
async def submit_ocr_job(request: Dict[str, Any]):
	"""
	OCR 작업 스케줄러에 작업 제출
	"""
	registration_logger.info("OCR 작업 제출 요청 수신")

	try:
		# 요청 데이터 검증
		images = request.get('images', [])
		priority = request.get('priority', 'normal')
		options = request.get('options', {})

		if not images:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="처리할 이미지가 없습니다"
			)

		# OCR 작업 요청 생성
		job_request = OCRJobRequest(
			images=images,
			priority=priority,
			options=options,
			submitted_at=datetime.utcnow()
		)

		# 스케줄러에 작업 제출
		scheduler = await get_ocr_scheduler()
		job_id = await scheduler.submit_job(job_request)

		registration_logger.info(f"OCR 작업 제출 완료: {job_id}")

		return {
			"message": "OCR 작업이 성공적으로 제출되었습니다",
			"job_id": job_id,
			"estimated_completion_time": await scheduler.estimate_completion_time(job_id),
			"queue_position": await scheduler.get_queue_position(job_id),
			"status": "success"
		}

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"OCR 작업 제출 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"OCR 작업 제출 실패: {str(e)}"
		)


@router.get("/gpu-ocr/scheduler/job/{job_id}")
async def get_job_status(job_id: str):
	"""
	OCR 작업 상태 조회
	"""
	registration_logger.info(f"OCR 작업 상태 조회: {job_id}")

	try:
		scheduler = await get_ocr_scheduler()
		job_status = await scheduler.get_job_status(job_id)

		if not job_status:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail=f"작업을 찾을 수 없습니다: {job_id}"
			)

		return {
			"job_id": job_id,
			"status": job_status.get("status", "unknown"),
			"progress": job_status.get("progress", 0),
			"created_at": job_status.get("created_at"),
			"started_at": job_status.get("started_at"),
			"completed_at": job_status.get("completed_at"),
			"processing_time": job_status.get("processing_time", 0),
			"results": job_status.get("results", []),
			"error_message": job_status.get("error_message"),
			"queue_position": job_status.get("queue_position", 0),
			"estimated_completion": job_status.get("estimated_completion"),
			"resource_usage": job_status.get("resource_usage", {}),
			"status": "success"
		}

	except HTTPException:
		raise
	except Exception as e:
		registration_logger.error(f"OCR 작업 상태 조회 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"OCR 작업 상태 조회 실패: {str(e)}"
		)


@router.post("/services/reset")
async def reset_services():
	"""
	서비스 강제 리셋 (개발/디버깅용)
	"""
	registration_logger.info("서비스 강제 리셋 요청 수신")

	try:
		global asset_matcher, confidence_evaluator, fuzzy_matcher

		# 모든 서비스를 None으로 설정
		asset_matcher = None
		confidence_evaluator = None
		fuzzy_matcher = None

		registration_logger.info("모든 서비스가 리셋되었습니다")

		return {
			"message": "모든 서비스가 성공적으로 리셋되었습니다",
			"status": "success"
		}

	except Exception as e:
		registration_logger.error(f"서비스 리셋 중 오류 발생: {str(e)}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"서비스 리셋 실패: {str(e)}"
		)


@router.get("/workflow")
async def get_workflow():
	registration_logger.info("워크플로우 정보 요청 수신")
	workflow = [
		{"step": 1, "name": "upload", "description": "이미지 업로드"},
		{"step": 2, "name": "segment", "description": "세그멘테이션 수행"},
		{"step": 3, "name": "ocr", "description": "OCR 수행"},
		{"step": 4, "name": "chatbot-assist", "description": "챗봇 지원"},
		{"step": 5, "name": "register", "description": "자산 등록"},
		{"step": 6, "name": "generate_label", "description": "라벨 생성"},
	]
	registration_logger.debug(f"워크플로우 단계 수: {len(workflow)}")
	return workflow
