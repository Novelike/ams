import numpy as np
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, mean_squared_error
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn이 설치되지 않았습니다. 기본 가중치를 사용합니다.")
    SKLEARN_AVAILABLE = False

@dataclass
class FeedbackData:
    """사용자 피드백 데이터 구조"""
    ocr_confidence: float
    pattern_confidence: float
    db_verification: float
    length_penalty: float
    user_accepted: bool  # 사용자가 수정했는지 여부
    final_confidence: float
    category: str
    timestamp: str
    original_text: str
    corrected_text: Optional[str] = None

class ConfidenceMLModel:
    """
    머신러닝 기반 신뢰도 가중치 학습 모델
    사용자 피드백을 바탕으로 최적의 가중치를 학습
    """
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 모델 파일 경로
        self.weight_model_path = self.model_dir / "confidence_weights.joblib"
        self.acceptance_model_path = self.model_dir / "acceptance_predictor.joblib"
        self.scaler_path = self.model_dir / "feature_scaler.joblib"
        self.metadata_path = self.model_dir / "model_metadata.json"
        
        # 모델 인스턴스
        self.weight_model = None
        self.acceptance_model = None
        self.scaler = None
        self.is_trained = False
        
        # 기본 가중치 (fallback)
        self.default_weights = {
            'ocr_confidence': 0.3,
            'pattern_confidence': 0.2,
            'db_verification': 0.4,
            'length_penalty': 0.1
        }
        
        # 모델 로드 시도
        self.load_models()

    def prepare_features(self, ocr_confidence: float, pattern_confidence: float, 
                        db_verification: float, length_penalty: float) -> np.ndarray:
        """특성 벡터 준비"""
        features = np.array([[
            ocr_confidence,
            pattern_confidence,
            db_verification,
            length_penalty,
            # 추가 특성들
            ocr_confidence * pattern_confidence,  # 상호작용 특성
            db_verification * ocr_confidence,
            abs(ocr_confidence - pattern_confidence),  # 차이 특성
            max(ocr_confidence, pattern_confidence, db_verification)  # 최대값 특성
        ]])
        
        return features

    async def train_from_feedback(self, feedback_data: List[FeedbackData]) -> Dict:
        """
        사용자 피드백 데이터로 모델 학습
        
        Args:
            feedback_data: 피드백 데이터 리스트
            
        Returns:
            학습 결과 통계
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn이 없어 모델 학습을 건너뜁니다.")
            return {"status": "skipped", "reason": "sklearn_not_available"}
        
        if len(feedback_data) < 10:
            logger.warning(f"학습 데이터가 부족합니다: {len(feedback_data)}/10")
            return {"status": "insufficient_data", "count": len(feedback_data)}

        try:
            # 특성과 타겟 준비
            X = []
            y_weights = []  # 최적 가중치 예측용
            y_acceptance = []  # 사용자 수용 예측용
            
            for feedback in feedback_data:
                features = self.prepare_features(
                    feedback.ocr_confidence,
                    feedback.pattern_confidence,
                    feedback.db_verification,
                    feedback.length_penalty
                )
                X.append(features[0])
                
                # 사용자가 수정했으면 0, 그대로 사용했으면 1
                y_acceptance.append(1 if feedback.user_accepted else 0)
                
                # 최종 신뢰도를 타겟으로 사용
                y_weights.append(feedback.final_confidence)

            X = np.array(X)
            y_weights = np.array(y_weights)
            y_acceptance = np.array(y_acceptance)
            
            # 데이터 분할
            X_train, X_test, y_w_train, y_w_test, y_a_train, y_a_test = train_test_split(
                X, y_weights, y_acceptance, test_size=0.2, random_state=42
            )
            
            # 특성 스케일링
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 가중치 예측 모델 학습 (회귀)
            self.weight_model = LinearRegression()
            self.weight_model.fit(X_train_scaled, y_w_train)
            
            # 사용자 수용 예측 모델 학습 (분류)
            self.acceptance_model = LogisticRegression(random_state=42)
            self.acceptance_model.fit(X_train_scaled, y_a_train)
            
            # 모델 평가
            weight_score = self.weight_model.score(X_test_scaled, y_w_test)
            acceptance_score = self.acceptance_model.score(X_test_scaled, y_a_test)
            
            # 교차 검증
            weight_cv_scores = cross_val_score(self.weight_model, X_train_scaled, y_w_train, cv=5)
            acceptance_cv_scores = cross_val_score(self.acceptance_model, X_train_scaled, y_a_train, cv=5)
            
            # 모델 저장
            await self._save_models()
            
            self.is_trained = True
            
            training_results = {
                "status": "success",
                "data_count": len(feedback_data),
                "weight_model_score": weight_score,
                "acceptance_model_score": acceptance_score,
                "weight_cv_mean": weight_cv_scores.mean(),
                "weight_cv_std": weight_cv_scores.std(),
                "acceptance_cv_mean": acceptance_cv_scores.mean(),
                "acceptance_cv_std": acceptance_cv_scores.std(),
                "training_date": datetime.utcnow().isoformat()
            }
            
            logger.info(f"모델 학습 완료: {training_results}")
            return training_results
            
        except Exception as e:
            logger.error(f"모델 학습 중 오류 발생: {str(e)}")
            return {"status": "error", "error": str(e)}

    def predict_confidence(self, ocr_confidence: float, pattern_confidence: float,
                          db_verification: float, length_penalty: float) -> Tuple[float, Dict]:
        """
        학습된 모델로 신뢰도 예측
        
        Returns:
            (예측된 신뢰도, 추가 정보)
        """
        if not self.is_trained or not SKLEARN_AVAILABLE:
            # 기본 가중치 사용
            confidence = (
                ocr_confidence * self.default_weights['ocr_confidence'] +
                pattern_confidence * self.default_weights['pattern_confidence'] +
                db_verification * self.default_weights['db_verification'] +
                length_penalty * self.default_weights['length_penalty']
            )
            return confidence, {
                "method": "default_weights",
                "weights_used": self.default_weights
            }
        
        try:
            # 특성 준비 및 스케일링
            features = self.prepare_features(ocr_confidence, pattern_confidence, 
                                           db_verification, length_penalty)
            features_scaled = self.scaler.transform(features)
            
            # 신뢰도 예측
            predicted_confidence = float(self.weight_model.predict(features_scaled)[0])
            
            # 사용자 수용 확률 예측
            acceptance_prob = float(self.acceptance_model.predict_proba(features_scaled)[0][1])
            
            # 예측된 가중치 계산 (모델 계수 기반)
            feature_importance = abs(self.weight_model.coef_[:4])  # 첫 4개 특성만
            total_importance = feature_importance.sum()
            predicted_weights = {
                'ocr_confidence': feature_importance[0] / total_importance,
                'pattern_confidence': feature_importance[1] / total_importance,
                'db_verification': feature_importance[2] / total_importance,
                'length_penalty': feature_importance[3] / total_importance
            }
            
            return predicted_confidence, {
                "method": "ml_prediction",
                "acceptance_probability": acceptance_prob,
                "predicted_weights": predicted_weights,
                "model_confidence": min(predicted_confidence, 1.0)
            }
            
        except Exception as e:
            logger.error(f"ML 예측 중 오류 발생: {str(e)}")
            # 폴백
            confidence = (
                ocr_confidence * self.default_weights['ocr_confidence'] +
                pattern_confidence * self.default_weights['pattern_confidence'] +
                db_verification * self.default_weights['db_verification'] +
                length_penalty * self.default_weights['length_penalty']
            )
            return confidence, {
                "method": "fallback_after_error",
                "error": str(e)
            }

    def get_optimal_weights(self) -> Dict[str, float]:
        """현재 학습된 모델에서 최적 가중치 추출"""
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return self.default_weights
        
        try:
            # 모델 계수에서 가중치 추출
            feature_importance = abs(self.weight_model.coef_[:4])
            total_importance = feature_importance.sum()
            
            return {
                'ocr_confidence': feature_importance[0] / total_importance,
                'pattern_confidence': feature_importance[1] / total_importance,
                'db_verification': feature_importance[2] / total_importance,
                'length_penalty': feature_importance[3] / total_importance
            }
        except Exception as e:
            logger.error(f"가중치 추출 중 오류: {str(e)}")
            return self.default_weights

    async def _save_models(self):
        """모델과 메타데이터 저장"""
        if not SKLEARN_AVAILABLE:
            return
        
        try:
            # 모델 저장
            joblib.dump(self.weight_model, self.weight_model_path)
            joblib.dump(self.acceptance_model, self.acceptance_model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            # 메타데이터 저장
            metadata = {
                "training_date": datetime.utcnow().isoformat(),
                "model_version": "1.0",
                "sklearn_available": SKLEARN_AVAILABLE,
                "optimal_weights": self.get_optimal_weights()
            }
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
            logger.info("모델 저장 완료")
            
        except Exception as e:
            logger.error(f"모델 저장 중 오류: {str(e)}")

    def load_models(self):
        """저장된 모델 로드"""
        if not SKLEARN_AVAILABLE:
            return
        
        try:
            if (self.weight_model_path.exists() and 
                self.acceptance_model_path.exists() and 
                self.scaler_path.exists()):
                
                self.weight_model = joblib.load(self.weight_model_path)
                self.acceptance_model = joblib.load(self.acceptance_model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                
                logger.info("저장된 모델 로드 완료")
                
                # 메타데이터 로드
                if self.metadata_path.exists():
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        logger.info(f"모델 메타데이터: {metadata}")
                        
        except Exception as e:
            logger.error(f"모델 로드 중 오류: {str(e)}")
            self.is_trained = False

    def collect_feedback(self, ocr_confidence: float, pattern_confidence: float,
                        db_verification: float, length_penalty: float,
                        user_accepted: bool, final_confidence: float,
                        category: str, original_text: str, 
                        corrected_text: Optional[str] = None) -> FeedbackData:
        """피드백 데이터 수집"""
        return FeedbackData(
            ocr_confidence=ocr_confidence,
            pattern_confidence=pattern_confidence,
            db_verification=db_verification,
            length_penalty=length_penalty,
            user_accepted=user_accepted,
            final_confidence=final_confidence,
            category=category,
            timestamp=datetime.utcnow().isoformat(),
            original_text=original_text,
            corrected_text=corrected_text
        )

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        info = {
            "sklearn_available": SKLEARN_AVAILABLE,
            "is_trained": self.is_trained,
            "default_weights": self.default_weights
        }
        
        if self.is_trained:
            info["optimal_weights"] = self.get_optimal_weights()
            
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    info["metadata"] = metadata
            except Exception as e:
                info["metadata_error"] = str(e)
                
        return info

    def reset_models(self):
        """모델 초기화"""
        self.weight_model = None
        self.acceptance_model = None
        self.scaler = None
        self.is_trained = False
        
        # 파일 삭제
        for path in [self.weight_model_path, self.acceptance_model_path, 
                    self.scaler_path, self.metadata_path]:
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.error(f"파일 삭제 실패 {path}: {str(e)}")
        
        logger.info("모델 초기화 완료")