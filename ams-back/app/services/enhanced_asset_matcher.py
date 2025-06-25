import asyncio
import aiofiles
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json
import csv
import pickle
from pathlib import Path
from datetime import datetime
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

@dataclass
class AssetMatcherConfig:
    cache_ttl: int = 3600  # 1시간
    max_workers: int = 4
    enable_cache: bool = True
    data_dir: str = "data/assets"

class EnhancedAssetMatcher:
    def __init__(self, config: AssetMatcherConfig):
        self.config = config
        self.assets_db: List[Dict] = []
        self.indexes = {
            'serial': {},
            'model': {},
            'manufacturer': {}
        }
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        self._loading = False
        self._loaded = False
        self.cache_file = Path(config.data_dir) / "matcher_cache.pkl"

    async def initialize(self):
        """비동기 초기화 - 애플리케이션 시작 시 백그라운드에서 실행"""
        if self._loading or self._loaded:
            return

        self._loading = True
        try:
            # 캐시에서 먼저 확인
            if self.config.enable_cache:
                cached_data = await self._load_from_cache()
                if cached_data:
                    self.assets_db, self.indexes = cached_data
                    self._loaded = True
                    logger.info(f"캐시에서 {len(self.assets_db)}개 자산 데이터 로드 완료")
                    return

            # 파일에서 로드
            await self._load_from_files()
            await self._build_indexes()

            # 캐시에 저장
            if self.config.enable_cache:
                await self._save_to_cache()

            self._loaded = True
            logger.info(f"파일에서 {len(self.assets_db)}개 자산 데이터 로드 완료")
        except Exception as e:
            logger.error(f"자산 매처 초기화 중 오류: {e}")
        finally:
            self._loading = False

    async def _load_from_cache(self) -> Optional[Tuple[List[Dict], Dict]]:
        """캐시에서 데이터 로드"""
        try:
            if not self.cache_file.exists():
                return None

            # 캐시 파일이 너무 오래된 경우 무시
            cache_age = datetime.now().timestamp() - self.cache_file.stat().st_mtime
            if cache_age > self.config.cache_ttl:
                logger.info("캐시 파일이 만료되어 새로 로드합니다")
                return None

            loop = asyncio.get_event_loop()
            with open(self.cache_file, 'rb') as f:
                data = await loop.run_in_executor(self.executor, pickle.load, f)

            return data
        except Exception as e:
            logger.warning(f"캐시 로드 실패: {e}")
            return None

    async def _save_to_cache(self):
        """캐시에 데이터 저장"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_event_loop()

            def save_cache():
                with open(self.cache_file, 'wb') as f:
                    pickle.dump((self.assets_db, self.indexes), f)

            await loop.run_in_executor(self.executor, save_cache)
            logger.info("자산 데이터 캐시 저장 완료")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")

    async def _load_from_files(self):
        """파일에서 비동기 로드"""
        csv_path = Path(self.config.data_dir) / "assets_list.csv"
        if not csv_path.exists():
            logger.warning("자산 목록 CSV 파일이 존재하지 않습니다")
            return

        # CSV 파일을 비동기로 읽기
        async with aiofiles.open(csv_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        # CSV 파싱을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        self.assets_db = await loop.run_in_executor(
            self.executor, 
            self._parse_csv_content, 
            content
        )

    def _parse_csv_content(self, content: str) -> List[Dict]:
        """CSV 내용 파싱"""
        assets = []
        try:
            from io import StringIO
            reader = csv.DictReader(StringIO(content))

            for row in reader:
                # JSON 상세 정보도 함께 로드
                asset_number = row.get('asset_number', '')
                if asset_number:
                    json_path = Path(self.config.data_dir) / "details" / f"{asset_number}.json"
                    if json_path.exists():
                        try:
                            with open(json_path, 'r', encoding='utf-8') as jf:
                                detail = json.load(jf)
                                row.update(detail.get('specs', {}))
                        except Exception as e:
                            logger.warning(f"JSON 파일 로드 실패 {json_path}: {e}")

                assets.append(row)

        except Exception as e:
            logger.error(f"CSV 파싱 중 오류: {e}")

        return assets

    async def _build_indexes(self):
        """인덱스 구축 - 검색 성능 최적화"""
        loop = asyncio.get_event_loop()
        self.indexes = await loop.run_in_executor(
            self.executor,
            self._build_indexes_sync
        )

    def _build_indexes_sync(self) -> Dict:
        """동기 인덱스 구축"""
        indexes = {
            'serial': {},
            'model': {},
            'manufacturer': {}
        }

        for asset in self.assets_db:
            # 시리얼번호 인덱스 (정확한 매칭용)
            if asset.get('serial_number'):
                serial = asset['serial_number'].strip().upper()
                indexes['serial'][serial] = asset

            # 모델명 인덱스 (부분 매칭용)
            if asset.get('model_name'):
                model_words = asset['model_name'].lower().split()
                for word in model_words:
                    if len(word) > 2:  # 2글자 이상만 인덱싱
                        if word not in indexes['model']:
                            indexes['model'][word] = []
                        indexes['model'][word].append(asset)

            # 제조사 인덱스
            if asset.get('manufacturer'):
                mfg = asset['manufacturer'].lower().strip()
                if mfg not in indexes['manufacturer']:
                    indexes['manufacturer'][mfg] = []
                indexes['manufacturer'][mfg].append(asset)

        logger.info(f"인덱스 구축 완료: 시리얼 {len(indexes['serial'])}개, "
                   f"모델 {len(indexes['model'])}개, 제조사 {len(indexes['manufacturer'])}개")
        return indexes

    async def verify_ocr_result_async(self, ocr_data: Dict) -> Dict:
        """비동기 OCR 결과 검증"""
        if not self._loaded:
            await self.initialize()

        # 병렬로 각 필드 검증
        tasks = [
            self._verify_serial_async(ocr_data.get('serial_number')),
            self._verify_model_async(ocr_data.get('model_name')),
            self._verify_manufacturer_async(ocr_data.get('manufacturer'))
        ]

        serial_result, model_result, manufacturer_result = await asyncio.gather(*tasks)

        # 교차 검증
        cross_validation = await self._cross_validate(serial_result, model_result, manufacturer_result)

        return {
            'serial_number': serial_result,
            'model_name': model_result,
            'manufacturer': manufacturer_result,
            'cross_validation': cross_validation,
            'confidence_score': self._calculate_overall_confidence([serial_result, model_result, manufacturer_result])
        }

    async def _verify_serial_async(self, serial: str) -> Dict:
        """시리얼번호 검증 (가장 신뢰도 높음)"""
        if not serial:
            return {'status': 'missing', 'confidence': 0.0}

        serial_clean = serial.strip().upper()

        # 정확한 매칭 우선
        exact_match = self.indexes['serial'].get(serial_clean)
        if exact_match:
            return {
                'status': 'verified',
                'matched_asset': exact_match,
                'confidence': 1.0,
                'method': 'exact_match'
            }

        # 퍼지 매칭
        fuzzy_matches = await self._find_fuzzy_serial(serial_clean)
        if fuzzy_matches:
            best_match = fuzzy_matches[0]
            return {
                'status': 'fuzzy_match',
                'matched_asset': best_match['asset'],
                'confidence': best_match['similarity'],
                'method': 'fuzzy_match',
                'suggestions': fuzzy_matches[:3]
            }

        return {'status': 'not_found', 'confidence': 0.0}

    async def _verify_model_async(self, model: str) -> Dict:
        """모델명 검증"""
        if not model:
            return {'status': 'missing', 'confidence': 0.0}

        model_clean = model.strip().lower()

        # 부분 매칭 검색
        candidates = []
        words = model_clean.split()

        for word in words:
            if len(word) > 2 and word in self.indexes['model']:
                candidates.extend(self.indexes['model'][word])

        if candidates:
            # 중복 제거 및 유사도 계산
            unique_candidates = list({asset['asset_number']: asset for asset in candidates}.values())

            # 유사도 계산
            similarities = []
            for candidate in unique_candidates:
                similarity = self._calculate_text_similarity(model_clean, candidate.get('model_name', '').lower())
                if similarity > 0.6:  # 임계값
                    similarities.append({
                        'asset': candidate,
                        'similarity': similarity
                    })

            if similarities:
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                best_match = similarities[0]

                return {
                    'status': 'fuzzy_match' if best_match['similarity'] < 0.9 else 'verified',
                    'matched_asset': best_match['asset'],
                    'confidence': best_match['similarity'],
                    'method': 'partial_match',
                    'suggestions': similarities[:3]
                }

        return {'status': 'not_found', 'confidence': 0.0}

    async def _verify_manufacturer_async(self, manufacturer: str) -> Dict:
        """제조사 검증"""
        if not manufacturer:
            return {'status': 'missing', 'confidence': 0.0}

        mfg_clean = manufacturer.strip().lower()

        # 정확한 매칭
        if mfg_clean in self.indexes['manufacturer']:
            assets = self.indexes['manufacturer'][mfg_clean]
            return {
                'status': 'verified',
                'matched_assets': assets,
                'confidence': 1.0,
                'method': 'exact_match'
            }

        # 부분 매칭
        similarities = []
        for indexed_mfg, assets in self.indexes['manufacturer'].items():
            similarity = self._calculate_text_similarity(mfg_clean, indexed_mfg)
            if similarity > 0.7:
                similarities.append({
                    'manufacturer': indexed_mfg,
                    'assets': assets,
                    'similarity': similarity
                })

        if similarities:
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            best_match = similarities[0]

            return {
                'status': 'fuzzy_match',
                'matched_manufacturer': best_match['manufacturer'],
                'matched_assets': best_match['assets'],
                'confidence': best_match['similarity'],
                'method': 'fuzzy_match',
                'suggestions': similarities[:3]
            }

        return {'status': 'not_found', 'confidence': 0.0}

    async def _find_fuzzy_serial(self, serial: str) -> List[Dict]:
        """퍼지 시리얼 매칭"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._find_fuzzy_serial_sync,
            serial
        )

    def _find_fuzzy_serial_sync(self, serial: str) -> List[Dict]:
        """동기 퍼지 시리얼 매칭"""
        matches = []

        for indexed_serial, asset in self.indexes['serial'].items():
            similarity = self._calculate_text_similarity(serial, indexed_serial)
            if similarity > 0.8:  # 시리얼은 높은 임계값 사용
                matches.append({
                    'asset': asset,
                    'similarity': similarity,
                    'matched_serial': indexed_serial
                })

        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산 (Levenshtein 거리 기반)"""
        if not text1 or not text2:
            return 0.0

        # 간단한 Levenshtein 거리 구현
        len1, len2 = len(text1), len(text2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0

        # DP 테이블 생성
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # 초기화
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        # DP 계산
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if text1[i-1] == text2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(
                        dp[i-1][j] + 1,    # 삭제
                        dp[i][j-1] + 1,    # 삽입
                        dp[i-1][j-1] + 1   # 교체
                    )

        # 유사도 계산 (0~1)
        max_len = max(len1, len2)
        distance = dp[len1][len2]
        similarity = 1.0 - (distance / max_len)

        return max(0.0, similarity)

    async def _cross_validate(self, serial_result: Dict, model_result: Dict, manufacturer_result: Dict) -> Dict:
        """교차 검증"""
        validation_score = 0.0
        validation_details = []

        # 시리얼번호로 찾은 자산과 다른 필드 결과 비교
        if serial_result.get('status') == 'verified':
            serial_asset = serial_result['matched_asset']

            # 모델명 교차 검증
            if model_result.get('matched_asset'):
                if serial_asset['asset_number'] == model_result['matched_asset']['asset_number']:
                    validation_score += 0.4
                    validation_details.append("시리얼-모델 일치")

            # 제조사 교차 검증
            if manufacturer_result.get('matched_assets'):
                for mfg_asset in manufacturer_result['matched_assets']:
                    if serial_asset['asset_number'] == mfg_asset['asset_number']:
                        validation_score += 0.4
                        validation_details.append("시리얼-제조사 일치")
                        break

        # 모델명과 제조사 교차 검증
        if (model_result.get('matched_asset') and 
            manufacturer_result.get('matched_assets')):
            model_asset = model_result['matched_asset']
            for mfg_asset in manufacturer_result['matched_assets']:
                if model_asset['asset_number'] == mfg_asset['asset_number']:
                    validation_score += 0.2
                    validation_details.append("모델-제조사 일치")
                    break

        return {
            'score': validation_score,
            'details': validation_details,
            'is_consistent': validation_score > 0.5
        }

    def _calculate_overall_confidence(self, results: List[Dict]) -> float:
        """전체 신뢰도 계산"""
        confidences = [r.get('confidence', 0.0) for r in results if r.get('confidence') is not None]
        if not confidences:
            return 0.0

        # 가중 평균 (시리얼 > 모델 > 제조사)
        weights = [0.5, 0.3, 0.2]
        weighted_sum = sum(c * w for c, w in zip(confidences, weights[:len(confidences)]))
        weight_sum = sum(weights[:len(confidences)])

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0

    async def get_suggestions(self, field_type: str, partial_text: str, limit: int = 5) -> List[str]:
        """자동완성 제안"""
        if not self._loaded:
            await self.initialize()

        suggestions = []
        partial_lower = partial_text.lower().strip()

        if field_type == 'model_name':
            for word, assets in self.indexes['model'].items():
                if word.startswith(partial_lower):
                    for asset in assets:
                        model_name = asset.get('model_name', '')
                        if model_name and model_name not in suggestions:
                            suggestions.append(model_name)
                            if len(suggestions) >= limit:
                                break
                if len(suggestions) >= limit:
                    break

        elif field_type == 'manufacturer':
            for mfg in self.indexes['manufacturer'].keys():
                if mfg.startswith(partial_lower):
                    # 원본 제조사명 찾기
                    assets = self.indexes['manufacturer'][mfg]
                    if assets:
                        original_mfg = assets[0].get('manufacturer', '')
                        if original_mfg and original_mfg not in suggestions:
                            suggestions.append(original_mfg)
                            if len(suggestions) >= limit:
                                break

        elif field_type == 'serial_number':
            for serial in self.indexes['serial'].keys():
                if serial.startswith(partial_text.upper()):
                    suggestions.append(serial)
                    if len(suggestions) >= limit:
                        break

        return suggestions[:limit]

    def get_stats(self) -> Dict:
        """자산 매처 통계 반환"""
        return {
            "total_assets": len(self.assets_db),
            "indexes": {
                "serial_count": len(self.indexes['serial']),
                "model_count": len(self.indexes['model']),
                "manufacturer_count": len(self.indexes['manufacturer'])
            },
            "config": {
                "cache_ttl": self.config.cache_ttl,
                "max_workers": self.config.max_workers,
                "enable_cache": self.config.enable_cache,
                "data_dir": self.config.data_dir
            },
            "status": {
                "loaded": self._loaded,
                "loading": self._loading,
                "cache_file_exists": self.cache_file.exists() if hasattr(self, 'cache_file') else False
            }
        }

# 전역 인스턴스
_asset_matcher = None

async def get_asset_matcher() -> EnhancedAssetMatcher:
    """자산 매처 싱글톤 인스턴스 반환"""
    global _asset_matcher
    if _asset_matcher is None:
        config = AssetMatcherConfig()
        _asset_matcher = EnhancedAssetMatcher(config)
        await _asset_matcher.initialize()
    return _asset_matcher
