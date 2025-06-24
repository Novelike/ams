from difflib import SequenceMatcher
import re
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class FuzzyMatcher:
    """
    OCR 특성을 고려한 퍼지 매칭 클래스
    문자 혼동, 편집 거리, 패턴 매칭을 통한 유사도 계산
    """
    
    # OCR에서 자주 혼동되는 문자 매핑
    CONFUSION_PAIRS = {
        '0': ['O', 'o', 'Q'],
        'O': ['0', 'o', 'Q'],
        'o': ['0', 'O', 'Q'],
        'Q': ['0', 'O', 'o'],
        '1': ['I', 'l', '|', 'i'],
        'I': ['1', 'l', '|', 'i'],
        'l': ['1', 'I', '|', 'i'],
        '|': ['1', 'I', 'l', 'i'],
        'i': ['1', 'I', 'l', '|'],
        '8': ['B'],
        'B': ['8'],
        '5': ['S', 's'],
        'S': ['5', 's'],
        's': ['5', 'S'],
        '6': ['G'],
        'G': ['6'],
        '2': ['Z'],
        'Z': ['2'],
        'u': ['v'],
        'v': ['u'],
        'rn': ['m'],
        'm': ['rn'],
        'cl': ['d'],
        'd': ['cl']
    }
    
    # 한글 자모 혼동 패턴
    KOREAN_CONFUSION = {
        'ㅇ': ['ㅁ'],
        'ㅁ': ['ㅇ'],
        'ㅗ': ['ㅜ'],
        'ㅜ': ['ㅗ'],
        'ㅓ': ['ㅏ'],
        'ㅏ': ['ㅓ']
    }
    
    def __init__(self):
        self.cache = {}  # 유사도 계산 캐시
        
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트 간 유사도 계산 (OCR 특성 고려)
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
            
        Returns:
            0.0 ~ 1.0 사이의 유사도 점수
        """
        if not text1 or not text2:
            return 0.0
            
        # 캐시 확인
        cache_key = f"{text1}||{text2}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 기본 전처리
        clean_text1 = self._preprocess_text(text1)
        clean_text2 = self._preprocess_text(text2)
        
        if clean_text1 == clean_text2:
            self.cache[cache_key] = 1.0
            return 1.0
        
        # 여러 유사도 계산 방법 조합
        similarities = []
        
        # 1. 기본 시퀀스 매칭
        basic_similarity = SequenceMatcher(None, clean_text1.lower(), clean_text2.lower()).ratio()
        similarities.append(('basic', basic_similarity, 0.3))
        
        # 2. OCR 혼동 문자 고려한 유사도
        ocr_similarity = self._calculate_ocr_aware_similarity(clean_text1, clean_text2)
        similarities.append(('ocr_aware', ocr_similarity, 0.4))
        
        # 3. 토큰 기반 유사도 (단어별 매칭)
        token_similarity = self._calculate_token_similarity(clean_text1, clean_text2)
        similarities.append(('token', token_similarity, 0.2))
        
        # 4. 길이 기반 패널티/보너스
        length_factor = self._calculate_length_factor(clean_text1, clean_text2)
        similarities.append(('length', length_factor, 0.1))
        
        # 가중 평균 계산
        weighted_sum = sum(score * weight for _, score, weight in similarities)
        total_weight = sum(weight for _, _, weight in similarities)
        
        final_similarity = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # 캐시에 저장
        self.cache[cache_key] = final_similarity
        
        return final_similarity
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        if not text:
            return ""
        
        # 공백 정리
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # 특수문자 정리 (일부만)
        cleaned = re.sub(r'[^\w\s가-힣-]', '', cleaned)
        
        return cleaned
    
    def _calculate_ocr_aware_similarity(self, text1: str, text2: str) -> float:
        """OCR 혼동 문자를 고려한 유사도 계산"""
        # 혼동 가능한 문자 변형 생성
        variants1 = self._generate_confusion_variants(text1)
        variants2 = self._generate_confusion_variants(text2)
        
        max_similarity = 0.0
        
        # 모든 변형 조합에서 최대 유사도 찾기
        for v1 in variants1[:5]:  # 성능을 위해 상위 5개만
            for v2 in variants2[:5]:
                similarity = SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _generate_confusion_variants(self, text: str, max_variants: int = 10) -> List[str]:
        """혼동 가능한 문자 변형 생성"""
        variants = [text]
        
        # 각 문자에 대해 혼동 가능한 문자로 치환
        for i, char in enumerate(text):
            if char in self.CONFUSION_PAIRS:
                for replacement in self.CONFUSION_PAIRS[char][:2]:  # 상위 2개만
                    variant = text[:i] + replacement + text[i+1:]
                    if variant not in variants:
                        variants.append(variant)
                        if len(variants) >= max_variants:
                            break
                if len(variants) >= max_variants:
                    break
        
        return variants
    
    def _calculate_token_similarity(self, text1: str, text2: str) -> float:
        """토큰(단어) 기반 유사도 계산"""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_length_factor(self, text1: str, text2: str) -> float:
        """길이 차이에 따른 보정 계수"""
        len1, len2 = len(text1), len(text2)
        
        if len1 == 0 and len2 == 0:
            return 1.0
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # 길이 비율 계산
        ratio = min(len1, len2) / max(len1, len2)
        
        # 길이가 비슷할수록 높은 점수
        return ratio
    
    def find_best_matches(self, query: str, candidates: List[str], 
                         threshold: float = 0.6, max_results: int = 5) -> List[Tuple[str, float]]:
        """
        후보 목록에서 가장 유사한 항목들 찾기
        
        Args:
            query: 검색할 텍스트
            candidates: 후보 텍스트 목록
            threshold: 최소 유사도 임계값
            max_results: 최대 결과 개수
            
        Returns:
            (텍스트, 유사도) 튜플의 리스트 (유사도 내림차순)
        """
        matches = []
        
        for candidate in candidates:
            similarity = self.calculate_similarity(query, candidate)
            if similarity >= threshold:
                matches.append((candidate, similarity))
        
        # 유사도 내림차순 정렬
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:max_results]
    
    def is_likely_same(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """
        두 텍스트가 같은 내용일 가능성이 높은지 판단
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
            threshold: 판단 임계값
            
        Returns:
            같은 내용일 가능성이 높으면 True
        """
        similarity = self.calculate_similarity(text1, text2)
        return similarity >= threshold
    
    def suggest_corrections(self, text: str, reference_list: List[str], 
                          max_suggestions: int = 3) -> List[Dict]:
        """
        텍스트 교정 제안
        
        Args:
            text: 교정할 텍스트
            reference_list: 참조 텍스트 목록
            max_suggestions: 최대 제안 개수
            
        Returns:
            교정 제안 목록 (딕셔너리 형태)
        """
        suggestions = []
        
        matches = self.find_best_matches(text, reference_list, threshold=0.5, max_results=max_suggestions)
        
        for match_text, similarity in matches:
            suggestion = {
                'original': text,
                'suggestion': match_text,
                'similarity': similarity,
                'confidence': self._calculate_correction_confidence(text, match_text, similarity),
                'reason': self._analyze_difference(text, match_text)
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    def _calculate_correction_confidence(self, original: str, suggestion: str, similarity: float) -> str:
        """교정 신뢰도 레벨 계산"""
        if similarity >= 0.9:
            return 'high'
        elif similarity >= 0.7:
            return 'medium'
        elif similarity >= 0.5:
            return 'low'
        else:
            return 'very_low'
    
    def _analyze_difference(self, text1: str, text2: str) -> str:
        """두 텍스트 간 차이점 분석"""
        if len(text1) == len(text2):
            # 같은 길이인 경우 문자 치환 확인
            diff_count = sum(1 for a, b in zip(text1, text2) if a != b)
            if diff_count == 1:
                return "단일 문자 차이"
            elif diff_count <= 2:
                return "소수 문자 차이"
            else:
                return "다수 문자 차이"
        else:
            # 길이가 다른 경우
            len_diff = abs(len(text1) - len(text2))
            if len_diff == 1:
                return "한 글자 추가/삭제"
            elif len_diff <= 3:
                return "소수 글자 추가/삭제"
            else:
                return "다수 글자 차이"
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        return {
            'cache_size': len(self.cache),
            'cache_keys': list(self.cache.keys())[:10]  # 상위 10개만
        }