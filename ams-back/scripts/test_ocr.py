# scripts/test_ocr.py

import sys
import time
from pathlib import Path
from io import BytesIO
# 프로젝트 루트를 import path에 추가 (필요하다면)
sys.path.append(str(Path(__file__).resolve().parent.parent))
from novelike.ocr import ocr_easy, ocr_trocr_full


def main():
	if len(sys.argv) != 2:
		print("Usage: python test_ocr.py <image_path>")
		sys.exit(1)

	img_path = Path(sys.argv[1])
	if not img_path.exists():
		print(f"File not found: {img_path}")
		sys.exit(1)

	image_bytes = img_path.read_bytes()

	# EasyOCR 테스트
	print("=== EasyOCR 결과 ===")
	start = time.time()
	easy_results = ocr_easy(image_bytes)
	duration = time.time() - start

	for i, res in enumerate(easy_results, 1):
		# res == [bbox, text, conf]
		if isinstance(res, (list, tuple)) and len(res) >= 3:
			text, conf = res[1], res[2]
		elif isinstance(res, dict):
			text, conf = res.get("text", ""), res.get("conf", 0.0)
		else:
			text, conf = str(res), 0.0
		print(f"{i}. \"{text}\"  (conf: {conf:.2f})")
	print(f"[EasyOCR 소요시간: {duration:.2f}s]\n")

	# TrOCR 테스트
	print("=== TrOCR 전체 텍스트 ===")
	start = time.time()
	full_text = ocr_trocr_full(image_bytes)
	duration = time.time() - start
	print(full_text)
	print(f"[TrOCR 소요시간: {duration:.2f}s]")



if __name__ == "__main__":
	main()
