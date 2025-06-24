import time
import psutil
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """요청 메트릭"""
    path: str
    method: str
    status_code: int
    response_time: float
    memory_used: int
    cpu_percent: float
    timestamp: datetime
    user_agent: str = ""
    ip_address: str = ""

@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage_percent: float
    active_connections: int
    timestamp: datetime

@dataclass
class PerformanceAlert:
    """성능 알림"""
    alert_type: str
    message: str
    severity: str  # low, medium, high, critical
    metrics: Dict[str, Any]
    timestamp: datetime

class PerformanceMonitor:
    """
    성능 모니터링 시스템
    - 요청 응답 시간 추적
    - 시스템 리소스 모니터링
    - 병목 지점 식별
    - 성능 알림
    """
    
    def __init__(self, 
                 max_metrics_history: int = 10000,
                 alert_thresholds: Dict[str, float] = None):
        self.max_metrics_history = max_metrics_history
        self.alert_thresholds = alert_thresholds or {
            'response_time': 5.0,  # 5초
            'memory_percent': 85.0,  # 85%
            'cpu_percent': 80.0,  # 80%
            'disk_usage': 90.0,  # 90%
            'error_rate': 5.0  # 5%
        }
        
        # 메트릭 저장소
        self.request_metrics: deque = deque(maxlen=max_metrics_history)
        self.system_metrics: deque = deque(maxlen=max_metrics_history)
        self.alerts: deque = deque(maxlen=1000)
        
        # 통계 캐시
        self.stats_cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 60  # 1분
        
        # 에러 카운터
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        
        # 백그라운드 태스크
        self.monitor_task = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # 데이터 저장 경로
        self.data_dir = Path("data/performance")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def start_monitoring(self):
        """모니터링 시작"""
        if self.monitor_task is None:
            self.monitor_task = asyncio.create_task(self._system_monitor_loop())
            logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """모니터링 중지"""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
            logger.info("Performance monitoring stopped")

    async def _system_monitor_loop(self):
        """시스템 메트릭 수집 루프"""
        while True:
            try:
                await asyncio.sleep(30)  # 30초마다 수집
                
                # 시스템 메트릭 수집
                loop = asyncio.get_event_loop()
                metrics = await loop.run_in_executor(
                    self.executor,
                    self._collect_system_metrics
                )
                
                if metrics:
                    self.system_metrics.append(metrics)
                    await self._check_system_alerts(metrics)
                
                # 주기적으로 데이터 저장
                if len(self.system_metrics) % 20 == 0:  # 10분마다
                    await self._save_metrics_to_file()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(60)

    def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            
            # 네트워크 연결 수
            connections = len(psutil.net_connections())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_available=memory.available,
                disk_usage_percent=(disk.used / disk.total) * 100,
                active_connections=connections,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return None

    async def record_request(self, request: Request, response: Response, 
                           response_time: float, memory_used: int):
        """요청 메트릭 기록"""
        try:
            # CPU 사용률 (비동기로 수집)
            loop = asyncio.get_event_loop()
            cpu_percent = await loop.run_in_executor(
                self.executor,
                lambda: psutil.cpu_percent()
            )
            
            metrics = RequestMetrics(
                path=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
                memory_used=memory_used,
                cpu_percent=cpu_percent,
                timestamp=datetime.utcnow(),
                user_agent=request.headers.get("user-agent", ""),
                ip_address=request.client.host if request.client else ""
            )
            
            self.request_metrics.append(metrics)
            
            # 요청 카운터 업데이트
            path_key = f"{request.method}:{request.url.path}"
            self.request_counts[path_key] += 1
            
            if response.status_code >= 400:
                self.error_counts[path_key] += 1
            
            # 성능 알림 확인
            await self._check_request_alerts(metrics)
            
            # 캐시 무효화
            self._invalidate_cache()
            
        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}")

    async def _check_request_alerts(self, metrics: RequestMetrics):
        """요청 기반 알림 확인"""
        alerts = []
        
        # 응답 시간 알림
        if metrics.response_time > self.alert_thresholds['response_time']:
            alerts.append(PerformanceAlert(
                alert_type="slow_response",
                message=f"Slow response detected: {metrics.path} took {metrics.response_time:.2f}s",
                severity="high" if metrics.response_time > 10 else "medium",
                metrics=asdict(metrics),
                timestamp=datetime.utcnow()
            ))
        
        # 메모리 사용량 알림
        if metrics.memory_used > 100 * 1024 * 1024:  # 100MB
            alerts.append(PerformanceAlert(
                alert_type="high_memory_usage",
                message=f"High memory usage: {metrics.path} used {metrics.memory_used / 1024 / 1024:.2f}MB",
                severity="medium",
                metrics=asdict(metrics),
                timestamp=datetime.utcnow()
            ))
        
        # 알림 저장
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"Performance Alert: {alert.message}")

    async def _check_system_alerts(self, metrics: SystemMetrics):
        """시스템 기반 알림 확인"""
        alerts = []
        
        # CPU 사용률 알림
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append(PerformanceAlert(
                alert_type="high_cpu_usage",
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                severity="critical" if metrics.cpu_percent > 95 else "high",
                metrics=asdict(metrics),
                timestamp=datetime.utcnow()
            ))
        
        # 메모리 사용률 알림
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append(PerformanceAlert(
                alert_type="high_memory_usage",
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                severity="critical" if metrics.memory_percent > 95 else "high",
                metrics=asdict(metrics),
                timestamp=datetime.utcnow()
            ))
        
        # 디스크 사용률 알림
        if metrics.disk_usage_percent > self.alert_thresholds['disk_usage']:
            alerts.append(PerformanceAlert(
                alert_type="high_disk_usage",
                message=f"High disk usage: {metrics.disk_usage_percent:.1f}%",
                severity="critical" if metrics.disk_usage_percent > 95 else "high",
                metrics=asdict(metrics),
                timestamp=datetime.utcnow()
            ))
        
        # 알림 저장
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"System Alert: {alert.message}")

    def _invalidate_cache(self):
        """캐시 무효화"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self.cache_expiry.items()
            if current_time > expiry
        ]
        
        for key in expired_keys:
            self.stats_cache.pop(key, None)
            self.cache_expiry.pop(key, None)

    def _get_cached_stats(self, key: str) -> Optional[Dict]:
        """캐시된 통계 조회"""
        current_time = time.time()
        
        if key in self.stats_cache and current_time < self.cache_expiry.get(key, 0):
            return self.stats_cache[key]
        
        return None

    def _cache_stats(self, key: str, stats: Dict):
        """통계 캐시 저장"""
        current_time = time.time()
        self.stats_cache[key] = stats
        self.cache_expiry[key] = current_time + self.cache_ttl

    async def get_request_stats(self, hours: int = 24) -> Dict:
        """요청 통계 조회"""
        cache_key = f"request_stats_{hours}"
        cached = self._get_cached_stats(cache_key)
        if cached:
            return cached
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.request_metrics
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"error": "No data available"}
            
            # 통계 계산
            response_times = [m.response_time for m in recent_metrics]
            memory_usage = [m.memory_used for m in recent_metrics]
            
            stats = {
                "total_requests": len(recent_metrics),
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "p95_response_time": self._percentile(response_times, 95),
                "p99_response_time": self._percentile(response_times, 99),
                "avg_memory_usage": sum(memory_usage) / len(memory_usage),
                "max_memory_usage": max(memory_usage),
                "error_rate": self._calculate_error_rate(recent_metrics),
                "requests_per_hour": len(recent_metrics) / hours,
                "top_slow_endpoints": self._get_slow_endpoints(recent_metrics),
                "status_code_distribution": self._get_status_distribution(recent_metrics)
            }
            
            self._cache_stats(cache_key, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate request stats: {e}")
            return {"error": str(e)}

    async def get_system_stats(self, hours: int = 24) -> Dict:
        """시스템 통계 조회"""
        cache_key = f"system_stats_{hours}"
        cached = self._get_cached_stats(cache_key)
        if cached:
            return cached
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.system_metrics
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"error": "No data available"}
            
            # 통계 계산
            cpu_usage = [m.cpu_percent for m in recent_metrics]
            memory_usage = [m.memory_percent for m in recent_metrics]
            disk_usage = [m.disk_usage_percent for m in recent_metrics]
            
            stats = {
                "avg_cpu_percent": sum(cpu_usage) / len(cpu_usage),
                "max_cpu_percent": max(cpu_usage),
                "avg_memory_percent": sum(memory_usage) / len(memory_usage),
                "max_memory_percent": max(memory_usage),
                "avg_disk_usage": sum(disk_usage) / len(disk_usage),
                "max_disk_usage": max(disk_usage),
                "current_metrics": asdict(recent_metrics[-1]) if recent_metrics else None,
                "data_points": len(recent_metrics)
            }
            
            self._cache_stats(cache_key, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate system stats: {e}")
            return {"error": str(e)}

    async def get_alerts(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """알림 조회"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_alerts = [
                alert for alert in self.alerts
                if alert.timestamp >= cutoff_time
            ]
            
            if severity:
                recent_alerts = [
                    alert for alert in recent_alerts
                    if alert.severity == severity
                ]
            
            return [asdict(alert) for alert in recent_alerts]
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_error_rate(self, metrics: List[RequestMetrics]) -> float:
        """에러율 계산"""
        if not metrics:
            return 0.0
        
        error_count = sum(1 for m in metrics if m.status_code >= 400)
        return (error_count / len(metrics)) * 100

    def _get_slow_endpoints(self, metrics: List[RequestMetrics], limit: int = 10) -> List[Dict]:
        """느린 엔드포인트 조회"""
        endpoint_times = defaultdict(list)
        
        for metric in metrics:
            endpoint_key = f"{metric.method} {metric.path}"
            endpoint_times[endpoint_key].append(metric.response_time)
        
        # 평균 응답 시간으로 정렬
        slow_endpoints = []
        for endpoint, times in endpoint_times.items():
            avg_time = sum(times) / len(times)
            slow_endpoints.append({
                "endpoint": endpoint,
                "avg_response_time": avg_time,
                "max_response_time": max(times),
                "request_count": len(times)
            })
        
        return sorted(slow_endpoints, key=lambda x: x["avg_response_time"], reverse=True)[:limit]

    def _get_status_distribution(self, metrics: List[RequestMetrics]) -> Dict[str, int]:
        """상태 코드 분포"""
        distribution = defaultdict(int)
        
        for metric in metrics:
            status_range = f"{metric.status_code // 100}xx"
            distribution[status_range] += 1
        
        return dict(distribution)

    async def _save_metrics_to_file(self):
        """메트릭을 파일로 저장"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
            
            # 요청 메트릭 저장
            if self.request_metrics:
                request_file = self.data_dir / f"requests_{timestamp}.json"
                request_data = [asdict(m) for m in list(self.request_metrics)[-1000:]]  # 최근 1000개
                
                # datetime 객체를 문자열로 변환
                for item in request_data:
                    item['timestamp'] = item['timestamp'].isoformat()
                
                with open(request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_data, f, indent=2, ensure_ascii=False)
            
            # 시스템 메트릭 저장
            if self.system_metrics:
                system_file = self.data_dir / f"system_{timestamp}.json"
                system_data = [asdict(m) for m in list(self.system_metrics)[-100:]]  # 최근 100개
                
                # datetime 객체를 문자열로 변환
                for item in system_data:
                    item['timestamp'] = item['timestamp'].isoformat()
                
                with open(system_file, 'w', encoding='utf-8') as f:
                    json.dump(system_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metrics saved to files at {timestamp}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics to file: {e}")

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """성능 모니터링 미들웨어"""
    
    def __init__(self, app, monitor: PerformanceMonitor):
        super().__init__(app)
        self.monitor = monitor

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        response = await call_next(request)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        response_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # 메트릭 기록
        await self.monitor.record_request(request, response, response_time, memory_used)
        
        # 응답 헤더에 성능 정보 추가
        response.headers["X-Response-Time"] = f"{response_time:.3f}"
        response.headers["X-Memory-Used"] = str(memory_used)
        
        return response


# 전역 성능 모니터 인스턴스
_performance_monitor = None

async def get_performance_monitor() -> PerformanceMonitor:
    """성능 모니터 싱글톤 인스턴스 반환"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        await _performance_monitor.start_monitoring()
    return _performance_monitor