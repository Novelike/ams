import asyncio
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID, KEYWORD, STORED
    from whoosh.qparser import QueryParser, MultifieldParser
    from whoosh.query import FuzzyTerm
    from whoosh.analysis import StandardAnalyzer
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False
    logging.warning("Whoosh not available. Install with: pip install whoosh")

logger = logging.getLogger(__name__)

class AssetSearchEngine:
    """
    고성능 자산 검색 엔진 (Whoosh 기반)
    - 퍼지 검색 지원
    - 다중 필드 검색
    - 실시간 인덱스 업데이트
    """
    
    def __init__(self, index_dir: str = "data/search_index"):
        self.index_dir = Path(index_dir)
        self.schema = Schema(
            asset_number=ID(stored=True, unique=True),
            model_name=TEXT(stored=True, analyzer=StandardAnalyzer()),
            serial_number=ID(stored=True),
            manufacturer=KEYWORD(stored=True, commas=True),
            asset_type=KEYWORD(stored=True),
            site=KEYWORD(stored=True),
            content=TEXT(analyzer=StandardAnalyzer()),  # 전체 텍스트 검색용
            created_at=STORED(),
            updated_at=STORED()
        )
        self.ix = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialized = False

    async def initialize(self):
        """검색 인덱스 초기화"""
        if self._initialized:
            return
            
        if not WHOOSH_AVAILABLE:
            logger.error("Whoosh is not available. Search functionality will be limited.")
            return
            
        try:
            # 인덱스 디렉토리 생성
            self.index_dir.mkdir(parents=True, exist_ok=True)
            
            # 인덱스 생성 또는 열기
            if not index.exists_in(str(self.index_dir)):
                logger.info(f"Creating new search index at {self.index_dir}")
                self.ix = index.create_in(str(self.index_dir), self.schema)
            else:
                logger.info(f"Opening existing search index at {self.index_dir}")
                self.ix = index.open_dir(str(self.index_dir))
            
            self._initialized = True
            logger.info("Search engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize search engine: {e}")
            raise

    async def index_assets(self, assets: List[Dict]):
        """자산 데이터 인덱싱"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            logger.warning("Search engine not available for indexing")
            return
            
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._index_assets_sync, assets)
            logger.info(f"Indexed {len(assets)} assets")
        except Exception as e:
            logger.error(f"Failed to index assets: {e}")
            raise

    def _index_assets_sync(self, assets: List[Dict]):
        """동기 자산 인덱싱"""
        writer = self.ix.writer()
        
        try:
            for asset in assets:
                # 전체 텍스트 검색용 콘텐츠 생성
                content_parts = [
                    asset.get('model_name', ''),
                    asset.get('manufacturer', ''),
                    asset.get('serial_number', ''),
                    asset.get('asset_type', ''),
                    asset.get('site', '')
                ]
                content = ' '.join(filter(None, content_parts))
                
                writer.add_document(
                    asset_number=asset.get('asset_number', ''),
                    model_name=asset.get('model_name', ''),
                    serial_number=asset.get('serial_number', ''),
                    manufacturer=asset.get('manufacturer', ''),
                    asset_type=asset.get('asset_type', ''),
                    site=asset.get('site', ''),
                    content=content,
                    created_at=asset.get('created_at', ''),
                    updated_at=asset.get('updated_at', '')
                )
            
            writer.commit()
            
        except Exception as e:
            writer.cancel()
            raise e

    async def fuzzy_search(self, query: str, field: str = "content", limit: int = 10, 
                          max_dist: int = 2) -> List[Dict]:
        """퍼지 검색 실행"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            logger.warning("Search engine not available for fuzzy search")
            return []
            
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor, 
                self._fuzzy_search_sync, 
                query, field, limit, max_dist
            )
            return results
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return []

    def _fuzzy_search_sync(self, query: str, field: str, limit: int, max_dist: int) -> List[Dict]:
        """동기 퍼지 검색"""
        with self.ix.searcher() as searcher:
            parser = QueryParser(field, self.ix.schema)
            
            # 퍼지 검색 쿼리 생성 (편집거리 기반)
            fuzzy_query = parser.parse(f"{query}~{max_dist}")
            results = searcher.search(fuzzy_query, limit=limit)
            
            return [dict(hit) for hit in results]

    async def multi_field_search(self, queries: Dict[str, str], limit: int = 10) -> List[Dict]:
        """다중 필드 검색"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            logger.warning("Search engine not available for multi-field search")
            return []
            
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self._multi_field_search_sync,
                queries, limit
            )
            return results
        except Exception as e:
            logger.error(f"Multi-field search failed: {e}")
            return []

    def _multi_field_search_sync(self, queries: Dict[str, str], limit: int) -> List[Dict]:
        """동기 다중 필드 검색"""
        with self.ix.searcher() as searcher:
            # 다중 필드 파서 생성
            parser = MultifieldParser(list(queries.keys()), self.ix.schema)
            
            # 쿼리 문자열 생성
            query_parts = []
            for field, value in queries.items():
                if value and value.strip():
                    query_parts.append(f"{field}:{value}")
            
            if not query_parts:
                return []
                
            query_string = " AND ".join(query_parts)
            query = parser.parse(query_string)
            
            results = searcher.search(query, limit=limit)
            return [dict(hit) for hit in results]

    async def suggest_completions(self, field: str, partial_text: str, limit: int = 5) -> List[str]:
        """자동 완성 제안"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            return []
            
        try:
            loop = asyncio.get_event_loop()
            suggestions = await loop.run_in_executor(
                self.executor,
                self._suggest_completions_sync,
                field, partial_text, limit
            )
            return suggestions
        except Exception as e:
            logger.error(f"Completion suggestion failed: {e}")
            return []

    def _suggest_completions_sync(self, field: str, partial_text: str, limit: int) -> List[str]:
        """동기 자동 완성 제안"""
        with self.ix.searcher() as searcher:
            # 부분 텍스트로 시작하는 용어들 찾기
            suggestions = []
            
            # 필드의 모든 용어를 검색
            for term in searcher.field_terms(field):
                if term.startswith(partial_text.lower()):
                    suggestions.append(term)
                    if len(suggestions) >= limit:
                        break
            
            return suggestions

    async def update_asset(self, asset_number: str, asset_data: Dict):
        """단일 자산 업데이트"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            return
            
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._update_asset_sync,
                asset_number, asset_data
            )
            logger.info(f"Updated asset {asset_number} in search index")
        except Exception as e:
            logger.error(f"Failed to update asset {asset_number}: {e}")

    def _update_asset_sync(self, asset_number: str, asset_data: Dict):
        """동기 자산 업데이트"""
        writer = self.ix.writer()
        
        try:
            # 기존 문서 삭제
            writer.delete_by_term('asset_number', asset_number)
            
            # 새 문서 추가
            content_parts = [
                asset_data.get('model_name', ''),
                asset_data.get('manufacturer', ''),
                asset_data.get('serial_number', ''),
                asset_data.get('asset_type', ''),
                asset_data.get('site', '')
            ]
            content = ' '.join(filter(None, content_parts))
            
            writer.add_document(
                asset_number=asset_number,
                model_name=asset_data.get('model_name', ''),
                serial_number=asset_data.get('serial_number', ''),
                manufacturer=asset_data.get('manufacturer', ''),
                asset_type=asset_data.get('asset_type', ''),
                site=asset_data.get('site', ''),
                content=content,
                updated_at=asset_data.get('updated_at', '')
            )
            
            writer.commit()
            
        except Exception as e:
            writer.cancel()
            raise e

    async def delete_asset(self, asset_number: str):
        """자산 삭제"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            return
            
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._delete_asset_sync,
                asset_number
            )
            logger.info(f"Deleted asset {asset_number} from search index")
        except Exception as e:
            logger.error(f"Failed to delete asset {asset_number}: {e}")

    def _delete_asset_sync(self, asset_number: str):
        """동기 자산 삭제"""
        writer = self.ix.writer()
        
        try:
            writer.delete_by_term('asset_number', asset_number)
            writer.commit()
        except Exception as e:
            writer.cancel()
            raise e

    async def get_stats(self) -> Dict:
        """검색 인덱스 통계"""
        if not self._initialized:
            await self.initialize()
            
        if not WHOOSH_AVAILABLE or not self.ix:
            return {"error": "Search engine not available"}
            
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(self.executor, self._get_stats_sync)
            return stats
        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {"error": str(e)}

    def _get_stats_sync(self) -> Dict:
        """동기 통계 조회"""
        with self.ix.searcher() as searcher:
            return {
                "total_documents": searcher.doc_count(),
                "index_size": self._get_index_size(),
                "last_modified": self._get_last_modified()
            }

    def _get_index_size(self) -> int:
        """인덱스 크기 계산"""
        total_size = 0
        for file_path in self.index_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def _get_last_modified(self) -> str:
        """마지막 수정 시간"""
        try:
            latest_time = 0
            for file_path in self.index_dir.rglob("*"):
                if file_path.is_file():
                    latest_time = max(latest_time, file_path.stat().st_mtime)
            return str(latest_time) if latest_time > 0 else "unknown"
        except Exception:
            return "unknown"

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# 전역 검색 엔진 인스턴스
_search_engine = None

async def get_search_engine() -> AssetSearchEngine:
    """검색 엔진 싱글톤 인스턴스 반환"""
    global _search_engine
    if _search_engine is None:
        _search_engine = AssetSearchEngine()
        await _search_engine.initialize()
    return _search_engine