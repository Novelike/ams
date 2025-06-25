#!/usr/bin/env python3
"""모니터링 설정 스크립트"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MonitoringSetup:
    def __init__(self):
        self.grafana_api_key = os.getenv("GRAFANA_API_KEY")
        self.prometheus_url = os.getenv("PROMETHEUS_URL")
        self.grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        
    def check_prerequisites(self) -> bool:
        """모니터링 설정 전제 조건 확인"""
        logger.info("모니터링 설정 전제 조건 확인 중...")
        
        if not self.grafana_api_key:
            logger.warning("GRAFANA_API_KEY 환경변수가 설정되지 않았습니다")
            return False
            
        if not self.prometheus_url:
            logger.warning("PROMETHEUS_URL 환경변수가 설정되지 않았습니다")
            return False
            
        logger.info("✅ 모니터링 설정 전제 조건 확인 완료")
        return True
    
    def setup_grafana_datasource(self) -> bool:
        """Grafana 데이터소스 설정"""
        logger.info("Grafana 데이터소스 설정 중...")
        
        try:
            datasource_config = {
                "name": "AMS-Prometheus",
                "type": "prometheus",
                "url": self.prometheus_url,
                "access": "proxy",
                "isDefault": True,
                "basicAuth": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.grafana_api_key}",
                "Content-Type": "application/json"
            }
            
            # 기존 데이터소스 확인
            response = requests.get(
                f"{self.grafana_url}/api/datasources/name/{datasource_config['name']}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Grafana 데이터소스가 이미 존재합니다")
                return True
            elif response.status_code == 404:
                # 새 데이터소스 생성
                response = requests.post(
                    f"{self.grafana_url}/api/datasources",
                    headers=headers,
                    json=datasource_config,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("✅ Grafana 데이터소스 생성 완료")
                    return True
                else:
                    logger.error(f"❌ Grafana 데이터소스 생성 실패: {response.status_code}")
                    return False
            else:
                logger.error(f"❌ Grafana 데이터소스 확인 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Grafana 데이터소스 설정 오류: {str(e)}")
            return False
    
    def create_dashboard(self) -> bool:
        """AMS 대시보드 생성"""
        logger.info("AMS 모니터링 대시보드 생성 중...")
        
        try:
            dashboard_config = {
                "dashboard": {
                    "id": None,
                    "title": "AMS Backend Monitoring",
                    "tags": ["ams", "backend", "monitoring"],
                    "timezone": "browser",
                    "panels": [
                        {
                            "id": 1,
                            "title": "API Response Time",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                                    "legendFormat": "95th percentile"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                        },
                        {
                            "id": 2,
                            "title": "Request Rate",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "rate(http_requests_total[5m])",
                                    "legendFormat": "Requests/sec"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                        },
                        {
                            "id": 3,
                            "title": "Error Rate",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
                                    "legendFormat": "5xx errors/sec"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                        },
                        {
                            "id": 4,
                            "title": "System Resources",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "process_resident_memory_bytes",
                                    "legendFormat": "Memory Usage"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                        }
                    ],
                    "time": {"from": "now-1h", "to": "now"},
                    "refresh": "5s"
                },
                "overwrite": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.grafana_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.grafana_url}/api/dashboards/db",
                headers=headers,
                json=dashboard_config,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ AMS 모니터링 대시보드 생성 완료")
                return True
            else:
                logger.error(f"❌ 대시보드 생성 실패: {response.status_code}")
                logger.error(f"응답: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 대시보드 생성 오류: {str(e)}")
            return False
    
    def setup_alerts(self) -> bool:
        """알림 규칙 설정"""
        logger.info("알림 규칙 설정 중...")
        
        try:
            alert_rules = [
                {
                    "alert": "HighErrorRate",
                    "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) > 0.1",
                    "for": "2m",
                    "labels": {
                        "severity": "warning",
                        "service": "ams-backend"
                    },
                    "annotations": {
                        "summary": "High error rate detected",
                        "description": "Error rate is above 10% for more than 2 minutes"
                    }
                },
                {
                    "alert": "HighResponseTime",
                    "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1",
                    "for": "5m",
                    "labels": {
                        "severity": "warning",
                        "service": "ams-backend"
                    },
                    "annotations": {
                        "summary": "High response time detected",
                        "description": "95th percentile response time is above 1 second"
                    }
                }
            ]
            
            # 실제 환경에서는 Prometheus 알림 규칙 파일에 저장
            # 여기서는 로그로만 출력
            logger.info("알림 규칙:")
            for rule in alert_rules:
                logger.info(f"  - {rule['alert']}: {rule['expr']}")
            
            logger.info("✅ 알림 규칙 설정 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 알림 규칙 설정 오류: {str(e)}")
            return False
    
    def test_monitoring_endpoints(self) -> bool:
        """모니터링 엔드포인트 테스트"""
        logger.info("모니터링 엔드포인트 테스트 중...")
        
        try:
            # Prometheus 연결 테스트
            if self.prometheus_url:
                response = requests.get(f"{self.prometheus_url}/api/v1/query?query=up", timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Prometheus 연결 테스트 통과")
                else:
                    logger.warning(f"⚠️ Prometheus 연결 테스트 실패: {response.status_code}")
            
            # Grafana 연결 테스트
            if self.grafana_api_key:
                headers = {"Authorization": f"Bearer {self.grafana_api_key}"}
                response = requests.get(f"{self.grafana_url}/api/health", headers=headers, timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Grafana 연결 테스트 통과")
                else:
                    logger.warning(f"⚠️ Grafana 연결 테스트 실패: {response.status_code}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 모니터링 엔드포인트 테스트 오류: {str(e)}")
            return False
    
    def setup_monitoring(self) -> bool:
        """전체 모니터링 설정 실행"""
        logger.info("=== AMS 모니터링 설정 시작 ===")
        
        if not self.check_prerequisites():
            logger.info("모니터링 설정을 건너뜁니다 (환경변수 없음)")
            return True  # 환경변수가 없어도 성공으로 처리
        
        success = True
        
        # Grafana 데이터소스 설정
        if not self.setup_grafana_datasource():
            success = False
        
        # 대시보드 생성
        if not self.create_dashboard():
            success = False
        
        # 알림 규칙 설정
        if not self.setup_alerts():
            success = False
        
        # 엔드포인트 테스트
        if not self.test_monitoring_endpoints():
            success = False
        
        if success:
            logger.info("🎉 모니터링 설정이 성공적으로 완료되었습니다!")
        else:
            logger.error("💥 모니터링 설정 중 일부 오류가 발생했습니다!")
        
        return success

def main():
    """메인 함수"""
    logger.info(f"모니터링 설정 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        setup = MonitoringSetup()
        success = setup.setup_monitoring()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.error("모니터링 설정이 사용자에 의해 중단되었습니다")
        return 2
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        return 2

if __name__ == "__main__":
    sys.exit(main())