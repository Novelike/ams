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

router = APIRouter(
	prefix="/api/registration",
	tags=["registration"],
	responses={404: {"description": "Not found"}},
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
