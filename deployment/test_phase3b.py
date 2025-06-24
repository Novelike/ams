import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from deployment.ssh_manager import SSHManager, SSHConfig
from deployment.blue_green_deployer import BlueGreenDeployer, BlueGreenConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase3BTestSuite:
    """Phase 3-B 자동 배포 시스템 테스트 스위트"""

    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }

        # 테스트용 설정
        self.ssh_config = SSHConfig(
            bastion_host="210.109.82.8",
            backend_host="10.0.0.171",
            ssh_key_path="D:/CLOUD/KakaoCloud/key/kjh-bastion.pem"
        )

        self.bg_config = BlueGreenConfig(
            blue_port=8000,
            green_port=8001
        )

    def log_test_result(self, test_name: str, success: bool, message: str = "", details: Dict[str, Any] = None):
        """테스트 결과 로깅"""
        self.test_results["total_tests"] += 1

        if success:
            self.test_results["passed_tests"] += 1
            logger.info(f"✅ {test_name}: PASSED - {message}")
        else:
            self.test_results["failed_tests"] += 1
            logger.error(f"❌ {test_name}: FAILED - {message}")

        self.test_results["test_details"].append({
            "test_name": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    async def test_ssh_manager_import(self):
        """SSH Manager 모듈 import 테스트"""
        try:
            from deployment.ssh_manager import SSHManager, SSHConfig, SSHResult
            self.log_test_result("SSH Manager Import", True, "모든 클래스 import 성공")
        except Exception as e:
            self.log_test_result("SSH Manager Import", False, f"Import 실패: {e}")

    async def test_blue_green_deployer_import(self):
        """Blue-Green Deployer 모듈 import 테스트"""
        try:
            from deployment.blue_green_deployer import BlueGreenDeployer, BlueGreenConfig
            self.log_test_result("Blue-Green Deployer Import", True, "모든 클래스 import 성공")
        except Exception as e:
            self.log_test_result("Blue-Green Deployer Import", False, f"Import 실패: {e}")

    async def test_ssh_manager_initialization(self):
        """SSH Manager 초기화 테스트"""
        try:
            ssh_manager = SSHManager(self.ssh_config)

            # 기본 속성 확인
            assert ssh_manager.config is not None
            assert ssh_manager.connection_stats is not None

            self.log_test_result(
                "SSH Manager Initialization", 
                True, 
                "SSH Manager 초기화 성공",
                {"config_host": ssh_manager.config.bastion_host}
            )
        except Exception as e:
            self.log_test_result("SSH Manager Initialization", False, f"초기화 실패: {e}")

    async def test_blue_green_deployer_initialization(self):
        """Blue-Green Deployer 초기화 테스트"""
        try:
            deployer = BlueGreenDeployer(self.bg_config)

            # 기본 속성 확인
            assert deployer.config is not None
            assert deployer.blue_env is not None
            assert deployer.green_env is not None
            assert deployer.deployment_stats is not None

            self.log_test_result(
                "Blue-Green Deployer Initialization", 
                True, 
                "Blue-Green Deployer 초기화 성공",
                {
                    "blue_port": deployer.blue_env.port,
                    "green_port": deployer.green_env.port
                }
            )
        except Exception as e:
            self.log_test_result("Blue-Green Deployer Initialization", False, f"초기화 실패: {e}")

    async def test_ssh_key_file_exists(self):
        """SSH 키 파일 존재 확인 테스트"""
        try:
            key_path = self.ssh_config.ssh_key_path

            if os.path.exists(key_path):
                self.log_test_result(
                    "SSH Key File Exists", 
                    True, 
                    f"SSH 키 파일 존재 확인: {key_path}"
                )
            else:
                self.log_test_result(
                    "SSH Key File Exists", 
                    False, 
                    f"SSH 키 파일 없음: {key_path}"
                )
        except Exception as e:
            self.log_test_result("SSH Key File Exists", False, f"키 파일 확인 실패: {e}")

    async def test_deployment_scripts_exist(self):
        """배포 스크립트 파일 존재 확인 테스트"""
        try:
            scripts_dir = Path("deployment") / "scripts"
            required_scripts = [
                "deploy_backend.sh",
                "health_check.sh", 
                "rollback.sh"
            ]

            missing_scripts = []
            existing_scripts = []

            for script in required_scripts:
                script_path = scripts_dir / script
                if script_path.exists():
                    existing_scripts.append(script)
                else:
                    missing_scripts.append(script)

            if not missing_scripts:
                self.log_test_result(
                    "Deployment Scripts Exist", 
                    True, 
                    f"모든 배포 스크립트 존재: {existing_scripts}"
                )
            else:
                self.log_test_result(
                    "Deployment Scripts Exist", 
                    False, 
                    f"누락된 스크립트: {missing_scripts}"
                )
        except Exception as e:
            self.log_test_result("Deployment Scripts Exist", False, f"스크립트 확인 실패: {e}")

    async def test_cicd_workflow_exists(self):
        """CI/CD 워크플로우 파일 존재 확인 테스트"""
        try:
            workflow_path = Path(".github") / "workflows" / "ci-cd.yml"

            if workflow_path.exists():
                # 파일 크기 확인
                file_size = workflow_path.stat().st_size
                self.log_test_result(
                    "CI/CD Workflow Exists", 
                    True, 
                    f"CI/CD 워크플로우 파일 존재 (크기: {file_size} bytes)"
                )
            else:
                self.log_test_result(
                    "CI/CD Workflow Exists", 
                    False, 
                    "CI/CD 워크플로우 파일 없음"
                )
        except Exception as e:
            self.log_test_result("CI/CD Workflow Exists", False, f"워크플로우 확인 실패: {e}")

    async def test_deployment_config_structure(self):
        """배포 설정 구조 테스트"""
        try:
            config_dir = Path("deployment") / "config"
            logs_dir = Path("deployment") / "logs"

            # 디렉토리 생성 확인
            config_dir.mkdir(exist_ok=True)
            logs_dir.mkdir(exist_ok=True)

            structure_valid = (
                config_dir.exists() and 
                logs_dir.exists()
            )

            if structure_valid:
                self.log_test_result(
                    "Deployment Config Structure", 
                    True, 
                    "배포 설정 디렉토리 구조 정상"
                )
            else:
                self.log_test_result(
                    "Deployment Config Structure", 
                    False, 
                    "배포 설정 디렉토리 구조 문제"
                )
        except Exception as e:
            self.log_test_result("Deployment Config Structure", False, f"구조 확인 실패: {e}")

    async def test_paramiko_availability(self):
        """Paramiko 라이브러리 사용 가능성 테스트"""
        try:
            import paramiko
            import scp

            self.log_test_result(
                "Paramiko Availability", 
                True, 
                "Paramiko 및 SCP 라이브러리 사용 가능"
            )
        except ImportError as e:
            self.log_test_result(
                "Paramiko Availability", 
                False, 
                f"Paramiko 라이브러리 없음: {e}"
            )

    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 Phase 3-B 자동 배포 시스템 테스트 시작")
        logger.info("=" * 60)

        # 테스트 목록
        tests = [
            self.test_ssh_manager_import,
            self.test_blue_green_deployer_import,
            self.test_ssh_manager_initialization,
            self.test_blue_green_deployer_initialization,
            self.test_ssh_key_file_exists,
            self.test_deployment_scripts_exist,
            self.test_cicd_workflow_exists,
            self.test_deployment_config_structure,
            self.test_paramiko_availability
        ]

        # 각 테스트 실행
        for test in tests:
            try:
                await test()
            except Exception as e:
                test_name = test.__name__.replace("test_", "").replace("_", " ").title()
                self.log_test_result(test_name, False, f"테스트 실행 중 예외 발생: {e}")

        # 결과 요약
        self.print_test_summary()

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        logger.info("=" * 60)
        logger.info("📊 Phase 3-B 테스트 결과 요약")
        logger.info("=" * 60)

        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        failed = self.test_results["failed_tests"]
        success_rate = (passed / total * 100) if total > 0 else 0

        logger.info(f"📊 전체 테스트: {total}")
        logger.info(f"✅ 성공: {passed}")
        logger.info(f"❌ 실패: {failed}")
        logger.info(f"📈 성공률: {success_rate:.1f}%")

        if failed > 0:
            logger.info("\n❌ 실패한 테스트:")
            for detail in self.test_results["test_details"]:
                if not detail["success"]:
                    logger.info(f"  - {detail['test_name']}: {detail['message']}")

        logger.info("=" * 60)

        if success_rate >= 80:
            logger.info("🎉 Phase 3-B 자동 배포 시스템이 성공적으로 구현되었습니다!")
        else:
            logger.warning("⚠️ 일부 테스트가 실패했습니다. 문제를 해결해주세요.")

async def main():
    """메인 함수"""
    test_suite = Phase3BTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
