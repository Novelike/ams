# novelike/ocr.py
from io import BytesIO

import easyocr
from PIL import Image
from transformers import VisionEncoderDecoderModel, TrOCRProcessor

# 로깅 설정
from app.utils.logging import ocr_logger

# EasyOCR reader 한 번만 초기화
ocr_logger.info("EasyOCR 리더 초기화 중...")
_reader = easyocr.Reader(['ko', 'en'], gpu=False)
ocr_logger.info("EasyOCR 리더 초기화 완료")


def ocr_easy(image_bytes: bytes):
	"""
	이미지에서 영역별(단어/라인)로 나눠서 텍스트+신뢰도 리턴
	"""
	ocr_logger.info("EasyOCR 텍스트 인식 시작")
	ocr_logger.debug(f"이미지 크기: {len(image_bytes)} 바이트")

	try:
		# detail=1 => [ [bbox, text, conf], ... ]
		results = _reader.readtext(image_bytes, detail=1, paragraph=False)

		ocr_logger.info(f"EasyOCR 텍스트 인식 완료: {len(results)}개 텍스트 영역 감지")
		for idx, (bbox, text, conf) in enumerate(results):
			ocr_logger.debug(f"텍스트 영역 {idx+1}: '{text}' (신뢰도: {conf:.2f})")

		return results
	except Exception as e:
		ocr_logger.error(f"EasyOCR 텍스트 인식 중 오류 발생: {str(e)}")
		raise


async def ocr_easy_with_progress(image_bytes: bytes, progress_callback=None):
	"""
	EasyOCR을 단계별로 실행하여 진행 상황을 전달하는 함수
	"""
	import asyncio

	ocr_logger.info("EasyOCR 단계별 텍스트 인식 시작")
	ocr_logger.debug(f"이미지 크기: {len(image_bytes)} 바이트")

	try:
		# 1단계: 이미지 전처리
		if progress_callback:
			await progress_callback("preprocessing", "이미지 전처리 중...", 10)

		ocr_logger.debug("이미지 전처리 중...")
		img = Image.open(BytesIO(image_bytes)).convert("RGB")
		ocr_logger.debug(f"이미지 크기: {img.width}x{img.height} 픽셀")

		# 단계별 진행을 체감할 수 있도록 약간의 지연 추가
		await asyncio.sleep(1.0)

		# 2단계: 텍스트 영역 감지 시작
		if progress_callback:
			await progress_callback("detection", "텍스트 영역 감지 중...", 30)

		ocr_logger.debug("텍스트 영역 감지 중...")
		await asyncio.sleep(1.0)

		# 3단계: 텍스트 인식 시작
		if progress_callback:
			await progress_callback("recognition", "텍스트 인식 중...", 60)

		ocr_logger.debug("텍스트 인식 중...")
		# EasyOCR의 실제 처리 (감지와 인식을 함께 수행)
		results = _reader.readtext(image_bytes, detail=1, paragraph=False)

		# 4단계: 후처리
		if progress_callback:
			await progress_callback("postprocessing", "결과 후처리 중...", 90)

		ocr_logger.debug("결과 후처리 중...")
		await asyncio.sleep(0.5)

		# 결과 로깅
		ocr_logger.info(f"EasyOCR 단계별 텍스트 인식 완료: {len(results)}개 텍스트 영역 감지")
		for idx, (bbox, text, conf) in enumerate(results):
			ocr_logger.debug(f"텍스트 영역 {idx+1}: '{text}' (신뢰도: {conf:.2f})")

		# 완료
		if progress_callback:
			await progress_callback("completed", "OCR 처리 완료", 100)

		return results

	except Exception as e:
		ocr_logger.error(f"EasyOCR 단계별 텍스트 인식 중 오류 발생: {str(e)}")
		if progress_callback:
			await progress_callback("error", f"OCR 오류: {str(e)}", 0)
		raise


# TrOCR processor/model 초기화 (printed 모델 예시)
ocr_logger.info("TrOCR 모델 초기화 중...")
_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
ocr_logger.info("TrOCR 모델 초기화 완료")


def ocr_trocr_full(image_bytes: bytes) -> str:
	"""
	TrOCR 전체 문장 OCR. post-processing 추가 예시 포함.
	"""
	ocr_logger.info("TrOCR 전체 문장 인식 시작")
	ocr_logger.debug(f"이미지 크기: {len(image_bytes)} 바이트")

	try:
		ocr_logger.debug("이미지 로드 및 전처리 중...")
		img = Image.open(BytesIO(image_bytes)).convert("RGB")
		ocr_logger.debug(f"이미지 크기: {img.width}x{img.height} 픽셀")

		ocr_logger.debug("TrOCR 프로세서로 이미지 인코딩 중...")
		pixel_values = _processor(images=img, return_tensors="pt").pixel_values

		ocr_logger.debug(f"TrOCR 모델로 텍스트 생성 중... (디바이스: {_model.device})")
		# GPU가 없으면 cpu 로
		output_ids = _model.generate(pixel_values.to(_model.device))

		ocr_logger.debug("생성된 텍스트 디코딩 중...")
		text = _processor.batch_decode(output_ids, skip_special_tokens=True)[0]
		result = text.strip()

		ocr_logger.info(f"TrOCR 텍스트 인식 완료: '{result}'")
		return result
	except Exception as e:
		ocr_logger.error(f"TrOCR 텍스트 인식 중 오류 발생: {str(e)}")
		raise
