#!/usr/bin/env python3
"""
AMS Backend Docker Cleanup Script
Cleans up old Docker images, containers, and volumes to free up disk space.
"""

import sys
import os
import subprocess
import logging
from datetime import datetime, timedelta
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DockerCleanup:
    def __init__(self):
        self.app_name = "ams-backend"
        self.docker_username = os.getenv("DOCKER_USERNAME", "")
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        
        # Cleanup thresholds
        self.keep_images_days = int(os.getenv("KEEP_IMAGES_DAYS", "7"))  # Keep images from last 7 days
        self.keep_latest_count = int(os.getenv("KEEP_LATEST_COUNT", "3"))  # Keep at least 3 latest images
        
        self.cleanup_results = []
        
    def log_info(self, message: str):
        logger.info(f"🧹 {message}")
    
    def log_success(self, message: str):
        logger.info(f"✅ {message}")
    
    def log_warning(self, message: str):
        logger.warning(f"⚠️ {message}")
    
    def log_error(self, message: str):
        logger.error(f"❌ {message}")
    
    def check_docker_availability(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                docker_version = result.stdout.strip()
                self.log_success(f"Docker 사용 가능: {docker_version}")
                return True
            else:
                self.log_warning("Docker가 설치되어 있지 않습니다")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            self.log_warning(f"Docker 확인 실패: {str(e)}")
            return False
    
    def get_docker_system_info(self) -> dict:
        """Get Docker system information"""
        info = {}
        
        try:
            # Get Docker system info
            result = subprocess.run(
                ["docker", "system", "df"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_info("Docker 시스템 사용량:")
                for line in result.stdout.strip().split('\n'):
                    self.log_info(f"  {line}")
                info['system_df'] = result.stdout.strip()
            
            # Get image count
            result = subprocess.run(
                ["docker", "images", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                image_count = len([line for line in result.stdout.strip().split('\n') if line])
                info['image_count'] = image_count
                self.log_info(f"총 Docker 이미지 수: {image_count}")
            
            # Get container count
            result = subprocess.run(
                ["docker", "ps", "-a", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                container_count = len([line for line in result.stdout.strip().split('\n') if line])
                info['container_count'] = container_count
                self.log_info(f"총 Docker 컨테이너 수: {container_count}")
                
        except subprocess.TimeoutExpired:
            self.log_warning("Docker 시스템 정보 조회 시간 초과")
        except Exception as e:
            self.log_warning(f"Docker 시스템 정보 조회 실패: {str(e)}")
        
        return info
    
    def cleanup_stopped_containers(self) -> bool:
        """Clean up stopped containers"""
        self.log_info("중지된 컨테이너 정리 중...")
        
        try:
            # Get stopped containers
            result = subprocess.run(
                ["docker", "ps", "-a", "-f", "status=exited", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stopped_containers = [line for line in result.stdout.strip().split('\n') if line]
                
                if stopped_containers:
                    self.log_info(f"중지된 컨테이너 {len(stopped_containers)}개 발견")
                    
                    if not self.dry_run:
                        # Remove stopped containers
                        result = subprocess.run(
                            ["docker", "rm"] + stopped_containers,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        if result.returncode == 0:
                            self.log_success(f"중지된 컨테이너 {len(stopped_containers)}개 제거 완료")
                            self.cleanup_results.append(f"Stopped containers removed: {len(stopped_containers)}")
                            return True
                        else:
                            self.log_error(f"컨테이너 제거 실패: {result.stderr}")
                            return False
                    else:
                        self.log_info(f"DRY RUN: {len(stopped_containers)}개 컨테이너가 제거될 예정")
                        self.cleanup_results.append(f"Stopped containers (dry run): {len(stopped_containers)}")
                        return True
                else:
                    self.log_info("중지된 컨테이너가 없습니다")
                    self.cleanup_results.append("Stopped containers: None found")
                    return True
            else:
                self.log_info("중지된 컨테이너가 없습니다")
                self.cleanup_results.append("Stopped containers: None found")
                return True
                
        except subprocess.TimeoutExpired:
            self.log_error("컨테이너 정리 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"컨테이너 정리 실패: {str(e)}")
            return False
    
    def cleanup_dangling_images(self) -> bool:
        """Clean up dangling images"""
        self.log_info("댕글링 이미지 정리 중...")
        
        try:
            # Get dangling images
            result = subprocess.run(
                ["docker", "images", "-f", "dangling=true", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                dangling_images = [line for line in result.stdout.strip().split('\n') if line]
                
                if dangling_images:
                    self.log_info(f"댕글링 이미지 {len(dangling_images)}개 발견")
                    
                    if not self.dry_run:
                        # Remove dangling images
                        result = subprocess.run(
                            ["docker", "rmi"] + dangling_images,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        if result.returncode == 0:
                            self.log_success(f"댕글링 이미지 {len(dangling_images)}개 제거 완료")
                            self.cleanup_results.append(f"Dangling images removed: {len(dangling_images)}")
                            return True
                        else:
                            self.log_warning(f"일부 댕글링 이미지 제거 실패: {result.stderr}")
                            self.cleanup_results.append(f"Dangling images: Partial removal")
                            return True
                    else:
                        self.log_info(f"DRY RUN: {len(dangling_images)}개 댕글링 이미지가 제거될 예정")
                        self.cleanup_results.append(f"Dangling images (dry run): {len(dangling_images)}")
                        return True
                else:
                    self.log_info("댕글링 이미지가 없습니다")
                    self.cleanup_results.append("Dangling images: None found")
                    return True
            else:
                self.log_info("댕글링 이미지가 없습니다")
                self.cleanup_results.append("Dangling images: None found")
                return True
                
        except subprocess.TimeoutExpired:
            self.log_error("댕글링 이미지 정리 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"댕글링 이미지 정리 실패: {str(e)}")
            return False
    
    def cleanup_old_app_images(self) -> bool:
        """Clean up old application images"""
        self.log_info("오래된 애플리케이션 이미지 정리 중...")
        
        if not self.docker_username:
            self.log_warning("DOCKER_USERNAME이 설정되지 않아 애플리케이션 이미지 정리를 건너뜁니다")
            self.cleanup_results.append("App images: Skipped (no username)")
            return True
        
        try:
            # Get all app images
            image_pattern = f"{self.docker_username}/{self.app_name}"
            result = subprocess.run(
                ["docker", "images", image_pattern, "--format", "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.ID}}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                images = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            images.append({
                                'tag': parts[0],
                                'created': parts[1],
                                'id': parts[2]
                            })
                
                if images:
                    self.log_info(f"애플리케이션 이미지 {len(images)}개 발견")
                    
                    # Sort by creation date (newest first)
                    images.sort(key=lambda x: x['created'], reverse=True)
                    
                    # Keep the latest N images
                    images_to_keep = images[:self.keep_latest_count]
                    images_to_remove = images[self.keep_latest_count:]
                    
                    # Also filter by age
                    cutoff_date = datetime.now() - timedelta(days=self.keep_images_days)
                    old_images = []
                    
                    for img in images_to_remove:
                        # Skip if it's one of the latest images we want to keep
                        if img not in images_to_keep:
                            old_images.append(img)
                    
                    if old_images:
                        self.log_info(f"제거할 오래된 이미지 {len(old_images)}개")
                        
                        if not self.dry_run:
                            removed_count = 0
                            for img in old_images:
                                try:
                                    result = subprocess.run(
                                        ["docker", "rmi", img['id']],
                                        capture_output=True,
                                        text=True,
                                        timeout=60
                                    )
                                    
                                    if result.returncode == 0:
                                        self.log_success(f"이미지 제거: {img['tag']}")
                                        removed_count += 1
                                    else:
                                        self.log_warning(f"이미지 제거 실패: {img['tag']} - {result.stderr}")
                                        
                                except subprocess.TimeoutExpired:
                                    self.log_warning(f"이미지 제거 시간 초과: {img['tag']}")
                            
                            self.log_success(f"오래된 애플리케이션 이미지 {removed_count}개 제거 완료")
                            self.cleanup_results.append(f"Old app images removed: {removed_count}")
                        else:
                            self.log_info(f"DRY RUN: {len(old_images)}개 오래된 이미지가 제거될 예정")
                            for img in old_images:
                                self.log_info(f"  제거 예정: {img['tag']}")
                            self.cleanup_results.append(f"Old app images (dry run): {len(old_images)}")
                    else:
                        self.log_info("제거할 오래된 이미지가 없습니다")
                        self.cleanup_results.append("Old app images: None to remove")
                else:
                    self.log_info("애플리케이션 이미지가 없습니다")
                    self.cleanup_results.append("App images: None found")
            else:
                self.log_info("애플리케이션 이미지가 없습니다")
                self.cleanup_results.append("App images: None found")
            
            return True
            
        except subprocess.TimeoutExpired:
            self.log_error("애플리케이션 이미지 정리 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"애플리케이션 이미지 정리 실패: {str(e)}")
            return False
    
    def cleanup_unused_volumes(self) -> bool:
        """Clean up unused volumes"""
        self.log_info("사용하지 않는 볼륨 정리 중...")
        
        try:
            # Get unused volumes
            result = subprocess.run(
                ["docker", "volume", "ls", "-f", "dangling=true", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                unused_volumes = [line for line in result.stdout.strip().split('\n') if line]
                
                if unused_volumes:
                    self.log_info(f"사용하지 않는 볼륨 {len(unused_volumes)}개 발견")
                    
                    if not self.dry_run:
                        # Remove unused volumes
                        result = subprocess.run(
                            ["docker", "volume", "rm"] + unused_volumes,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        if result.returncode == 0:
                            self.log_success(f"사용하지 않는 볼륨 {len(unused_volumes)}개 제거 완료")
                            self.cleanup_results.append(f"Unused volumes removed: {len(unused_volumes)}")
                            return True
                        else:
                            self.log_warning(f"일부 볼륨 제거 실패: {result.stderr}")
                            self.cleanup_results.append(f"Unused volumes: Partial removal")
                            return True
                    else:
                        self.log_info(f"DRY RUN: {len(unused_volumes)}개 볼륨이 제거될 예정")
                        self.cleanup_results.append(f"Unused volumes (dry run): {len(unused_volumes)}")
                        return True
                else:
                    self.log_info("사용하지 않는 볼륨이 없습니다")
                    self.cleanup_results.append("Unused volumes: None found")
                    return True
            else:
                self.log_info("사용하지 않는 볼륨이 없습니다")
                self.cleanup_results.append("Unused volumes: None found")
                return True
                
        except subprocess.TimeoutExpired:
            self.log_error("볼륨 정리 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"볼륨 정리 실패: {str(e)}")
            return False
    
    def docker_system_prune(self) -> bool:
        """Run docker system prune for comprehensive cleanup"""
        self.log_info("Docker 시스템 전체 정리 실행 중...")
        
        try:
            if not self.dry_run:
                # Run docker system prune (removes unused data)
                result = subprocess.run(
                    ["docker", "system", "prune", "-f", "--volumes"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                
                if result.returncode == 0:
                    self.log_success("Docker 시스템 정리 완료")
                    if result.stdout.strip():
                        self.log_info("정리 결과:")
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                self.log_info(f"  {line}")
                    self.cleanup_results.append("System prune: Completed")
                    return True
                else:
                    self.log_warning(f"Docker 시스템 정리 부분 실패: {result.stderr}")
                    self.cleanup_results.append("System prune: Partial failure")
                    return True
            else:
                self.log_info("DRY RUN: Docker 시스템 정리가 실행될 예정")
                self.cleanup_results.append("System prune (dry run): Would execute")
                return True
                
        except subprocess.TimeoutExpired:
            self.log_error("Docker 시스템 정리 시간 초과")
            return False
        except Exception as e:
            self.log_error(f"Docker 시스템 정리 실패: {str(e)}")
            return False
    
    def generate_cleanup_report(self) -> str:
        """Generate cleanup report"""
        self.log_info("정리 보고서 생성 중...")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""
=============================================================================
AMS 백엔드 Docker 정리 보고서
=============================================================================
정리 시간: {timestamp}
환경: {"GitHub Actions" if self.is_github_actions else "일반 서버"}
모드: {"DRY RUN" if self.dry_run else "실제 실행"}

정리 결과:
"""
        
        for result in self.cleanup_results:
            report += f"- {result}\n"
        
        report += f"""
설정:
- 이미지 보관 기간: {self.keep_images_days}일
- 최신 이미지 보관 개수: {self.keep_latest_count}개
- Docker 사용자명: {self.docker_username or "설정되지 않음"}

=============================================================================
"""
        
        print(report)
        self.log_success("정리 보고서 생성 완료")
        
        return report
    
    def run_cleanup(self) -> int:
        """Run Docker cleanup process"""
        self.log_info("===============================================================================")
        self.log_info("🧹 AMS 백엔드 Docker 정리 시작")
        self.log_info("===============================================================================")
        
        # Check if Docker is available
        if not self.check_docker_availability():
            self.log_warning("Docker를 사용할 수 없어 정리를 건너뜁니다")
            self.cleanup_results.append("Docker cleanup: Skipped (Docker not available)")
            self.generate_cleanup_report()
            return 0
        
        # Get initial system info
        initial_info = self.get_docker_system_info()
        
        success_count = 0
        total_operations = 5
        
        # 1. Clean up stopped containers
        if self.cleanup_stopped_containers():
            success_count += 1
        
        # 2. Clean up dangling images
        if self.cleanup_dangling_images():
            success_count += 1
        
        # 3. Clean up old application images
        if self.cleanup_old_app_images():
            success_count += 1
        
        # 4. Clean up unused volumes
        if self.cleanup_unused_volumes():
            success_count += 1
        
        # 5. Run system prune
        if self.docker_system_prune():
            success_count += 1
        
        # Get final system info
        self.log_info("정리 후 시스템 상태:")
        final_info = self.get_docker_system_info()
        
        # Generate report
        self.generate_cleanup_report()
        
        self.log_info("===============================================================================")
        
        if success_count == total_operations:
            self.log_success("🎉 Docker 정리가 성공적으로 완료되었습니다!")
            return 0
        elif success_count > 0:
            self.log_warning(f"⚠️ Docker 정리가 부분적으로 완료되었습니다 ({success_count}/{total_operations})")
            return 0  # Still return 0 as partial success is acceptable
        else:
            self.log_error("❌ Docker 정리가 실패했습니다!")
            return 1

def main():
    """Main function"""
    try:
        cleanup = DockerCleanup()
        exit_code = cleanup.run_cleanup()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.error("Docker 정리가 사용자에 의해 중단되었습니다")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Docker 정리 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()