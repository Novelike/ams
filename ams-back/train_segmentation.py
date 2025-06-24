#!/usr/bin/env python3
# train_segmentation.py

import os
from pathlib import Path
import torch
import yaml
from ultralytics import YOLO


def main():
	# 기본 설정
	data_yaml = Path("data/asset_labels.yaml")
	model_ckpt = Path("models/yolov8n-seg.pt")
	epochs = 100
	batch_size = 8
	img_size = 640
	project_dir = Path("runs/train")
	exp_name = "asset_seg_experiment"
	workers = 2

	# 경로 검증
	if not data_yaml.is_file():
		raise FileNotFoundError(f"Dataset YAML not found: {data_yaml.resolve()}")
	if not model_ckpt.is_file():
		raise FileNotFoundError(f"YOLOv8 model checkpoint not found: {model_ckpt.resolve()}")

	save_dir = (project_dir / exp_name).resolve()
	save_dir.mkdir(parents=True, exist_ok=True)

	# 디바이스 결정
	device = "cuda" if torch.cuda.is_available() else "cpu"
	if device == "cpu":
		print("⚠️  CUDA GPU가 감지되지 않아 CPU로 학습을 진행합니다.")

	# YAML을 UTF-8로 읽어 파싱
	cfg = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
	# val/images 경로 확인
	val_images = Path(cfg["val"])
	val_images = (data_yaml.parent / val_images).resolve()
	do_val = val_images.is_dir() and any(val_images.iterdir())
	if not do_val:
		print(f"⚠️  검증 이미지가 없음({val_images}), 검증 단계를 생략합니다.")

	# 설정 출력
	print("\n🛰️  YOLOv8 Segmentation 학습 시작")
	print(f" • 데이터셋 YAML  : {data_yaml.resolve()}")
	print(f" • 체크포인트    : {model_ckpt.resolve()}")
	print(f" • 에폭(epochs)  : {epochs}")
	print(f" • 배치크기(batch): {batch_size}")
	print(f" • 이미지 크기   : {img_size}")
	print(f" • 저장 경로     : {save_dir}")
	print(f" • 디바이스      : {device}")
	print(f" • 워커(worker)  : {workers}")
	print(f" • Validation    : {'ON' if do_val else 'OFF'}\n")

	# 모델 로드
	model = YOLO(str(model_ckpt))

	# 학습 실행
	model.train(
		data=str(data_yaml),
		epochs=epochs,
		batch=batch_size,
		imgsz=img_size,
		project=str(project_dir),
		name=exp_name,
		device=device,
		workers=workers,
		save=True,
		cache=True,
		val=do_val
	)


if __name__ == "__main__":
	main()
