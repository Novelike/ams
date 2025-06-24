#!/usr/bin/env python3
"""
OCR 진행 상황 기능 테스트 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelike.ocr import ocr_easy_with_progress


async def test_progress_callback(stage: str, message: str, progress: float):
    """테스트용 진행 상황 콜백 함수"""
    print(f"[{progress:5.1f}%] {stage}: {message}")


async def test_ocr_progress():
    """OCR 진행 상황 기능 테스트"""
    print("=== OCR 진행 상황 기능 테스트 시작 ===")
    
    # 테스트 이미지 경로 (기존 테스트 이미지 사용)
    test_image_path = project_root / "datasets" / "asset" / "train" / "images" / "test1.jpg"
    
    if not test_image_path.exists():
        print(f"❌ 테스트 이미지를 찾을 수 없습니다: {test_image_path}")
        print("테스트 이미지를 업로드하거나 다른 이미지 경로를 사용하세요.")
        return
    
    print(f"📁 테스트 이미지: {test_image_path}")
    
    try:
        # 이미지 파일 읽기
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        
        print(f"📄 이미지 크기: {len(image_bytes)} 바이트")
        print("\n🔄 OCR 진행 상황 테스트 시작...")
        
        # 진행 상황 콜백과 함께 OCR 실행
        results = await ocr_easy_with_progress(image_bytes, test_progress_callback)
        
        print(f"\n✅ OCR 완료! 감지된 텍스트 영역 수: {len(results)}")
        
        # 결과 출력
        for i, (bbox, text, confidence) in enumerate(results):
            print(f"  {i+1}. '{text}' (신뢰도: {confidence:.2f})")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ocr_progress())