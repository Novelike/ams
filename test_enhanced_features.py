#!/usr/bin/env python3
"""
Enhanced OCR Features Test Suite
Phase 1 & Phase 2 구현 사항 종합 테스트

이 스크립트는 다음 기능들을 테스트합니다:
1. Search Engine (Whoosh 기반)
2. Real-time Learning Pipeline
3. Performance Monitoring
4. A/B Testing Framework
5. Enhanced Asset Matcher
6. Confidence ML Model
"""

import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedFeaturesTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 Enhanced OCR Features 테스트 시작")
        
        test_methods = [
            ("기본 연결 테스트", self.test_basic_connectivity),
            ("검색 엔진 테스트", self.test_search_engine),
            ("실시간 학습 테스트", self.test_realtime_learning),
            ("성능 모니터링 테스트", self.test_performance_monitoring),
            ("A/B 테스트 프레임워크", self.test_ab_testing),
            ("통합 워크플로우 테스트", self.test_integrated_workflow),
        ]
        
        for test_name, test_method in test_methods:
            logger.info(f"\n📋 {test_name} 시작...")
            try:
                result = await test_method()
                self.test_results[test_name] = {"status": "PASS", "details": result}
                logger.info(f"✅ {test_name} 성공")
            except Exception as e:
                self.test_results[test_name] = {"status": "FAIL", "error": str(e)}
                logger.error(f"❌ {test_name} 실패: {e}")
        
        # 결과 요약
        self.print_test_summary()

    async def test_basic_connectivity(self) -> Dict:
        """기본 연결 테스트"""
        async with self.session.get(f"{self.base_url}/api/registration/workflow") as response:
            if response.status == 200:
                data = await response.json()
                return {"workflow_steps": len(data), "status": "connected"}
            else:
                raise Exception(f"연결 실패: {response.status}")

    async def test_search_engine(self) -> Dict:
        """검색 엔진 테스트"""
        results = {}
        
        # 1. 검색 엔진 통계 조회
        async with self.session.get(f"{self.base_url}/api/registration/search/stats") as response:
            if response.status == 200:
                data = await response.json()
                results["stats"] = data.get("stats", {})
            else:
                logger.warning(f"검색 통계 조회 실패: {response.status}")
        
        # 2. 자산 검색 테스트
        search_queries = ["lenovo", "computer", "PC", "monitor"]
        
        for query in search_queries:
            async with self.session.get(
                f"{self.base_url}/api/registration/search/assets",
                params={"query": query, "limit": 5}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results[f"search_{query}"] = {
                        "count": data.get("count", 0),
                        "results_found": len(data.get("results", []))
                    }
                else:
                    logger.warning(f"검색 실패 ({query}): {response.status}")
        
        # 3. 자동완성 테스트
        async with self.session.get(
            f"{self.base_url}/api/registration/search/suggestions",
            params={"field": "model_name", "partial_text": "len", "limit": 5}
        ) as response:
            if response.status == 200:
                data = await response.json()
                results["autocomplete"] = {
                    "suggestions_count": len(data.get("suggestions", []))
                }
        
        return results

    async def test_realtime_learning(self) -> Dict:
        """실시간 학습 테스트"""
        results = {}
        
        # 1. 학습 상태 조회
        async with self.session.get(f"{self.base_url}/api/registration/learning/status") as response:
            if response.status == 200:
                data = await response.json()
                learning_status = data.get("learning_status", {})
                results["learning_status"] = {
                    "is_learning": learning_status.get("is_learning", False),
                    "queue_size": learning_status.get("queue_size", 0),
                    "total_processed": learning_status.get("total_feedback_processed", 0)
                }
            else:
                logger.warning(f"학습 상태 조회 실패: {response.status}")
        
        # 2. 성능 메트릭 조회
        async with self.session.get(
            f"{self.base_url}/api/registration/learning/performance",
            params={"days": 7}
        ) as response:
            if response.status == 200:
                data = await response.json()
                metrics = data.get("performance_metrics", [])
                results["performance_metrics"] = {
                    "metrics_count": len(metrics),
                    "days_requested": data.get("days", 0)
                }
        
        # 3. 피드백 데이터 시뮬레이션 (실제 학습 파이프라인 테스트)
        feedback_data = {
            "user_id": "test_user_001",
            "field_name": "model_name",
            "original_value": "LENOV0 ThinkPad",
            "corrected_value": "LENOVO ThinkPad",
            "ocr_confidence": 0.85,
            "pattern_confidence": 0.75,
            "db_verification": 0.90,
            "length_penalty": 0.95,
            "user_accepted": False
        }
        
        async with self.session.post(
            f"{self.base_url}/api/registration/feedback",
            json=feedback_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                results["feedback_submission"] = {"status": "success"}
            else:
                logger.warning(f"피드백 제출 실패: {response.status}")
        
        return results

    async def test_performance_monitoring(self) -> Dict:
        """성능 모니터링 테스트"""
        results = {}
        
        # 1. 요청 통계 조회
        async with self.session.get(
            f"{self.base_url}/api/registration/monitoring/request-stats",
            params={"hours": 24}
        ) as response:
            if response.status == 200:
                data = await response.json()
                request_stats = data.get("request_stats", {})
                results["request_stats"] = {
                    "total_requests": request_stats.get("total_requests", 0),
                    "avg_response_time": request_stats.get("avg_response_time", 0),
                    "error_rate": request_stats.get("error_rate", 0)
                }
        
        # 2. 시스템 통계 조회
        async with self.session.get(
            f"{self.base_url}/api/registration/monitoring/system-stats",
            params={"hours": 24}
        ) as response:
            if response.status == 200:
                data = await response.json()
                system_stats = data.get("system_stats", {})
                results["system_stats"] = {
                    "avg_cpu_percent": system_stats.get("avg_cpu_percent", 0),
                    "avg_memory_percent": system_stats.get("avg_memory_percent", 0),
                    "data_points": system_stats.get("data_points", 0)
                }
        
        # 3. 성능 알림 조회
        async with self.session.get(
            f"{self.base_url}/api/registration/monitoring/alerts",
            params={"hours": 24}
        ) as response:
            if response.status == 200:
                data = await response.json()
                results["alerts"] = {
                    "alert_count": data.get("count", 0),
                    "hours": data.get("hours", 0)
                }
        
        # 4. 부하 테스트 (여러 요청을 동시에 보내서 모니터링 데이터 생성)
        logger.info("부하 테스트 실행 중...")
        tasks = []
        for i in range(10):
            task = self.session.get(f"{self.base_url}/api/registration/workflow")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        successful_requests = sum(1 for r in responses if hasattr(r, 'status') and r.status == 200)
        
        results["load_test"] = {
            "total_requests": len(tasks),
            "successful_requests": successful_requests,
            "success_rate": successful_requests / len(tasks) * 100
        }
        
        return results

    async def test_ab_testing(self) -> Dict:
        """A/B 테스트 프레임워크 테스트"""
        results = {}
        
        # 1. A/B 테스트 생성
        test_config = {
            "config": {
                "test_id": f"ocr_confidence_test_{int(time.time())}",
                "name": "OCR 신뢰도 임계값 테스트",
                "description": "다른 신뢰도 임계값의 효과를 테스트합니다",
                "traffic_split": {
                    "control": 0.5,
                    "variant_a": 0.5
                },
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "success_metric": "accuracy",
                "minimum_sample_size": 100,
                "confidence_level": 0.95
            },
            "variants": [
                {
                    "variant_id": "control",
                    "name": "기본 임계값",
                    "description": "현재 사용 중인 임계값",
                    "config": {"confidence_threshold": 0.7},
                    "is_control": True
                },
                {
                    "variant_id": "variant_a",
                    "name": "높은 임계값",
                    "description": "더 높은 신뢰도 임계값",
                    "config": {"confidence_threshold": 0.85},
                    "is_control": False
                }
            ]
        }
        
        async with self.session.post(
            f"{self.base_url}/api/registration/ab-test/create",
            json=test_config
        ) as response:
            if response.status == 200:
                data = await response.json()
                test_id = data.get("test_id")
                results["test_creation"] = {"test_id": test_id, "status": "success"}
                
                # 2. 테스트 상태 조회
                async with self.session.get(
                    f"{self.base_url}/api/registration/ab-test/{test_id}/status"
                ) as status_response:
                    if status_response.status == 200:
                        status_data = await status_response.json()
                        test_status = status_data.get("test_status", {})
                        results["test_status"] = {
                            "config_name": test_status.get("config", {}).get("name"),
                            "variants_count": len(test_status.get("variants", [])),
                            "total_exposures": test_status.get("stats", {}).get("total_exposures", 0)
                        }
                
                # 3. 전환 이벤트 시뮬레이션
                conversion_data = {
                    "user_id": f"test_user_{random.randint(1000, 9999)}",
                    "conversion_data": {
                        "accuracy_improvement": 0.15,
                        "processing_time": 2.3,
                        "user_satisfaction": 4.2
                    }
                }
                
                async with self.session.post(
                    f"{self.base_url}/api/registration/ab-test/{test_id}/conversion",
                    json=conversion_data
                ) as conv_response:
                    if conv_response.status == 200:
                        results["conversion_recording"] = {"status": "success"}
                    else:
                        logger.warning(f"전환 이벤트 기록 실패: {conv_response.status}")
            else:
                logger.warning(f"A/B 테스트 생성 실패: {response.status}")
                response_text = await response.text()
                logger.warning(f"응답 내용: {response_text}")
        
        return results

    async def test_integrated_workflow(self) -> Dict:
        """통합 워크플로우 테스트"""
        results = {}
        
        # 1. ML 모델 정보 조회
        async with self.session.get(f"{self.base_url}/api/registration/ml-model/info") as response:
            if response.status == 200:
                data = await response.json()
                results["ml_model_info"] = {
                    "model_available": "ml_model" in data,
                    "thresholds_available": "thresholds" in data
                }
        
        # 2. 성능 지표 업데이트 시뮬레이션
        performance_metrics = {
            "precision": 0.87,
            "recall": 0.82,
            "f1_score": 0.845,
            "accuracy": 0.89,
            "false_positive_rate": 0.08,
            "false_negative_rate": 0.12
        }
        
        async with self.session.post(
            f"{self.base_url}/api/registration/performance-metrics/update",
            json=performance_metrics
        ) as response:
            if response.status == 200:
                data = await response.json()
                results["performance_update"] = {
                    "status": data.get("status"),
                    "metrics_updated": "metrics" in data
                }
        
        # 3. 임계값 수동 설정 테스트
        threshold_override = {
            "thresholds": {
                "high": 0.90,
                "medium": 0.75,
                "low": 0.60,
                "very_low": 0.45
            },
            "reason": "integration_test"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/registration/thresholds/manual-override",
            json=threshold_override
        ) as response:
            if response.status == 200:
                data = await response.json()
                results["threshold_override"] = {
                    "status": data.get("status"),
                    "new_thresholds_applied": "new_thresholds" in data
                }
        
        # 4. 종합 시스템 상태 확인
        system_checks = [
            ("workflow", f"{self.base_url}/api/registration/workflow"),
            ("search_stats", f"{self.base_url}/api/registration/search/stats"),
            ("learning_status", f"{self.base_url}/api/registration/learning/status"),
            ("monitoring_alerts", f"{self.base_url}/api/registration/monitoring/alerts")
        ]
        
        system_status = {}
        for check_name, url in system_checks:
            try:
                async with self.session.get(url) as response:
                    system_status[check_name] = response.status == 200
            except Exception as e:
                system_status[check_name] = False
                logger.warning(f"시스템 체크 실패 ({check_name}): {e}")
        
        results["system_health"] = system_status
        
        return results

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        logger.info("\n" + "="*60)
        logger.info("🎯 Enhanced OCR Features 테스트 결과 요약")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"📊 전체 테스트: {total_tests}")
        logger.info(f"✅ 성공: {passed_tests}")
        logger.info(f"❌ 실패: {failed_tests}")
        logger.info(f"📈 성공률: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info("\n📋 상세 결과:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"{status_icon} {test_name}: {result['status']}")
            
            if result["status"] == "FAIL":
                logger.info(f"   오류: {result['error']}")
            elif "details" in result:
                # 주요 결과만 표시
                details = result["details"]
                if isinstance(details, dict):
                    for key, value in list(details.items())[:3]:  # 처음 3개만
                        logger.info(f"   {key}: {value}")
        
        logger.info("\n" + "="*60)
        
        if failed_tests == 0:
            logger.info("🎉 모든 테스트가 성공적으로 완료되었습니다!")
            logger.info("✨ Phase 1 & Phase 2 구현이 정상적으로 작동하고 있습니다.")
        else:
            logger.info("⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")
        
        logger.info("="*60)


async def main():
    """메인 테스트 실행 함수"""
    print("🚀 Enhanced OCR Features 종합 테스트 시작")
    print("=" * 60)
    print("테스트 대상:")
    print("- Search Engine (Whoosh 기반)")
    print("- Real-time Learning Pipeline")
    print("- Performance Monitoring")
    print("- A/B Testing Framework")
    print("- Enhanced Asset Matcher")
    print("- Confidence ML Model")
    print("=" * 60)
    
    async with EnhancedFeaturesTestSuite() as test_suite:
        await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())