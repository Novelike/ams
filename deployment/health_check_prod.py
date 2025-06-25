#!/usr/bin/env python3
"""
AMS Backend Production Health Check Script
Performs comprehensive health checks for the production environment.
"""

import sys
import os
import time
import subprocess
import requests
from datetime import datetime
import logging
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.app_name = "ams-backend"
        self.service_name = "ams-backend"
        self.base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")
        self.health_endpoints = [
            "/api/registration/workflow",
            "/api/registration/search/stats", 
            "/api/registration/gpu-ocr/stats",
            "/api/registration/gpu-ocr/scheduler/status",
            "/api/health"
        ]
        self.timeout = 10
        self.max_retries = 3
        self.critical_memory_threshold = 90
        self.critical_disk_threshold = 90
        self.critical_cpu_threshold = 95

        self.health_results = []
        self.overall_status = "HEALTHY"
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        self.skip_http_checks = os.getenv("SKIP_HTTP_CHECKS", "false").lower() == "true"
        self.skip_db_checks = os.getenv("SKIP_DB_CHECKS", "false").lower() == "true"

    def log_info(self, message: str):
        logger.info(f"🔍 {message}")

    def log_success(self, message: str):
        logger.info(f"✅ {message}")

    def log_warning(self, message: str):
        logger.warning(f"⚠️ {message}")

    def log_error(self, message: str):
        logger.error(f"❌ {message}")

    def check_service_status(self) -> bool:
        """Check if the service is running"""
        self.log_info("서비스 상태 확인 중...")

        # Skip service checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 서비스 상태 확인을 건너뜁니다")
            self.health_results.append("Service Status: SKIPPED (GitHub Actions/Windows)")
            return True

        try:
            # Check if service is active (for systemd environments)
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                self.log_success("systemd 서비스가 실행 중입니다")
                self.health_results.append("Service Status: PASS")
                return True
            else:
                self.log_warning("systemd 서비스 상태를 확인할 수 없습니다")

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_info("systemd를 사용하지 않는 환경입니다")

        # Check for uvicorn processes (Linux/Unix only)
        try:
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn.*main:app"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                process_count = len(result.stdout.strip().split('\n'))
                self.log_success(f"uvicorn 프로세스 {process_count}개가 실행 중입니다")
                self.health_results.append("Service Status: PASS")
                return True
            else:
                self.log_warning("uvicorn 프로세스가 실행되지 않고 있습니다")
                self.health_results.append("Service Status: WARNING")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_warning("프로세스 확인을 수행할 수 없습니다")
            self.health_results.append("Service Status: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def check_http_endpoints(self) -> bool:
        if self.is_github_actions or self.skip_http_checks:
            self.log_info("GitHub Actions 환경에서는 HTTP 엔드포인트 확인을 건너뜁니다")
            self.health_results.append("HTTP Endpoints: SKIPPED (GitHub Actions)")
            return True

        """Check HTTP endpoints"""
        self.log_info("HTTP 엔드포인트 확인 중...")

        failed_endpoints = 0
        endpoint_results = []

        for endpoint in self.health_endpoints:
            url = f"{self.base_url}{endpoint}"
            success = False

            self.log_info(f"엔드포인트 테스트: {endpoint}")

            for attempt in range(1, self.max_retries + 1):
                try:
                    start_time = time.time()
                    response = requests.get(url, timeout=self.timeout)
                    response_time = time.time() - start_time

                    if response.status_code == 200:
                        self.log_success(f"  ✓ {endpoint} - HTTP {response.status_code} ({response_time:.2f}s)")
                        endpoint_results.append(f"{endpoint}: PASS ({response_time:.2f}s)")
                        success = True
                        break
                    else:
                        if attempt < self.max_retries:
                            self.log_warning(f"  ⚠ {endpoint} - HTTP {response.status_code} (시도 {attempt}/{self.max_retries})")
                            time.sleep(2)
                        else:
                            self.log_error(f"  ✗ {endpoint} - HTTP {response.status_code} (최종 실패)")
                            endpoint_results.append(f"{endpoint}: FAIL (HTTP {response.status_code})")
                            failed_endpoints += 1

                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        self.log_warning(f"  ⚠ {endpoint} - 연결 오류 (시도 {attempt}/{self.max_retries}): {str(e)}")
                        time.sleep(2)
                    else:
                        self.log_error(f"  ✗ {endpoint} - 연결 실패: {str(e)}")
                        endpoint_results.append(f"{endpoint}: FAIL (Connection Error)")
                        failed_endpoints += 1

        # Evaluate results
        if failed_endpoints == 0:
            self.log_success("모든 HTTP 엔드포인트가 정상입니다")
            self.health_results.append("HTTP Endpoints: PASS")
            return True
        elif failed_endpoints < len(self.health_endpoints):
            self.log_warning(f"일부 HTTP 엔드포인트에 문제가 있습니다 ({failed_endpoints}/{len(self.health_endpoints)} 실패)")
            self.health_results.append("HTTP Endpoints: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True
        else:
            self.log_error("모든 HTTP 엔드포인트가 실패했습니다")
            self.health_results.append("HTTP Endpoints: FAIL")
            self.overall_status = "UNHEALTHY"
            return False

        # Add detailed results
        for result in endpoint_results:
            self.health_results.append(f"  {result}")

    def check_database_connectivity(self) -> bool:
        if self.is_github_actions or self.skip_db_checks:
            self.log_info("GitHub Actions 환경에서는 데이터베이스 연결 확인을 건너뜁니다")
            self.health_results.append("Database: SKIPPED (GitHub Actions)")
            return True

        """Check database connectivity through application"""
        self.log_info("데이터베이스 연결 확인 중...")

        try:
            url = f"{self.base_url}/api/registration/workflow"
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                self.log_success("데이터베이스 연결이 정상입니다")
                self.health_results.append("Database: PASS")
                return True
            else:
                self.log_error(f"데이터베이스 연결에 문제가 있습니다 (HTTP {response.status_code})")
                self.health_results.append("Database: FAIL")
                self.overall_status = "UNHEALTHY"
                return False

        except requests.exceptions.RequestException as e:
            self.log_error(f"데이터베이스 연결 확인 실패: {str(e)}")
            self.health_results.append("Database: FAIL")
            self.overall_status = "UNHEALTHY"
            return False

    def check_system_resources(self) -> bool:
        """Check system resources"""
        self.log_info("시스템 리소스 확인 중...")

        # Skip system resource checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 시스템 리소스 확인을 건너뜁니다")
            self.health_results.append("System Resources: SKIPPED (GitHub Actions/Windows)")
            return True

        try:
            # Memory check (Linux only)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()

                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal:' in line][0].split()[1])
                mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable:' in line][0].split()[1])
                memory_usage = ((mem_total - mem_available) / mem_total) * 100

                if memory_usage < self.critical_memory_threshold:
                    self.log_success(f"메모리 사용률: {memory_usage:.1f}% (정상)")
                    self.health_results.append(f"Memory Usage: PASS ({memory_usage:.1f}%)")
                else:
                    self.log_warning(f"메모리 사용률이 높습니다: {memory_usage:.1f}%")
                    self.health_results.append(f"Memory Usage: WARNING ({memory_usage:.1f}%)")
                    if self.overall_status == "HEALTHY":
                        self.overall_status = "WARNING"
            except (FileNotFoundError, IndexError):
                self.log_warning("메모리 정보를 읽을 수 없습니다")
                self.health_results.append("Memory Usage: WARNING (Cannot read)")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"

            # Disk check (Linux/Unix only)
            try:
                result = subprocess.run(["df", "/"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        disk_info = lines[1].split()
                        if len(disk_info) >= 5:
                            disk_usage = int(disk_info[4].rstrip('%'))

                            if disk_usage < self.critical_disk_threshold:
                                self.log_success(f"디스크 사용률: {disk_usage}% (정상)")
                                self.health_results.append(f"Disk Usage: PASS ({disk_usage}%)")
                            else:
                                self.log_warning(f"디스크 사용률이 높습니다: {disk_usage}%")
                                self.health_results.append(f"Disk Usage: WARNING ({disk_usage}%)")
                                if self.overall_status == "HEALTHY":
                                    self.overall_status = "WARNING"
                        else:
                            self.log_warning("디스크 정보 형식을 파싱할 수 없습니다")
                            self.health_results.append("Disk Usage: WARNING (Parse error)")
                    else:
                        self.log_warning("디스크 정보를 읽을 수 없습니다")
                        self.health_results.append("Disk Usage: WARNING (No data)")
                else:
                    self.log_warning("디스크 사용률 확인 명령이 실패했습니다")
                    self.health_results.append("Disk Usage: WARNING (Command failed)")
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                self.log_warning("디스크 사용률을 확인할 수 없습니다")
                self.health_results.append("Disk Usage: WARNING (Command not available)")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"

            return True

        except Exception as e:
            self.log_error(f"시스템 리소스 확인 실패: {str(e)}")
            self.health_results.append("System Resources: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def generate_health_report(self) -> str:
        """Generate health check report"""
        self.log_info("헬스 체크 보고서 생성 중...")

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = f"""
=============================================================================
AMS 백엔드 헬스 체크 보고서
=============================================================================
검사 시간: {timestamp}
전체 상태: {self.overall_status}
호스트명: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}

상세 검사 결과:
"""

        for result in self.health_results:
            report += f"{result}\n"

        report += f"""
=============================================================================
"""

        self.log_success("헬스 체크 보고서 생성 완료")
        print(report)

        return report

    def run_health_check(self) -> int:
        """Run complete health check"""
        self.log_info("===============================================================================")
        self.log_info("🏥 AMS 백엔드 헬스 체크 시작")
        self.log_info("===============================================================================")

        # 1. Service status check
        self.check_service_status()

        # 2. HTTP endpoints check
        self.check_http_endpoints()

        # 3. Database connectivity check
        self.check_database_connectivity()

        # 4. System resources check
        self.check_system_resources()

        # 5. Generate report
        self.generate_health_report()

        self.log_info("===============================================================================")

        # Return appropriate exit code
        if self.overall_status == "HEALTHY":
            self.log_success("✅ 전체 시스템 상태: 정상")
            return 0
        elif self.overall_status == "WARNING":
            self.log_warning("⚠️ 전체 시스템 상태: 경고")
            return 1
        else:
            self.log_error("❌ 전체 시스템 상태: 비정상")
            return 2

def main():
    """Main function"""
    try:
        health_checker = HealthChecker()
        exit_code = health_checker.run_health_check()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.error("헬스 체크가 사용자에 의해 중단되었습니다")
        sys.exit(3)
    except Exception as e:
        logger.error(f"헬스 체크 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()
