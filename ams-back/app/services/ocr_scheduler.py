import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid
from concurrent.futures import ThreadPoolExecutor
import heapq
from pathlib import Path
import json

from .gpu_manager import get_gpu_manager, GPUManager
from .batch_ocr_engine import get_batch_ocr_engine, BatchOCREngine, BatchOCRResult

logger = logging.getLogger(__name__)

class JobPriority(Enum):
    """작업 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class JobStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class OCRJob:
    """OCR 작업"""
    job_id: str
    images: List[Any]  # 이미지 경로 또는 데이터
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[BatchOCRResult] = None
    error: Optional[str] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = None
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        """우선순위 큐를 위한 비교 연산자"""
        # 우선순위가 높을수록 먼저 처리 (숫자가 클수록 우선순위 높음)
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # 같은 우선순위면 생성 시간이 빠른 것부터
        return self.created_at < other.created_at

@dataclass
class SchedulerStats:
    """스케줄러 통계"""
    total_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    average_processing_time: float = 0.0
    throughput_per_hour: float = 0.0
    gpu_utilization: float = 0.0
    memory_usage: float = 0.0

@dataclass
class OCRJobRequest:
    """OCR 작업 요청"""
    images: List[Any]  # 이미지 데이터 또는 경로
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    options: Dict[str, Any] = None
    submitted_at: datetime = None
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = None

class OCRScheduler:
    """
    OCR 작업 스케줄러
    - 우선순위 기반 작업 큐 관리
    - 리소스 모니터링 및 최적화
    - 자동 재시도 및 오류 처리
    - 작업 상태 추적 및 콜백
    """

    def __init__(self, max_concurrent_jobs: int = 4, enable_gpu_monitoring: bool = True):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.enable_gpu_monitoring = enable_gpu_monitoring

        # 작업 큐 (우선순위 큐)
        self.job_queue: List[OCRJob] = []
        self.processing_jobs: Dict[str, OCRJob] = {}
        self.completed_jobs: Dict[str, OCRJob] = {}
        self.failed_jobs: Dict[str, OCRJob] = {}

        # 동기화
        self.queue_lock = asyncio.Lock()
        self.processing_lock = asyncio.Lock()

        # 서비스 인스턴스
        self.gpu_manager: Optional[GPUManager] = None
        self.batch_ocr_engine: Optional[BatchOCREngine] = None

        # 스케줄러 태스크
        self.scheduler_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None

        # 통계
        self.stats = SchedulerStats()
        self.processing_times: List[float] = []

        # 설정
        self.job_timeout = 300  # 5분
        self.cleanup_interval = 3600  # 1시간
        self.stats_update_interval = 60  # 1분

        # 초기화
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """스케줄러 초기화"""
        try:
            # 서비스 초기화
            self.gpu_manager = await get_gpu_manager()
            self.batch_ocr_engine = await get_batch_ocr_engine()

            # 스케줄러 시작
            await self.start_scheduler()

            logger.info("OCR Scheduler initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OCR Scheduler: {e}")

    async def start_scheduler(self):
        """스케줄러 시작"""
        try:
            if self.scheduler_task is None:
                self.scheduler_task = asyncio.create_task(self._scheduler_loop())

            if self.monitor_task is None and self.enable_gpu_monitoring:
                self.monitor_task = asyncio.create_task(self._monitor_loop())

            logger.info("OCR Scheduler started")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

    async def stop_scheduler(self):
        """스케줄러 중지"""
        try:
            # 스케줄러 태스크 중지
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
                self.scheduler_task = None

            # 모니터 태스크 중지
            if self.monitor_task:
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
                self.monitor_task = None

            # 진행 중인 작업 완료 대기
            await self._wait_for_completion()

            logger.info("OCR Scheduler stopped")

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

    async def submit_job(self, images: List[Any], priority: JobPriority = JobPriority.NORMAL,
                        callback: Optional[Callable] = None, metadata: Dict[str, Any] = None) -> str:
        """작업 제출"""
        try:
            job_id = str(uuid.uuid4())

            job = OCRJob(
                job_id=job_id,
                images=images,
                priority=priority,
                status=JobStatus.PENDING,
                created_at=datetime.utcnow(),
                callback=callback,
                metadata=metadata or {}
            )

            async with self.queue_lock:
                heapq.heappush(self.job_queue, job)
                self.stats.total_jobs += 1
                self.stats.pending_jobs += 1

            logger.info(f"Job {job_id} submitted with priority {priority.name}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        try:
            # 진행 중인 작업 확인
            async with self.processing_lock:
                if job_id in self.processing_jobs:
                    job = self.processing_jobs[job_id]
                    return self._job_to_dict(job)

            # 완료된 작업 확인
            if job_id in self.completed_jobs:
                job = self.completed_jobs[job_id]
                return self._job_to_dict(job)

            # 실패한 작업 확인
            if job_id in self.failed_jobs:
                job = self.failed_jobs[job_id]
                return self._job_to_dict(job)

            # 대기 중인 작업 확인
            async with self.queue_lock:
                for job in self.job_queue:
                    if job.job_id == job_id:
                        return self._job_to_dict(job)

            return None

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None

    def _job_to_dict(self, job: OCRJob) -> Dict[str, Any]:
        """작업을 딕셔너리로 변환"""
        job_dict = {
            "job_id": job.job_id,
            "priority": job.priority.name,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "metadata": job.metadata,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries
        }

        if job.result:
            job_dict["result"] = {
                "batch_size": job.result.batch_size,
                "total_processing_time": job.result.total_processing_time,
                "average_confidence": job.result.average_confidence,
                "device_used": job.result.device_used,
                "results_count": len(job.result.results)
            }

        return job_dict

    async def cancel_job(self, job_id: str) -> bool:
        """작업 취소"""
        try:
            # 대기 중인 작업 취소
            async with self.queue_lock:
                for i, job in enumerate(self.job_queue):
                    if job.job_id == job_id:
                        job.status = JobStatus.CANCELLED
                        self.job_queue.pop(i)
                        heapq.heapify(self.job_queue)
                        self.stats.pending_jobs -= 1
                        logger.info(f"Job {job_id} cancelled from queue")
                        return True

            # 진행 중인 작업은 취소할 수 없음 (이미 처리 중)
            async with self.processing_lock:
                if job_id in self.processing_jobs:
                    logger.warning(f"Job {job_id} is already processing, cannot cancel")
                    return False

            logger.warning(f"Job {job_id} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while True:
            try:
                await asyncio.sleep(1)  # 1초마다 체크

                # 현재 진행 중인 작업 수 확인
                async with self.processing_lock:
                    current_jobs = len(self.processing_jobs)

                if current_jobs >= self.max_concurrent_jobs:
                    continue

                # 대기 중인 작업 가져오기
                job = await self._get_next_job()
                if not job:
                    continue

                # 작업 처리 시작
                asyncio.create_task(self._process_job(job))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)

    async def _get_next_job(self) -> Optional[OCRJob]:
        """다음 작업 가져오기"""
        try:
            async with self.queue_lock:
                if not self.job_queue:
                    return None

                job = heapq.heappop(self.job_queue)
                job.status = JobStatus.QUEUED
                self.stats.pending_jobs -= 1

                return job

        except Exception as e:
            logger.error(f"Failed to get next job: {e}")
            return None

    async def _process_job(self, job: OCRJob):
        """작업 처리"""
        try:
            # 진행 중인 작업으로 이동
            async with self.processing_lock:
                self.processing_jobs[job.job_id] = job
                self.stats.processing_jobs += 1

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()

            logger.info(f"Processing job {job.job_id}")

            # OCR 처리
            start_time = time.time()
            result = await self.batch_ocr_engine.process_image_batch(job.images)
            processing_time = time.time() - start_time

            # 결과 저장
            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            # 통계 업데이트
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 100:  # 최근 100개만 유지
                self.processing_times.pop(0)

            # 콜백 실행
            if job.callback:
                try:
                    await job.callback(job.job_id, result)
                except Exception as e:
                    logger.error(f"Callback error for job {job.job_id}: {e}")

            # 완료된 작업으로 이동
            async with self.processing_lock:
                del self.processing_jobs[job.job_id]
                self.stats.processing_jobs -= 1

            self.completed_jobs[job.job_id] = job
            self.stats.completed_jobs += 1

            logger.info(f"Job {job.job_id} completed in {processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to process job {job.job_id}: {e}")
            await self._handle_job_failure(job, str(e))

    async def _handle_job_failure(self, job: OCRJob, error: str):
        """작업 실패 처리"""
        try:
            job.error = error
            job.retry_count += 1

            # 재시도 가능한지 확인
            if job.retry_count <= job.max_retries:
                logger.info(f"Retrying job {job.job_id} (attempt {job.retry_count}/{job.max_retries})")

                # 재시도를 위해 큐에 다시 추가
                job.status = JobStatus.PENDING
                async with self.queue_lock:
                    heapq.heappush(self.job_queue, job)
                    self.stats.pending_jobs += 1
            else:
                # 최대 재시도 횟수 초과
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()

                # 실패한 작업으로 이동
                self.failed_jobs[job.job_id] = job
                self.stats.failed_jobs += 1

                logger.error(f"Job {job.job_id} failed after {job.retry_count} attempts: {error}")

            # 진행 중인 작업에서 제거
            async with self.processing_lock:
                if job.job_id in self.processing_jobs:
                    del self.processing_jobs[job.job_id]
                    self.stats.processing_jobs -= 1

        except Exception as e:
            logger.error(f"Failed to handle job failure: {e}")

    async def _monitor_loop(self):
        """모니터링 루프"""
        while True:
            try:
                await asyncio.sleep(self.stats_update_interval)
                await self._update_stats()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(60)

    async def _update_stats(self):
        """통계 업데이트"""
        try:
            # 평균 처리 시간 계산
            if self.processing_times:
                self.stats.average_processing_time = sum(self.processing_times) / len(self.processing_times)

            # 시간당 처리량 계산
            completed_in_last_hour = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            for job in self.completed_jobs.values():
                if job.completed_at and job.completed_at >= cutoff_time:
                    completed_in_last_hour += 1

            self.stats.throughput_per_hour = completed_in_last_hour

            # GPU 사용률 업데이트
            if self.gpu_manager:
                gpu_usage = await self.gpu_manager.monitor_gpu_usage()
                if gpu_usage:
                    total_utilization = sum(info.get("utilization", 0) for info in gpu_usage.values())
                    self.stats.gpu_utilization = total_utilization / len(gpu_usage) if gpu_usage else 0

                    total_memory_used = sum(info.get("memory_used", 0) for info in gpu_usage.values())
                    total_memory_total = sum(info.get("memory_total", 1) for info in gpu_usage.values())
                    self.stats.memory_usage = (total_memory_used / total_memory_total * 100) if total_memory_total > 0 else 0

        except Exception as e:
            logger.error(f"Failed to update stats: {e}")

    async def _wait_for_completion(self):
        """진행 중인 작업 완료 대기"""
        try:
            timeout = 30  # 30초 타임아웃
            start_time = time.time()

            while self.processing_jobs and (time.time() - start_time) < timeout:
                await asyncio.sleep(1)

            if self.processing_jobs:
                logger.warning(f"Timeout waiting for {len(self.processing_jobs)} jobs to complete")

        except Exception as e:
            logger.error(f"Failed to wait for completion: {e}")

    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """스케줄러 통계 조회"""
        try:
            await self._update_stats()

            stats_dict = asdict(self.stats)

            # 추가 정보
            async with self.queue_lock:
                stats_dict["queue_size"] = len(self.job_queue)

            async with self.processing_lock:
                stats_dict["active_jobs"] = len(self.processing_jobs)

            stats_dict["max_concurrent_jobs"] = self.max_concurrent_jobs
            stats_dict["job_timeout"] = self.job_timeout

            return stats_dict

        except Exception as e:
            logger.error(f"Failed to get scheduler stats: {e}")
            return {"error": str(e)}

    async def get_job_list(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """작업 목록 조회"""
        try:
            jobs = []

            if status is None or status == JobStatus.PENDING:
                async with self.queue_lock:
                    jobs.extend([self._job_to_dict(job) for job in self.job_queue[:limit]])

            if status is None or status == JobStatus.PROCESSING:
                async with self.processing_lock:
                    jobs.extend([self._job_to_dict(job) for job in list(self.processing_jobs.values())[:limit]])

            if status is None or status == JobStatus.COMPLETED:
                completed_list = list(self.completed_jobs.values())[-limit:]
                jobs.extend([self._job_to_dict(job) for job in completed_list])

            if status is None or status == JobStatus.FAILED:
                failed_list = list(self.failed_jobs.values())[-limit:]
                jobs.extend([self._job_to_dict(job) for job in failed_list])

            # 생성 시간 기준 정렬
            jobs.sort(key=lambda x: x["created_at"], reverse=True)

            return jobs[:limit]

        except Exception as e:
            logger.error(f"Failed to get job list: {e}")
            return []

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """오래된 작업 정리"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            # 완료된 작업 정리
            to_remove = []
            for job_id, job in self.completed_jobs.items():
                if job.completed_at and job.completed_at < cutoff_time:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self.completed_jobs[job_id]

            # 실패한 작업 정리
            to_remove = []
            for job_id, job in self.failed_jobs.items():
                if job.completed_at and job.completed_at < cutoff_time:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self.failed_jobs[job_id]

            logger.info(f"Cleaned up {len(to_remove)} old jobs")

        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")

    def __del__(self):
        """소멸자 - 리소스 정리"""
        try:
            if hasattr(self, 'scheduler_task') and self.scheduler_task:
                self.scheduler_task.cancel()
            if hasattr(self, 'monitor_task') and self.monitor_task:
                self.monitor_task.cancel()
        except Exception:
            pass


# 전역 OCR 스케줄러 인스턴스
_ocr_scheduler = None

async def get_ocr_scheduler() -> OCRScheduler:
    """OCR 스케줄러 싱글톤 인스턴스 반환"""
    global _ocr_scheduler
    if _ocr_scheduler is None:
        _ocr_scheduler = OCRScheduler()
    return _ocr_scheduler
