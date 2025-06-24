# novelike/seg.py

from ultralytics import YOLO
import os

# 로깅 설정
from app.utils.logging import seg_logger

# YOLOv8 세그멘테이션 학습된 체크포인트 경로
modelPath = "models/yolov8n-seg.pt"

# YOLO 모델 로드
seg_logger.info(f"YOLOv8 세그멘테이션 모델 초기화 중... (모델 경로: {modelPath})")
_model = YOLO(modelPath)
seg_logger.info("YOLOv8 세그멘테이션 모델 초기화 완료")

def segment_image(image_path: str, conf: float = 0.25):
	"""
	이미지 파일 경로를 받아 YOLOv8 세그멘테이션 수행
	"""
	seg_logger.info(f"이미지 세그멘테이션 시작: {os.path.basename(image_path)}")
	seg_logger.debug(f"전체 이미지 경로: {image_path}")
	seg_logger.debug(f"신뢰도 임계값: {conf}")

	try:
		# 이미지 존재 확인
		if not os.path.exists(image_path):
			seg_logger.error(f"이미지 파일을 찾을 수 없음: {image_path}")
			raise FileNotFoundError(f"이미지 파일을 찾을 수 없음: {image_path}")

		seg_logger.debug("YOLOv8 세그멘테이션 모델 예측 실행 중...")
		results = _model.predict(source=image_path,
		                         task="segment",
		                         conf=conf)

		# 결과 로깅
		if hasattr(results, '__len__'):
			seg_logger.info(f"세그멘테이션 완료: {len(results)}개 결과 생성")

			# 각 결과에 대한 상세 정보 로깅
			for i, result in enumerate(results):
				if hasattr(result, 'boxes') and result.boxes is not None:
					boxes_count = len(result.boxes)
					seg_logger.debug(f"결과 {i+1}: {boxes_count}개 객체 감지됨")

					# 클래스별 객체 수 계산
					if hasattr(result.boxes, 'cls') and result.boxes.cls is not None:
						classes = result.boxes.cls.tolist()
						class_counts = {}
						for cls in classes:
							cls_name = result.names[int(cls)] if hasattr(result, 'names') else f"클래스 {int(cls)}"
							class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

						for cls_name, count in class_counts.items():
							seg_logger.debug(f"  - {cls_name}: {count}개")

				if hasattr(result, 'masks') and result.masks is not None:
					seg_logger.debug(f"  - 마스크 정보 포함됨")
		else:
			seg_logger.info("세그멘테이션 완료: 결과 객체 생성됨")

		# results.masks 에서 마스크 정보 확인 가능
		return results
	except Exception as e:
		seg_logger.error(f"세그멘테이션 중 오류 발생: {str(e)}")
		raise
