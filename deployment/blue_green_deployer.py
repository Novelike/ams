import asyncio
import logging
import time
import json
import shutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum

from deployment.ssh_manager import get_ssh_manager, SSHManager, SSHResult

logger = logging.getLogger(__name__)

class DeploymentEnvironment(Enum):
    """배포 환경"""
    BLUE = "blue"
    GREEN = "green"

class DeploymentStatus(Enum):
    """배포 상태"""
    IDLE = "idle"
    PREPARING = "preparing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    SWITCHING = "switching"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"

@dataclass
class BlueGreenConfig:
    """Blue-Green 배포 설정"""
    blue_port: int = 8000
    green_port: int = 8001
    nginx_config_path: str = "/etc/nginx/sites-available/ams"
    nginx_enabled_path: str = "/etc/nginx/sites-enabled/ams"
    app_base_dir: str = "/opt"
    app_name: str = "ams-backend"
    health_check_url_template: str = "http://localhost:{port}/api/registration/workflow"
    health_check_timeout: int = 30
    health_check_interval: int = 5
    max_health_check_attempts: int = 12
    traffic_switch_delay: int = 10
    rollback_timeout: int = 300

@dataclass
class EnvironmentInfo:
    """환경 정보"""
    name: DeploymentEnvironment
    port: int
    app_dir: str
    service_name: str
    is_active: bool = False
    is_healthy: bool = False
    version: Optional[str] = None
    last_deployed: Optional[datetime] = None

@dataclass
class DeploymentResult:
    """배포 결과"""
    success: bool
    environment: DeploymentEnvironment
    version: str
    deployment_time: float
    status: DeploymentStatus
    error_message: Optional[str] = None
    rollback_performed: bool = False

