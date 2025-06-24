import asyncio
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import pickle

from .confidence_ml import ConfidenceMLModel, FeedbackData
from .dynamic_thresholds import DynamicThresholdManager, PerformanceMetrics

logger = logging.getLogger(__name__)

@dataclass
class LearningConfig:
    """실시간 학습 설정"""
    batch_size: int = 50
    learning_interval_minutes: int = 30
    min_feedback_count: int = 10
    performance_threshold: float = 0.8
    auto_deploy: bool = True
    backup_models: bool = True
    max_model_versions: int = 5

@dataclass
class ModelPerformance:
    """모델 성능 메트릭"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    timestamp: datetime
    sample_size: int

class RealtimeLearningPipeline:
    """
    실시간 학습 파이프라인
    - 사용자 피드백 배치 처리
    - 모델 성능 평가
    - 자동 모델 업데이트
    - 성능 모니터링
    """
    
    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        self.ml_model = ConfidenceMLModel()
        self.threshold_manager = DynamicThresholdManager()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 피드백 큐
        self.feedback_queue: List[FeedbackData] = []
        self.feedback_lock = asyncio.Lock()
        
        # 성능 이력
        self.performance_history: List[ModelPerformance] = []
        
        # 모델 백업 디렉토리
        self.backup_dir = Path("models/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 학습 상태
        self.is_learning = False
        self.last_learning_time = None
        
        # 스케줄러 태스크
        self.scheduler_task = None

    async def start_pipeline(self):
        """파이프라인 시작"""
        if self.scheduler_task is None:
            self.scheduler_task = asyncio.create_task(self._learning_scheduler())
            logger.info("Real-time learning pipeline started")

    async def stop_pipeline(self):
        """파이프라인 중지"""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            self.scheduler_task = None
            logger.info("Real-time learning pipeline stopped")

    async def add_feedback(self, feedback: FeedbackData):
        """피드백 데이터 추가"""
        async with self.feedback_lock:
            self.feedback_queue.append(feedback)
            logger.debug(f"Added feedback. Queue size: {len(self.feedback_queue)}")
            
            # 배치 크기에 도달하면 즉시 학습 트리거
            if len(self.feedback_queue) >= self.config.batch_size:
                asyncio.create_task(self._process_feedback_batch())

    async def _learning_scheduler(self):
        """주기적 학습 스케줄러"""
        while True:
            try:
                await asyncio.sleep(self.config.learning_interval_minutes * 60)
                
                async with self.feedback_lock:
                    if len(self.feedback_queue) >= self.config.min_feedback_count:
                        await self._process_feedback_batch()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Learning scheduler error: {e}")
                await asyncio.sleep(60)  # 1분 후 재시도

    async def _process_feedback_batch(self):
        """피드백 배치 처리"""
        if self.is_learning:
            logger.info("Learning already in progress, skipping batch")
            return
            
        self.is_learning = True
        
        try:
            async with self.feedback_lock:
                if len(self.feedback_queue) < self.config.min_feedback_count:
                    logger.info(f"Insufficient feedback data: {len(self.feedback_queue)}")
                    return
                
                # 배치 데이터 추출
                batch_data = self.feedback_queue[:self.config.batch_size]
                self.feedback_queue = self.feedback_queue[self.config.batch_size:]
                
            logger.info(f"Processing feedback batch of size: {len(batch_data)}")
            
            # 1. 현재 모델 백업
            if self.config.backup_models:
                await self._backup_current_model()
            
            # 2. 모델 학습
            success = await self._train_model(batch_data)
            
            if success:
                # 3. 성능 평가
                performance = await self._evaluate_model_performance(batch_data)
                
                # 4. 성능 기반 배포 결정
                if await self._should_deploy_model(performance):
                    await self._deploy_new_model()
                    logger.info("New model deployed successfully")
                else:
                    await self._rollback_model()
                    logger.info("Model rollback due to poor performance")
                
                # 5. 임계값 조정
                await self._update_thresholds(performance)
                
                # 6. 성능 이력 저장
                self.performance_history.append(performance)
                await self._save_performance_history()
                
            self.last_learning_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            await self._rollback_model()
        finally:
            self.is_learning = False

    async def _train_model(self, feedback_data: List[FeedbackData]) -> bool:
        """모델 학습"""
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.executor,
                self._train_model_sync,
                feedback_data
            )
            return success
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def _train_model_sync(self, feedback_data: List[FeedbackData]) -> bool:
        """동기 모델 학습"""
        try:
            # FeedbackData를 딕셔너리로 변환
            feedback_dicts = [asdict(feedback) for feedback in feedback_data]
            
            # 모델 학습
            success = asyncio.run(self.ml_model.train_from_feedback(feedback_dicts))
            return success
        except Exception as e:
            logger.error(f"Sync model training failed: {e}")
            return False

    async def _evaluate_model_performance(self, test_data: List[FeedbackData]) -> ModelPerformance:
        """모델 성능 평가"""
        try:
            loop = asyncio.get_event_loop()
            performance = await loop.run_in_executor(
                self.executor,
                self._evaluate_performance_sync,
                test_data
            )
            return performance
        except Exception as e:
            logger.error(f"Performance evaluation failed: {e}")
            return self._create_default_performance()

    def _evaluate_performance_sync(self, test_data: List[FeedbackData]) -> ModelPerformance:
        """동기 성능 평가"""
        try:
            true_labels = []
            predictions = []
            
            for feedback in test_data:
                # 실제 라벨 (사용자가 수정했으면 0, 그대로 사용했으면 1)
                true_label = 1 if feedback.user_accepted else 0
                true_labels.append(true_label)
                
                # 모델 예측
                predicted_confidence = self.ml_model.predict_confidence(
                    feedback.ocr_confidence,
                    feedback.pattern_confidence,
                    feedback.db_verification,
                    feedback.length_penalty
                )
                
                # 임계값 기반 예측 (0.7 이상이면 1, 미만이면 0)
                predicted_label = 1 if predicted_confidence >= 0.7 else 0
                predictions.append(predicted_label)
            
            # 성능 메트릭 계산
            true_labels = np.array(true_labels)
            predictions = np.array(predictions)
            
            tp = np.sum((predictions == 1) & (true_labels == 1))
            tn = np.sum((predictions == 0) & (true_labels == 0))
            fp = np.sum((predictions == 1) & (true_labels == 0))
            fn = np.sum((predictions == 0) & (true_labels == 1))
            
            accuracy = (tp + tn) / len(true_labels) if len(true_labels) > 0 else 0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
            
            return ModelPerformance(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                false_positive_rate=fpr,
                false_negative_rate=fnr,
                timestamp=datetime.utcnow(),
                sample_size=len(test_data)
            )
            
        except Exception as e:
            logger.error(f"Sync performance evaluation failed: {e}")
            return self._create_default_performance()

    def _create_default_performance(self) -> ModelPerformance:
        """기본 성능 객체 생성"""
        return ModelPerformance(
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            false_positive_rate=1.0,
            false_negative_rate=1.0,
            timestamp=datetime.utcnow(),
            sample_size=0
        )

    async def _should_deploy_model(self, performance: ModelPerformance) -> bool:
        """모델 배포 여부 결정"""
        # 성능 임계값 확인
        if performance.accuracy < self.config.performance_threshold:
            logger.warning(f"Model accuracy {performance.accuracy} below threshold {self.config.performance_threshold}")
            return False
        
        # 이전 성능과 비교
        if self.performance_history:
            last_performance = self.performance_history[-1]
            if performance.accuracy < last_performance.accuracy * 0.95:  # 5% 이상 성능 저하
                logger.warning(f"Model performance degraded: {performance.accuracy} < {last_performance.accuracy}")
                return False
        
        return True

    async def _backup_current_model(self):
        """현재 모델 백업"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"confidence_model_{timestamp}.joblib"
            
            # 현재 모델 백업
            if self.ml_model.model_path.exists():
                import shutil
                shutil.copy2(self.ml_model.model_path, backup_path)
                logger.info(f"Model backed up to {backup_path}")
            
            # 오래된 백업 정리
            await self._cleanup_old_backups()
            
        except Exception as e:
            logger.error(f"Model backup failed: {e}")

    async def _cleanup_old_backups(self):
        """오래된 백업 정리"""
        try:
            backup_files = list(self.backup_dir.glob("confidence_model_*.joblib"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 최대 버전 수를 초과하는 백업 삭제
            for backup_file in backup_files[self.config.max_model_versions:]:
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")
                
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    async def _deploy_new_model(self):
        """새 모델 배포"""
        try:
            # 모델이 이미 저장되어 있으므로 추가 작업 없음
            logger.info("New model deployed")
        except Exception as e:
            logger.error(f"Model deployment failed: {e}")

    async def _rollback_model(self):
        """모델 롤백"""
        try:
            backup_files = list(self.backup_dir.glob("confidence_model_*.joblib"))
            if backup_files:
                # 가장 최근 백업으로 롤백
                latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                
                import shutil
                shutil.copy2(latest_backup, self.ml_model.model_path)
                
                # 모델 다시 로드
                self.ml_model.load_model()
                
                logger.info(f"Model rolled back to {latest_backup}")
            else:
                logger.warning("No backup available for rollback")
                
        except Exception as e:
            logger.error(f"Model rollback failed: {e}")

    async def _update_thresholds(self, performance: ModelPerformance):
        """임계값 업데이트"""
        try:
            metrics = PerformanceMetrics(
                false_positive_rate=performance.false_positive_rate,
                false_negative_rate=performance.false_negative_rate,
                accuracy=performance.accuracy,
                precision=performance.precision,
                recall=performance.recall,
                f1_score=performance.f1_score,
                timestamp=performance.timestamp
            )
            
            await self.threshold_manager.adjust_thresholds(asdict(metrics))
            logger.info("Thresholds updated based on performance")
            
        except Exception as e:
            logger.error(f"Threshold update failed: {e}")

    async def _save_performance_history(self):
        """성능 이력 저장"""
        try:
            history_path = Path("data/performance_history.json")
            history_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 성능 이력을 JSON으로 변환
            history_data = []
            for perf in self.performance_history[-100:]:  # 최근 100개만 저장
                perf_dict = asdict(perf)
                perf_dict['timestamp'] = perf.timestamp.isoformat()
                history_data.append(perf_dict)
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Performance history saved: {len(history_data)} records")
            
        except Exception as e:
            logger.error(f"Performance history save failed: {e}")

    async def get_learning_status(self) -> Dict:
        """학습 상태 조회"""
        async with self.feedback_lock:
            queue_size = len(self.feedback_queue)
        
        latest_performance = self.performance_history[-1] if self.performance_history else None
        
        return {
            "is_learning": self.is_learning,
            "queue_size": queue_size,
            "last_learning_time": self.last_learning_time.isoformat() if self.last_learning_time else None,
            "latest_performance": asdict(latest_performance) if latest_performance else None,
            "total_feedback_processed": len(self.performance_history),
            "config": asdict(self.config)
        }

    async def get_performance_metrics(self, days: int = 7) -> List[Dict]:
        """성능 메트릭 조회"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_performance = [
            perf for perf in self.performance_history
            if perf.timestamp >= cutoff_date
        ]
        
        return [asdict(perf) for perf in recent_performance]

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# 전역 학습 파이프라인 인스턴스
_learning_pipeline = None

async def get_learning_pipeline() -> RealtimeLearningPipeline:
    """학습 파이프라인 싱글톤 인스턴스 반환"""
    global _learning_pipeline
    if _learning_pipeline is None:
        _learning_pipeline = RealtimeLearningPipeline()
        await _learning_pipeline.start_pipeline()
    return _learning_pipeline