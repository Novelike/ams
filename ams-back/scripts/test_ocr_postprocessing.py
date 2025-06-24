#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR 텍스트 후처리 기능 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.registration import post_process_ocr_text, categorize_from_title, clean_content

def test_text_processing():
    """텍스트 후처리 함수 테스트"""
    print("=== OCR 텍스트 후처리 기능 테스트 ===\n")

    # 테스트 케이스들
    test_cases = [
        {
            "input": "모델명: 15U50R",
            "expected_category": "model",
            "expected_value": "15U50R",
            "description": "기본 콜론 패턴"
        },
        {
            "input": "제조사: 엘지",
            "expected_category": "manufacturer", 
            "expected_value": "엘지",
            "description": "제조사 콜론 패턴"
        },
        {
            "input": "모델명: 기자재의 명칭제품명칭 (모델명)",
            "expected_category": "model",
            "expected_value": "명칭제품명칭",
            "description": "복잡한 모델명 패턴"
        },
        {
            "input": "제조사: 상호명제조업체명",
            "expected_category": "manufacturer",
            "expected_value": "제조업체명",
            "description": "복잡한 제조사 패턴"
        },
        {
            "input": "시리얼번호: PC123456",
            "expected_category": "serial",
            "expected_value": "PC123456",
            "description": "시리얼번호 패턴"
        },
        {
            "input": "정격전압: 220V",
            "expected_category": "spec",
            "expected_value": "220V",
            "description": "스펙 정보 패턴"
        },
        {
            "input": "모델명 ThinkPad X1",
            "expected_category": "model",
            "expected_value": "ThinkPad X1",
            "description": "공백 구분 패턴"
        },
        {
            "input": "일반 텍스트",
            "expected_category": "other",
            "expected_value": "일반 텍스트",
            "description": "일반 텍스트"
        }
    ]

    success_count = 0
    total_count = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['description']}")
        print(f"   입력: '{test_case['input']}'")

        try:
            result = post_process_ocr_text(test_case['input'])

            print(f"   결과: 카테고리='{result['category']}', 값='{result['value']}', 신뢰도={result['confidence']}")

            # 검증
            category_match = result['category'] == test_case['expected_category']
            value_match = result['value'] == test_case['expected_value']

            if category_match and value_match:
                print(f"   ✅ 성공")
                success_count += 1
            else:
                print(f"   ❌ 실패")
                if not category_match:
                    print(f"      카테고리 불일치: 예상='{test_case['expected_category']}', 실제='{result['category']}'")
                if not value_match:
                    print(f"      값 불일치: 예상='{test_case['expected_value']}', 실제='{result['value']}'")

        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")

        print()

    print(f"=== 테스트 결과: {success_count}/{total_count} 성공 ===")
    return success_count == total_count

def test_individual_functions():
    """개별 함수들 테스트"""
    print("\n=== 개별 함수 테스트 ===\n")

    # categorize_from_title 테스트
    print("1. categorize_from_title 함수 테스트")
    title_tests = [
        ("모델명", "model"),
        ("제조사", "manufacturer"),
        ("시리얼번호", "serial"),
        ("정격전압", "spec"),
        ("기타", "other")
    ]

    for title, expected in title_tests:
        result = categorize_from_title(title)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{title}' -> '{result}' (예상: '{expected}')")

    # clean_content 테스트
    print("\n2. clean_content 함수 테스트")
    content_tests = [
        ("기자재의 명칭제품명칭 (모델명)", "명칭제품명칭"),
        ("상호명제조업체명", "제조업체명"),
        ("제조자 삼성전자", "삼성전자"),
        ("일반 텍스트", "일반 텍스트"),
        ("(괄호) 제거 [대괄호] 테스트", "제거 테스트")
    ]

    for content, expected in content_tests:
        result = clean_content(content)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{content}' -> '{result}' (예상: '{expected}')")

if __name__ == "__main__":
    print("🚀 OCR 텍스트 후처리 기능 테스트 시작\n")

    # 메인 테스트 실행
    main_success = test_text_processing()

    # 개별 함수 테스트
    test_individual_functions()

    print(f"\n🎉 테스트 완료! 메인 테스트 {'성공' if main_success else '실패'}")
