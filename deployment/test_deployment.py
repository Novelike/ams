#!/usr/bin/env python3
"""배포 후 테스트 스크립트"""

import sys
import os
import argparse
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DeploymentTester:
    def __init__(self, environment: str):
        self.environment = environment
        self.base_url = self._get_base_url()
        self.test_results = []
        
    def _get_base_url(self) -> str:
        """환경별 기본 URL 반환"""
        if self.environment == "development":
            return os.getenv("DEV_BASE_URL", "http://localhost:8000")
        elif self.environment == "production":
            return os.getenv("PROD_BASE_URL", "http://localhost:8000")
        else:
            return "http://localhost:8000"
    
    def test_health_endpoint(self) -> bool:
        """헬스 체크 엔드포인트 테스트"""
        logger.info("헬스 체크 엔드포인트 테스트 중...")
        
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 헬스 체크 통과: {data.get('status', 'unknown')}")
                self.test_results.append({
                    "test": "health_check",
                    "status": "pass",
                    "response_time": response.elapsed.total_seconds(),
                    "details": data
                })
                return True
            else:
                logger.error(f"❌ 헬스 체크 실패: HTTP {response.status_code}")
                self.test_results.append({
                    "test": "health_check",
                    "status": "fail",
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                })
                return False
                
        except Exception as e:
            logger.error(f"❌ 헬스 체크 오류: {str(e)}")
            self.test_results.append({
                "test": "health_check",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def test_api_endpoints(self) -> bool:
        """주요 API 엔드포인트 테스트"""
        logger.info("주요 API 엔드포인트 테스트 중...")
        
        endpoints = [
            "/api/registration/workflow",
            "/api/registration/verification/stats"
        ]
        
        all_passed = True
        
        for endpoint in endpoints:
            try:
                logger.info(f"테스트 중: {endpoint}")
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ {endpoint} 테스트 통과")
                    self.test_results.append({
                        "test": f"api_endpoint_{endpoint.replace('/', '_')}",
                        "status": "pass",
                        "response_time": response.elapsed.total_seconds()
                    })
                else:
                    logger.error(f"❌ {endpoint} 테스트 실패: HTTP {response.status_code}")
                    self.test_results.append({
                        "test": f"api_endpoint_{endpoint.replace('/', '_')}",
                        "status": "fail",
                        "error": f"HTTP {response.status_code}"
                    })
                    all_passed = False
                    
            except Exception as e:
                logger.error(f"❌ {endpoint} 테스트 오류: {str(e)}")
                self.test_results.append({
                    "test": f"api_endpoint_{endpoint.replace('/', '_')}",
                    "status": "error",
                    "error": str(e)
                })
                all_passed = False
        
        return all_passed
    
    def test_performance(self) -> bool:
        """기본 성능 테스트"""
        logger.info("기본 성능 테스트 중...")
        
        try:
            # 여러 번 요청하여 평균 응답 시간 측정
            response_times = []
            
            for i in range(5):
                start_time = time.time()
                response = requests.get(f"{self.base_url}/api/health", timeout=10)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                else:
                    logger.warning(f"성능 테스트 중 응답 오류: HTTP {response.status_code}")
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                logger.info(f"평균 응답 시간: {avg_response_time:.3f}초")
                logger.info(f"최대 응답 시간: {max_response_time:.3f}초")
                
                # 성능 기준: 평균 응답 시간 1초 이하
                if avg_response_time <= 1.0:
                    logger.info("✅ 성능 테스트 통과")
                    self.test_results.append({
                        "test": "performance",
                        "status": "pass",
                        "avg_response_time": avg_response_time,
                        "max_response_time": max_response_time
                    })
                    return True
                else:
                    logger.warning(f"⚠️ 성능 테스트 경고: 평균 응답 시간이 기준을 초과했습니다")
                    self.test_results.append({
                        "test": "performance",
                        "status": "warning",
                        "avg_response_time": avg_response_time,
                        "max_response_time": max_response_time
                    })
                    return True  # 경고이지만 통과로 처리
            else:
                logger.error("❌ 성능 테스트 실패: 유효한 응답이 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"❌ 성능 테스트 오류: {str(e)}")
            self.test_results.append({
                "test": "performance",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def run_all_tests(self) -> bool:
        """모든 테스트 실행"""
        logger.info(f"=== {self.environment.upper()} 환경 배포 테스트 시작 ===")
        logger.info(f"테스트 대상: {self.base_url}")
        
        tests = [
            ("헬스 체크", self.test_health_endpoint),
            ("API 엔드포인트", self.test_api_endpoints),
            ("기본 성능", self.test_performance)
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            logger.info(f"\n--- {test_name} 테스트 ---")
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {test_name} 테스트 중 오류 발생: {str(e)}")
                all_passed = False
        
        # 테스트 결과 요약
        self._print_test_summary()
        
        return all_passed
    
    def _print_test_summary(self):
        """테스트 결과 요약 출력"""
        logger.info("\n=== 테스트 결과 요약 ===")
        
        passed = len([r for r in self.test_results if r["status"] == "pass"])
        failed = len([r for r in self.test_results if r["status"] == "fail"])
        errors = len([r for r in self.test_results if r["status"] == "error"])
        warnings = len([r for r in self.test_results if r["status"] == "warning"])
        
        logger.info(f"총 테스트: {len(self.test_results)}개")
        logger.info(f"통과: {passed}개")
        logger.info(f"실패: {failed}개")
        logger.info(f"오류: {errors}개")
        logger.info(f"경고: {warnings}개")
        
        if failed == 0 and errors == 0:
            logger.info("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            logger.error("💥 일부 테스트가 실패했습니다!")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Test Deployment")
    parser.add_argument("--environment", required=True, 
                       choices=["development", "production"],
                       help="Environment to test")
    args = parser.parse_args()
    
    logger.info(f"배포 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        tester = DeploymentTester(args.environment)
        success = tester.run_all_tests()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.error("테스트가 사용자에 의해 중단되었습니다")
        return 2
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        return 2

if __name__ == "__main__":
    sys.exit(main())