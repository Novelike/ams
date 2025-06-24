import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import random
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """테스트 상태"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class ABTestConfig:
    """A/B 테스트 설정"""
    test_id: str
    name: str
    description: str
    status: TestStatus
    traffic_split: Dict[str, float]  # {"control": 0.5, "variant_a": 0.5}
    start_date: datetime
    end_date: datetime
    success_metric: str  # "accuracy", "user_satisfaction", "processing_time"
    minimum_sample_size: int
    confidence_level: float  # 0.95 for 95% confidence
    created_by: str
    created_at: datetime
    updated_at: datetime

@dataclass
class TestVariant:
    """테스트 변형"""
    variant_id: str
    name: str
    description: str
    config: Dict[str, Any]  # 변형별 설정 (임계값, 알고리즘 등)
    is_control: bool = False

@dataclass
class TestEvent:
    """테스트 이벤트"""
    event_id: str
    test_id: str
    variant_id: str
    user_id: str
    session_id: str
    event_type: str  # "exposure", "conversion", "feedback"
    event_data: Dict[str, Any]
    timestamp: datetime

@dataclass
class TestResult:
    """테스트 결과"""
    test_id: str
    variant_id: str
    sample_size: int
    conversion_rate: float
    confidence_interval: Tuple[float, float]
    p_value: float
    is_significant: bool
    effect_size: float
    timestamp: datetime

class ABTestingFramework:
    """
    A/B 테스트 프레임워크
    - 사용자 그룹 분할
    - 테스트 변형 관리
    - 성능 지표 수집
    - 통계적 유의성 검증
    """
    
    def __init__(self, data_dir: str = "data/ab_testing"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 테스트 저장소
        self.active_tests: Dict[str, ABTestConfig] = {}
        self.test_variants: Dict[str, List[TestVariant]] = {}
        self.test_events: List[TestEvent] = []
        self.test_results: Dict[str, List[TestResult]] = {}
        
        # 사용자 할당 캐시
        self.user_assignments: Dict[str, Dict[str, str]] = {}  # {user_id: {test_id: variant_id}}
        
        # 백그라운드 태스크
        self.analysis_task = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 설정
        self.hash_salt = "ams_ab_testing_salt"
        
        # 데이터 로드
        asyncio.create_task(self._load_data())

    async def start_framework(self):
        """프레임워크 시작"""
        if self.analysis_task is None:
            self.analysis_task = asyncio.create_task(self._analysis_loop())
            logger.info("A/B testing framework started")

    async def stop_framework(self):
        """프레임워크 중지"""
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
            self.analysis_task = None
            logger.info("A/B testing framework stopped")

    async def create_test(self, config: ABTestConfig, variants: List[TestVariant]) -> bool:
        """새 테스트 생성"""
        try:
            # 유효성 검사
            if not self._validate_test_config(config, variants):
                return False
            
            # 테스트 저장
            self.active_tests[config.test_id] = config
            self.test_variants[config.test_id] = variants
            self.test_results[config.test_id] = []
            
            # 파일로 저장
            await self._save_test_config(config, variants)
            
            logger.info(f"A/B test created: {config.test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            return False

    def _validate_test_config(self, config: ABTestConfig, variants: List[TestVariant]) -> bool:
        """테스트 설정 유효성 검사"""
        # 트래픽 분할 합계 확인
        total_traffic = sum(config.traffic_split.values())
        if abs(total_traffic - 1.0) > 0.001:
            logger.error(f"Traffic split must sum to 1.0, got {total_traffic}")
            return False
        
        # 변형 ID와 트래픽 분할 일치 확인
        variant_ids = {v.variant_id for v in variants}
        traffic_ids = set(config.traffic_split.keys())
        
        if variant_ids != traffic_ids:
            logger.error(f"Variant IDs {variant_ids} don't match traffic split {traffic_ids}")
            return False
        
        # 컨트롤 그룹 확인
        control_variants = [v for v in variants if v.is_control]
        if len(control_variants) != 1:
            logger.error(f"Must have exactly one control variant, got {len(control_variants)}")
            return False
        
        return True

    async def get_user_variant(self, test_id: str, user_id: str) -> Optional[str]:
        """사용자에게 할당된 변형 조회"""
        try:
            # 테스트 존재 확인
            if test_id not in self.active_tests:
                return None
            
            test_config = self.active_tests[test_id]
            
            # 테스트 활성 상태 확인
            if test_config.status != TestStatus.ACTIVE:
                return None
            
            # 테스트 기간 확인
            now = datetime.utcnow()
            if now < test_config.start_date or now > test_config.end_date:
                return None
            
            # 기존 할당 확인
            if user_id in self.user_assignments and test_id in self.user_assignments[user_id]:
                variant_id = self.user_assignments[user_id][test_id]
                
                # 노출 이벤트 기록
                await self._record_exposure(test_id, variant_id, user_id)
                return variant_id
            
            # 새 할당 생성
            variant_id = self._assign_user_to_variant(test_id, user_id, test_config.traffic_split)
            
            if variant_id:
                # 할당 저장
                if user_id not in self.user_assignments:
                    self.user_assignments[user_id] = {}
                self.user_assignments[user_id][test_id] = variant_id
                
                # 노출 이벤트 기록
                await self._record_exposure(test_id, variant_id, user_id)
                
                return variant_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user variant: {e}")
            return None

    def _assign_user_to_variant(self, test_id: str, user_id: str, traffic_split: Dict[str, float]) -> Optional[str]:
        """사용자를 변형에 할당"""
        try:
            # 일관된 해시 생성
            hash_input = f"{test_id}:{user_id}:{self.hash_salt}"
            hash_value = hashlib.md5(hash_input.encode()).hexdigest()
            
            # 0-1 사이의 값으로 변환
            hash_float = int(hash_value[:8], 16) / (2**32)
            
            # 트래픽 분할에 따라 할당
            cumulative = 0.0
            for variant_id, percentage in traffic_split.items():
                cumulative += percentage
                if hash_float <= cumulative:
                    return variant_id
            
            # 기본값 (마지막 변형)
            return list(traffic_split.keys())[-1]
            
        except Exception as e:
            logger.error(f"Failed to assign user to variant: {e}")
            return None

    async def _record_exposure(self, test_id: str, variant_id: str, user_id: str):
        """노출 이벤트 기록"""
        try:
            event = TestEvent(
                event_id=f"{test_id}_{variant_id}_{user_id}_{int(datetime.utcnow().timestamp())}",
                test_id=test_id,
                variant_id=variant_id,
                user_id=user_id,
                session_id="",  # 세션 ID는 별도로 관리
                event_type="exposure",
                event_data={},
                timestamp=datetime.utcnow()
            )
            
            self.test_events.append(event)
            
        except Exception as e:
            logger.error(f"Failed to record exposure: {e}")

    async def record_conversion(self, test_id: str, user_id: str, 
                              conversion_data: Dict[str, Any]) -> bool:
        """전환 이벤트 기록"""
        try:
            # 사용자 할당 확인
            if (user_id not in self.user_assignments or 
                test_id not in self.user_assignments[user_id]):
                logger.warning(f"User {user_id} not assigned to test {test_id}")
                return False
            
            variant_id = self.user_assignments[user_id][test_id]
            
            event = TestEvent(
                event_id=f"{test_id}_{variant_id}_{user_id}_conv_{int(datetime.utcnow().timestamp())}",
                test_id=test_id,
                variant_id=variant_id,
                user_id=user_id,
                session_id="",
                event_type="conversion",
                event_data=conversion_data,
                timestamp=datetime.utcnow()
            )
            
            self.test_events.append(event)
            logger.info(f"Conversion recorded for test {test_id}, variant {variant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record conversion: {e}")
            return False

    async def record_feedback(self, test_id: str, user_id: str, 
                            feedback_data: Dict[str, Any]) -> bool:
        """피드백 이벤트 기록"""
        try:
            # 사용자 할당 확인
            if (user_id not in self.user_assignments or 
                test_id not in self.user_assignments[user_id]):
                return False
            
            variant_id = self.user_assignments[user_id][test_id]
            
            event = TestEvent(
                event_id=f"{test_id}_{variant_id}_{user_id}_feedback_{int(datetime.utcnow().timestamp())}",
                test_id=test_id,
                variant_id=variant_id,
                user_id=user_id,
                session_id="",
                event_type="feedback",
                event_data=feedback_data,
                timestamp=datetime.utcnow()
            )
            
            self.test_events.append(event)
            return True
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False

    async def _analysis_loop(self):
        """주기적 분석 루프"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 분석
                
                for test_id in self.active_tests:
                    await self._analyze_test(test_id)
                
                # 데이터 저장
                await self._save_events()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                await asyncio.sleep(300)  # 5분 후 재시도

    async def _analyze_test(self, test_id: str):
        """테스트 분석"""
        try:
            test_config = self.active_tests[test_id]
            
            # 최소 샘플 크기 확인
            total_exposures = len([e for e in self.test_events 
                                 if e.test_id == test_id and e.event_type == "exposure"])
            
            if total_exposures < test_config.minimum_sample_size:
                logger.info(f"Test {test_id} has insufficient sample size: {total_exposures}")
                return
            
            # 변형별 분석
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self._calculate_test_results,
                test_id, test_config
            )
            
            if results:
                self.test_results[test_id] = results
                await self._save_test_results(test_id, results)
                
                # 자동 완료 확인
                await self._check_auto_completion(test_id, results)
            
        except Exception as e:
            logger.error(f"Failed to analyze test {test_id}: {e}")

    def _calculate_test_results(self, test_id: str, test_config: ABTestConfig) -> List[TestResult]:
        """테스트 결과 계산"""
        try:
            results = []
            
            # 변형별 데이터 수집
            variant_data = {}
            
            for variant in self.test_variants[test_id]:
                exposures = [e for e in self.test_events 
                           if e.test_id == test_id and e.variant_id == variant.variant_id 
                           and e.event_type == "exposure"]
                
                conversions = [e for e in self.test_events 
                             if e.test_id == test_id and e.variant_id == variant.variant_id 
                             and e.event_type == "conversion"]
                
                variant_data[variant.variant_id] = {
                    "exposures": len(exposures),
                    "conversions": len(conversions),
                    "is_control": variant.is_control
                }
            
            # 컨트롤 그룹 찾기
            control_variant = None
            for variant_id, data in variant_data.items():
                if data["is_control"]:
                    control_variant = variant_id
                    break
            
            if not control_variant:
                logger.error(f"No control variant found for test {test_id}")
                return []
            
            control_data = variant_data[control_variant]
            
            # 각 변형에 대해 통계 분석
            for variant_id, data in variant_data.items():
                if data["exposures"] == 0:
                    continue
                
                conversion_rate = data["conversions"] / data["exposures"]
                
                if variant_id == control_variant:
                    # 컨트롤 그룹
                    ci_lower, ci_upper = self._calculate_confidence_interval(
                        data["conversions"], data["exposures"], test_config.confidence_level
                    )
                    
                    results.append(TestResult(
                        test_id=test_id,
                        variant_id=variant_id,
                        sample_size=data["exposures"],
                        conversion_rate=conversion_rate,
                        confidence_interval=(ci_lower, ci_upper),
                        p_value=1.0,  # 컨트롤 그룹은 p-value 1.0
                        is_significant=False,
                        effect_size=0.0,
                        timestamp=datetime.utcnow()
                    ))
                else:
                    # 테스트 변형
                    p_value, effect_size = self._calculate_significance(
                        control_data["conversions"], control_data["exposures"],
                        data["conversions"], data["exposures"]
                    )
                    
                    ci_lower, ci_upper = self._calculate_confidence_interval(
                        data["conversions"], data["exposures"], test_config.confidence_level
                    )
                    
                    is_significant = p_value < (1 - test_config.confidence_level)
                    
                    results.append(TestResult(
                        test_id=test_id,
                        variant_id=variant_id,
                        sample_size=data["exposures"],
                        conversion_rate=conversion_rate,
                        confidence_interval=(ci_lower, ci_upper),
                        p_value=p_value,
                        is_significant=is_significant,
                        effect_size=effect_size,
                        timestamp=datetime.utcnow()
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to calculate test results: {e}")
            return []

    def _calculate_confidence_interval(self, successes: int, trials: int, 
                                     confidence_level: float) -> Tuple[float, float]:
        """신뢰구간 계산"""
        if trials == 0:
            return (0.0, 0.0)
        
        try:
            # Wilson score interval
            z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
            p = successes / trials
            n = trials
            
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2 * n)) / denominator
            margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
            
            return (max(0, center - margin), min(1, center + margin))
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence interval: {e}")
            return (0.0, 1.0)

    def _calculate_significance(self, control_successes: int, control_trials: int,
                              variant_successes: int, variant_trials: int) -> Tuple[float, float]:
        """통계적 유의성 계산"""
        try:
            # Fisher's exact test
            from scipy.stats import fisher_exact
            
            # 2x2 contingency table
            table = [
                [control_successes, control_trials - control_successes],
                [variant_successes, variant_trials - variant_successes]
            ]
            
            odds_ratio, p_value = fisher_exact(table)
            
            # Effect size (Cohen's h)
            p1 = control_successes / control_trials if control_trials > 0 else 0
            p2 = variant_successes / variant_trials if variant_trials > 0 else 0
            
            effect_size = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))
            
            return p_value, effect_size
            
        except Exception as e:
            logger.error(f"Failed to calculate significance: {e}")
            return 1.0, 0.0

    async def _check_auto_completion(self, test_id: str, results: List[TestResult]):
        """자동 완료 확인"""
        try:
            test_config = self.active_tests[test_id]
            
            # 유의한 결과가 있는지 확인
            significant_results = [r for r in results if r.is_significant]
            
            if significant_results:
                # 충분한 샘플 크기와 유의한 결과가 있으면 테스트 완료
                total_sample = sum(r.sample_size for r in results)
                if total_sample >= test_config.minimum_sample_size * 2:  # 2배 이상
                    await self.complete_test(test_id, "Significant results detected")
            
        except Exception as e:
            logger.error(f"Failed to check auto completion: {e}")

    async def complete_test(self, test_id: str, reason: str = "") -> bool:
        """테스트 완료"""
        try:
            if test_id not in self.active_tests:
                return False
            
            self.active_tests[test_id].status = TestStatus.COMPLETED
            self.active_tests[test_id].updated_at = datetime.utcnow()
            
            # 최종 분석 실행
            await self._analyze_test(test_id)
            
            logger.info(f"A/B test {test_id} completed. Reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete test {test_id}: {e}")
            return False

    async def get_test_status(self, test_id: str) -> Optional[Dict]:
        """테스트 상태 조회"""
        try:
            if test_id not in self.active_tests:
                return None
            
            test_config = self.active_tests[test_id]
            
            # 이벤트 통계
            exposures = len([e for e in self.test_events 
                           if e.test_id == test_id and e.event_type == "exposure"])
            conversions = len([e for e in self.test_events 
                             if e.test_id == test_id and e.event_type == "conversion"])
            
            # 최신 결과
            latest_results = self.test_results.get(test_id, [])
            
            return {
                "config": asdict(test_config),
                "variants": [asdict(v) for v in self.test_variants[test_id]],
                "stats": {
                    "total_exposures": exposures,
                    "total_conversions": conversions,
                    "conversion_rate": conversions / exposures if exposures > 0 else 0
                },
                "latest_results": [asdict(r) for r in latest_results],
                "user_assignments": len(self.user_assignments)
            }
            
        except Exception as e:
            logger.error(f"Failed to get test status: {e}")
            return None

    async def _load_data(self):
        """데이터 로드"""
        try:
            # 테스트 설정 로드
            config_dir = self.data_dir / "configs"
            if config_dir.exists():
                for config_file in config_dir.glob("*.json"):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        test_config = ABTestConfig(**data["config"])
                        variants = [TestVariant(**v) for v in data["variants"]]
                        
                        self.active_tests[test_config.test_id] = test_config
                        self.test_variants[test_config.test_id] = variants
            
            # 이벤트 로드
            events_file = self.data_dir / "events.json"
            if events_file.exists():
                with open(events_file, 'r', encoding='utf-8') as f:
                    events_data = json.load(f)
                    self.test_events = [TestEvent(**e) for e in events_data]
            
            logger.info(f"Loaded {len(self.active_tests)} tests and {len(self.test_events)} events")
            
        except Exception as e:
            logger.error(f"Failed to load A/B testing data: {e}")

    async def _save_test_config(self, config: ABTestConfig, variants: List[TestVariant]):
        """테스트 설정 저장"""
        try:
            config_dir = self.data_dir / "configs"
            config_dir.mkdir(exist_ok=True)
            
            config_file = config_dir / f"{config.test_id}.json"
            
            data = {
                "config": asdict(config),
                "variants": [asdict(v) for v in variants]
            }
            
            # datetime 객체를 문자열로 변환
            data["config"]["start_date"] = config.start_date.isoformat()
            data["config"]["end_date"] = config.end_date.isoformat()
            data["config"]["created_at"] = config.created_at.isoformat()
            data["config"]["updated_at"] = config.updated_at.isoformat()
            data["config"]["status"] = config.status.value
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Failed to save test config: {e}")

    async def _save_events(self):
        """이벤트 저장"""
        try:
            events_file = self.data_dir / "events.json"
            
            events_data = []
            for event in self.test_events[-10000:]:  # 최근 10000개만 저장
                event_dict = asdict(event)
                event_dict["timestamp"] = event.timestamp.isoformat()
                events_data.append(event_dict)
            
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Failed to save events: {e}")

    async def _save_test_results(self, test_id: str, results: List[TestResult]):
        """테스트 결과 저장"""
        try:
            results_dir = self.data_dir / "results"
            results_dir.mkdir(exist_ok=True)
            
            results_file = results_dir / f"{test_id}.json"
            
            results_data = []
            for result in results:
                result_dict = asdict(result)
                result_dict["timestamp"] = result.timestamp.isoformat()
                results_data.append(result_dict)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# 전역 A/B 테스트 프레임워크 인스턴스
_ab_testing_framework = None

async def get_ab_testing_framework() -> ABTestingFramework:
    """A/B 테스트 프레임워크 싱글톤 인스턴스 반환"""
    global _ab_testing_framework
    if _ab_testing_framework is None:
        _ab_testing_framework = ABTestingFramework()
        await _ab_testing_framework.start_framework()
    return _ab_testing_framework