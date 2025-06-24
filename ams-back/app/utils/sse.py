"""
Server-Sent Events (SSE) utility functions for FastAPI.
This module provides functionality for sending real-time updates to clients.
"""

import asyncio
import json
from typing import Dict, Any, List, Callable, Awaitable

from sse_starlette.sse import EventSourceResponse

# 로깅 설정
from app.utils.logging import sse_logger

# In-memory message queue for SSE
# Structure: {job_id: [list of subscribers]}
_subscribers: Dict[str, List[asyncio.Queue]] = {}

sse_logger.info("SSE 유틸리티 모듈 초기화 완료")

async def push_sse(job_id: str, data: Dict[str, Any]) -> None:
    """
    Push an SSE event to all subscribers of a specific job.

    Args:
        job_id: The unique identifier for the job
        data: The data to send as an event
    """
    sse_logger.info(f"작업 ID '{job_id}'에 대한 SSE 이벤트 전송 시작")

    if job_id not in _subscribers:
        sse_logger.warning(f"작업 ID '{job_id}'에 대한 구독자가 없음")
        return

    # 이벤트 정보 로깅
    stage = data.get("stage", "unknown")
    message = data.get("message", "")
    sse_logger.info(f"이벤트 정보 - 단계: {stage}, 메시지: {message}")
    sse_logger.debug(f"전체 이벤트 데이터: {data}")

    # Convert data to JSON string
    message = json.dumps(data)

    # Push to all subscribers
    subscriber_count = len(_subscribers[job_id])
    sse_logger.info(f"'{job_id}' 작업에 대한 {subscriber_count}개 구독자에게 이벤트 전송 중")

    for i, queue in enumerate(_subscribers[job_id]):
        sse_logger.debug(f"구독자 {i+1}/{subscriber_count}에게 이벤트 전송 중")
        await queue.put(message)

    sse_logger.info(f"작업 ID '{job_id}'에 대한 SSE 이벤트 전송 완료")

def subscribe_to_job(job_id: str) -> asyncio.Queue:
    """
    Subscribe to events for a specific job.

    Args:
        job_id: The unique identifier for the job

    Returns:
        An asyncio Queue that will receive events for this job
    """
    sse_logger.info(f"작업 ID '{job_id}'에 대한 새 구독 요청")

    if job_id not in _subscribers:
        sse_logger.debug(f"작업 ID '{job_id}'에 대한 첫 번째 구독자 등록")
        _subscribers[job_id] = []
    else:
        current_subscribers = len(_subscribers[job_id])
        sse_logger.debug(f"작업 ID '{job_id}'에 대한 기존 구독자 수: {current_subscribers}")

    # Create a new queue for this subscriber
    queue = asyncio.Queue()
    _subscribers[job_id].append(queue)

    new_count = len(_subscribers[job_id])
    sse_logger.info(f"작업 ID '{job_id}'에 대한 구독 완료 (총 구독자 수: {new_count})")
    return queue

def unsubscribe_from_job(job_id: str, queue: asyncio.Queue) -> None:
    """
    Unsubscribe from events for a specific job.

    Args:
        job_id: The unique identifier for the job
        queue: The queue to unsubscribe
    """
    sse_logger.info(f"작업 ID '{job_id}'에 대한 구독 취소 요청")

    if job_id in _subscribers and queue in _subscribers[job_id]:
        sse_logger.debug(f"작업 ID '{job_id}'에서 구독자 제거 중")
        _subscribers[job_id].remove(queue)

        # Clean up if no more subscribers
        if not _subscribers[job_id]:
            sse_logger.debug(f"작업 ID '{job_id}'에 대한 마지막 구독자 제거됨, 작업 정리 중")
            del _subscribers[job_id]
            sse_logger.info(f"작업 ID '{job_id}'에 대한 모든 구독자 제거 완료")
        else:
            remaining = len(_subscribers[job_id])
            sse_logger.info(f"작업 ID '{job_id}'에 대한 구독 취소 완료 (남은 구독자 수: {remaining})")
    else:
        sse_logger.warning(f"작업 ID '{job_id}'에 대한 구독 취소 실패: 구독자를 찾을 수 없음")

async def event_generator(job_id: str):
    """
    Generate SSE events for a specific job.

    Args:
        job_id: The unique identifier for the job

    Yields:
        SSE events as they become available
    """
    sse_logger.info(f"작업 ID '{job_id}'에 대한 SSE 이벤트 생성기 시작")

    # Create a queue for this client
    queue = subscribe_to_job(job_id)

    try:
        # Send initial connection established event
        sse_logger.debug(f"작업 ID '{job_id}'에 대한 초기 연결 이벤트 전송")
        initial_data = json.dumps({"status": "connected", "job_id": job_id})
        yield {"event": "connected", "data": initial_data}

        # Listen for messages
        sse_logger.info(f"작업 ID '{job_id}'에 대한 메시지 수신 대기 시작")
        while True:
            try:
                # Wait for a message with a timeout
                sse_logger.debug(f"작업 ID '{job_id}'에 대한 메시지 대기 중 (타임아웃: 60초)")
                message = await asyncio.wait_for(queue.get(), timeout=60.0)
                sse_logger.debug(f"작업 ID '{job_id}'에 대한 메시지 수신됨, 클라이언트로 전송 중")
                yield {"data": message}
            except asyncio.TimeoutError:
                # Send a keep-alive message every 60 seconds
                sse_logger.debug(f"작업 ID '{job_id}'에 대한 타임아웃 발생, 핑 메시지 전송")
                yield {"event": "ping", "data": ""}
    except asyncio.CancelledError:
        # Client disconnected
        sse_logger.info(f"작업 ID '{job_id}'에 대한 클라이언트 연결 종료됨")
    finally:
        # Clean up subscription when client disconnects
        sse_logger.debug(f"작업 ID '{job_id}'에 대한 구독 정리 중")
        unsubscribe_from_job(job_id, queue)
        sse_logger.info(f"작업 ID '{job_id}'에 대한 SSE 이벤트 생성기 종료")

def sse_response(job_id: str) -> EventSourceResponse:
    """
    Create an SSE response for a specific job.

    Args:
        job_id: The unique identifier for the job

    Returns:
        An EventSourceResponse that will stream events to the client
    """
    sse_logger.info(f"작업 ID '{job_id}'에 대한 SSE 응답 생성")
    response = EventSourceResponse(event_generator(job_id))
    sse_logger.debug(f"작업 ID '{job_id}'에 대한 EventSourceResponse 객체 생성 완료")
    return response
