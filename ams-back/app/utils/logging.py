"""
로깅 유틸리티 모듈.
한글 로그 메시지를 지원하는 로깅 설정을 제공합니다.
"""

import logging
import sys
from datetime import datetime

# 루트 로거 설정 - 모든 로거에 영향을 미침
def configure_root_logger(level=logging.INFO):
    """
    루트 로거를 설정하여 모든 로거에 기본 설정을 적용합니다.

    Args:
        level: 로깅 레벨 (기본값: INFO)
    """
    # 기존 핸들러 제거
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 로깅 레벨 설정
    root_logger.setLevel(level)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # 포맷터 설정 - 한글 지원
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    root_logger.addHandler(console_handler)

# 로거 설정
def setup_logger(name, level=logging.INFO):
    """
    지정된 이름과 레벨로 로거를 설정합니다.

    Args:
        name: 로거 이름
        level: 로깅 레벨 (기본값: INFO)

    Returns:
        설정된 로거 인스턴스
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 이미 핸들러가 설정되어 있으면 추가하지 않음
    if not logger.handlers:
        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # 포맷터 설정 - 한글 지원
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        logger.addHandler(console_handler)

    return logger

# 루트 로거 초기 설정
configure_root_logger()

# OCR 로거
ocr_logger = setup_logger("novelike.ocr")

# 세그멘테이션 로거
seg_logger = setup_logger("novelike.seg")

# SSE 로거
sse_logger = setup_logger("app.utils.sse")

# 등록 로거
registration_logger = setup_logger("app.routers.registration")
