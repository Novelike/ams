#!/usr/bin/env python3
"""
AMS Backend Post-Deployment Verification Script
Performs comprehensive verification after deployment to ensure the application is working correctly.
"""

import sys
import os
import time
import subprocess
import requests
import argparse
from datetime import datetime
import logging
import platform
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DeploymentVerifier:
    def __init__(self, environment: str):
        self.environment = environment
        self.app_name = "ams-backend"
        self.service_name = "ams-backend"
        self.base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

        # Verification endpoints - comprehensive list for post-deployment testing
        self.verification_endpoints = [
            "/api/registration/workflow",
            "/api/registration/search/stats", 
            "/api/registration/gpu-ocr/stats",
            "/api/registration/gpu-ocr/scheduler/status",
            "/api/registration/verification/stats",
            "/api/health",
            "/"
        ]

        # Critical endpoints that must pass
        self.critical_endpoints = [
            "/api/registration/workflow",
            "/api/registration/search/stats"
        ]

        self.timeout = 15
        self.max_retries = 5
        self.retry_delay = 3

        self.verification_results = []
        self.overall_status = "HEALTHY"
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"

        # Performance thresholds for production
        self.max_response_time = 5.0  # seconds
        self.critical_response_time = 10.0  # seconds

    def log_info(self, message: str):
        logger.info(f"🔍 {message}")

    def log_success(self, message: str):
        logger.info(f"✅ {message}")

    def log_warning(self, message: str):
        logger.warning(f"⚠️ {message}")

    def log_error(self, message: str):
        logger.error(f"❌ {message}")

    def verify_service_status(self) -> bool:
        """Verify that the service is running properly"""
        self.log_info("서비스 상태 검증 중...")

        # Skip service checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 서비스 상태 검증을 건너뜁니다")
            self.verification_results.append("Service Status: SKIPPED (GitHub Actions/Windows)")
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
                self.log_success("systemd 서비스가 정상 실행 중입니다")

                # Get service status details
                status_result = subprocess.run(
                    ["systemctl", "status", self.service_name, "--no-pager", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if "active (running)" in status_result.stdout:
                    self.log_success("서비스가 활성 상태입니다")
                    self.verification_results.append("Service Status: PASS")
                    return True
                else:
                    self.log_warning("서비스 상태가 불확실합니다")

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_info("systemd를 사용하지 않는 환경입니다")

        # Check for uvicorn processes
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
                self.verification_results.append("Service Status: PASS")
                return True
            else:
                self.log_error("uvicorn 프로세스가 실행되지 않고 있습니다")
                self.verification_results.append("Service Status: FAIL")
                self.overall_status = "UNHEALTHY"
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_warning("프로세스 확인을 수행할 수 없습니다")
            self.verification_results.append("Service Status: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def verify_endpoints(self) -> bool:
        """Verify all application endpoints"""
        self.log_info("애플리케이션 엔드포인트 검증 중...")

        # Skip endpoint checks in GitHub Actions
        if self.is_github_actions:
            self.log_info("GitHub Actions 환경에서는 엔드포인트 검증을 건너뜁니다")
            self.verification_results.append("Endpoints: SKIPPED (GitHub Actions)")
            return True

        failed_endpoints = 0
        critical_failed = 0
        endpoint_results = []
        performance_issues = 0

        for endpoint in self.verification_endpoints:
            url = f"{self.base_url}{endpoint}"
            success = False
            best_response_time = float('inf')

            self.log_info(f"엔드포인트 검증: {endpoint}")

            for attempt in range(1, self.max_retries + 1):
                try:
                    start_time = time.time()
                    response = requests.get(url, timeout=self.timeout)
                    response_time = time.time() - start_time

                    if response_time < best_response_time:
                        best_response_time = response_time

                    if response.status_code == 200:
                        # Check response time performance
                        if response_time > self.critical_response_time:
                            self.log_warning(f"  ⚠ {endpoint} - 응답 시간이 매우 느림: {response_time:.2f}s")
                            performance_issues += 1
                        elif response_time > self.max_response_time:
                            self.log_warning(f"  ⚠ {endpoint} - 응답 시간이 느림: {response_time:.2f}s")
                            performance_issues += 1
                        else:
                            self.log_success(f"  ✓ {endpoint} - HTTP {response.status_code} ({response_time:.2f}s)")

                        endpoint_results.append(f"{endpoint}: PASS ({response_time:.2f}s)")
                        success = True
                        break
                    else:
                        if attempt < self.max_retries:
                            self.log_warning(f"  ⚠ {endpoint} - HTTP {response.status_code} (시도 {attempt}/{self.max_retries})")
                            time.sleep(self.retry_delay)
                        else:
                            self.log_error(f"  ✗ {endpoint} - HTTP {response.status_code} (최종 실패)")
                            endpoint_results.append(f"{endpoint}: FAIL (HTTP {response.status_code})")
                            failed_endpoints += 1

                            # Check if this is a critical endpoint
                            if endpoint in self.critical_endpoints:
                                critical_failed += 1

                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        self.log_warning(f"  ⚠ {endpoint} - 연결 오류 (시도 {attempt}/{self.max_retries}): {str(e)}")
                        time.sleep(self.retry_delay)
                    else:
                        self.log_error(f"  ✗ {endpoint} - 연결 실패: {str(e)}")
                        endpoint_results.append(f"{endpoint}: FAIL (Connection Error)")
                        failed_endpoints += 1

                        # Check if this is a critical endpoint
                        if endpoint in self.critical_endpoints:
                            critical_failed += 1

        # Evaluate results
        if critical_failed > 0:
            self.log_error(f"중요 엔드포인트 {critical_failed}개가 실패했습니다")
            self.verification_results.append("Endpoints: FAIL (Critical endpoints failed)")
            self.overall_status = "UNHEALTHY"
            return False
        elif failed_endpoints == 0:
            if performance_issues > 0:
                self.log_warning(f"모든 엔드포인트가 정상이지만 성능 문제가 {performance_issues}개 발견되었습니다")
                self.verification_results.append("Endpoints: WARNING (Performance issues)")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"
            else:
                self.log_success("모든 엔드포인트가 정상입니다")
                self.verification_results.append("Endpoints: PASS")
            return True
        elif failed_endpoints < len(self.verification_endpoints) / 2:
            self.log_warning(f"일부 엔드포인트에 문제가 있습니다 ({failed_endpoints}/{len(self.verification_endpoints)} 실패)")
            self.verification_results.append("Endpoints: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True
        else:
            self.log_error(f"너무 많은 엔드포인트가 실패했습니다 ({failed_endpoints}/{len(self.verification_endpoints)} 실패)")
            self.verification_results.append("Endpoints: FAIL")
            self.overall_status = "UNHEALTHY"
            return False

        # Add detailed results
        for result in endpoint_results:
            self.verification_results.append(f"  {result}")

    def verify_database_connectivity(self) -> bool:
        """Verify database connectivity and basic operations"""
        self.log_info("데이터베이스 연결 검증 중...")

        # Skip database checks in GitHub Actions
        if self.is_github_actions:
            self.log_info("GitHub Actions 환경에서는 데이터베이스 검증을 건너뜁니다")
            self.verification_results.append("Database: SKIPPED (GitHub Actions)")
            return True

        try:
            # Test database connectivity through the application
            url = f"{self.base_url}/api/registration/workflow"

            # Perform multiple tests to ensure consistency
            success_count = 0
            total_tests = 3

            for i in range(total_tests):
                try:
                    response = requests.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        success_count += 1
                    time.sleep(1)  # Brief pause between tests
                except requests.exceptions.RequestException:
                    pass

            if success_count == total_tests:
                self.log_success("데이터베이스 연결이 안정적으로 정상입니다")
                self.verification_results.append("Database: PASS")
                return True
            elif success_count > 0:
                self.log_warning(f"데이터베이스 연결이 불안정합니다 ({success_count}/{total_tests} 성공)")
                self.verification_results.append("Database: WARNING")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"
                return True
            else:
                self.log_error("데이터베이스 연결에 문제가 있습니다")
                self.verification_results.append("Database: FAIL")
                self.overall_status = "UNHEALTHY"
                return False

        except Exception as e:
            self.log_error(f"데이터베이스 검증 실패: {str(e)}")
            self.verification_results.append("Database: FAIL")
            self.overall_status = "UNHEALTHY"
            return False

    def verify_deployment_artifacts(self) -> bool:
        """Verify deployment artifacts and configuration"""
        self.log_info("배포 아티팩트 검증 중...")

        # Skip artifact checks in GitHub Actions
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 아티팩트 검증을 건너뜁니다")
            self.verification_results.append("Deployment Artifacts: SKIPPED (GitHub Actions/Windows)")
            return True

        try:
            # Check if application directory exists
            app_dirs = [
                "/opt/ams-backend",
                "/opt/ams-backend-blue",
                "/opt/ams-backend-green"
            ]

            found_app_dir = False
            for app_dir in app_dirs:
                if os.path.exists(app_dir):
                    found_app_dir = True
                    self.log_success(f"애플리케이션 디렉토리 발견: {app_dir}")

                    # Check for essential files
                    essential_files = ["main.py", "requirements.txt"]
                    missing_files = []

                    for file in essential_files:
                        file_path = os.path.join(app_dir, file)
                        if not os.path.exists(file_path):
                            missing_files.append(file)

                    if missing_files:
                        self.log_warning(f"필수 파일이 누락되었습니다: {', '.join(missing_files)}")
                    else:
                        self.log_success("모든 필수 파일이 존재합니다")
                    break

            if found_app_dir:
                self.verification_results.append("Deployment Artifacts: PASS")
                return True
            else:
                self.log_warning("애플리케이션 디렉토리를 찾을 수 없습니다")
                self.verification_results.append("Deployment Artifacts: WARNING")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"
                return True

        except Exception as e:
            self.log_error(f"아티팩트 검증 실패: {str(e)}")
            self.verification_results.append("Deployment Artifacts: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def verify_system_resources(self) -> bool:
        """Verify system resources are adequate for production"""
        self.log_info("시스템 리소스 검증 중...")

        # Skip system resource checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 시스템 리소스 검증을 건너뜁니다")
            self.verification_results.append("System Resources: SKIPPED (GitHub Actions/Windows)")
            return True

        try:
            # Memory check
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()

                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal:' in line][0].split()[1])
                mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable:' in line][0].split()[1])
                memory_usage = ((mem_total - mem_available) / mem_total) * 100

                if memory_usage < 80:
                    self.log_success(f"메모리 사용률: {memory_usage:.1f}% (양호)")
                    self.verification_results.append(f"Memory Usage: PASS ({memory_usage:.1f}%)")
                elif memory_usage < 90:
                    self.log_warning(f"메모리 사용률이 높습니다: {memory_usage:.1f}%")
                    self.verification_results.append(f"Memory Usage: WARNING ({memory_usage:.1f}%)")
                    if self.overall_status == "HEALTHY":
                        self.overall_status = "WARNING"
                else:
                    self.log_error(f"메모리 사용률이 위험 수준입니다: {memory_usage:.1f}%")
                    self.verification_results.append(f"Memory Usage: FAIL ({memory_usage:.1f}%)")
                    self.overall_status = "UNHEALTHY"

            except (FileNotFoundError, IndexError):
                self.log_warning("메모리 정보를 읽을 수 없습니다")
                self.verification_results.append("Memory Usage: WARNING (Cannot read)")

            # Disk check
            try:
                result = subprocess.run(["df", "/"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        disk_info = lines[1].split()
                        if len(disk_info) >= 5:
                            disk_usage = int(disk_info[4].rstrip('%'))

                            if disk_usage < 80:
                                self.log_success(f"디스크 사용률: {disk_usage}% (양호)")
                                self.verification_results.append(f"Disk Usage: PASS ({disk_usage}%)")
                            elif disk_usage < 90:
                                self.log_warning(f"디스크 사용률이 높습니다: {disk_usage}%")
                                self.verification_results.append(f"Disk Usage: WARNING ({disk_usage}%)")
                                if self.overall_status == "HEALTHY":
                                    self.overall_status = "WARNING"
                            else:
                                self.log_error(f"디스크 사용률이 위험 수준입니다: {disk_usage}%")
                                self.verification_results.append(f"Disk Usage: FAIL ({disk_usage}%)")
                                self.overall_status = "UNHEALTHY"

            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                self.log_warning("디스크 사용률을 확인할 수 없습니다")
                self.verification_results.append("Disk Usage: WARNING (Command not available)")

            return True

        except Exception as e:
            self.log_error(f"시스템 리소스 검증 실패: {str(e)}")
            self.verification_results.append("System Resources: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def verify_security_configuration(self) -> bool:
        """Verify basic security configuration"""
        self.log_info("보안 설정 검증 중...")

        # Skip security checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 보안 설정 검증을 건너뜁니다")
            self.verification_results.append("Security: SKIPPED (GitHub Actions/Windows)")
            return True

        try:
            security_issues = 0

            # Check for common security headers (if we can access the application)
            try:
                response = requests.get(f"{self.base_url}/api/registration/workflow", timeout=self.timeout)
                headers = response.headers

                # Check for security headers
                security_headers = [
                    'X-Content-Type-Options',
                    'X-Frame-Options',
                    'X-XSS-Protection'
                ]

                missing_headers = []
                for header in security_headers:
                    if header not in headers:
                        missing_headers.append(header)

                if missing_headers:
                    self.log_warning(f"보안 헤더가 누락되었습니다: {', '.join(missing_headers)}")
                    security_issues += 1
                else:
                    self.log_success("보안 헤더가 적절히 설정되어 있습니다")

            except requests.exceptions.RequestException:
                self.log_warning("보안 헤더 확인을 위한 HTTP 요청 실패")
                security_issues += 1

            # Check file permissions (basic check)
            app_dirs = ["/opt/ams-backend", "/opt/ams-backend-blue", "/opt/ams-backend-green"]
            for app_dir in app_dirs:
                if os.path.exists(app_dir):
                    try:
                        # Check if directory is world-writable
                        stat_info = os.stat(app_dir)
                        if stat_info.st_mode & 0o002:  # World-writable
                            self.log_warning(f"애플리케이션 디렉토리가 모든 사용자에게 쓰기 권한이 있습니다: {app_dir}")
                            security_issues += 1
                        else:
                            self.log_success(f"애플리케이션 디렉토리 권한이 적절합니다: {app_dir}")
                    except OSError:
                        self.log_warning(f"디렉토리 권한을 확인할 수 없습니다: {app_dir}")
                    break

            if security_issues == 0:
                self.verification_results.append("Security: PASS")
                return True
            elif security_issues <= 2:
                self.verification_results.append("Security: WARNING")
                if self.overall_status == "HEALTHY":
                    self.overall_status = "WARNING"
                return True
            else:
                self.verification_results.append("Security: FAIL")
                self.overall_status = "UNHEALTHY"
                return False

        except Exception as e:
            self.log_error(f"보안 설정 검증 실패: {str(e)}")
            self.verification_results.append("Security: WARNING")
            if self.overall_status == "HEALTHY":
                self.overall_status = "WARNING"
            return True

    def generate_verification_report(self) -> str:
        """Generate comprehensive verification report"""
        self.log_info("배포 검증 보고서 생성 중...")

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = f"""
=============================================================================
AMS 백엔드 배포 검증 보고서
=============================================================================
검증 시간: {timestamp}
검증 환경: {self.environment}
전체 상태: {self.overall_status}
호스트명: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}

상세 검증 결과:
"""

        for result in self.verification_results:
            report += f"{result}\n"

        report += f"""

검증 설정:
- 최대 응답 시간: {self.max_response_time}초
- 중요 응답 시간: {self.critical_response_time}초
- 재시도 횟수: {self.max_retries}회
- 타임아웃: {self.timeout}초

=============================================================================
"""

        self.log_success("배포 검증 보고서 생성 완료")
        print(report)

        return report

    def run_verification(self) -> int:
        """Run complete deployment verification"""
        self.log_info("===============================================================================")
        self.log_info(f"🔍 AMS 백엔드 배포 검증 시작 (환경: {self.environment})")
        self.log_info("===============================================================================")

        verification_steps = [
            ("서비스 상태", self.verify_service_status),
            ("엔드포인트", self.verify_endpoints),
            ("데이터베이스 연결", self.verify_database_connectivity),
            ("배포 아티팩트", self.verify_deployment_artifacts),
            ("시스템 리소스", self.verify_system_resources),
            ("보안 설정", self.verify_security_configuration)
        ]

        passed_steps = 0
        total_steps = len(verification_steps)

        for step_name, step_func in verification_steps:
            self.log_info(f"📋 {step_name} 검증 중...")
            try:
                if step_func():
                    passed_steps += 1
                    self.log_success(f"✅ {step_name} 검증 통과")
                else:
                    self.log_error(f"❌ {step_name} 검증 실패")
            except Exception as e:
                self.log_error(f"❌ {step_name} 검증 중 오류: {str(e)}")

        # Generate report
        self.generate_verification_report()

        self.log_info("===============================================================================")

        # Determine final result
        if self.overall_status == "HEALTHY":
            self.log_success(f"🎉 배포 검증 성공! ({passed_steps}/{total_steps} 단계 통과)")
            return 0
        elif self.overall_status == "WARNING":
            self.log_warning(f"⚠️ 배포 검증 완료 (경고 있음) ({passed_steps}/{total_steps} 단계 통과)")
            return 1
        else:
            self.log_error(f"💥 배포 검증 실패! ({passed_steps}/{total_steps} 단계 통과)")
            return 2

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="AMS Backend Post-Deployment Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_deployment.py --environment=production
  python verify_deployment.py --environment=staging
        """
    )

    parser.add_argument(
        "--environment",
        required=True,
        choices=["production", "staging", "development"],
        help="Deployment environment to verify"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="AMS Backend Deployment Verification v1.0.0"
    )

    args = parser.parse_args()

    try:
        verifier = DeploymentVerifier(args.environment)
        exit_code = verifier.run_verification()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.error("배포 검증이 사용자에 의해 중단되었습니다")
        sys.exit(3)
    except Exception as e:
        logger.error(f"배포 검증 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()
