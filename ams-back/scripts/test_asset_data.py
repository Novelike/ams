import requests
import json
from datetime import datetime

# 백엔드 서버 URL
BASE_URL = "http://localhost:8000"

# 테스트용 자산 데이터
test_assets = [
    {
        "model_name": "ThinkPad X1 Carbon",
        "detailed_model": "X1 Carbon Gen 9",
        "serial_number": "PC123456",
        "manufacturer": "Lenovo",
        "site": "서울본사",
        "asset_type": "laptop",
        "user": "홍길동",
        "specs": {
            "cpu": "Intel i7-1165G7",
            "memory": "16GB LPDDR4X",
            "storage": "512GB SSD",
            "display": "14인치 WQHD"
        },
        "ocr_results": {
            "model": "ThinkPad X1 Carbon",
            "serial": "PC123456",
            "manufacturer": "Lenovo"
        }
    },
    {
        "model_name": "Dell XPS 15",
        "detailed_model": "XPS 15 9520",
        "serial_number": "DL789012",
        "manufacturer": "Dell",
        "site": "부산지사",
        "asset_type": "laptop",
        "user": "김철수",
        "specs": {
            "cpu": "Intel i7-12700H",
            "memory": "32GB DDR5",
            "storage": "1TB SSD",
            "display": "15.6인치 4K OLED"
        },
        "ocr_results": {
            "model": "Dell XPS 15",
            "serial": "DL789012",
            "manufacturer": "Dell"
        }
    },
    {
        "model_name": "MacBook Pro",
        "detailed_model": "MacBook Pro 14-inch",
        "serial_number": "AP345678",
        "manufacturer": "Apple",
        "site": "대구지사",
        "asset_type": "laptop",
        "user": "이영희",
        "specs": {
            "cpu": "Apple M2 Pro",
            "memory": "16GB Unified Memory",
            "storage": "512GB SSD",
            "display": "14.2인치 Liquid Retina XDR"
        },
        "ocr_results": {
            "model": "MacBook Pro",
            "serial": "AP345678",
            "manufacturer": "Apple"
        }
    },
    {
        "model_name": "LG UltraWide Monitor",
        "detailed_model": "34WP65C-B",
        "serial_number": "LG901234",
        "manufacturer": "LG",
        "site": "서울본사",
        "asset_type": "monitor",
        "user": "박지민",
        "specs": {
            "size": "34인치",
            "resolution": "3440x1440",
            "panel": "IPS",
            "refresh_rate": "75Hz"
        },
        "ocr_results": {
            "model": "34WP65C-B",
            "serial": "LG901234",
            "manufacturer": "LG"
        }
    },
    {
        "model_name": "Magic Keyboard",
        "detailed_model": "Magic Keyboard with Touch ID",
        "serial_number": "KB567890",
        "manufacturer": "Apple",
        "site": "광주지사",
        "asset_type": "keyboard",
        "user": "최민수",
        "specs": {
            "type": "무선 키보드",
            "layout": "한국어",
            "connectivity": "Bluetooth",
            "features": "Touch ID"
        },
        "ocr_results": {
            "model": "Magic Keyboard",
            "serial": "KB567890",
            "manufacturer": "Apple"
        }
    }
]

def test_save_asset_data():
    """자산 데이터 저장 API 테스트"""
    print("=== 자산 데이터 저장 API 테스트 시작 ===")

    for i, asset_data in enumerate(test_assets, 1):
        print(f"\n{i}. {asset_data['model_name']} 저장 중...")

        try:
            response = requests.post(
                f"{BASE_URL}/api/registration/save-asset-data",
                json=asset_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 성공: {result['message']}")
                print(f"   📄 자산번호: {result['asset_number']}")
                print(f"   📁 CSV 경로: {result['csv_path']}")
                print(f"   📄 JSON 경로: {result['json_path']}")
            else:
                print(f"   ❌ 실패: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")

def test_get_assets_list():
    """자산 목록 조회 API 테스트"""
    print("\n=== 자산 목록 조회 API 테스트 시작 ===")

    try:
        # 전체 목록 조회
        response = requests.get(f"{BASE_URL}/api/registration/assets/list")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 전체 목록 조회 성공")
            print(f"   📊 총 자산 수: {result['total']}")
            print(f"   📄 현재 페이지: {result['page']}")
            print(f"   📄 페이지 크기: {result['page_size']}")
            print(f"   📄 총 페이지: {result['total_pages']}")

            if result['items']:
                print(f"   📋 첫 번째 자산: {result['items'][0]['asset_number']} - {result['items'][0]['model_name']}")
        else:
            print(f"❌ 실패: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

    # 검색 테스트
    print("\n--- 검색 테스트 ---")
    try:
        response = requests.get(
            f"{BASE_URL}/api/registration/assets/list",
            params={"search": "ThinkPad", "page_size": 5}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 'ThinkPad' 검색 성공: {result['total']}개 결과")
        else:
            print(f"❌ 검색 실패: {response.status_code}")

    except Exception as e:
        print(f"❌ 검색 오류: {str(e)}")

def test_get_asset_detail():
    """자산 상세 정보 조회 API 테스트"""
    print("\n=== 자산 상세 정보 조회 API 테스트 시작 ===")

    try:
        # 먼저 목록에서 자산 번호 가져오기
        list_response = requests.get(f"{BASE_URL}/api/registration/assets/list")

        if list_response.status_code == 200:
            assets = list_response.json()['items']
            if assets:
                asset_number = assets[0]['asset_number']
                print(f"테스트 대상 자산: {asset_number}")

                # 상세 정보 조회
                detail_response = requests.get(f"{BASE_URL}/api/registration/assets/{asset_number}")

                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    print(f"✅ 상세 정보 조회 성공")
                    print(f"   📄 기본 정보: {detail.get('basic_info', {}).get('model_name', 'N/A')}")
                    print(f"   🔧 스펙 정보: {'있음' if detail.get('specs') else '없음'}")
                    print(f"   👁️ OCR 결과: {'있음' if detail.get('ocr_results') else '없음'}")
                else:
                    print(f"❌ 상세 정보 조회 실패: {detail_response.status_code}")
            else:
                print("❌ 조회할 자산이 없습니다.")
        else:
            print(f"❌ 목록 조회 실패: {list_response.status_code}")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")

if __name__ == "__main__":
    print("🚀 자산 관리 시스템 API 테스트 시작")
    print(f"📡 서버 URL: {BASE_URL}")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 자산 데이터 저장 테스트
    test_save_asset_data()

    # 2. 자산 목록 조회 테스트
    test_get_assets_list()

    # 3. 자산 상세 정보 조회 테스트
    test_get_asset_detail()

    print("\n🎉 모든 테스트 완료!")
