import asyncio
import logging
import psutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

try:
    import torch
    import torch.cuda
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. GPU functionality will be limited.")

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logging.warning("GPUtil not available. Install with: pip install gputil")

logger = logging.getLogger(__name__)

@dataclass
class GPUInfo:
    """GPU 정보"""
    id: int
    name: str
    memory_total: int  # MB
    memory_used: int   # MB
    memory_free: int   # MB
    utilization: float  # %
    temperature: float  # °C
    is_available: bool

@dataclass
class GPUMemoryPool:
    """GPU 메모리 풀"""
    device_id: int
    total_memory: int
    allocated_memory: int
    cached_memory: int
    reserved_memory: int

class GPUManager:
    """
    GPU 관리 시스템
    - GPU 환경 검증
    - 메모리 관리 및 최적화
    - 배치 크기 자동 조정
    - GPU 리소스 모니터링
    """
    
    def __init__(self):
        self.available_gpus: List[GPUInfo] = []
        self.memory_pools: Dict[int, GPUMemoryPool] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.optimal_batch_sizes: Dict[str, int] = {}
        
        # 설정
        self.memory_reserve_ratio = 0.1  # 10% 메모리 예약
        self.max_memory_usage_ratio = 0.85  # 최대 85% 메모리 사용
        
        # 초기화
        asyncio.create_task(self._initialize_gpu_environment())

    async def _initialize_gpu_environment(self):
        """GPU 환경 초기화"""
        try:
            if not TORCH_AVAILABLE:
                logger.warning("PyTorch not available. GPU functionality disabled.")
                return
            
            # CUDA 사용 가능 여부 확인
            if not torch.cuda.is_available():
                logger.info("CUDA not available. Using CPU mode.")
                return
            
            # GPU 정보 수집
            await self._collect_gpu_info()
            
            # 메모리 풀 초기화
            await self._initialize_memory_pools()
            
            logger.info(f"GPU environment initialized. Available GPUs: {len(self.available_gpus)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPU environment: {e}")

    async def _collect_gpu_info(self):
        """GPU 정보 수집"""
        try:
            loop = asyncio.get_event_loop()
            gpu_info = await loop.run_in_executor(self.executor, self._collect_gpu_info_sync)
            self.available_gpus = gpu_info
        except Exception as e:
            logger.error(f"Failed to collect GPU info: {e}")

    def _collect_gpu_info_sync(self) -> List[GPUInfo]:
        """동기 GPU 정보 수집"""
        gpu_list = []
        
        try:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                
                for i in range(device_count):
                    try:
                        # PyTorch를 통한 기본 정보
                        props = torch.cuda.get_device_properties(i)
                        memory_info = torch.cuda.mem_get_info(i)
                        
                        gpu_info = GPUInfo(
                            id=i,
                            name=props.name,
                            memory_total=props.total_memory // (1024 * 1024),  # MB
                            memory_used=(props.total_memory - memory_info[0]) // (1024 * 1024),
                            memory_free=memory_info[0] // (1024 * 1024),
                            utilization=0.0,  # PyTorch로는 직접 얻기 어려움
                            temperature=0.0,  # PyTorch로는 직접 얻기 어려움
                            is_available=True
                        )
                        
                        # GPUtil이 있으면 추가 정보 수집
                        if GPUTIL_AVAILABLE:
                            try:
                                gpus = GPUtil.getGPUs()
                                if i < len(gpus):
                                    gpu = gpus[i]
                                    gpu_info.utilization = gpu.load * 100
                                    gpu_info.temperature = gpu.temperature
                            except Exception as e:
                                logger.warning(f"Failed to get additional GPU info: {e}")
                        
                        gpu_list.append(gpu_info)
                        
                    except Exception as e:
                        logger.warning(f"Failed to get info for GPU {i}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect GPU info: {e}")
        
        return gpu_list

    async def _initialize_memory_pools(self):
        """메모리 풀 초기화"""
        try:
            for gpu in self.available_gpus:
                if gpu.is_available:
                    pool = GPUMemoryPool(
                        device_id=gpu.id,
                        total_memory=gpu.memory_total,
                        allocated_memory=0,
                        cached_memory=0,
                        reserved_memory=int(gpu.memory_total * self.memory_reserve_ratio)
                    )
                    self.memory_pools[gpu.id] = pool
                    
                    logger.info(f"Memory pool initialized for GPU {gpu.id}: {gpu.memory_total}MB total")
                    
        except Exception as e:
            logger.error(f"Failed to initialize memory pools: {e}")

    async def get_optimal_batch_size(self, model_type: str, input_size: Tuple[int, ...], 
                                   device_id: int = 0) -> int:
        """최적 배치 크기 계산"""
        try:
            cache_key = f"{model_type}_{input_size}_{device_id}"
            
            if cache_key in self.optimal_batch_sizes:
                return self.optimal_batch_sizes[cache_key]
            
            loop = asyncio.get_event_loop()
            batch_size = await loop.run_in_executor(
                self.executor,
                self._calculate_optimal_batch_size,
                model_type, input_size, device_id
            )
            
            self.optimal_batch_sizes[cache_key] = batch_size
            return batch_size
            
        except Exception as e:
            logger.error(f"Failed to calculate optimal batch size: {e}")
            return 1  # 기본값

    def _calculate_optimal_batch_size(self, model_type: str, input_size: Tuple[int, ...], 
                                    device_id: int) -> int:
        """동기 최적 배치 크기 계산"""
        try:
            if not TORCH_AVAILABLE or device_id not in self.memory_pools:
                return 1
            
            pool = self.memory_pools[device_id]
            available_memory = pool.total_memory - pool.reserved_memory
            max_usable_memory = int(available_memory * self.max_memory_usage_ratio)
            
            # 모델 타입별 메모리 사용량 추정
            if model_type == "easyocr":
                # EasyOCR 모델의 대략적인 메모리 사용량 (MB per image)
                base_memory = 500  # 모델 자체
                per_image_memory = 50  # 이미지당 메모리
                
                if len(input_size) >= 2:
                    # 이미지 크기에 따른 메모리 조정
                    pixel_count = input_size[0] * input_size[1]
                    per_image_memory = max(50, pixel_count // 10000)  # 대략적인 계산
                
                max_batch_size = max(1, (max_usable_memory - base_memory) // per_image_memory)
                
            else:
                # 기본 계산
                max_batch_size = max(1, max_usable_memory // 100)  # 보수적 추정
            
            # 실용적인 범위로 제한
            optimal_batch_size = min(max_batch_size, 32)  # 최대 32
            optimal_batch_size = max(optimal_batch_size, 1)  # 최소 1
            
            logger.info(f"Calculated optimal batch size for {model_type}: {optimal_batch_size}")
            return optimal_batch_size
            
        except Exception as e:
            logger.error(f"Failed to calculate batch size: {e}")
            return 1

    @contextmanager
    def gpu_memory_context(self, device_id: int = 0):
        """GPU 메모리 컨텍스트 관리자"""
        try:
            if TORCH_AVAILABLE and device_id in self.memory_pools:
                # 메모리 정리
                torch.cuda.empty_cache()
                
                # 메모리 사용량 기록
                if torch.cuda.is_available():
                    initial_memory = torch.cuda.memory_allocated(device_id)
                else:
                    initial_memory = 0
                
                yield
                
                # 정리 작업
                if torch.cuda.is_available():
                    final_memory = torch.cuda.memory_allocated(device_id)
                    memory_used = final_memory - initial_memory
                    
                    if memory_used > 0:
                        logger.debug(f"GPU {device_id} memory used: {memory_used / (1024*1024):.2f}MB")
                    
                    torch.cuda.empty_cache()
            else:
                yield
                
        except Exception as e:
            logger.error(f"GPU memory context error: {e}")
            yield

    async def monitor_gpu_usage(self) -> Dict[int, Dict[str, Any]]:
        """GPU 사용량 모니터링"""
        try:
            loop = asyncio.get_event_loop()
            usage_info = await loop.run_in_executor(self.executor, self._monitor_gpu_usage_sync)
            return usage_info
        except Exception as e:
            logger.error(f"Failed to monitor GPU usage: {e}")
            return {}

    def _monitor_gpu_usage_sync(self) -> Dict[int, Dict[str, Any]]:
        """동기 GPU 사용량 모니터링"""
        usage_info = {}
        
        try:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                for gpu in self.available_gpus:
                    if gpu.is_available:
                        device_id = gpu.id
                        
                        # 메모리 정보
                        memory_info = torch.cuda.mem_get_info(device_id)
                        memory_allocated = torch.cuda.memory_allocated(device_id)
                        memory_cached = torch.cuda.memory_reserved(device_id)
                        
                        usage_info[device_id] = {
                            "name": gpu.name,
                            "memory_total": gpu.memory_total,
                            "memory_free": memory_info[0] // (1024 * 1024),
                            "memory_used": (gpu.memory_total * 1024 * 1024 - memory_info[0]) // (1024 * 1024),
                            "memory_allocated": memory_allocated // (1024 * 1024),
                            "memory_cached": memory_cached // (1024 * 1024),
                            "utilization": gpu.utilization,
                            "temperature": gpu.temperature
                        }
                        
                        # GPUtil로 추가 정보 수집
                        if GPUTIL_AVAILABLE:
                            try:
                                gpus = GPUtil.getGPUs()
                                if device_id < len(gpus):
                                    gpu_util = gpus[device_id]
                                    usage_info[device_id].update({
                                        "utilization": gpu_util.load * 100,
                                        "temperature": gpu_util.temperature
                                    })
                            except Exception as e:
                                logger.warning(f"Failed to get GPU utilization: {e}")
                                
        except Exception as e:
            logger.error(f"Failed to monitor GPU usage: {e}")
        
        return usage_info

    async def cleanup_gpu_memory(self, device_id: Optional[int] = None):
        """GPU 메모리 정리"""
        try:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                if device_id is not None:
                    # 특정 GPU 정리
                    with torch.cuda.device(device_id):
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                    logger.info(f"Cleaned up GPU {device_id} memory")
                else:
                    # 모든 GPU 정리
                    for gpu in self.available_gpus:
                        if gpu.is_available:
                            with torch.cuda.device(gpu.id):
                                torch.cuda.empty_cache()
                                torch.cuda.synchronize()
                    logger.info("Cleaned up all GPU memory")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup GPU memory: {e}")

    async def get_gpu_stats(self) -> Dict[str, Any]:
        """GPU 통계 정보"""
        try:
            stats = {
                "gpu_count": len(self.available_gpus),
                "cuda_available": TORCH_AVAILABLE and torch.cuda.is_available(),
                "gputil_available": GPUTIL_AVAILABLE,
                "memory_pools": len(self.memory_pools),
                "optimal_batch_sizes": dict(self.optimal_batch_sizes)
            }
            
            if self.available_gpus:
                stats["gpus"] = []
                for gpu in self.available_gpus:
                    gpu_stat = {
                        "id": gpu.id,
                        "name": gpu.name,
                        "memory_total": gpu.memory_total,
                        "is_available": gpu.is_available
                    }
                    stats["gpus"].append(gpu_stat)
            
            # 현재 사용량 정보
            usage_info = await self.monitor_gpu_usage()
            if usage_info:
                stats["current_usage"] = usage_info
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get GPU stats: {e}")
            return {"error": str(e)}

    def is_gpu_available(self, device_id: int = 0) -> bool:
        """GPU 사용 가능 여부 확인"""
        try:
            if not TORCH_AVAILABLE or not torch.cuda.is_available():
                return False
            
            if device_id >= len(self.available_gpus):
                return False
            
            return self.available_gpus[device_id].is_available
            
        except Exception as e:
            logger.error(f"Failed to check GPU availability: {e}")
            return False

    def get_recommended_device(self) -> int:
        """권장 GPU 디바이스 반환"""
        try:
            if not self.available_gpus:
                return -1  # CPU 사용
            
            # 메모리 사용량이 가장 적은 GPU 선택
            best_gpu = min(
                self.available_gpus,
                key=lambda gpu: gpu.memory_used if gpu.is_available else float('inf')
            )
            
            return best_gpu.id if best_gpu.is_available else -1
            
        except Exception as e:
            logger.error(f"Failed to get recommended device: {e}")
            return -1

    def __del__(self):
        """소멸자 - 리소스 정리"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except Exception:
            pass


# 전역 GPU 관리자 인스턴스
_gpu_manager = None

async def get_gpu_manager() -> GPUManager:
    """GPU 관리자 싱글톤 인스턴스 반환"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager