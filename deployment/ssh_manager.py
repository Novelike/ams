import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

try:
    import paramiko
    import scp
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    logging.warning("Paramiko not available. Install with: pip install paramiko scp")

logger = logging.getLogger(__name__)

@dataclass
class SSHConfig:
    """SSH 연결 설정"""
    bastion_host: str
    bastion_port: int = 22
    bastion_user: str = "ubuntu"
    backend_host: str = "10.0.0.171"
    backend_port: int = 22
    backend_user: str = "ubuntu"
    ssh_key_path: str = "D:/CLOUD/KakaoCloud/key/kjh-bastion.pem"
    connection_timeout: int = 30
    command_timeout: int = 300

@dataclass
class SSHResult:
    """SSH 명령 실행 결과"""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    host: str

@dataclass
class FileTransferResult:
    """파일 전송 결과"""
    success: bool
    local_path: str
    remote_path: str
    file_size: int
    transfer_time: float
    error_message: Optional[str] = None

class SSHManager:
    """
    SSH 연결 관리자
    - Bastion Host를 통한 Backend 서버 접근
    - 원격 명령 실행
    - 파일 업로드/다운로드
    - 연결 풀링 및 재사용
    """

    def __init__(self, config: SSHConfig = None):
        self.config = config or SSHConfig(
            bastion_host="210.109.82.8",
            backend_host="10.0.0.171",
            ssh_key_path="D:/CLOUD/KakaoCloud/key/kjh-bastion.pem"
        )
        
        # 연결 풀
        self.bastion_client: Optional[paramiko.SSHClient] = None
        self.backend_client: Optional[paramiko.SSHClient] = None
        self.tunnel_transport: Optional[paramiko.Transport] = None
        
        # 통계
        self.connection_stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "total_transfers": 0,
            "successful_transfers": 0,
            "failed_transfers": 0
        }
        
        # 로깅 설정
        self.setup_logging()

    def setup_logging(self):
        """로깅 설정"""
        log_dir = Path("deployment/logs")
        log_dir.mkdir(exist_ok=True)
        
        # SSH 전용 로거 설정
        ssh_logger = logging.getLogger("ssh_manager")
        ssh_logger.setLevel(logging.INFO)
        
        # 파일 핸들러
        log_file = log_dir / f"ssh_manager_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        ssh_logger.addHandler(file_handler)

    async def connect_to_bastion(self) -> bool:
        """Bastion Host에 연결"""
        try:
            if not PARAMIKO_AVAILABLE:
                logger.error("Paramiko not available")
                return False

            logger.info(f"Connecting to bastion host: {self.config.bastion_host}")
            
            self.bastion_client = paramiko.SSHClient()
            self.bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # SSH 키 로드
            if not os.path.exists(self.config.ssh_key_path):
                logger.error(f"SSH key not found: {self.config.ssh_key_path}")
                return False
            
            key = paramiko.RSAKey.from_private_key_file(self.config.ssh_key_path)
            
            # Bastion 연결
            self.bastion_client.connect(
                hostname=self.config.bastion_host,
                port=self.config.bastion_port,
                username=self.config.bastion_user,
                pkey=key,
                timeout=self.config.connection_timeout
            )
            
            self.connection_stats["total_connections"] += 1
            self.connection_stats["successful_connections"] += 1
            
            logger.info("Successfully connected to bastion host")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to bastion host: {e}")
            self.connection_stats["total_connections"] += 1
            self.connection_stats["failed_connections"] += 1
            return False

    async def connect_to_backend(self) -> bool:
        """Backend 서버에 연결 (Bastion을 통해)"""
        try:
            if not self.bastion_client:
                if not await self.connect_to_bastion():
                    return False
            
            logger.info(f"Creating tunnel to backend: {self.config.backend_host}")
            
            # SSH 터널 생성
            transport = self.bastion_client.get_transport()
            dest_addr = (self.config.backend_host, self.config.backend_port)
            local_addr = ('127.0.0.1', 0)  # 임의의 로컬 포트
            
            channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
            
            # Backend 연결
            self.backend_client = paramiko.SSHClient()
            self.backend_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # SSH 키 로드
            key = paramiko.RSAKey.from_private_key_file(self.config.ssh_key_path)
            
            # 터널을 통한 연결
            self.backend_client.connect(
                hostname=self.config.backend_host,
                port=self.config.backend_port,
                username=self.config.backend_user,
                pkey=key,
                sock=channel,
                timeout=self.config.connection_timeout
            )
            
            logger.info("Successfully connected to backend server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to backend server: {e}")
            return False

    async def execute_command(self, command: str, host: str = "backend") -> SSHResult:
        """원격 명령 실행"""
        start_time = time.time()
        
        try:
            self.connection_stats["total_commands"] += 1
            
            # 연결 선택
            if host == "bastion":
                client = self.bastion_client
                if not client:
                    await self.connect_to_bastion()
                    client = self.bastion_client
            else:  # backend
                client = self.backend_client
                if not client:
                    await self.connect_to_backend()
                    client = self.backend_client
            
            if not client:
                raise Exception(f"Failed to connect to {host}")
            
            logger.info(f"Executing command on {host}: {command}")
            
            # 명령 실행
            stdin, stdout, stderr = client.exec_command(
                command, 
                timeout=self.config.command_timeout
            )
            
            # 결과 수집
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            execution_time = time.time() - start_time
            
            result = SSHResult(
                exit_code=exit_code,
                stdout=stdout_data,
                stderr=stderr_data,
                execution_time=execution_time,
                command=command,
                host=host
            )
            
            if exit_code == 0:
                self.connection_stats["successful_commands"] += 1
                logger.info(f"Command executed successfully in {execution_time:.2f}s")
            else:
                self.connection_stats["failed_commands"] += 1
                logger.error(f"Command failed with exit code {exit_code}: {stderr_data}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to execute command: {e}")
            self.connection_stats["failed_commands"] += 1
            
            return SSHResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                command=command,
                host=host
            )

    async def upload_file(self, local_path: str, remote_path: str, host: str = "backend") -> FileTransferResult:
        """파일 업로드"""
        start_time = time.time()
        
        try:
            self.connection_stats["total_transfers"] += 1
            
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            file_size = os.path.getsize(local_path)
            
            # 연결 선택
            if host == "bastion":
                client = self.bastion_client
                if not client:
                    await self.connect_to_bastion()
                    client = self.bastion_client
            else:  # backend
                client = self.backend_client
                if not client:
                    await self.connect_to_backend()
                    client = self.backend_client
            
            if not client:
                raise Exception(f"Failed to connect to {host}")
            
            logger.info(f"Uploading file to {host}: {local_path} -> {remote_path}")
            
            # SCP를 사용한 파일 전송
            with scp.SCPClient(client.get_transport()) as scp_client:
                scp_client.put(local_path, remote_path)
            
            transfer_time = time.time() - start_time
            
            self.connection_stats["successful_transfers"] += 1
            logger.info(f"File uploaded successfully in {transfer_time:.2f}s")
            
            return FileTransferResult(
                success=True,
                local_path=local_path,
                remote_path=remote_path,
                file_size=file_size,
                transfer_time=transfer_time
            )
            
        except Exception as e:
            transfer_time = time.time() - start_time
            logger.error(f"Failed to upload file: {e}")
            self.connection_stats["failed_transfers"] += 1
            
            return FileTransferResult(
                success=False,
                local_path=local_path,
                remote_path=remote_path,
                file_size=0,
                transfer_time=transfer_time,
                error_message=str(e)
            )

    async def download_file(self, remote_path: str, local_path: str, host: str = "backend") -> FileTransferResult:
        """파일 다운로드"""
        start_time = time.time()
        
        try:
            self.connection_stats["total_transfers"] += 1
            
            # 연결 선택
            if host == "bastion":
                client = self.bastion_client
                if not client:
                    await self.connect_to_bastion()
                    client = self.bastion_client
            else:  # backend
                client = self.backend_client
                if not client:
                    await self.connect_to_backend()
                    client = self.backend_client
            
            if not client:
                raise Exception(f"Failed to connect to {host}")
            
            logger.info(f"Downloading file from {host}: {remote_path} -> {local_path}")
            
            # 로컬 디렉토리 생성
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # SCP를 사용한 파일 전송
            with scp.SCPClient(client.get_transport()) as scp_client:
                scp_client.get(remote_path, local_path)
            
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
            transfer_time = time.time() - start_time
            
            self.connection_stats["successful_transfers"] += 1
            logger.info(f"File downloaded successfully in {transfer_time:.2f}s")
            
            return FileTransferResult(
                success=True,
                local_path=local_path,
                remote_path=remote_path,
                file_size=file_size,
                transfer_time=transfer_time
            )
            
        except Exception as e:
            transfer_time = time.time() - start_time
            logger.error(f"Failed to download file: {e}")
            self.connection_stats["failed_transfers"] += 1
            
            return FileTransferResult(
                success=False,
                local_path=local_path,
                remote_path=remote_path,
                file_size=0,
                transfer_time=transfer_time,
                error_message=str(e)
            )

    async def test_connectivity(self) -> Dict[str, Any]:
        """연결 테스트"""
        results = {
            "bastion_connection": False,
            "backend_connection": False,
            "bastion_test_command": False,
            "backend_test_command": False,
            "errors": []
        }
        
        try:
            # Bastion 연결 테스트
            if await self.connect_to_bastion():
                results["bastion_connection"] = True
                
                # Bastion 명령 테스트
                test_result = await self.execute_command("echo 'bastion test'", "bastion")
                if test_result.exit_code == 0:
                    results["bastion_test_command"] = True
                else:
                    results["errors"].append(f"Bastion command test failed: {test_result.stderr}")
            else:
                results["errors"].append("Failed to connect to bastion host")
            
            # Backend 연결 테스트
            if await self.connect_to_backend():
                results["backend_connection"] = True
                
                # Backend 명령 테스트
                test_result = await self.execute_command("echo 'backend test'", "backend")
                if test_result.exit_code == 0:
                    results["backend_test_command"] = True
                else:
                    results["errors"].append(f"Backend command test failed: {test_result.stderr}")
            else:
                results["errors"].append("Failed to connect to backend server")
                
        except Exception as e:
            results["errors"].append(f"Connectivity test error: {str(e)}")
        
        return results

    async def get_system_info(self, host: str = "backend") -> Dict[str, Any]:
        """시스템 정보 조회"""
        try:
            commands = {
                "hostname": "hostname",
                "uptime": "uptime",
                "disk_usage": "df -h",
                "memory_usage": "free -h",
                "cpu_info": "lscpu | head -20",
                "network_info": "ip addr show",
                "docker_status": "docker --version && docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'",
                "processes": "ps aux | head -20"
            }
            
            system_info = {}
            
            for info_type, command in commands.items():
                result = await self.execute_command(command, host)
                system_info[info_type] = {
                    "success": result.exit_code == 0,
                    "output": result.stdout if result.exit_code == 0 else result.stderr,
                    "execution_time": result.execution_time
                }
            
            return system_info
            
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}

    async def get_stats(self) -> Dict[str, Any]:
        """SSH 관리자 통계 조회"""
        return {
            "connection_stats": dict(self.connection_stats),
            "config": {
                "bastion_host": self.config.bastion_host,
                "backend_host": self.config.backend_host,
                "connection_timeout": self.config.connection_timeout,
                "command_timeout": self.config.command_timeout
            },
            "connection_status": {
                "bastion_connected": self.bastion_client is not None,
                "backend_connected": self.backend_client is not None
            }
        }

    async def close_connections(self):
        """모든 연결 종료"""
        try:
            if self.backend_client:
                self.backend_client.close()
                self.backend_client = None
                logger.info("Backend connection closed")
            
            if self.bastion_client:
                self.bastion_client.close()
                self.bastion_client = None
                logger.info("Bastion connection closed")
                
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

    def __del__(self):
        """소멸자 - 연결 정리"""
        try:
            if hasattr(self, 'backend_client') and self.backend_client:
                self.backend_client.close()
            if hasattr(self, 'bastion_client') and self.bastion_client:
                self.bastion_client.close()
        except Exception:
            pass


# 전역 SSH 관리자 인스턴스
_ssh_manager = None

async def get_ssh_manager() -> SSHManager:
    """SSH 관리자 싱글톤 인스턴스 반환"""
    global _ssh_manager
    if _ssh_manager is None:
        _ssh_manager = SSHManager()
    return _ssh_manager