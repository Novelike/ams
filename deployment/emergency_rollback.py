#!/usr/bin/env python3
"""
AMS Backend Emergency Rollback Script
Performs emergency rollback when deployment fails.
"""

import sys
import os
import time
import subprocess
import shutil
import requests
from datetime import datetime
from pathlib import Path
import logging
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class EmergencyRollback:
    def __init__(self):
        self.app_name = "ams-backend"
        self.service_name = "ams-backend"
        self.app_dir = os.getenv("APP_DIR", "/opt/ams-backend")
        self.backup_dir = os.getenv("BACKUP_DIR", "/opt/backups/ams-backend")
        self.health_check_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000/api/registration/workflow")
        self.max_health_check_attempts = 30
        self.health_check_interval = 10
        
        # For GitHub Actions environment, we might not have traditional backup directories
        # Instead, we'll try to use Git-based rollback or container-based rollback
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        self.github_workspace = os.getenv("GITHUB_WORKSPACE", ".")
        
    def log_info(self, message: str):
        logger.info(f"🔄 {message}")
    
    def log_success(self, message: str):
        logger.info(f"✅ {message}")
    
    def log_warning(self, message: str):
        logger.warning(f"⚠️ {message}")
    
    def log_error(self, message: str):
        logger.error(f"❌ {message}")
    
    def check_service_status(self) -> bool:
        """Check if service is running"""
        # Skip service checks in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 서비스 상태 확인을 건너뜁니다")
            return False
        
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # In Docker environment, check for processes
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "uvicorn.*main:app"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0 and result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return False
    
    def stop_services(self) -> bool:
        """Stop services safely"""
        self.log_info("서비스 중지 중...")
        
        service_was_active = self.check_service_status()
        
        # Skip service management in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 서비스 중지를 건너뜁니다")
            return service_was_active
        
        try:
            # Try systemctl first
            result = subprocess.run(
                ["systemctl", "stop", self.service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_success("systemd 서비스가 중지되었습니다")
                return service_was_active
            else:
                self.log_warning("systemctl을 사용할 수 없습니다")
                
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_info("systemd를 사용하지 않는 환경입니다")
        
        # Try to kill uvicorn processes (Linux/Unix only)
        try:
            result = subprocess.run(
                ["pkill", "-f", "uvicorn.*main:app"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.log_success("uvicorn 프로세스가 종료되었습니다")
                time.sleep(2)  # Wait for graceful shutdown
            else:
                self.log_warning("실행 중인 uvicorn 프로세스가 없습니다")
                
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_warning("프로세스 종료를 수행할 수 없습니다")
        
        return service_was_active
    
    def start_services(self) -> bool:
        """Start services"""
        self.log_info("서비스 시작 중...")
        
        # Skip service management in GitHub Actions or Windows
        if self.is_github_actions or platform.system() == "Windows":
            self.log_info("GitHub Actions/Windows 환경에서는 서비스 시작을 건너뜁니다")
            return True
        
        try:
            # Try systemctl first
            result = subprocess.run(
                ["systemctl", "start", self.service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_success("systemd 서비스가 시작되었습니다")
                return True
            else:
                self.log_warning("systemctl을 사용할 수 없습니다")
                
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self.log_info("systemd를 사용하지 않는 환경입니다")
        
        # For non-systemd environments, we can't easily restart the service
        self.log_warning("서비스 재시작을 수행할 수 없습니다")
        return False
    
    def health_check(self) -> bool:
        """Perform health check"""
        self.log_info("헬스 체크 수행 중...")
        
        for attempt in range(1, self.max_health_check_attempts + 1):
            try:
                response = requests.get(self.health_check_url, timeout=10)
                
                if response.status_code == 200:
                    self.log_success(f"헬스 체크 성공 (시도 {attempt}/{self.max_health_check_attempts})")
                    return True
                else:
                    self.log_warning(f"헬스 체크 실패 - HTTP {response.status_code} (시도 {attempt}/{self.max_health_check_attempts})")
                    
            except requests.exceptions.RequestException as e:
                self.log_warning(f"헬스 체크 연결 실패 (시도 {attempt}/{self.max_health_check_attempts}): {str(e)}")
            
            if attempt < self.max_health_check_attempts:
                time.sleep(self.health_check_interval)
        
        self.log_error("헬스 체크 최종 실패")
        return False
    
    def list_available_backups(self):
        """List available backups"""
        backups = []
        
        if os.path.exists(self.backup_dir):
            backup_path = Path(self.backup_dir)
            backup_dirs = [d for d in backup_path.iterdir() if d.is_dir() and d.name.startswith("backup_")]
            backups = sorted([str(d) for d in backup_dirs], reverse=True)
        
        return backups
    
    def git_rollback(self) -> bool:
        """Attempt Git-based rollback"""
        self.log_info("Git 기반 롤백 시도 중...")
        
        try:
            # Get current directory (should be the workspace in GitHub Actions)
            work_dir = self.github_workspace if self.is_github_actions else "."
            
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "status"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log_error("Git 저장소가 아닙니다")
                return False
            
            # Get the previous commit
            result = subprocess.run(
                ["git", "log", "--oneline", "-n", "2"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                commits = result.stdout.strip().split('\n')
                if len(commits) >= 2:
                    previous_commit = commits[1].split()[0]
                    self.log_info(f"이전 커밋으로 롤백: {previous_commit}")
                    
                    # Reset to previous commit
                    result = subprocess.run(
                        ["git", "reset", "--hard", previous_commit],
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        self.log_success("Git 롤백 성공")
                        return True
                    else:
                        self.log_error(f"Git 롤백 실패: {result.stderr}")
                        return False
                else:
                    self.log_error("롤백할 이전 커밋이 없습니다")
                    return False
            else:
                self.log_error("Git 로그를 가져올 수 없습니다")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_error("Git 명령 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"Git 롤백 중 오류: {str(e)}")
            return False
    
    def backup_rollback(self) -> bool:
        """Attempt backup-based rollback"""
        self.log_info("백업 기반 롤백 시도 중...")
        
        available_backups = self.list_available_backups()
        
        if not available_backups:
            self.log_error("사용 가능한 백업이 없습니다")
            return False
        
        # Use the latest backup
        latest_backup = available_backups[0]
        self.log_info(f"최신 백업 사용: {os.path.basename(latest_backup)}")
        
        try:
            # Create emergency backup of current state
            if os.path.exists(self.app_dir):
                emergency_backup = f"{self.backup_dir}/emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(os.path.dirname(emergency_backup), exist_ok=True)
                shutil.copytree(self.app_dir, emergency_backup)
                self.log_success(f"긴급 백업 생성: {emergency_backup}")
            
            # Restore from backup
            if os.path.exists(self.app_dir):
                shutil.rmtree(self.app_dir)
            
            shutil.copytree(latest_backup, self.app_dir)
            self.log_success("백업에서 복원 완료")
            
            return True
            
        except Exception as e:
            self.log_error(f"백업 롤백 중 오류: {str(e)}")
            return False
    
    def container_rollback(self) -> bool:
        """Attempt container-based rollback (for Docker environments)"""
        self.log_info("컨테이너 기반 롤백 시도 중...")
        
        try:
            # Check if Docker is available
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self.log_warning("Docker를 사용할 수 없습니다")
                return False
            
            # Try to restart the container with previous image
            # This is a simplified approach - in real scenarios, you'd have more sophisticated logic
            container_name = f"{self.app_name}-container"
            
            # Stop current container
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=30
            )
            
            # Remove current container
            subprocess.run(
                ["docker", "rm", container_name],
                capture_output=True,
                timeout=30
            )
            
            self.log_info("컨테이너 롤백은 수동으로 수행해야 합니다")
            return False
            
        except subprocess.TimeoutExpired:
            self.log_error("Docker 명령 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"컨테이너 롤백 중 오류: {str(e)}")
            return False
    
    def generate_rollback_report(self, success: bool, method: str):
        """Generate rollback report"""
        self.log_info("롤백 보고서 생성 중...")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "성공" if success else "실패"
        
        report = f"""
=============================================================================
AMS 백엔드 긴급 롤백 보고서
=============================================================================
롤백 시간: {timestamp}
롤백 방법: {method}
롤백 상태: {status}
환경: {"GitHub Actions" if self.is_github_actions else "일반 서버"}

시스템 정보:
- 호스트명: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}
- 작업 디렉토리: {os.getcwd()}
- 애플리케이션 디렉토리: {self.app_dir}

롤백 결과: {"성공적으로 완료되었습니다" if success else "실패했습니다"}
=============================================================================
"""
        
        print(report)
        self.log_success("롤백 보고서 생성 완료")
    
    def run_emergency_rollback(self) -> int:
        """Run emergency rollback process"""
        self.log_info("===============================================================================")
        self.log_info("🚨 AMS 백엔드 긴급 롤백 시작")
        self.log_info("===============================================================================")
        
        rollback_success = False
        rollback_method = "없음"
        
        # Record original service state
        service_was_active = self.stop_services()
        
        # Try different rollback methods in order of preference
        rollback_methods = [
            ("Git 기반", self.git_rollback),
            ("백업 기반", self.backup_rollback),
            ("컨테이너 기반", self.container_rollback)
        ]
        
        for method_name, method_func in rollback_methods:
            self.log_info(f"{method_name} 롤백 시도...")
            
            try:
                if method_func():
                    rollback_success = True
                    rollback_method = method_name
                    self.log_success(f"{method_name} 롤백 성공")
                    break
                else:
                    self.log_warning(f"{method_name} 롤백 실패")
            except Exception as e:
                self.log_error(f"{method_name} 롤백 중 오류: {str(e)}")
        
        # Try to restart services if rollback was successful
        if rollback_success:
            if service_was_active:
                self.log_info("서비스 재시작 시도...")
                if self.start_services():
                    # Perform health check
                    if self.health_check():
                        self.log_success("롤백 후 헬스 체크 성공")
                    else:
                        self.log_error("롤백 후 헬스 체크 실패")
                        rollback_success = False
                else:
                    self.log_error("서비스 재시작 실패")
                    rollback_success = False
            else:
                self.log_info("원래 서비스가 실행되지 않았으므로 재시작하지 않습니다")
        
        # Generate report
        self.generate_rollback_report(rollback_success, rollback_method)
        
        self.log_info("===============================================================================")
        
        if rollback_success:
            self.log_success("🎉 긴급 롤백이 성공적으로 완료되었습니다!")
            return 0
        else:
            self.log_error("💥 긴급 롤백이 실패했습니다!")
            return 1

def main():
    """Main function"""
    try:
        rollback = EmergencyRollback()
        exit_code = rollback.run_emergency_rollback()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.error("긴급 롤백이 사용자에 의해 중단되었습니다")
        sys.exit(2)
    except Exception as e:
        logger.error(f"긴급 롤백 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()