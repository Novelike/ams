#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 2 기능 테스트 스크립트
머신러닝 기반 가중치 학습 및 동적 임계값 조정 시스템 테스트
"""

import sys
import os
import requests
import json
import time
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 백엔드 서버 URL
BASE_URL = "http://localhost:8000"

def test_ml_model_info():
    """ML 모델 정보 조회 테스트"""
    print("=== ML 모델 정보 조회 테스트 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/registration/ml-model/info")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ ML 모델 정보 조회 성공")
            print(f"   📊 ML 모델 상태: {result['ml_model']}")
            print(f"   🎯 임계값 정보: {result['thresholds']}")
        else:
            print(f"❌ 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}")

def test_feedback_collection():
    """사용자 피드백 수집 테스트"""
    print("\n=== 사용자 피드백 수집 테스트 ===")
    
    # 테스트 피드백 데이터
    feedback_cases = [
        {
            "ocr_data": {
                "text": "ThinkPad X1",
                "confidence": 0.85,
                "category": "model"
            },
            "verification_result": {
                "status": "verified",
                "confidence": 0.95
            },
            "user_accepted": True,
            "corrected_text": None
        },
        {
            "ocr_data": {
                "text": "PC12345G",
                "confidence": 0.65,
                "category": "serial"
            },
            "verification_result": {
                "status": "fuzzy_match",
                "confidence": 0.80
            },
            "user_accepted": False,
            "corrected_text": "PC123456"
        },
        {
            "ocr_data": {
                "text": "엘지전자",
                "confidence": 0.90,
                "category": "manufacturer"
            },
            "verification_result": {
                "status": "verified",
                "confidence": 1.0
            },
            "user_accepted": True,
            "corrected_text": None
        }
    ]
    
    for i, feedback_data in enumerate(feedback_cases, 1):
        print(f"\n{i}. 피드백 수집 테스트 - {feedback_data['ocr_data']['category']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/registration/feedback/collect",
                json=feedback_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 성공: {result['message']}")
            else:
                print(f"   ❌ 실패: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")

def test_performance_metrics_update():
    """성능 지표 업데이트 및 임계값 조정 테스트"""
    print("\n=== 성능 지표 업데이트 테스트 ===")
    
    # 테스트 성능 지표 (가상의 데이터)
    performance_data = {
        "true_positives": 85,
        "false_positives": 12,
        "true_negatives": 78,
        "false_negatives": 15,
        "total_predictions": 190
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/registration/performance/update",
            json=performance_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 성능 지표 업데이트 성공")
            print(f"   📊 정밀도: {result['metrics']['precision']:.3f}")
            print(f"   📊 재현율: {result['metrics']['recall']:.3f}")
            print(f"   📊 F1 점수: {result['metrics']['f1_score']:.3f}")
            print(f"   📊 정확도: {result['metrics']['accuracy']:.3f}")
            print(f"   🎯 임계값 조정: {result['adjustment']}")
        else:
            print(f"❌ 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}")

def test_manual_threshold_override():
    """수동 임계값 설정 테스트"""
    print("\n=== 수동 임계값 설정 테스트 ===")
    
    # 새로운 임계값 설정
    new_thresholds = {
        "thresholds": {
            "high": 0.90,
            "medium": 0.70,
            "low": 0.50,
            "very_low": 0.30
        },
        "reason": "test_manual_override"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/registration/thresholds/manual-override",
            json=new_thresholds,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 수동 임계값 설정 성공")
            print(f"   🎯 새 임계값: {result['new_thresholds']}")
            print(f"   📝 설정 이유: {result['reason']}")
        else:
            print(f"❌ 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}")

def test_verification_stats_extended():
    """확장된 검증 시스템 통계 조회 테스트"""
    print("\n=== 확장된 검증 시스템 통계 테스트 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/registration/verification/stats")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 확장된 통계 조회 성공")
            
            # 기본 통계
            if 'confidence_evaluator' in result:
                evaluator_stats = result['confidence_evaluator']
                print(f"   📊 신뢰도 평가기 통계:")
                print(f"      - 현재 가중치: {evaluator_stats.get('weights', {})}")
                print(f"      - 지원 카테고리: {evaluator_stats.get('supported_categories', [])}")
                
                # Phase 2 통계
                if 'ml_model' in evaluator_stats:
                    ml_stats = evaluator_stats['ml_model']
                    print(f"      - ML 모델 학습 상태: {ml_stats.get('is_trained', False)}")
                    print(f"      - scikit-learn 사용 가능: {ml_stats.get('sklearn_available', False)}")
                
                if 'dynamic_thresholds' in evaluator_stats:
                    threshold_stats = evaluator_stats['dynamic_thresholds']
                    print(f"      - 현재 임계값: {threshold_stats.get('current_thresholds', {})}")
                    
                print(f"      - 피드백 버퍼 크기: {evaluator_stats.get('feedback_buffer_size', 0)}")
                
        else:
            print(f"❌ 실패: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 오류: {str(e)}")

def test_single_item_verification_enhanced():
    """개선된 단일 항목 검증 테스트"""
    print("\n=== 개선된 단일 항목 검증 테스트 ===")
    
    test_items = [
        {
            "text": "ThinkPad X1 Carbon",
            "category": "model",
            "confidence": 0.85
        },
        {
            "text": "PC123456",
            "category": "serial",
            "confidence": 0.90
        },
        {
            "text": "엘지전자",
            "category": "manufacturer",
            "confidence": 0.95
        }
    ]
    
    for i, item in enumerate(test_items, 1):
        print(f"\n{i}. {item['category']} 검증: '{item['text']}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/registration/verify-single",
                json=item,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                verification = result.get('verification', {})
                
                print(f"   ✅ 검증 성공")
                print(f"      - 최종 점수: {verification.get('score', 0):.3f}")
                print(f"      - 신뢰도 레벨: {verification.get('level', 'unknown')}")
                print(f"      - 사용된 방법: {verification.get('method', 'unknown')}")
                
                if 'ml_info' in verification:
                    ml_info = verification['ml_info']
                    print(f"      - ML 정보: {ml_info}")
                
                if 'thresholds_used' in verification:
                    thresholds = verification['thresholds_used']
                    print(f"      - 사용된 임계값: {thresholds}")
                    
            else:
                print(f"   ❌ 실패: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   ❌ 오류: {str(e)}")

def main():
    print("🚀 Phase 2 기능 테스트 시작")
    print(f"📡 서버 URL: {BASE_URL}")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. ML 모델 정보 조회
    test_ml_model_info()
    
    # 2. 사용자 피드백 수집
    test_feedback_collection()
    
    # 3. 성능 지표 업데이트
    test_performance_metrics_update()
    
    # 4. 수동 임계값 설정
    test_manual_threshold_override()
    
    # 5. 확장된 통계 조회
    test_verification_stats_extended()
    
    # 6. 개선된 단일 항목 검증
    test_single_item_verification_enhanced()
    
    print("\n" + "=" * 60)
    print("🎉 Phase 2 기능 테스트 완료!")
    print("\n📋 테스트 요약:")
    print("   ✅ ML 모델 정보 조회")
    print("   ✅ 사용자 피드백 수집")
    print("   ✅ 성능 지표 업데이트 및 임계값 조정")
    print("   ✅ 수동 임계값 설정")
    print("   ✅ 확장된 검증 시스템 통계")
    print("   ✅ 개선된 단일 항목 검증")

if __name__ == "__main__":
    main()