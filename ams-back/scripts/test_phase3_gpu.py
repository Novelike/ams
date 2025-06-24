import asyncio
import aiohttp
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
import io
from PIL import Image
import numpy as np

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase3GPUTester:
    """Phase 3 GPU OCR 기능 테스트 클래스"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def create_test_image(self, width: int = 200, height: int = 100, text: str = "TEST") -> bytes:
        """테스트용 이미지 생성"""
        # 간단한 텍스트 이미지 생성
        img = Image.new('RGB', (width, height), color='white')
        
        # PIL로 텍스트 추가는 복잡하므로 간단한 패턴으로 대체
        pixels = np.array(img)
        # 중앙에 검은색 사각형 그리기 (텍스트 대신)
        h_start, h_end = height//3, 2*height//3
        w_start, w_end = width//4, 3*width//4
        pixels[h_start:h_end, w_start:w_end] = [0, 0, 0]
        
        img = Image.fromarray(pixels)
        
        # 바이트로 변환
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    async def test_connection(self) -> bool:
        """기본 연결 테스트"""
        logger.info("🔗 기본 연결 테스트 시작")
        
        try:
            async with self.session.get(f"{self.base_url}/api/registration/workflow") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ 연결 성공: {len(data)}개 워크플로우 단계")
                    self.test_results.append({"test": "connection", "status": "PASS", "details": f"{len(data)} workflow steps"})
                    return True
                else:
                    logger.error(f"❌ 연결 실패: HTTP {response.status}")
                    self.test_results.append({"test": "connection", "status": "FAIL", "details": f"HTTP {response.status}"})
                    return False
        except Exception as e:
            logger.error(f"❌ 연결 오류: {str(e)}")
            self.test_results.append({"test": "connection", "status": "FAIL", "details": str(e)})
            return False
    
    async def test_gpu_ocr_stats(self) -> bool:
        """GPU OCR 통계 조회 테스트"""
        logger.info("📊 GPU OCR 통계 테스트 시작")
        
        try:
            async with self.session.get(f"{self.base_url}/api/registration/gpu-ocr/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    gpu_available = data.get("gpu_info", {}).get("available", False)
                    device_count = data.get("gpu_info", {}).get("device_count", 0)
                    
                    logger.info(f"✅ GPU 통계 조회 성공")
                    logger.info(f"   - GPU 사용 가능: {gpu_available}")
                    logger.info(f"   - GPU 장치 수: {device_count}")
                    
                    self.test_results.append({
                        "test": "gpu_stats", 
                        "status": "PASS", 
                        "details": f"GPU available: {gpu_available}, devices: {device_count}"
                    })
                    return True
                else:
                    logger.error(f"❌ GPU 통계 조회 실패: HTTP {response.status}")
                    error_text = await response.text()
                    self.test_results.append({
                        "test": "gpu_stats", 
                        "status": "FAIL", 
                        "details": f"HTTP {response.status}: {error_text}"
                    })
                    return False
        except Exception as e:
            logger.error(f"❌ GPU 통계 테스트 오류: {str(e)}")
            self.test_results.append({"test": "gpu_stats", "status": "FAIL", "details": str(e)})
            return False
    
    async def test_scheduler_status(self) -> bool:
        """OCR 스케줄러 상태 테스트"""
        logger.info("⏰ OCR 스케줄러 상태 테스트 시작")
        
        try:
            async with self.session.get(f"{self.base_url}/api/registration/gpu-ocr/scheduler/status") as response:
                if response.status == 200:
                    data = await response.json()
                    queue_info = data.get("queue_info", {})
                    pending_jobs = queue_info.get("pending_jobs", 0)
                    running_jobs = queue_info.get("running_jobs", 0)
                    
                    logger.info(f"✅ 스케줄러 상태 조회 성공")
                    logger.info(f"   - 대기 중인 작업: {pending_jobs}")
                    logger.info(f"   - 실행 중인 작업: {running_jobs}")
                    
                    self.test_results.append({
                        "test": "scheduler_status", 
                        "status": "PASS", 
                        "details": f"Pending: {pending_jobs}, Running: {running_jobs}"
                    })
                    return True
                else:
                    logger.error(f"❌ 스케줄러 상태 조회 실패: HTTP {response.status}")
                    error_text = await response.text()
                    self.test_results.append({
                        "test": "scheduler_status", 
                        "status": "FAIL", 
                        "details": f"HTTP {response.status}: {error_text}"
                    })
                    return False
        except Exception as e:
            logger.error(f"❌ 스케줄러 상태 테스트 오류: {str(e)}")
            self.test_results.append({"test": "scheduler_status", "status": "FAIL", "details": str(e)})
            return False
    
    async def test_batch_gpu_ocr(self) -> bool:
        """GPU 배치 OCR 처리 테스트"""
        logger.info("🖼️ GPU 배치 OCR 테스트 시작")
        
        try:
            # 테스트 이미지 생성
            test_images = []
            for i in range(3):
                img_data = self.create_test_image(text=f"TEST_{i}")
                test_images.append(('files', (f'test_image_{i}.png', img_data, 'image/png')))
            
            # FormData로 전송
            data = aiohttp.FormData()
            for field_name, (filename, file_data, content_type) in test_images:
                data.add_field(field_name, file_data, filename=filename, content_type=content_type)
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/registration/gpu-ocr/batch",
                data=data
            ) as response:
                processing_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    total_images = result.get("total_images", 0)
                    processed_images = result.get("processed_images", 0)
                    gpu_used = result.get("gpu_used", False)
                    
                    logger.info(f"✅ GPU 배치 OCR 처리 성공")
                    logger.info(f"   - 총 이미지: {total_images}")
                    logger.info(f"   - 처리된 이미지: {processed_images}")
                    logger.info(f"   - GPU 사용: {gpu_used}")
                    logger.info(f"   - 처리 시간: {processing_time:.2f}초")
                    
                    self.test_results.append({
                        "test": "batch_gpu_ocr", 
                        "status": "PASS", 
                        "details": f"Processed {processed_images}/{total_images} images, GPU: {gpu_used}, Time: {processing_time:.2f}s"
                    })
                    return True
                else:
                    logger.error(f"❌ GPU 배치 OCR 처리 실패: HTTP {response.status}")
                    error_text = await response.text()
                    self.test_results.append({
                        "test": "batch_gpu_ocr", 
                        "status": "FAIL", 
                        "details": f"HTTP {response.status}: {error_text}"
                    })
                    return False
        except Exception as e:
            logger.error(f"❌ GPU 배치 OCR 테스트 오류: {str(e)}")
            self.test_results.append({"test": "batch_gpu_ocr", "status": "FAIL", "details": str(e)})
            return False
    
    async def test_ocr_job_submission(self) -> bool:
        """OCR 작업 제출 및 상태 조회 테스트"""
        logger.info("📝 OCR 작업 제출 테스트 시작")
        
        try:
            # 작업 제출 데이터
            job_data = {
                "images": [
                    {"filename": "test1.png", "data": "base64_encoded_data_here"},
                    {"filename": "test2.png", "data": "base64_encoded_data_here"}
                ],
                "priority": "high",
                "options": {
                    "use_gpu": True,
                    "batch_size": 2
                }
            }
            
            # 작업 제출
            async with self.session.post(
                f"{self.base_url}/api/registration/gpu-ocr/scheduler/job",
                json=job_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    job_id = result.get("job_id")
                    
                    logger.info(f"✅ OCR 작업 제출 성공: {job_id}")
                    
                    # 작업 상태 조회
                    await asyncio.sleep(1)  # 잠시 대기
                    
                    async with self.session.get(
                        f"{self.base_url}/api/registration/gpu-ocr/scheduler/job/{job_id}"
                    ) as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            job_status = status_data.get("status", "unknown")
                            
                            logger.info(f"✅ OCR 작업 상태 조회 성공: {job_status}")
                            
                            self.test_results.append({
                                "test": "ocr_job_submission", 
                                "status": "PASS", 
                                "details": f"Job {job_id} submitted and status: {job_status}"
                            })
                            return True
                        else:
                            logger.error(f"❌ 작업 상태 조회 실패: HTTP {status_response.status}")
                            self.test_results.append({
                                "test": "ocr_job_submission", 
                                "status": "FAIL", 
                                "details": f"Status check failed: HTTP {status_response.status}"
                            })
                            return False
                else:
                    logger.error(f"❌ OCR 작업 제출 실패: HTTP {response.status}")
                    error_text = await response.text()
                    self.test_results.append({
                        "test": "ocr_job_submission", 
                        "status": "FAIL", 
                        "details": f"HTTP {response.status}: {error_text}"
                    })
                    return False
        except Exception as e:
            logger.error(f"❌ OCR 작업 제출 테스트 오류: {str(e)}")
            self.test_results.append({"test": "ocr_job_submission", "status": "FAIL", "details": str(e)})
            return False
    
    async def test_performance_monitoring(self) -> bool:
        """성능 모니터링 테스트"""
        logger.info("📈 성능 모니터링 테스트 시작")
        
        try:
            # GPU 통계 다시 조회하여 성능 데이터 확인
            async with self.session.get(f"{self.base_url}/api/registration/gpu-ocr/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    performance_stats = data.get("performance_stats", {})
                    total_processed = performance_stats.get("total_processed", 0)
                    avg_time = performance_stats.get("average_processing_time", 0)
                    
                    logger.info(f"✅ 성능 모니터링 데이터 조회 성공")
                    logger.info(f"   - 총 처리된 작업: {total_processed}")
                    logger.info(f"   - 평균 처리 시간: {avg_time:.3f}초")
                    
                    self.test_results.append({
                        "test": "performance_monitoring", 
                        "status": "PASS", 
                        "details": f"Total processed: {total_processed}, Avg time: {avg_time:.3f}s"
                    })
                    return True
                else:
                    logger.error(f"❌ 성능 모니터링 실패: HTTP {response.status}")
                    self.test_results.append({
                        "test": "performance_monitoring", 
                        "status": "FAIL", 
                        "details": f"HTTP {response.status}"
                    })
                    return False
        except Exception as e:
            logger.error(f"❌ 성능 모니터링 테스트 오류: {str(e)}")
            self.test_results.append({"test": "performance_monitoring", "status": "FAIL", "details": str(e)})
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 테스트 실행"""
        logger.info("🚀 Phase 3 GPU OCR 테스트 시작")
        logger.info("=" * 60)
        
        tests = [
            ("기본 연결", self.test_connection),
            ("GPU OCR 통계", self.test_gpu_ocr_stats),
            ("스케줄러 상태", self.test_scheduler_status),
            ("GPU 배치 OCR", self.test_batch_gpu_ocr),
            ("OCR 작업 제출", self.test_ocr_job_submission),
            ("성능 모니터링", self.test_performance_monitoring),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 {test_name} 테스트 실행 중...")
            try:
                result = await test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"❌ {test_name} 테스트 중 예외 발생: {str(e)}")
                failed += 1
                self.test_results.append({
                    "test": test_name.lower().replace(" ", "_"), 
                    "status": "ERROR", 
                    "details": str(e)
                })
        
        # 결과 요약
        total_tests = passed + failed
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 Phase 3 GPU OCR 테스트 결과 요약")
        logger.info("=" * 60)
        logger.info(f"📊 전체 테스트: {total_tests}")
        logger.info(f"✅ 성공: {passed}")
        logger.info(f"❌ 실패: {failed}")
        logger.info(f"📈 성공률: {success_rate:.1f}%")
        
        # 상세 결과
        logger.info("\n📋 상세 테스트 결과:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            logger.info(f"  {status_icon} {result['test']}: {result['status']} - {result['details']}")
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "detailed_results": self.test_results
        }

async def main():
    """메인 테스트 실행 함수"""
    async with Phase3GPUTester() as tester:
        results = await tester.run_all_tests()
        
        # 결과를 파일로 저장
        results_file = Path("phase3_gpu_test_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 테스트 결과가 {results_file}에 저장되었습니다.")
        
        # 성공률이 80% 이상이면 성공으로 간주
        if results["success_rate"] >= 80:
            logger.info("🎉 Phase 3 GPU OCR 테스트 전체적으로 성공!")
            return 0
        else:
            logger.error("💥 Phase 3 GPU OCR 테스트에서 문제가 발견되었습니다.")
            return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)