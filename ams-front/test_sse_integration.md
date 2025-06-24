# SSE Integration Test Guide

## Overview
This document describes how to test the newly implemented Server-Sent Events (SSE) integration in the Registration component.

## Changes Made

### 1. CenteredLoader Component Enhanced
- **File**: `src/components/CenteredLoader.jsx`
- **Changes**: 
  - Added indeterminate LinearProgress when no specific progress percentage is provided
  - Progress bar now shows indeterminate animation for SSE status updates
  - Maintains determinate progress for file uploads with percentage

### 2. Registration Component SSE Integration
- **File**: `src/pages/Registration.jsx`
- **Changes**:
  - Added SSE state management (`jobId`, `eventSource`, `currentMessage`)
  - Implemented `connectSSE()` function for EventSource management
  - Updated button handlers for segmentation, OCR, and registration
  - Modified CenteredLoader usage to display SSE messages

## Expected Flow

### 1. Image Upload (Existing Behavior Maintained)
```
User uploads image → Shows "업로드 중... X%" with determinate progress bar
```

### 2. Segmentation with SSE
```
User clicks "세그멘테이션 시작" → 
API call returns {job_id: "xxx"} → 
SSE connection established → 
Shows indeterminate progress with messages like:
- "세그멘테이션 시작..."
- "이미지 분석 중..."
- "세그멘테이션 완료"
→ Auto-advance to next step
```

### 3. OCR with SSE
```
User clicks "OCR 시작" → 
API call returns {job_id: "yyy"} → 
SSE connection established → 
Shows indeterminate progress with messages like:
- "OCR 시작..."
- "텍스트 인식 중..."
- "OCR 완료"
→ Auto-advance to next step
```

### 4. Registration with SSE
```
User clicks "자산 등록" → 
API call returns {job_id: "zzz"} → 
SSE connection established → 
Shows indeterminate progress with messages like:
- "자산 등록 시작..."
- "데이터 처리 중..."
- "등록 완료"
→ Auto-advance to next step
```

## Backend Requirements

For this implementation to work, the backend needs to:

1. **Return job_id in API responses**:
   ```json
   {
     "job_id": "unique-job-identifier",
     "status": "started"
   }
   ```

2. **Provide SSE endpoint**: `/api/registration/status/{job_id}`

3. **Send SSE messages in format**:
   ```json
   {
     "stage": "segment_start|segment_done|ocr_start|ocr_done|register_start|register_done",
     "message": "Human readable status message",
     "result": "Optional result data when stage is *_done"
   }
   ```

## Testing Steps

1. **Start the application**
2. **Upload an image** - Verify upload progress shows percentage
3. **Click segmentation** - Verify SSE connection and indeterminate progress
4. **Click OCR** - Verify SSE messages update in real-time
5. **Click registration** - Verify final step completes properly

## Fallback Behavior

If the backend doesn't return `job_id`, the component falls back to the original behavior without SSE, ensuring backward compatibility.

## Key Features Implemented

✅ SSE connection management with EventSource  
✅ Real-time status message updates  
✅ Indeterminate progress bar for SSE operations  
✅ Determinate progress bar for file uploads  
✅ Automatic step advancement on completion  
✅ Proper cleanup of SSE connections  
✅ Fallback to original behavior if no job_id  
✅ Unified loading experience with CenteredLoader