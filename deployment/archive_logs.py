#!/usr/bin/env python3
"""
AMS Backend Log Archive Script
Archives deployment logs and old log files to free up disk space.
"""

import sys
import os
import shutil
import gzip
import logging
from datetime import datetime, timedelta
from pathlib import Path
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class LogArchiver:
    def __init__(self):
        self.app_name = "ams-backend"
        self.is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        
        # Archive settings
        self.archive_days = int(os.getenv("ARCHIVE_DAYS", "30"))  # Archive logs older than 30 days
        self.keep_days = int(os.getenv("KEEP_DAYS", "90"))  # Keep archived logs for 90 days
        
        # Log directories to check
        self.log_directories = [
            "deployment/logs",
            "/var/log/ams-backend",
            "/opt/ams-backend/logs",
            "logs",
            ".github/workflows/logs"
        ]
        
        # Archive directory
        self.archive_dir = os.getenv("ARCHIVE_DIR", "deployment/archives")
        
        self.archive_results = []
        
    def log_info(self, message: str):
        logger.info(f"📦 {message}")
    
    def log_success(self, message: str):
        logger.info(f"✅ {message}")
    
    def log_warning(self, message: str):
        logger.warning(f"⚠️ {message}")
    
    def log_error(self, message: str):
        logger.error(f"❌ {message}")
    
    def ensure_archive_directory(self):
        """Ensure archive directory exists"""
        try:
            os.makedirs(self.archive_dir, exist_ok=True)
            self.log_success(f"아카이브 디렉토리 준비: {self.archive_dir}")
            return True
        except Exception as e:
            self.log_error(f"아카이브 디렉토리 생성 실패: {str(e)}")
            return False
    
    def find_log_files(self) -> list:
        """Find log files in various directories"""
        log_files = []
        
        for log_dir in self.log_directories:
            if os.path.exists(log_dir):
                self.log_info(f"로그 디렉토리 검사: {log_dir}")
                
                try:
                    log_path = Path(log_dir)
                    
                    # Find log files with common extensions
                    patterns = ["*.log", "*.log.*", "*.out", "*.err", "*.txt"]
                    
                    for pattern in patterns:
                        for log_file in log_path.rglob(pattern):
                            if log_file.is_file():
                                # Get file modification time
                                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                                size = log_file.stat().st_size
                                
                                log_files.append({
                                    'path': str(log_file),
                                    'mtime': mtime,
                                    'size': size,
                                    'age_days': (datetime.now() - mtime).days
                                })
                
                except Exception as e:
                    self.log_warning(f"로그 디렉토리 검사 실패 {log_dir}: {str(e)}")
            else:
                self.log_info(f"로그 디렉토리 없음: {log_dir}")
        
        self.log_info(f"총 {len(log_files)}개 로그 파일 발견")
        return log_files
    
    def archive_old_logs(self, log_files: list) -> bool:
        """Archive old log files"""
        self.log_info("오래된 로그 파일 아카이브 중...")
        
        archived_count = 0
        archived_size = 0
        
        # Filter files older than archive_days
        old_files = [f for f in log_files if f['age_days'] > self.archive_days]
        
        if not old_files:
            self.log_info("아카이브할 오래된 로그 파일이 없습니다")
            self.archive_results.append("Old logs archived: 0")
            return True
        
        self.log_info(f"아카이브할 파일 {len(old_files)}개 발견 ({self.archive_days}일 이상)")
        
        # Create date-based archive directory
        archive_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_archive_dir = os.path.join(self.archive_dir, f"logs_{archive_date}")
        
        try:
            if not self.dry_run:
                os.makedirs(date_archive_dir, exist_ok=True)
            
            for log_file in old_files:
                try:
                    source_path = log_file['path']
                    file_name = os.path.basename(source_path)
                    
                    # Create compressed archive name
                    if not file_name.endswith('.gz'):
                        archive_name = f"{file_name}.gz"
                    else:
                        archive_name = file_name
                    
                    archive_path = os.path.join(date_archive_dir, archive_name)
                    
                    if not self.dry_run:
                        # Compress and archive the file
                        with open(source_path, 'rb') as f_in:
                            with gzip.open(archive_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Remove original file
                        os.remove(source_path)
                        
                        self.log_success(f"아카이브 완료: {file_name}")
                    else:
                        self.log_info(f"DRY RUN: {file_name} 아카이브 예정")
                    
                    archived_count += 1
                    archived_size += log_file['size']
                    
                except Exception as e:
                    self.log_error(f"파일 아카이브 실패 {source_path}: {str(e)}")
            
            if archived_count > 0:
                size_mb = archived_size / (1024 * 1024)
                self.log_success(f"로그 아카이브 완료: {archived_count}개 파일, {size_mb:.2f}MB")
                self.archive_results.append(f"Old logs archived: {archived_count} files ({size_mb:.2f}MB)")
            else:
                self.archive_results.append("Old logs archived: 0")
            
            return True
            
        except Exception as e:
            self.log_error(f"로그 아카이브 실패: {str(e)}")
            return False
    
    def cleanup_old_archives(self) -> bool:
        """Clean up old archive files"""
        self.log_info("오래된 아카이브 정리 중...")
        
        if not os.path.exists(self.archive_dir):
            self.log_info("아카이브 디렉토리가 없습니다")
            self.archive_results.append("Old archives cleaned: 0")
            return True
        
        try:
            archive_path = Path(self.archive_dir)
            cutoff_date = datetime.now() - timedelta(days=self.keep_days)
            
            cleaned_count = 0
            cleaned_size = 0
            
            for archive_item in archive_path.iterdir():
                if archive_item.is_file() or archive_item.is_dir():
                    mtime = datetime.fromtimestamp(archive_item.stat().st_mtime)
                    
                    if mtime < cutoff_date:
                        try:
                            if archive_item.is_file():
                                size = archive_item.stat().st_size
                                if not self.dry_run:
                                    archive_item.unlink()
                                self.log_success(f"오래된 아카이브 파일 삭제: {archive_item.name}")
                            else:
                                size = sum(f.stat().st_size for f in archive_item.rglob('*') if f.is_file())
                                if not self.dry_run:
                                    shutil.rmtree(archive_item)
                                self.log_success(f"오래된 아카이브 디렉토리 삭제: {archive_item.name}")
                            
                            cleaned_count += 1
                            cleaned_size += size
                            
                        except Exception as e:
                            self.log_error(f"아카이브 삭제 실패 {archive_item}: {str(e)}")
            
            if cleaned_count > 0:
                size_mb = cleaned_size / (1024 * 1024)
                self.log_success(f"오래된 아카이브 정리 완료: {cleaned_count}개 항목, {size_mb:.2f}MB")
                self.archive_results.append(f"Old archives cleaned: {cleaned_count} items ({size_mb:.2f}MB)")
            else:
                self.log_info("정리할 오래된 아카이브가 없습니다")
                self.archive_results.append("Old archives cleaned: 0")
            
            return True
            
        except Exception as e:
            self.log_error(f"오래된 아카이브 정리 실패: {str(e)}")
            return False
    
    def cleanup_large_logs(self, log_files: list) -> bool:
        """Clean up large log files"""
        self.log_info("대용량 로그 파일 정리 중...")
        
        # Define large file threshold (100MB)
        large_file_threshold = 100 * 1024 * 1024
        
        large_files = [f for f in log_files if f['size'] > large_file_threshold and f['age_days'] > 1]
        
        if not large_files:
            self.log_info("정리할 대용량 로그 파일이 없습니다")
            self.archive_results.append("Large logs cleaned: 0")
            return True
        
        self.log_info(f"대용량 로그 파일 {len(large_files)}개 발견")
        
        cleaned_count = 0
        cleaned_size = 0
        
        for log_file in large_files:
            try:
                file_path = log_file['path']
                file_size_mb = log_file['size'] / (1024 * 1024)
                
                if not self.dry_run:
                    # Truncate large log files instead of deleting them
                    with open(file_path, 'w') as f:
                        f.write(f"# Log file truncated on {datetime.now().isoformat()}\n")
                        f.write(f"# Original size: {file_size_mb:.2f}MB\n")
                    
                    self.log_success(f"대용량 로그 파일 정리: {os.path.basename(file_path)} ({file_size_mb:.2f}MB)")
                else:
                    self.log_info(f"DRY RUN: {os.path.basename(file_path)} 정리 예정 ({file_size_mb:.2f}MB)")
                
                cleaned_count += 1
                cleaned_size += log_file['size']
                
            except Exception as e:
                self.log_error(f"대용량 로그 파일 정리 실패 {log_file['path']}: {str(e)}")
        
        if cleaned_count > 0:
            size_mb = cleaned_size / (1024 * 1024)
            self.log_success(f"대용량 로그 정리 완료: {cleaned_count}개 파일, {size_mb:.2f}MB")
            self.archive_results.append(f"Large logs cleaned: {cleaned_count} files ({size_mb:.2f}MB)")
        else:
            self.archive_results.append("Large logs cleaned: 0")
        
        return True
    
    def generate_archive_report(self) -> str:
        """Generate archive report"""
        self.log_info("아카이브 보고서 생성 중...")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""
=============================================================================
AMS 백엔드 로그 아카이브 보고서
=============================================================================
아카이브 시간: {timestamp}
환경: {"GitHub Actions" if self.is_github_actions else "일반 서버"}
모드: {"DRY RUN" if self.dry_run else "실제 실행"}

아카이브 결과:
"""
        
        for result in self.archive_results:
            report += f"- {result}\n"
        
        report += f"""
설정:
- 아카이브 기준: {self.archive_days}일 이상
- 아카이브 보관 기간: {self.keep_days}일
- 아카이브 디렉토리: {self.archive_dir}

검사한 로그 디렉토리:
"""
        
        for log_dir in self.log_directories:
            status = "존재" if os.path.exists(log_dir) else "없음"
            report += f"- {log_dir} ({status})\n"
        
        report += f"""
=============================================================================
"""
        
        print(report)
        self.log_success("아카이브 보고서 생성 완료")
        
        return report
    
    def run_archive(self) -> int:
        """Run log archive process"""
        self.log_info("===============================================================================")
        self.log_info("📦 AMS 백엔드 로그 아카이브 시작")
        self.log_info("===============================================================================")
        
        # Ensure archive directory exists
        if not self.ensure_archive_directory():
            return 1
        
        # Find all log files
        log_files = self.find_log_files()
        
        if not log_files:
            self.log_info("처리할 로그 파일이 없습니다")
            self.archive_results.append("No log files found")
            self.generate_archive_report()
            return 0
        
        success_count = 0
        total_operations = 3
        
        # 1. Archive old logs
        if self.archive_old_logs(log_files):
            success_count += 1
        
        # 2. Clean up old archives
        if self.cleanup_old_archives():
            success_count += 1
        
        # 3. Clean up large logs
        if self.cleanup_large_logs(log_files):
            success_count += 1
        
        # Generate report
        self.generate_archive_report()
        
        self.log_info("===============================================================================")
        
        if success_count == total_operations:
            self.log_success("🎉 로그 아카이브가 성공적으로 완료되었습니다!")
            return 0
        elif success_count > 0:
            self.log_warning(f"⚠️ 로그 아카이브가 부분적으로 완료되었습니다 ({success_count}/{total_operations})")
            return 0  # Still return 0 as partial success is acceptable
        else:
            self.log_error("❌ 로그 아카이브가 실패했습니다!")
            return 1

def main():
    """Main function"""
    try:
        archiver = LogArchiver()
        exit_code = archiver.run_archive()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.error("로그 아카이브가 사용자에 의해 중단되었습니다")
        sys.exit(2)
    except Exception as e:
        logger.error(f"로그 아카이브 중 예상치 못한 오류 발생: {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()