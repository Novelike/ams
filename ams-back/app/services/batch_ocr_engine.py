import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from PIL import Image
import cv2

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR not available. Install with: pip install easyocr")

try:
    import torch
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. GPU functionality will be limited.")

from .gpu_manager import get_gpu_manager, GPUManager

logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    """OCR 결과"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    processing_time: float

@dataclass
class BatchOCRResult:
    """배치 OCR 결과"""
    results: List[OCRResult]
    batch_size: int
    total_processing_time: float
    average_confidence: float
    device_used: str  # "cpu" or "cuda:0"

@dataclass
class OCRConfig:
    """OCR 설정"""
    languages: List[str] = None
    gpu: bool = True
    batch_size: int = 8
    confidence_threshold: float = 0.5
    preprocessing: List[str] = None
    postprocessing: List[str] = None

@dataclass
class BatchOCRRequest:
    """배치 OCR 요청"""
    images: List[Dict[str, Any]]  # 이미지 데이터 리스트
    use_gpu: bool = True
    batch_size: int = 8
    languages: List[str] = None
    confidence_threshold: float = 0.5
    preprocessing: List[str] = None
    postprocessing: List[str] = None

class BatchOCREngine:
    """
    배치 OCR 엔진
    - GPU/CPU 자동 선택
    - 배치 처리 최적화
    - 메모리 효율적 처리
    - 전처리/후처리 파이프라인
    """

    def __init__(self, config: OCRConfig = None):
        self.config = config or OCRConfig()
        if self.config.languages is None:
            self.config.languages = ['ko', 'en']
        if self.config.preprocessing is None:
            self.config.preprocessing = ['resize', 'normalize']
        if self.config.postprocessing is None:
            self.config.postprocessing = ['filter_confidence', 'merge_text']

        # OCR 리더 (지연 초기화)
        self.cpu_reader = None
        self.gpu_reader = None
        self.current_device = "cpu"

        # GPU 관리자
        self.gpu_manager: Optional[GPUManager] = None

        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 통계
        self.processing_stats = {
            "total_images": 0,
            "total_batches": 0,
            "gpu_batches": 0,
            "cpu_batches": 0,
            "average_batch_time": 0.0,
            "average_confidence": 0.0
        }

        # 초기화
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """비동기 초기화"""
        try:
            # GPU 관리자 초기화
            self.gpu_manager = await get_gpu_manager()

            # 최적 디바이스 선택
            await self._select_optimal_device()

            logger.info(f"Batch OCR Engine initialized. Device: {self.current_device}")

        except Exception as e:
            logger.error(f"Failed to initialize Batch OCR Engine: {e}")

    async def _select_optimal_device(self):
        """최적 디바이스 선택"""
        try:
            if not self.config.gpu or not TORCH_AVAILABLE:
                self.current_device = "cpu"
                return

            if self.gpu_manager and self.gpu_manager.is_gpu_available():
                recommended_device = self.gpu_manager.get_recommended_device()
                if recommended_device >= 0:
                    self.current_device = f"cuda:{recommended_device}"
                else:
                    self.current_device = "cpu"
            else:
                self.current_device = "cpu"

            logger.info(f"Selected device: {self.current_device}")

        except Exception as e:
            logger.error(f"Failed to select optimal device: {e}")
            self.current_device = "cpu"

    def _get_ocr_reader(self, use_gpu: bool = None) -> Optional[Any]:
        """OCR 리더 가져오기 (지연 초기화)"""
        try:
            if not EASYOCR_AVAILABLE:
                logger.error("EasyOCR not available")
                return None

            if use_gpu is None:
                use_gpu = self.current_device.startswith("cuda")

            if use_gpu and self.gpu_reader is None:
                self.gpu_reader = easyocr.Reader(
                    self.config.languages,
                    gpu=True
                )
                logger.info("GPU OCR reader initialized")

            elif not use_gpu and self.cpu_reader is None:
                self.cpu_reader = easyocr.Reader(
                    self.config.languages,
                    gpu=False
                )
                logger.info("CPU OCR reader initialized")

            return self.gpu_reader if use_gpu else self.cpu_reader

        except Exception as e:
            logger.error(f"Failed to get OCR reader: {e}")
            return None

    async def process_image_batch(self, images: List[Union[str, np.ndarray, Image.Image]]) -> BatchOCRResult:
        """이미지 배치 처리"""
        start_time = time.time()

        try:
            if not images:
                return BatchOCRResult([], 0, 0.0, 0.0, self.current_device)

            # 배치 크기 최적화
            optimal_batch_size = await self._get_optimal_batch_size(len(images))

            # 이미지 전처리
            processed_images = await self._preprocess_batch(images)

            # 배치 단위로 처리
            all_results = []
            total_confidence = 0.0

            for i in range(0, len(processed_images), optimal_batch_size):
                batch = processed_images[i:i + optimal_batch_size]
                batch_results = await self._process_single_batch(batch)
                all_results.extend(batch_results)

                # 신뢰도 누적
                for result in batch_results:
                    total_confidence += result.confidence

            # 후처리
            final_results = await self._postprocess_batch(all_results)

            # 통계 업데이트
            processing_time = time.time() - start_time
            average_confidence = total_confidence / len(final_results) if final_results else 0.0

            await self._update_stats(len(images), processing_time, average_confidence)

            return BatchOCRResult(
                results=final_results,
                batch_size=len(images),
                total_processing_time=processing_time,
                average_confidence=average_confidence,
                device_used=self.current_device
            )

        except Exception as e:
            logger.error(f"Failed to process image batch: {e}")
            return BatchOCRResult([], 0, 0.0, 0.0, self.current_device)

    async def _get_optimal_batch_size(self, total_images: int) -> int:
        """최적 배치 크기 계산"""
        try:
            if self.gpu_manager and self.current_device.startswith("cuda"):
                device_id = int(self.current_device.split(":")[1])
                # 이미지 크기를 가정 (실제로는 이미지에서 추출해야 함)
                estimated_size = (640, 480)  # 기본 크기

                optimal_size = await self.gpu_manager.get_optimal_batch_size(
                    "easyocr", estimated_size, device_id
                )
                return min(optimal_size, total_images, self.config.batch_size)
            else:
                # CPU 모드에서는 설정된 배치 크기 사용
                return min(self.config.batch_size, total_images)

        except Exception as e:
            logger.error(f"Failed to calculate optimal batch size: {e}")
            return min(self.config.batch_size, total_images)

    async def _preprocess_batch(self, images: List[Union[str, np.ndarray, Image.Image]]) -> List[np.ndarray]:
        """배치 전처리"""
        try:
            loop = asyncio.get_event_loop()
            processed_images = await loop.run_in_executor(
                self.executor,
                self._preprocess_batch_sync,
                images
            )
            return processed_images
        except Exception as e:
            logger.error(f"Failed to preprocess batch: {e}")
            return []

    def _preprocess_batch_sync(self, images: List[Union[str, np.ndarray, Image.Image]]) -> List[np.ndarray]:
        """동기 배치 전처리"""
        processed_images = []

        for img in images:
            try:
                # 이미지 로드
                if isinstance(img, str):
                    # 파일 경로
                    image = cv2.imread(img)
                    if image is None:
                        logger.warning(f"Failed to load image: {img}")
                        continue
                elif isinstance(img, Image.Image):
                    # PIL Image
                    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                elif isinstance(img, np.ndarray):
                    # NumPy array
                    image = img.copy()
                else:
                    logger.warning(f"Unsupported image type: {type(img)}")
                    continue

                # 전처리 적용
                for preprocessing in self.config.preprocessing:
                    image = self._apply_preprocessing(image, preprocessing)

                processed_images.append(image)

            except Exception as e:
                logger.error(f"Failed to preprocess image: {e}")
                continue

        return processed_images

    def _apply_preprocessing(self, image: np.ndarray, preprocessing: str) -> np.ndarray:
        """전처리 적용"""
        try:
            if preprocessing == "resize":
                # 크기 조정 (최대 1920x1080)
                height, width = image.shape[:2]
                if width > 1920 or height > 1080:
                    scale = min(1920/width, 1080/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    image = cv2.resize(image, (new_width, new_height))

            elif preprocessing == "normalize":
                # 정규화
                image = cv2.convertScaleAbs(image, alpha=1.2, beta=10)

            elif preprocessing == "denoise":
                # 노이즈 제거
                image = cv2.fastNlMeansDenoisingColored(image)

            elif preprocessing == "sharpen":
                # 샤프닝
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                image = cv2.filter2D(image, -1, kernel)

            elif preprocessing == "grayscale":
                # 그레이스케일 변환
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            return image

        except Exception as e:
            logger.error(f"Failed to apply preprocessing {preprocessing}: {e}")
            return image

    async def _process_single_batch(self, batch: List[np.ndarray]) -> List[OCRResult]:
        """단일 배치 처리"""
        try:
            use_gpu = self.current_device.startswith("cuda")

            if use_gpu and self.gpu_manager:
                # GPU 메모리 컨텍스트 사용
                device_id = int(self.current_device.split(":")[1])
                with self.gpu_manager.gpu_memory_context(device_id):
                    return await self._ocr_batch_sync(batch, use_gpu)
            else:
                return await self._ocr_batch_sync(batch, use_gpu)

        except Exception as e:
            logger.error(f"Failed to process single batch: {e}")
            return []

    async def _ocr_batch_sync(self, batch: List[np.ndarray], use_gpu: bool) -> List[OCRResult]:
        """동기 OCR 배치 처리"""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self._ocr_batch_worker,
                batch, use_gpu
            )
            return results
        except Exception as e:
            logger.error(f"Failed to process OCR batch: {e}")
            return []

    def _ocr_batch_worker(self, batch: List[np.ndarray], use_gpu: bool) -> List[OCRResult]:
        """OCR 배치 워커"""
        results = []

        try:
            reader = self._get_ocr_reader(use_gpu)
            if not reader:
                logger.error("OCR reader not available")
                return results

            for image in batch:
                start_time = time.time()

                try:
                    # EasyOCR 실행
                    ocr_results = reader.readtext(image)
                    processing_time = time.time() - start_time

                    # 결과 변환
                    for (bbox, text, confidence) in ocr_results:
                        if confidence >= self.config.confidence_threshold:
                            # bbox 좌표 변환
                            x_coords = [point[0] for point in bbox]
                            y_coords = [point[1] for point in bbox]
                            x1, y1 = int(min(x_coords)), int(min(y_coords))
                            x2, y2 = int(max(x_coords)), int(max(y_coords))

                            result = OCRResult(
                                text=text.strip(),
                                confidence=confidence,
                                bbox=(x1, y1, x2, y2),
                                processing_time=processing_time
                            )
                            results.append(result)

                except Exception as e:
                    logger.error(f"Failed to process single image: {e}")
                    continue

        except Exception as e:
            logger.error(f"OCR batch worker failed: {e}")

        return results

    async def _postprocess_batch(self, results: List[OCRResult]) -> List[OCRResult]:
        """배치 후처리"""
        try:
            processed_results = results.copy()

            for postprocessing in self.config.postprocessing:
                processed_results = await self._apply_postprocessing(processed_results, postprocessing)

            return processed_results

        except Exception as e:
            logger.error(f"Failed to postprocess batch: {e}")
            return results

    async def _apply_postprocessing(self, results: List[OCRResult], postprocessing: str) -> List[OCRResult]:
        """후처리 적용"""
        try:
            if postprocessing == "filter_confidence":
                # 신뢰도 필터링
                return [r for r in results if r.confidence >= self.config.confidence_threshold]

            elif postprocessing == "merge_text":
                # 인접한 텍스트 병합
                return await self._merge_adjacent_text(results)

            elif postprocessing == "remove_duplicates":
                # 중복 제거
                return await self._remove_duplicate_text(results)

            elif postprocessing == "sort_by_position":
                # 위치별 정렬
                return sorted(results, key=lambda r: (r.bbox[1], r.bbox[0]))

            return results

        except Exception as e:
            logger.error(f"Failed to apply postprocessing {postprocessing}: {e}")
            return results

    async def _merge_adjacent_text(self, results: List[OCRResult]) -> List[OCRResult]:
        """인접한 텍스트 병합"""
        try:
            if len(results) <= 1:
                return results

            merged_results = []
            current_group = [results[0]]

            for i in range(1, len(results)):
                current = results[i]
                last_in_group = current_group[-1]

                # 인접성 검사 (Y 좌표 차이가 작고 X 좌표가 연속적인지)
                y_diff = abs(current.bbox[1] - last_in_group.bbox[1])
                x_gap = current.bbox[0] - last_in_group.bbox[2]

                if y_diff < 20 and 0 <= x_gap < 50:  # 인접한 텍스트
                    current_group.append(current)
                else:
                    # 그룹 완료, 병합
                    if len(current_group) > 1:
                        merged_result = self._merge_text_group(current_group)
                        merged_results.append(merged_result)
                    else:
                        merged_results.extend(current_group)

                    current_group = [current]

            # 마지막 그룹 처리
            if len(current_group) > 1:
                merged_result = self._merge_text_group(current_group)
                merged_results.append(merged_result)
            else:
                merged_results.extend(current_group)

            return merged_results

        except Exception as e:
            logger.error(f"Failed to merge adjacent text: {e}")
            return results

    def _merge_text_group(self, group: List[OCRResult]) -> OCRResult:
        """텍스트 그룹 병합"""
        try:
            # 텍스트 결합
            merged_text = " ".join([r.text for r in group])

            # 평균 신뢰도
            avg_confidence = sum([r.confidence for r in group]) / len(group)

            # 전체 바운딩 박스
            x1 = min([r.bbox[0] for r in group])
            y1 = min([r.bbox[1] for r in group])
            x2 = max([r.bbox[2] for r in group])
            y2 = max([r.bbox[3] for r in group])

            # 총 처리 시간
            total_time = sum([r.processing_time for r in group])

            return OCRResult(
                text=merged_text,
                confidence=avg_confidence,
                bbox=(x1, y1, x2, y2),
                processing_time=total_time
            )

        except Exception as e:
            logger.error(f"Failed to merge text group: {e}")
            return group[0]  # 첫 번째 결과 반환

    async def _remove_duplicate_text(self, results: List[OCRResult]) -> List[OCRResult]:
        """중복 텍스트 제거"""
        try:
            unique_results = []
            seen_texts = set()

            for result in results:
                text_key = result.text.lower().strip()
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_results.append(result)

            return unique_results

        except Exception as e:
            logger.error(f"Failed to remove duplicate text: {e}")
            return results

    async def _update_stats(self, batch_size: int, processing_time: float, avg_confidence: float):
        """통계 업데이트"""
        try:
            self.processing_stats["total_images"] += batch_size
            self.processing_stats["total_batches"] += 1

            if self.current_device.startswith("cuda"):
                self.processing_stats["gpu_batches"] += 1
            else:
                self.processing_stats["cpu_batches"] += 1

            # 평균 계산
            total_batches = self.processing_stats["total_batches"]
            self.processing_stats["average_batch_time"] = (
                (self.processing_stats["average_batch_time"] * (total_batches - 1) + processing_time) / total_batches
            )
            self.processing_stats["average_confidence"] = (
                (self.processing_stats["average_confidence"] * (total_batches - 1) + avg_confidence) / total_batches
            )

        except Exception as e:
            logger.error(f"Failed to update stats: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        try:
            stats = dict(self.processing_stats)
            stats["current_device"] = self.current_device
            stats["config"] = asdict(self.config)

            if self.gpu_manager:
                gpu_stats = await self.gpu_manager.get_gpu_stats()
                stats["gpu_info"] = gpu_stats

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def switch_device(self, device: str = "auto"):
        """디바이스 전환"""
        try:
            if device == "auto":
                await self._select_optimal_device()
            elif device == "cpu":
                self.current_device = "cpu"
            elif device.startswith("cuda:"):
                if self.gpu_manager and self.gpu_manager.is_gpu_available(int(device.split(":")[1])):
                    self.current_device = device
                else:
                    logger.warning(f"GPU {device} not available, using CPU")
                    self.current_device = "cpu"
            else:
                logger.warning(f"Invalid device: {device}")
                return False

            logger.info(f"Switched to device: {self.current_device}")
            return True

        except Exception as e:
            logger.error(f"Failed to switch device: {e}")
            return False

    def __del__(self):
        """소멸자 - 리소스 정리"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except Exception:
            pass


# 전역 배치 OCR 엔진 인스턴스
_batch_ocr_engine = None

async def get_batch_ocr_engine() -> BatchOCREngine:
    """배치 OCR 엔진 싱글톤 인스턴스 반환"""
    global _batch_ocr_engine
    if _batch_ocr_engine is None:
        _batch_ocr_engine = BatchOCREngine()
    return _batch_ocr_engine
