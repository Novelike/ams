import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """성능 지표 데이터 구조"""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    total_predictions: int = 0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    @property
    def precision(self) -> float:
        """정밀도 계산"""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    @property
    def recall(self) -> float:
        """재현율 계산"""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    @property
    def f1_score(self) -> float:
        """F1 점수 계산"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)
    
    @property
    def accuracy(self) -> float:
        """정확도 계산"""
        if self.total_predictions == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total_predictions
    
    @property
    def false_positive_rate(self) -> float:
        """거짓 양성률 계산"""
        if self.false_positives + self.true_negatives == 0:
            return 0.0
        return self.false_positives / (self.false_positives + self.true_negatives)
    
    @property
    def false_negative_rate(self) -> float:
        """거짓 음성률 계산"""
        if self.false_negatives + self.true_positives == 0:
            return 0.0
        return self.false_negatives / (self.false_negatives + self.true_positives)

@dataclass
class ThresholdConfig:
    """임계값 설정"""
    high: float = 0.85
    medium: float = 0.65
    low: float = 0.45
    very_low: float = 0.25
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'ThresholdConfig':
        return cls(**data)

@dataclass
class AdjustmentHistory:
    """임계값 조정 이력"""
    timestamp: str
    old_thresholds: ThresholdConfig
    new_thresholds: ThresholdConfig
    metrics: PerformanceMetrics
    reason: str
    adjustment_magnitude: float

class DynamicThresholdManager:
    """
    동적 임계값 조정 시스템
    성능 지표에 따라 신뢰도 임계값을 자동으로 조정
    """
    
    def __init__(self, data_dir: str = "data/thresholds"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 경로
        self.thresholds_file = self.data_dir / "current_thresholds.json"
        self.history_file = self.data_dir / "adjustment_history.jsonl"
        self.metrics_file = self.data_dir / "performance_metrics.jsonl"
        
        # 현재 임계값
        self.thresholds = ThresholdConfig()
        
        # 조정 설정
        self.adjustment_config = {
            'min_samples_for_adjustment': 50,  # 조정을 위한 최소 샘플 수
            'adjustment_step': 0.02,  # 기본 조정 단계
            'max_adjustment_per_cycle': 0.05,  # 한 번에 최대 조정량
            'target_precision': 0.85,  # 목표 정밀도
            'target_recall': 0.80,  # 목표 재현율
            'max_false_positive_rate': 0.10,  # 최대 허용 거짓 양성률
            'max_false_negative_rate': 0.15,  # 최대 허용 거짓 음성률
            'adjustment_cooldown_hours': 24,  # 조정 후 대기 시간 (시간)
        }
        
        # 조정 이력
        self.adjustment_history: List[AdjustmentHistory] = []
        
        # 현재 임계값 로드
        self.load_current_thresholds()
        self.load_adjustment_history()

    def load_current_thresholds(self):
        """현재 임계값 로드"""
        try:
            if self.thresholds_file.exists():
                with open(self.thresholds_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.thresholds = ThresholdConfig.from_dict(data)
                    logger.info(f"임계값 로드 완료: {self.thresholds}")
            else:
                # 기본값으로 저장
                self.save_current_thresholds()
                logger.info("기본 임계값으로 초기화")
        except Exception as e:
            logger.error(f"임계값 로드 중 오류: {str(e)}")
            self.thresholds = ThresholdConfig()

    def save_current_thresholds(self):
        """현재 임계값 저장"""
        try:
            with open(self.thresholds_file, 'w', encoding='utf-8') as f:
                json.dump(self.thresholds.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("임계값 저장 완료")
        except Exception as e:
            logger.error(f"임계값 저장 중 오류: {str(e)}")

    def load_adjustment_history(self):
        """조정 이력 로드"""
        try:
            if self.history_file.exists():
                self.adjustment_history = []
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            history = AdjustmentHistory(
                                timestamp=data['timestamp'],
                                old_thresholds=ThresholdConfig.from_dict(data['old_thresholds']),
                                new_thresholds=ThresholdConfig.from_dict(data['new_thresholds']),
                                metrics=PerformanceMetrics(**data['metrics']),
                                reason=data['reason'],
                                adjustment_magnitude=data['adjustment_magnitude']
                            )
                            self.adjustment_history.append(history)
                logger.info(f"조정 이력 로드 완료: {len(self.adjustment_history)}개 항목")
        except Exception as e:
            logger.error(f"조정 이력 로드 중 오류: {str(e)}")
            self.adjustment_history = []

    def save_adjustment_history(self, history: AdjustmentHistory):
        """조정 이력 저장"""
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                data = {
                    'timestamp': history.timestamp,
                    'old_thresholds': history.old_thresholds.to_dict(),
                    'new_thresholds': history.new_thresholds.to_dict(),
                    'metrics': asdict(history.metrics),
                    'reason': history.reason,
                    'adjustment_magnitude': history.adjustment_magnitude
                }
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            self.adjustment_history.append(history)
        except Exception as e:
            logger.error(f"조정 이력 저장 중 오류: {str(e)}")

    def save_performance_metrics(self, metrics: PerformanceMetrics):
        """성능 지표 저장"""
        try:
            with open(self.metrics_file, 'a', encoding='utf-8') as f:
                data = asdict(metrics)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"성능 지표 저장 중 오류: {str(e)}")

    async def adjust_thresholds(self, metrics: PerformanceMetrics) -> Dict:
        """
        성능 지표에 따른 임계값 조정
        
        Args:
            metrics: 현재 성능 지표
            
        Returns:
            조정 결과
        """
        logger.info(f"임계값 조정 검토 시작: {metrics}")
        
        # 성능 지표 저장
        self.save_performance_metrics(metrics)
        
        # 조정 가능 여부 확인
        if not self._can_adjust():
            return {
                "adjusted": False,
                "reason": "adjustment_cooldown",
                "next_adjustment_time": self._get_next_adjustment_time()
            }
        
        if metrics.total_predictions < self.adjustment_config['min_samples_for_adjustment']:
            return {
                "adjusted": False,
                "reason": "insufficient_samples",
                "current_samples": metrics.total_predictions,
                "required_samples": self.adjustment_config['min_samples_for_adjustment']
            }
        
        # 조정 필요성 분석
        adjustment_needed, reason, magnitude = self._analyze_adjustment_need(metrics)
        
        if not adjustment_needed:
            return {
                "adjusted": False,
                "reason": "no_adjustment_needed",
                "current_performance": {
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1_score": metrics.f1_score,
                    "false_positive_rate": metrics.false_positive_rate,
                    "false_negative_rate": metrics.false_negative_rate
                }
            }
        
        # 임계값 조정 실행
        old_thresholds = ThresholdConfig(**self.thresholds.to_dict())
        new_thresholds = self._calculate_new_thresholds(metrics, magnitude)
        
        # 조정 적용
        self.thresholds = new_thresholds
        self.save_current_thresholds()
        
        # 조정 이력 저장
        history = AdjustmentHistory(
            timestamp=datetime.utcnow().isoformat(),
            old_thresholds=old_thresholds,
            new_thresholds=new_thresholds,
            metrics=metrics,
            reason=reason,
            adjustment_magnitude=magnitude
        )
        self.save_adjustment_history(history)
        
        logger.info(f"임계값 조정 완료: {old_thresholds.to_dict()} -> {new_thresholds.to_dict()}")
        
        return {
            "adjusted": True,
            "reason": reason,
            "magnitude": magnitude,
            "old_thresholds": old_thresholds.to_dict(),
            "new_thresholds": new_thresholds.to_dict(),
            "performance_improvement_expected": self._estimate_improvement(metrics, magnitude)
        }

    def _can_adjust(self) -> bool:
        """조정 가능 여부 확인 (쿨다운 시간 체크)"""
        if not self.adjustment_history:
            return True
        
        last_adjustment = self.adjustment_history[-1]
        last_time = datetime.fromisoformat(last_adjustment.timestamp)
        cooldown_hours = self.adjustment_config['adjustment_cooldown_hours']
        
        return datetime.utcnow() - last_time > timedelta(hours=cooldown_hours)

    def _get_next_adjustment_time(self) -> Optional[str]:
        """다음 조정 가능 시간 반환"""
        if not self.adjustment_history:
            return None
        
        last_adjustment = self.adjustment_history[-1]
        last_time = datetime.fromisoformat(last_adjustment.timestamp)
        cooldown_hours = self.adjustment_config['adjustment_cooldown_hours']
        next_time = last_time + timedelta(hours=cooldown_hours)
        
        return next_time.isoformat()

    def _analyze_adjustment_need(self, metrics: PerformanceMetrics) -> Tuple[bool, str, float]:
        """
        조정 필요성 분석
        
        Returns:
            (조정 필요 여부, 이유, 조정 크기)
        """
        config = self.adjustment_config
        
        # False Positive가 너무 높은 경우 (임계값을 높여야 함)
        if metrics.false_positive_rate > config['max_false_positive_rate']:
            magnitude = min(
                metrics.false_positive_rate - config['max_false_positive_rate'],
                config['max_adjustment_per_cycle']
            )
            return True, "high_false_positive_rate", magnitude
        
        # False Negative가 너무 높은 경우 (임계값을 낮춰야 함)
        if metrics.false_negative_rate > config['max_false_negative_rate']:
            magnitude = min(
                metrics.false_negative_rate - config['max_false_negative_rate'],
                config['max_adjustment_per_cycle']
            )
            return True, "high_false_negative_rate", -magnitude
        
        # 정밀도가 목표보다 낮은 경우
        if metrics.precision < config['target_precision']:
            magnitude = min(
                config['target_precision'] - metrics.precision,
                config['max_adjustment_per_cycle']
            )
            return True, "low_precision", magnitude
        
        # 재현율이 목표보다 낮은 경우
        if metrics.recall < config['target_recall']:
            magnitude = min(
                config['target_recall'] - metrics.recall,
                config['max_adjustment_per_cycle']
            )
            return True, "low_recall", -magnitude
        
        return False, "performance_acceptable", 0.0

    def _calculate_new_thresholds(self, metrics: PerformanceMetrics, magnitude: float) -> ThresholdConfig:
        """새로운 임계값 계산"""
        new_thresholds = ThresholdConfig(**self.thresholds.to_dict())
        
        # 조정 방향에 따라 모든 임계값을 비례적으로 조정
        if magnitude > 0:  # 임계값 상향 조정 (더 엄격하게)
            new_thresholds.high = min(0.95, new_thresholds.high + magnitude)
            new_thresholds.medium = min(0.85, new_thresholds.medium + magnitude * 0.8)
            new_thresholds.low = min(0.75, new_thresholds.low + magnitude * 0.6)
            new_thresholds.very_low = min(0.65, new_thresholds.very_low + magnitude * 0.4)
        else:  # 임계값 하향 조정 (더 관대하게)
            magnitude = abs(magnitude)
            new_thresholds.high = max(0.75, new_thresholds.high - magnitude)
            new_thresholds.medium = max(0.55, new_thresholds.medium - magnitude * 0.8)
            new_thresholds.low = max(0.35, new_thresholds.low - magnitude * 0.6)
            new_thresholds.very_low = max(0.15, new_thresholds.very_low - magnitude * 0.4)
        
        return new_thresholds

    def _estimate_improvement(self, metrics: PerformanceMetrics, magnitude: float) -> Dict:
        """조정 후 예상 성능 개선 추정"""
        if magnitude > 0:
            # 임계값 상향 조정 시
            return {
                "precision_change": "+0.02 to +0.05",
                "recall_change": "-0.01 to -0.03",
                "false_positive_reduction": "expected",
                "overall_accuracy": "likely_improved"
            }
        else:
            # 임계값 하향 조정 시
            return {
                "precision_change": "-0.01 to -0.03",
                "recall_change": "+0.02 to +0.05",
                "false_negative_reduction": "expected",
                "overall_accuracy": "likely_improved"
            }

    def get_current_thresholds(self) -> Dict[str, float]:
        """현재 임계값 반환"""
        return self.thresholds.to_dict()

    def get_adjustment_history(self, limit: int = 10) -> List[Dict]:
        """조정 이력 반환"""
        recent_history = self.adjustment_history[-limit:] if limit > 0 else self.adjustment_history
        return [
            {
                'timestamp': h.timestamp,
                'old_thresholds': h.old_thresholds.to_dict(),
                'new_thresholds': h.new_thresholds.to_dict(),
                'reason': h.reason,
                'magnitude': h.adjustment_magnitude,
                'performance': {
                    'precision': h.metrics.precision,
                    'recall': h.metrics.recall,
                    'f1_score': h.metrics.f1_score,
                    'accuracy': h.metrics.accuracy
                }
            }
            for h in recent_history
        ]

    def get_performance_trend(self, days: int = 7) -> Dict:
        """성능 트렌드 분석"""
        try:
            if not self.metrics_file.exists():
                return {"trend": "no_data"}
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            recent_metrics = []
            
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        if timestamp >= cutoff_time:
                            recent_metrics.append(PerformanceMetrics(**data))
            
            if len(recent_metrics) < 2:
                return {"trend": "insufficient_data"}
            
            # 트렌드 계산
            first_half = recent_metrics[:len(recent_metrics)//2]
            second_half = recent_metrics[len(recent_metrics)//2:]
            
            avg_precision_first = sum(m.precision for m in first_half) / len(first_half)
            avg_precision_second = sum(m.precision for m in second_half) / len(second_half)
            
            avg_recall_first = sum(m.recall for m in first_half) / len(first_half)
            avg_recall_second = sum(m.recall for m in second_half) / len(second_half)
            
            return {
                "trend": "improving" if (avg_precision_second > avg_precision_first and 
                                       avg_recall_second > avg_recall_first) else "declining",
                "precision_trend": avg_precision_second - avg_precision_first,
                "recall_trend": avg_recall_second - avg_recall_first,
                "sample_count": len(recent_metrics),
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"성능 트렌드 분석 중 오류: {str(e)}")
            return {"trend": "error", "error": str(e)}

    def manual_threshold_override(self, new_thresholds: Dict[str, float], reason: str = "manual_override"):
        """수동 임계값 설정"""
        old_thresholds = ThresholdConfig(**self.thresholds.to_dict())
        self.thresholds = ThresholdConfig.from_dict(new_thresholds)
        self.save_current_thresholds()
        
        # 수동 조정 이력 저장
        history = AdjustmentHistory(
            timestamp=datetime.utcnow().isoformat(),
            old_thresholds=old_thresholds,
            new_thresholds=self.thresholds,
            metrics=PerformanceMetrics(),  # 빈 메트릭
            reason=reason,
            adjustment_magnitude=0.0
        )
        self.save_adjustment_history(history)
        
        logger.info(f"수동 임계값 설정 완료: {new_thresholds}")

    def reset_to_defaults(self):
        """기본값으로 초기화"""
        self.thresholds = ThresholdConfig()
        self.save_current_thresholds()
        logger.info("임계값을 기본값으로 초기화")