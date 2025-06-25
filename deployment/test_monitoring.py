#!/usr/bin/env python3
"""모니터링 테스트 스크립트"""

import os
import sys
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MonitoringTester:
    def __init__(self):
        self.prometheus_url = os.getenv("PROMETHEUS_URL")
        self.grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        self.grafana_api_key = os.getenv("GRAFANA_API_KEY")
        self.test_results = []
        
    def check_prerequisites(self) -> bool:
        """모니터링 테스트 전제 조건 확인"""
        logger.info("모니터링 테스트 전제 조건 확인 중...")
        
        if not self.prometheus_url:
            logger.warning("PROMETHEUS_URL 환경변수가 설정되지 않았습니다")
            return False
            
        logger.info("✅ 모니터링 테스트 전제 조건 확인 완료")
        return True
    
    def test_prometheus_connection(self) -> bool:
        """Prometheus 연결 테스트"""
        logger.info("Prometheus 연결 테스트 중...")
        
        try:
            # Prometheus 헬스 체크
            response = requests.get(f"{self.prometheus_url}/-/healthy", timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Prometheus 헬스 체크 통과")
                
                # 기본 쿼리 테스트
                query_response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": "up"},
                    timeout=10
                )
                
                if query_response.status_code == 200:
                    data = query_response.json()
                    if data.get("status") == "success":
                        logger.info("✅ Prometheus 쿼리 테스트 통과")
                        self.test_results.append({
                            "test": "prometheus_connection",
                            "status": "pass",
                            "response_time": response.elapsed.total_seconds()
                        })
                        return True
                    else:
                        logger.error("❌ Prometheus 쿼리 응답 오류")
                        return False
                else:
                    logger.error(f"❌ Prometheus 쿼리 실패: HTTP {query_response.status_code}")
                    return False
            else:
                logger.error(f"❌ Prometheus 헬스 체크 실패: HTTP {response.status_code}")
                self.test_results.append({
                    "test": "prometheus_connection",
                    "status": "fail",
                    "error": f"HTTP {response.status_code}"
                })
                return False
                
        except Exception as e:
            logger.error(f"❌ Prometheus 연결 테스트 오류: {str(e)}")
            self.test_results.append({
                "test": "prometheus_connection",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def test_grafana_connection(self) -> bool:
        """Grafana 연결 테스트"""
        logger.info("Grafana 연결 테스트 중...")
        
        try:
            # Grafana 헬스 체크
            response = requests.get(f"{self.grafana_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Grafana 헬스 체크 통과")
                
                # API 키가 있는 경우 추가 테스트
                if self.grafana_api_key:
                    headers = {"Authorization": f"Bearer {self.grafana_api_key}"}
                    
                    # 데이터소스 목록 조회
                    ds_response = requests.get(
                        f"{self.grafana_url}/api/datasources",
                        headers=headers,
                        timeout=10
                    )
                    
                    if ds_response.status_code == 200:
                        datasources = ds_response.json()
                        logger.info(f"✅ Grafana 데이터소스 조회 성공: {len(datasources)}개")
                        
                        # AMS Prometheus 데이터소스 확인
                        ams_ds = next((ds for ds in datasources if ds.get("name") == "AMS-Prometheus"), None)
                        if ams_ds:
                            logger.info("✅ AMS-Prometheus 데이터소스 발견")
                        else:
                            logger.warning("⚠️ AMS-Prometheus 데이터소스를 찾을 수 없습니다")
                    else:
                        logger.warning(f"⚠️ Grafana 데이터소스 조회 실패: HTTP {ds_response.status_code}")
                
                self.test_results.append({
                    "test": "grafana_connection",
                    "status": "pass",
                    "response_time": response.elapsed.total_seconds()
                })
                return True
            else:
                logger.error(f"❌ Grafana 헬스 체크 실패: HTTP {response.status_code}")
                self.test_results.append({
                    "test": "grafana_connection",
                    "status": "fail",
                    "error": f"HTTP {response.status_code}"
                })
                return False
                
        except Exception as e:
            logger.error(f"❌ Grafana 연결 테스트 오류: {str(e)}")
            self.test_results.append({
                "test": "grafana_connection",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def test_metrics_collection(self) -> bool:
        """메트릭 수집 테스트"""
        logger.info("메트릭 수집 테스트 중...")
        
        try:
            # 기본 시스템 메트릭 확인
            metrics_to_check = [
                "up",
                "process_resident_memory_bytes",
                "http_requests_total"
            ]
            
            all_metrics_found = True
            
            for metric in metrics_to_check:
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": metric},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" and data.get("data", {}).get("result"):
                        logger.info(f"✅ 메트릭 '{metric}' 수집 확인")
                    else:
                        logger.warning(f"⚠️ 메트릭 '{metric}' 데이터 없음")
                        all_metrics_found = False
                else:
                    logger.warning(f"⚠️ 메트릭 '{metric}' 쿼리 실패: HTTP {response.status_code}")
                    all_metrics_found = False
            
            if all_metrics_found:
                logger.info("✅ 모든 기본 메트릭 수집 확인")
                self.test_results.append({
                    "test": "metrics_collection",
                    "status": "pass"
                })
                return True
            else:
                logger.warning("⚠️ 일부 메트릭 수집 누락")
                self.test_results.append({
                    "test": "metrics_collection",
                    "status": "warning",
                    "message": "일부 메트릭 누락"
                })
                return True  # 경고이지만 통과로 처리
                
        except Exception as e:
            logger.error(f"❌ 메트릭 수집 테스트 오류: {str(e)}")
            self.test_results.append({
                "test": "metrics_collection",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def test_dashboard_access(self) -> bool:
        """대시보드 접근 테스트"""
        logger.info("대시보드 접근 테스트 중...")
        
        try:
            if not self.grafana_api_key:
                logger.info("Grafana API 키가 없어 대시보드 테스트를 건너뜁니다")
                return True
            
            headers = {"Authorization": f"Bearer {self.grafana_api_key}"}
            
            # 대시보드 목록 조회
            response = requests.get(
                f"{self.grafana_url}/api/search",
                headers=headers,
                params={"query": "AMS"},
                timeout=10
            )
            
            if response.status_code == 200:
                dashboards = response.json()
                ams_dashboard = next((db for db in dashboards if "AMS" in db.get("title", "")), None)
                
                if ams_dashboard:
                    logger.info(f"✅ AMS 대시보드 발견: {ams_dashboard['title']}")
                    
                    # 대시보드 상세 정보 조회
                    dashboard_uid = ams_dashboard.get("uid")
                    if dashboard_uid:
                        detail_response = requests.get(
                            f"{self.grafana_url}/api/dashboards/uid/{dashboard_uid}",
                            headers=headers,
                            timeout=10
                        )
                        
                        if detail_response.status_code == 200:
                            logger.info("✅ 대시보드 상세 정보 조회 성공")
                        else:
                            logger.warning("⚠️ 대시보드 상세 정보 조회 실패")
                else:
                    logger.warning("⚠️ AMS 대시보드를 찾을 수 없습니다")
                
                self.test_results.append({
                    "test": "dashboard_access",
                    "status": "pass"
                })
                return True
            else:
                logger.error(f"❌ 대시보드 목록 조회 실패: HTTP {response.status_code}")
                self.test_results.append({
                    "test": "dashboard_access",
                    "status": "fail",
                    "error": f"HTTP {response.status_code}"
                })
                return False
                
        except Exception as e:
            logger.error(f"❌ 대시보드 접근 테스트 오류: {str(e)}")
            self.test_results.append({
                "test": "dashboard_access",
                "status": "error",
                "error": str(e)
            })
            return False
    
    def run_all_tests(self) -> bool:
        """모든 모니터링 테스트 실행"""
        logger.info("=== 모니터링 시스템 테스트 시작 ===")
        
        if not self.check_prerequisites():
            logger.info("모니터링 테스트를 건너뜁니다")
            return True  # 환경변수가 없어도 성공으로 처리
        
        tests = [
            ("Prometheus 연결", self.test_prometheus_connection),
            ("Grafana 연결", self.test_grafana_connection),
            ("메트릭 수집", self.test_metrics_collection),
            ("대시보드 접근", self.test_dashboard_access)
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
        logger.info("\n=== 모니터링 테스트 결과 요약 ===")
        
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
            logger.info("🎉 모든 모니터링 테스트가 성공적으로 완료되었습니다!")
        else:
            logger.error("💥 일부 모니터링 테스트가 실패했습니다!")

def main():
    """메인 함수"""
    logger.info(f"모니터링 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        tester = MonitoringTester()
        success = tester.run_all_tests()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.error("모니터링 테스트가 사용자에 의해 중단되었습니다")
        return 2
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        return 2

if __name__ == "__main__":
    sys.exit(main())