class BlueGreenDeployer:
    """
    Blue-Green 배포 관리자
    - 무중단 배포 구현
    - 트래픽 전환 관리
    - 자동 롤백 기능
    - 헬스 체크 및 검증
    """

    def __init__(self, config: BlueGreenConfig = None):
        self.config = config or BlueGreenConfig()
        self.ssh_manager: Optional[SSHManager] = None

        # 환경 정보
        self.blue_env = EnvironmentInfo(
            name=DeploymentEnvironment.BLUE,
            port=self.config.blue_port,
            app_dir=f"{self.config.app_base_dir}/{self.config.app_name}-blue",
            service_name=f"{self.config.app_name}-blue"
        )

        self.green_env = EnvironmentInfo(
            name=DeploymentEnvironment.GREEN,
            port=self.config.green_port,
            app_dir=f"{self.config.app_base_dir}/{self.config.app_name}-green",
            service_name=f"{self.config.app_name}-green"
        )

        # 배포 상태
        self.current_status = DeploymentStatus.IDLE
        self.active_environment: Optional[DeploymentEnvironment] = None
        self.standby_environment: Optional[DeploymentEnvironment] = None

        # 통계
        self.deployment_stats = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "rollbacks_performed": 0,
            "average_deployment_time": 0.0,
            "last_deployment": None
        }

        # 초기화
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """비동기 초기화"""
        try:
            # SSH 관리자 초기화
            self.ssh_manager = await get_ssh_manager()

            # 현재 환경 상태 확인
            await self._detect_current_environment()

            logger.info("Blue-Green Deployer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Blue-Green Deployer: {e}")

    async def _detect_current_environment(self):
        """현재 활성 환경 감지"""
        try:
            # Nginx 설정에서 현재 활성 포트 확인
            nginx_config = await self._get_nginx_config()

            if f":{self.config.blue_port}" in nginx_config:
                self.active_environment = DeploymentEnvironment.BLUE
                self.standby_environment = DeploymentEnvironment.GREEN
                self.blue_env.is_active = True
            elif f":{self.config.green_port}" in nginx_config:
                self.active_environment = DeploymentEnvironment.GREEN
                self.standby_environment = DeploymentEnvironment.BLUE
                self.green_env.is_active = True
            else:
                # 기본값으로 Blue를 활성으로 설정
                self.active_environment = DeploymentEnvironment.BLUE
                self.standby_environment = DeploymentEnvironment.GREEN
                self.blue_env.is_active = True

            # 환경 상태 업데이트
            await self._update_environment_status()

            logger.info(f"Current active environment: {self.active_environment.value}")

        except Exception as e:
            logger.error(f"Failed to detect current environment: {e}")
            # 기본값 설정
            self.active_environment = DeploymentEnvironment.BLUE
            self.standby_environment = DeploymentEnvironment.GREEN

    async def _detect_initial_deployment(self) -> bool:
        """최초 배포인지 확인"""
        try:
            # Blue, Green 환경 모두 확인
            blue_exists = await self._check_environment_exists(DeploymentEnvironment.BLUE)
            green_exists = await self._check_environment_exists(DeploymentEnvironment.GREEN)

            return not (blue_exists or green_exists)
        except Exception as e:
            logger.warning(f"환경 감지 실패, 최초 배포로 간주: {e}")
            return True

    async def _check_environment_exists(self, environment: DeploymentEnvironment) -> bool:
        """환경이 존재하는지 확인"""
        try:
            env_config = self._get_environment_config(environment)

            # 서비스 상태 확인
            check_command = f"systemctl is-active {env_config.service_name} || echo 'inactive'"
            result = await self.ssh_manager.execute_command(check_command)

            if result.success and "active" in result.stdout:
                logger.info(f"{environment.value} 환경이 실행 중입니다")
                return True
            else:
                logger.info(f"{environment.value} 환경이 비활성 상태입니다")
                return False

        except Exception as e:
            logger.warning(f"{environment.value} 환경 확인 실패: {e}")
            return False

    async def _initial_deployment(self, branch: str) -> DeploymentResult:
        """최초 배포 실행"""
        start_time = time.time()
        logger.info("최초 배포를 시작합니다")

        try:
            self.current_status = DeploymentStatus.PREPARING

            # Blue 환경에 직접 배포
            logger.info("Blue 환경에 최초 배포 중...")
            await self._deploy_to_environment(DeploymentEnvironment.BLUE, branch)

            # 헬스 체크
            self.current_status = DeploymentStatus.TESTING
            if not await self._health_check_environment(DeploymentEnvironment.BLUE):
                raise Exception("Initial deployment health check failed")

            # Nginx 설정
            await self._configure_nginx_for_environment(DeploymentEnvironment.BLUE)

            # 환경 설정 업데이트
            self.active_environment = DeploymentEnvironment.BLUE
            self.standby_environment = DeploymentEnvironment.GREEN

            deployment_time = time.time() - start_time

            # 통계 업데이트
            await self._update_deployment_stats(True, deployment_time)

            self.current_status = DeploymentStatus.COMPLETED

            result = DeploymentResult(
                success=True,
                environment=DeploymentEnvironment.BLUE,
                version=branch,
                deployment_time=deployment_time,
                status=self.current_status
            )

            logger.info(f"최초 배포가 성공적으로 완료되었습니다 ({deployment_time:.2f}s)")
            self.current_status = DeploymentStatus.IDLE

            return result

        except Exception as e:
            logger.error(f"최초 배포 실패: {e}")
            deployment_time = time.time() - start_time
            await self._update_deployment_stats(False, deployment_time)

            self.current_status = DeploymentStatus.FAILED

            return DeploymentResult(
                success=False,
                environment=DeploymentEnvironment.BLUE,
                version=branch,
                deployment_time=deployment_time,
                status=self.current_status,
                error_message=str(e)
            )

    async def deploy(self, branch: str = "main", force: bool = False) -> DeploymentResult:
        """배포 실행 (최초 배포 고려)"""
        start_time = time.time()

        try:
            if self.current_status != DeploymentStatus.IDLE and not force:
                raise Exception(f"Deployment already in progress: {self.current_status.value}")

            # 최초 배포 감지
            is_initial = await self._detect_initial_deployment()

            if is_initial:
                logger.info("최초 배포가 감지되었습니다")
                return await self._initial_deployment(branch)

            # 기존 Blue-Green 배포 로직
            self.current_status = DeploymentStatus.PREPARING

            logger.info(f"Starting Blue-Green deployment (branch: {branch})")
            logger.info(f"Active: {self.active_environment.value}, Standby: {self.standby_environment.value}")

            # 1. 대기 환경 준비
            await self._prepare_standby_environment()

            # 2. 대기 환경에 배포
            self.current_status = DeploymentStatus.DEPLOYING
            await self._deploy_to_standby(branch)

            # 3. 대기 환경 헬스 체크
            self.current_status = DeploymentStatus.TESTING
            if not await self._health_check_standby():
                raise Exception("Standby environment health check failed")

            # 4. 트래픽 전환
            self.current_status = DeploymentStatus.SWITCHING
            await self._switch_traffic()

            # 5. 최종 검증
            if not await self._verify_deployment():
                raise Exception("Final deployment verification failed")

            # 6. 배포 완료
            self.current_status = DeploymentStatus.COMPLETED
            deployment_time = time.time() - start_time

            # 통계 업데이트
            await self._update_deployment_stats(True, deployment_time)

            result = DeploymentResult(
                success=True,
                environment=self.standby_environment,
                version=branch,
                deployment_time=deployment_time,
                status=self.current_status
            )

            logger.info(f"Blue-Green deployment completed successfully in {deployment_time:.2f}s")

            # 환경 전환
            await self._swap_environments()

            self.current_status = DeploymentStatus.IDLE

            return result

        except Exception as e:
            logger.error(f"Blue-Green deployment failed: {e}")

            # 롤백 수행
            self.current_status = DeploymentStatus.ROLLING_BACK
            rollback_success = await self._rollback_deployment()

            deployment_time = time.time() - start_time
            await self._update_deployment_stats(False, deployment_time)

            self.current_status = DeploymentStatus.FAILED if not rollback_success else DeploymentStatus.IDLE

            return DeploymentResult(
                success=False,
                environment=self.standby_environment,
                version=branch,
                deployment_time=deployment_time,
                status=self.current_status,
                error_message=str(e),
                rollback_performed=rollback_success
            )

    async def _prepare_standby_environment(self):
        """대기 환경 준비"""
        logger.info("Preparing standby environment...")

        standby_env = self._get_standby_env()

        # 대기 환경 서비스 중지
        await self._stop_environment_service(standby_env)

        # 디렉토리 준비
        await self._prepare_environment_directory(standby_env)

        logger.info("Standby environment prepared")

    async def _deploy_to_standby(self, branch: str):
        """대기 환경에 배포"""
        logger.info(f"Deploying to standby environment: {self.standby_environment.value}")

        standby_env = self._get_standby_env()

        # 배포 스크립트 실행
        deploy_script = "deployment/scripts/deploy_backend.sh"

        # 배포 스크립트를 대기 환경용으로 수정하여 실행
        deploy_command = f"""
        export APP_DIR="{standby_env.app_dir}"
        export SERVICE_NAME="{standby_env.service_name}"
        export APP_PORT="{standby_env.port}"
        bash {deploy_script} {branch}
        """

        result = await self.ssh_manager.execute_command(deploy_command)

        if result.exit_code != 0:
            raise Exception(f"Deployment to standby failed: {result.stderr}")

        logger.info("Deployment to standby environment completed")

    async def _health_check_standby(self) -> bool:
        """대기 환경 헬스 체크"""
        logger.info("Performing health check on standby environment...")

        standby_env = self._get_standby_env()
        health_url = self.config.health_check_url_template.format(port=standby_env.port)

        for attempt in range(self.config.max_health_check_attempts):
            logger.info(f"Health check attempt {attempt + 1}/{self.config.max_health_check_attempts}")

            # HTTP 헬스 체크
            check_command = f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {self.config.health_check_timeout} {health_url}"
            result = await self.ssh_manager.execute_command(check_command)

            if result.exit_code == 0 and result.stdout.strip() == "200":
                logger.info("Standby environment health check passed")
                standby_env.is_healthy = True
                return True

            if attempt < self.config.max_health_check_attempts - 1:
                await asyncio.sleep(self.config.health_check_interval)

        logger.error("Standby environment health check failed")
        return False

    async def _switch_traffic(self):
        """트래픽 전환"""
        logger.info("Switching traffic to standby environment...")

        standby_env = self._get_standby_env()

        # Nginx 설정 업데이트
        await self._update_nginx_config(standby_env.port)

        # Nginx 리로드
        await self._reload_nginx()

        # 전환 지연
        await asyncio.sleep(self.config.traffic_switch_delay)

        logger.info("Traffic switched successfully")

    async def _verify_deployment(self) -> bool:
        """배포 검증"""
        logger.info("Verifying deployment...")

        # 새로운 활성 환경 헬스 체크
        standby_env = self._get_standby_env()
        health_url = self.config.health_check_url_template.format(port=standby_env.port)

        # 외부에서 접근 가능한지 확인 (Nginx를 통해)
        external_check_command = f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 10 http://localhost/api/registration/workflow"
        result = await self.ssh_manager.execute_command(external_check_command)

        if result.exit_code == 0 and result.stdout.strip() == "200":
            logger.info("Deployment verification passed")
            return True

        logger.error("Deployment verification failed")
        return False

    async def _rollback_deployment(self) -> bool:
        """배포 롤백"""
        logger.info("Rolling back deployment...")

        try:
            # 이전 활성 환경으로 트래픽 복원
            active_env = self._get_active_env()
            await self._update_nginx_config(active_env.port)
            await self._reload_nginx()

            # 대기 환경 서비스 중지
            standby_env = self._get_standby_env()
            await self._stop_environment_service(standby_env)

            # 롤백 통계 업데이트
            self.deployment_stats["rollbacks_performed"] += 1

            logger.info("Rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def _swap_environments(self):
        """환경 전환"""
        # 활성/대기 환경 교체
        old_active = self.active_environment
        old_standby = self.standby_environment

        self.active_environment = old_standby
        self.standby_environment = old_active

        # 환경 정보 업데이트
        if self.active_environment == DeploymentEnvironment.BLUE:
            self.blue_env.is_active = True
            self.green_env.is_active = False
        else:
            self.green_env.is_active = True
            self.blue_env.is_active = False

        logger.info(f"Environments swapped: Active={self.active_environment.value}, Standby={self.standby_environment.value}")

    async def _get_nginx_config(self) -> str:
        """Nginx 설정 조회"""
        result = await self.ssh_manager.execute_command(f"cat {self.config.nginx_config_path}")
        return result.stdout if result.exit_code == 0 else ""

    async def _update_nginx_config(self, port: int):
        """Nginx 설정 업데이트"""
        logger.info(f"Updating Nginx config to use port {port}")

        # Nginx 설정 템플릿
        nginx_config = f"""
server {{
    listen 80;
    server_name _;

    location / {{
        proxy_pass http://localhost:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 버퍼링 설정
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }}

    # 헬스 체크 엔드포인트
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}
"""

        # 설정 파일 업데이트
        update_command = f"echo '{nginx_config}' | sudo tee {self.config.nginx_config_path} > /dev/null"
        result = await self.ssh_manager.execute_command(update_command)

        if result.exit_code != 0:
            raise Exception(f"Failed to update Nginx config: {result.stderr}")

        # 심볼릭 링크 생성 (필요한 경우)
        link_command = f"sudo ln -sf {self.config.nginx_config_path} {self.config.nginx_enabled_path}"
        await self.ssh_manager.execute_command(link_command)

    async def _reload_nginx(self):
        """Nginx 리로드"""
        logger.info("Reloading Nginx...")

        # 설정 테스트
        test_result = await self.ssh_manager.execute_command("sudo nginx -t")
        if test_result.exit_code != 0:
            raise Exception(f"Nginx config test failed: {test_result.stderr}")

        # Nginx 리로드
        reload_result = await self.ssh_manager.execute_command("sudo systemctl reload nginx")
        if reload_result.exit_code != 0:
            raise Exception(f"Nginx reload failed: {reload_result.stderr}")

        logger.info("Nginx reloaded successfully")

    async def _stop_environment_service(self, env: EnvironmentInfo):
        """환경 서비스 중지"""
        logger.info(f"Stopping service: {env.service_name}")

        # 서비스 중지
        stop_command = f"sudo systemctl stop {env.service_name} || true"
        await self.ssh_manager.execute_command(stop_command)

        # 프로세스 강제 종료
        kill_command = f"pkill -f 'uvicorn.*--port {env.port}' || true"
        await self.ssh_manager.execute_command(kill_command)

    async def _prepare_environment_directory(self, env: EnvironmentInfo):
        """환경 디렉토리 준비"""
        logger.info(f"Preparing directory: {env.app_dir}")

        # 디렉토리 생성
        mkdir_command = f"sudo mkdir -p {env.app_dir}"
        await self.ssh_manager.execute_command(mkdir_command)

        # 권한 설정
        chown_command = f"sudo chown -R ubuntu:ubuntu {env.app_dir}"
        await self.ssh_manager.execute_command(chown_command)

    async def _update_environment_status(self):
        """환경 상태 업데이트"""
        try:
            # Blue 환경 상태 확인
            blue_health = await self._check_environment_health(self.blue_env)
            self.blue_env.is_healthy = blue_health

            # Green 환경 상태 확인
            green_health = await self._check_environment_health(self.green_env)
            self.green_env.is_healthy = green_health

        except Exception as e:
            logger.error(f"Failed to update environment status: {e}")

    async def _check_environment_health(self, env: EnvironmentInfo) -> bool:
        """환경 헬스 체크"""
        try:
            health_url = self.config.health_check_url_template.format(port=env.port)
            check_command = f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 {health_url}"
            result = await self.ssh_manager.execute_command(check_command)

            return result.exit_code == 0 and result.stdout.strip() == "200"

        except Exception:
            return False

    async def _update_deployment_stats(self, success: bool, deployment_time: float):
        """배포 통계 업데이트"""
        self.deployment_stats["total_deployments"] += 1

        if success:
            self.deployment_stats["successful_deployments"] += 1
        else:
            self.deployment_stats["failed_deployments"] += 1

        # 평균 배포 시간 계산
        total = self.deployment_stats["total_deployments"]
        current_avg = self.deployment_stats["average_deployment_time"]
        self.deployment_stats["average_deployment_time"] = (
            (current_avg * (total - 1) + deployment_time) / total
        )

        self.deployment_stats["last_deployment"] = datetime.utcnow().isoformat()

    def _get_active_env(self) -> EnvironmentInfo:
        """활성 환경 정보 반환"""
        return self.blue_env if self.active_environment == DeploymentEnvironment.BLUE else self.green_env

    def _get_standby_env(self) -> EnvironmentInfo:
        """대기 환경 정보 반환"""
        return self.blue_env if self.standby_environment == DeploymentEnvironment.BLUE else self.green_env

    async def get_status(self) -> Dict[str, Any]:
        """배포 상태 조회"""
        await self._update_environment_status()

        return {
            "current_status": self.current_status.value,
            "active_environment": self.active_environment.value if self.active_environment else None,
            "standby_environment": self.standby_environment.value if self.standby_environment else None,
            "environments": {
                "blue": asdict(self.blue_env),
                "green": asdict(self.green_env)
            },
            "deployment_stats": dict(self.deployment_stats),
            "config": {
                "blue_port": self.config.blue_port,
                "green_port": self.config.green_port,
                "health_check_timeout": self.config.health_check_timeout,
                "max_health_check_attempts": self.config.max_health_check_attempts
            }
        }

    async def force_switch_environment(self) -> bool:
        """강제 환경 전환"""
        try:
            logger.info("Forcing environment switch...")

            if self.current_status != DeploymentStatus.IDLE:
                logger.warning(f"Forcing switch during {self.current_status.value}")

            # 대기 환경이 건강한지 확인
            standby_env = self._get_standby_env()
            if not await self._check_environment_health(standby_env):
                logger.error("Standby environment is not healthy")
                return False

            # 트래픽 전환
            await self._switch_traffic()

            # 환경 교체
            await self._swap_environments()

            logger.info("Environment switch completed")
            return True

        except Exception as e:
            logger.error(f"Force switch failed: {e}")
            return False

    async def emergency_rollback(self) -> bool:
        """긴급 롤백"""
        try:
            logger.info("Performing emergency rollback...")

            self.current_status = DeploymentStatus.ROLLING_BACK

            # 이전 활성 환경으로 복원
            success = await self._rollback_deployment()

            self.current_status = DeploymentStatus.IDLE if success else DeploymentStatus.FAILED

            return success

        except Exception as e:
            logger.error(f"Emergency rollback failed: {e}")
            self.current_status = DeploymentStatus.FAILED
            return False


# 전역 Blue-Green 배포자 인스턴스
_blue_green_deployer = None

async def get_blue_green_deployer() -> BlueGreenDeployer:
    """Blue-Green 배포자 싱글톤 인스턴스 반환"""
    global _blue_green_deployer
    if _blue_green_deployer is None:
        _blue_green_deployer = BlueGreenDeployer()
    return _blue_green_deployer
