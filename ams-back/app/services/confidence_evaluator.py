import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# 새로운 서비스 임포트
from .confidence_ml import ConfidenceMLModel, FeedbackData
from .dynamic_thresholds import DynamicThresholdManager, PerformanceMetrics

logger = logging.getLogger(__name__)

@dataclass
class ConfidenceThresholds:
    """신뢰도 임계값 설정 (레거시 호환성용)"""
    high: float = 0.85
    medium: float = 0.65
    low: float = 0.45
    very_low: float = 0.25

class ConfidenceEvaluator:
    """
    OCR 결과의 종합적인 신뢰도 평가 시스템
    OCR 신뢰도, 패턴 매칭, DB 검증 결과를 통합하여 최종 신뢰도 산출
    Phase 2: 머신러닝 기반 가중치 학습 및 동적 임계값 조정 통합
    """

    def __init__(self, thresholds: ConfidenceThresholds = None):
        self.thresholds = thresholds or ConfidenceThresholds()

        # Phase 2: 새로운 서비스 초기화
        self.ml_model = ConfidenceMLModel()
        self.threshold_manager = DynamicThresholdManager()

        # 피드백 수집을 위한 임시 저장소
        self.feedback_buffer: List[FeedbackData] = []
        self.performance_buffer: List[PerformanceMetrics] = []

        # 필드별 패턴 정의
        self.field_patterns = {
            'serial': [
                r'^[A-Z0-9]{6,12}$',  # 영문 대문자 + 숫자 6-12자
                r'^[A-Z]{2,3}[0-9]{4,8}$',  # 영문 2-3자 + 숫자 4-8자
                r'^[0-9]{8,12}$'  # 숫자만 8-12자
            ],
            'model': [
                r'^[A-Z0-9\-\s]{3,20}$',  # 영문 대문자 + 숫자 + 하이픈 + 공백
                r'^[가-힣A-Za-z0-9\s]{2,30}$',  # 한글 + 영문 + 숫자
                r'^\w+\s+\w+',  # 단어 + 공백 + 단어 패턴
            ],
            'manufacturer': [
                r'^[가-힣]{2,10}(전자|일렉트로닉스)?(\(주\))?$',  # 한글 제조사
                r'^[A-Za-z]{2,15}(\s+(Inc|Corp|Ltd|Co)\.?)?$',  # 영문 제조사
                r'^(LG|삼성|애플|델|레노버|HP|ASUS|MSI)',  # 주요 제조사
            ],
            'spec': [
                r'\d+\s*V',  # 전압
                r'\d+\s*A',  # 전류
                r'\d+\s*W',  # 전력
                r'\d+\s*Hz',  # 주파수
                r'\d+\s*(GB|TB|MB)',  # 용량
            ]
        }

        # 가중치 설정 (Phase 2: ML 모델에서 동적으로 조정)
        self.default_weights = {
            'ocr_confidence': 0.3,
            'pattern_confidence': 0.2,
            'db_verification': 0.4,
            'length_penalty': 0.1
        }

        # 현재 사용 중인 가중치 (ML 모델 또는 기본값)
        self.weights = self.ml_model.get_optimal_weights()

    def evaluate_ocr_result(self, ocr_data: Dict, verification_result: Optional[Dict] = None) -> Dict:
        """
        OCR 결과의 종합적인 신뢰도 평가 (Phase 2: ML 모델 통합)

        Args:
            ocr_data: OCR 결과 데이터 (text, confidence, category 포함)
            verification_result: DB 검증 결과 (선택사항)

        Returns:
            종합 신뢰도 평가 결과
        """
        text = ocr_data.get('text', '')
        ocr_confidence = ocr_data.get('confidence', 0.0)
        category = ocr_data.get('category', 'other')

        # 각 요소별 점수 계산
        scores = {
            'ocr_confidence': ocr_confidence,
            'pattern_confidence': self.evaluate_pattern_match(text, category),
            'db_verification': self._extract_db_confidence(verification_result),
            'length_penalty': self.calculate_length_penalty(text, category)
        }

        # Phase 2: ML 모델을 사용한 신뢰도 예측
        ml_confidence, ml_info = self.ml_model.predict_confidence(
            scores['ocr_confidence'],
            scores['pattern_confidence'],
            scores['db_verification'],
            scores['length_penalty']
        )

        # 기존 가중 평균과 ML 예측 결합
        traditional_score = sum(scores[key] * self.weights[key] for key in scores.keys())

        # ML 모델이 학습되어 있으면 ML 예측을 우선 사용, 아니면 기존 방식 사용
        if self.ml_model.is_trained:
            final_score = ml_confidence
            method = "ml_prediction"
        else:
            final_score = traditional_score
            method = "traditional_weighted"

        # Phase 2: 동적 임계값 사용
        current_thresholds = self.threshold_manager.get_current_thresholds()
        level = self._get_confidence_level_dynamic(final_score, current_thresholds)

        # 추천 사항 생성
        recommendations = self.generate_recommendations(scores, text, category)

        result = {
            'score': final_score,
            'level': level,
            'breakdown': scores,
            'recommendations': recommendations,
            'category': category,
            'text': text,
            'ml_info': ml_info,
            'method': method,
            'traditional_score': traditional_score,
            'thresholds_used': current_thresholds
        }

        return result

    def evaluate_pattern_match(self, text: str, category: str) -> float:
        """
        텍스트가 해당 카테고리의 패턴에 얼마나 잘 맞는지 평가

        Args:
            text: 평가할 텍스트
            category: 카테고리 (model, serial, manufacturer, spec)

        Returns:
            패턴 매칭 점수 (0.0 ~ 1.0)
        """
        if not text or category not in self.field_patterns:
            return 0.0

        patterns = self.field_patterns[category]
        max_score = 0.0

        for pattern in patterns:
            try:
                if re.match(pattern, text, re.IGNORECASE):
                    # 완전 매칭
                    max_score = max(max_score, 1.0)
                elif re.search(pattern, text, re.IGNORECASE):
                    # 부분 매칭
                    max_score = max(max_score, 0.7)
                else:
                    # 유사 패턴 검사
                    similarity = self._calculate_pattern_similarity(text, pattern)
                    max_score = max(max_score, similarity)
            except re.error:
                logger.warning(f"잘못된 정규식 패턴: {pattern}")
                continue

        # 추가 휴리스틱 검사
        heuristic_score = self._apply_heuristic_rules(text, category)
        max_score = max(max_score, heuristic_score)

        return min(max_score, 1.0)

    def _calculate_pattern_similarity(self, text: str, pattern: str) -> float:
        """패턴과 텍스트의 유사도 계산"""
        # 간단한 휴리스틱: 패턴의 특성과 텍스트 특성 비교

        # 숫자 비율 비교
        text_digit_ratio = sum(1 for c in text if c.isdigit()) / len(text) if text else 0
        pattern_has_digits = r'\d' in pattern or '[0-9]' in pattern

        # 영문 비율 비교
        text_alpha_ratio = sum(1 for c in text if c.isalpha()) / len(text) if text else 0
        pattern_has_alpha = r'[A-Za-z]' in pattern or r'[가-힣]' in pattern

        # 길이 적합성
        length_score = 0.5  # 기본값
        if r'{' in pattern:
            # 길이 제한이 있는 패턴
            length_match = re.search(r'\{(\d+),?(\d+)?\}', pattern)
            if length_match:
                min_len = int(length_match.group(1))
                max_len = int(length_match.group(2)) if length_match.group(2) else min_len
                if min_len <= len(text) <= max_len:
                    length_score = 1.0
                else:
                    length_score = 0.3

        # 종합 점수
        scores = []
        if pattern_has_digits:
            scores.append(text_digit_ratio)
        if pattern_has_alpha:
            scores.append(text_alpha_ratio)
        scores.append(length_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _apply_heuristic_rules(self, text: str, category: str) -> float:
        """카테고리별 휴리스틱 규칙 적용"""
        if not text:
            return 0.0

        score = 0.0

        if category == 'serial':
            # 시리얼번호 휴리스틱
            if len(text) >= 6:
                score += 0.3
            if any(c.isdigit() for c in text):
                score += 0.2
            if any(c.isupper() for c in text):
                score += 0.2
            if not any(c.islower() for c in text):  # 소문자가 없으면 좋음
                score += 0.1
            if not any(c in '!@#$%^&*()' for c in text):  # 특수문자가 없으면 좋음
                score += 0.2

        elif category == 'model':
            # 모델명 휴리스틱
            if len(text) >= 3:
                score += 0.2
            if any(c.isdigit() for c in text):
                score += 0.2
            if any(c.isalpha() for c in text):
                score += 0.2
            words = text.split()
            if len(words) >= 2:  # 여러 단어로 구성
                score += 0.2
            if len(words) <= 4:  # 너무 많지 않음
                score += 0.2

        elif category == 'manufacturer':
            # 제조사 휴리스틱
            known_manufacturers = [
                'lg', '삼성', 'samsung', '애플', 'apple', '델', 'dell', 
                '레노버', 'lenovo', 'hp', 'asus', 'msi', '소니', 'sony'
            ]
            if any(mfg in text.lower() for mfg in known_manufacturers):
                score += 0.8
            elif any(c.isalpha() for c in text):
                score += 0.4
            if '전자' in text or 'electronics' in text.lower():
                score += 0.2
            if '(주)' in text or 'inc' in text.lower() or 'corp' in text.lower():
                score += 0.1

        elif category == 'spec':
            # 스펙 휴리스틱
            spec_units = ['v', 'a', 'w', 'hz', 'gb', 'tb', 'mb', 'ghz', 'mhz']
            if any(unit in text.lower() for unit in spec_units):
                score += 0.6
            if any(c.isdigit() for c in text):
                score += 0.3
            if re.search(r'\d+\s*[a-zA-Z]+', text):  # 숫자 + 단위 패턴
                score += 0.1

        return min(score, 1.0)

    def calculate_length_penalty(self, text: str, category: str) -> float:
        """텍스트 길이에 따른 패널티/보너스 계산"""
        if not text:
            return 0.0

        length = len(text)

        # 카테고리별 적정 길이 범위
        optimal_ranges = {
            'serial': (6, 15),
            'model': (3, 25),
            'manufacturer': (2, 20),
            'spec': (2, 30),
            'other': (1, 50)
        }

        min_len, max_len = optimal_ranges.get(category, (1, 50))

        if min_len <= length <= max_len:
            # 적정 범위 내
            return 1.0
        elif length < min_len:
            # 너무 짧음
            return max(0.0, length / min_len)
        else:
            # 너무 김
            penalty = max(0.0, 1.0 - (length - max_len) / max_len)
            return penalty

    def _extract_db_confidence(self, verification_result: Optional[Dict]) -> float:
        """DB 검증 결과에서 신뢰도 추출"""
        if not verification_result:
            return 0.0

        status = verification_result.get('status', 'not_found')
        confidence = verification_result.get('confidence', 0.0)

        # 상태별 기본 신뢰도
        status_scores = {
            'verified': 1.0,
            'fuzzy_match': 0.8,
            'partial_match': 0.6,
            'similar_match': 0.5,
            'not_found': 0.0,
            'missing': 0.0
        }

        base_score = status_scores.get(status, 0.0)

        # 검증 결과의 신뢰도와 조합
        return min(base_score * confidence, 1.0) if confidence > 0 else base_score

    def get_confidence_level(self, score: float) -> str:
        """신뢰도 점수를 레벨로 변환 (레거시 호환성)"""
        if score >= self.thresholds.high:
            return 'high'
        elif score >= self.thresholds.medium:
            return 'medium'
        elif score >= self.thresholds.low:
            return 'low'
        else:
            return 'very_low'

    def _get_confidence_level_dynamic(self, score: float, thresholds: Dict[str, float]) -> str:
        """동적 임계값을 사용한 신뢰도 레벨 결정"""
        if score >= thresholds.get('high', 0.85):
            return 'high'
        elif score >= thresholds.get('medium', 0.65):
            return 'medium'
        elif score >= thresholds.get('low', 0.45):
            return 'low'
        else:
            return 'very_low'

    def generate_recommendations(self, scores: Dict, text: str, category: str) -> List[str]:
        """신뢰도 점수를 바탕으로 개선 권장사항 생성"""
        recommendations = []

        # OCR 신뢰도가 낮은 경우
        if scores['ocr_confidence'] < 0.6:
            recommendations.append("OCR 인식 신뢰도가 낮습니다. 이미지 품질을 확인하거나 수동으로 검토해주세요.")

        # 패턴 매칭이 낮은 경우
        if scores['pattern_confidence'] < 0.5:
            recommendations.append(f"{category} 형식에 맞지 않는 것 같습니다. 올바른 형식인지 확인해주세요.")

        # DB 검증이 실패한 경우
        if scores['db_verification'] < 0.3:
            recommendations.append("데이터베이스에서 일치하는 정보를 찾을 수 없습니다. 새로운 자산이거나 오타가 있을 수 있습니다.")

        # 길이 문제
        if scores['length_penalty'] < 0.5:
            if len(text) < 3:
                recommendations.append("텍스트가 너무 짧습니다. 누락된 부분이 있는지 확인해주세요.")
            else:
                recommendations.append("텍스트가 예상보다 깁니다. 불필요한 부분이 포함되었는지 확인해주세요.")

        # 전체적으로 낮은 경우
        overall_score = sum(scores[key] * self.weights[key] for key in scores.keys())
        if overall_score < 0.4:
            recommendations.append("전반적인 신뢰도가 낮습니다. 수동으로 확인하고 수정해주세요.")

        return recommendations

    def batch_evaluate(self, ocr_results: List[Dict], verification_results: Optional[Dict] = None) -> Dict:
        """여러 OCR 결과를 일괄 평가"""
        evaluations = {}
        summary = {
            'total_count': len(ocr_results),
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0,
            'very_low_confidence': 0,
            'average_score': 0.0
        }

        total_score = 0.0

        for ocr_data in ocr_results:
            item_id = ocr_data.get('id', str(len(evaluations)))
            verification_result = verification_results.get(item_id) if verification_results else None

            evaluation = self.evaluate_ocr_result(ocr_data, verification_result)
            evaluations[item_id] = evaluation

            # 통계 업데이트
            level = evaluation['level']
            summary[f'{level}_confidence'] += 1
            total_score += evaluation['score']

        summary['average_score'] = total_score / len(ocr_results) if ocr_results else 0.0

        return {
            'evaluations': evaluations,
            'summary': summary
        }

    def update_thresholds(self, new_thresholds: ConfidenceThresholds):
        """신뢰도 임계값 업데이트"""
        self.thresholds = new_thresholds

    # Phase 2: 새로운 메서드들 추가

    async def collect_user_feedback(self, ocr_data: Dict, verification_result: Optional[Dict], 
                                   user_accepted: bool, corrected_text: Optional[str] = None):
        """사용자 피드백 수집"""
        text = ocr_data.get('text', '')
        ocr_confidence = ocr_data.get('confidence', 0.0)
        category = ocr_data.get('category', 'other')

        # 점수 계산
        scores = {
            'ocr_confidence': ocr_confidence,
            'pattern_confidence': self.evaluate_pattern_match(text, category),
            'db_verification': self._extract_db_confidence(verification_result),
            'length_penalty': self.calculate_length_penalty(text, category)
        }

        # 최종 신뢰도 계산
        final_confidence = sum(scores[key] * self.weights[key] for key in scores.keys())

        # 피드백 데이터 생성
        feedback = self.ml_model.collect_feedback(
            ocr_confidence=scores['ocr_confidence'],
            pattern_confidence=scores['pattern_confidence'],
            db_verification=scores['db_verification'],
            length_penalty=scores['length_penalty'],
            user_accepted=user_accepted,
            final_confidence=final_confidence,
            category=category,
            original_text=text,
            corrected_text=corrected_text
        )

        # 버퍼에 추가
        self.feedback_buffer.append(feedback)

        # 일정량 쌓이면 모델 재학습
        if len(self.feedback_buffer) >= 20:
            await self._retrain_ml_model()

    async def _retrain_ml_model(self):
        """ML 모델 재학습"""
        if len(self.feedback_buffer) >= 10:
            try:
                result = await self.ml_model.train_from_feedback(self.feedback_buffer)
                if result.get('status') == 'success':
                    # 가중치 업데이트
                    self.weights = self.ml_model.get_optimal_weights()
                    logger.info(f"ML 모델 재학습 완료: {result}")

                    # 버퍼 초기화
                    self.feedback_buffer = []

            except Exception as e:
                logger.error(f"ML 모델 재학습 중 오류: {str(e)}")

    async def update_performance_metrics(self, metrics: PerformanceMetrics):
        """성능 지표 업데이트 및 임계값 조정"""
        try:
            adjustment_result = await self.threshold_manager.adjust_thresholds(metrics)
            if adjustment_result.get('adjusted'):
                logger.info(f"임계값 자동 조정됨: {adjustment_result}")
            return adjustment_result
        except Exception as e:
            logger.error(f"임계값 조정 중 오류: {str(e)}")
            return {"adjusted": False, "error": str(e)}

    def get_ml_model_info(self) -> Dict:
        """ML 모델 정보 반환"""
        return self.ml_model.get_model_info()

    def get_threshold_info(self) -> Dict:
        """임계값 관리 정보 반환"""
        return {
            "current_thresholds": self.threshold_manager.get_current_thresholds(),
            "adjustment_history": self.threshold_manager.get_adjustment_history(5),
            "performance_trend": self.threshold_manager.get_performance_trend()
        }

    def get_stats(self) -> Dict:
        """평가 시스템 통계 (Phase 2: 확장)"""
        base_stats = {
            'thresholds': {
                'high': self.thresholds.high,
                'medium': self.thresholds.medium,
                'low': self.thresholds.low,
                'very_low': self.thresholds.very_low
            },
            'weights': self.weights,
            'supported_categories': list(self.field_patterns.keys())
        }

        # Phase 2: 추가 통계
        base_stats.update({
            'ml_model': self.get_ml_model_info(),
            'dynamic_thresholds': self.get_threshold_info(),
            'feedback_buffer_size': len(self.feedback_buffer),
            'performance_buffer_size': len(self.performance_buffer)
        })

        return base_stats
