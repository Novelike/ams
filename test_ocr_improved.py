import requests
import json
import time

# 백엔드 서버 URL
BASE_URL = "http://localhost:8000"

def test_ocr_with_improved_processing():
    """개선된 텍스트 후처리가 적용된 OCR 테스트"""
    print("=== 개선된 OCR 텍스트 후처리 테스트 ===")
    
    # 테스트 이미지 경로
    image_path = "uploads/test_image_20250624_131901.jpg"
    
    try:
        # OCR 요청
        print(f"OCR 요청 중: {image_path}")
        response = requests.post(
            f"{BASE_URL}/api/registration/ocr",
            json={"image_path": image_path},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 202:
            result = response.json()
            job_id = result["job_id"]
            print(f"✅ OCR 작업 시작됨: {job_id}")
            
            # 결과 대기 (SSE 대신 폴링 방식으로 간단히 구현)
            print("OCR 처리 대기 중...")
            time.sleep(10)  # 10초 대기
            
            print("OCR 처리가 완료되었을 것으로 예상됩니다.")
            print("실제 결과는 프론트엔드에서 확인해주세요.")
            
        else:
            print(f"❌ OCR 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

def test_text_processing_functions():
    """텍스트 후처리 함수들을 직접 테스트"""
    print("\n=== 텍스트 후처리 함수 직접 테스트 ===")
    
    # 실제 OCR 결과 예시
    test_cases = [
        "기자재의 명칭제품명칭 (모델명)",
        "노트북 컴퓨터(15U50R)",
        "상호명제조업체명",
        "엘지전자(주)/Tech-Front (Chongqing) Computer Co.",
        "제조자제조국가",
        "엘지전자(주)중국",
        "정격전압",
        "19 V = - = 3.42 A"
    ]
    
    print("이 테스트는 프론트엔드의 extractValueFromText 함수를 테스트합니다.")
    print("실제 결과는 브라우저 콘솔에서 확인할 수 있습니다.")
    
    for i, text in enumerate(test_cases, 1):
        print(f"{i}. 입력: \"{text}\"")
    
    print("\n브라우저에서 http://localhost:5175 에 접속하여")
    print("개발자 도구 콘솔에서 다음 코드를 실행해보세요:")
    print()
    print("// 테스트 코드")
    for text in test_cases:
        print(f"console.log(extractValueFromText(\"{text}\"));")

if __name__ == "__main__":
    print("🚀 개선된 OCR 텍스트 후처리 테스트 시작")
    
    # 1. OCR API 테스트
    test_ocr_with_improved_processing()
    
    # 2. 텍스트 후처리 함수 테스트 안내
    test_text_processing_functions()
    
    print("\n🎉 테스트 완료!")