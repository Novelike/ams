# AMS 백엔드 API

이 프로젝트는 FastAPI로 구축된 자산 관리 시스템(AMS)의 백엔드 API입니다.

## 요구사항

- Python 3.10
- FastAPI
- Uvicorn
- qrcode (라벨 생성용)
- 기타 `requirements.txt`에 나열된 의존성 패키지

## 설치 및 실행

1. 가상 환경 생성:
   ```
   python -m venv venv
   ```

2. 가상 환경 활성화:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

3. 의존성 패키지 설치:
   ```
   pip install -r requirements.txt
   ```

4. 환경 변수 설정:
   `.env` 파일을 프로젝트 루트 디렉토리에 생성하고 다음과 같이 설정합니다:
   ```
   # 백엔드 환경 변수
   PORT=8000

   # CORS 설정
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173

   # 프로덕션 서버 IP (프로덕션 환경에서 주석 해제 및 설정)
   # PROD_SERVER_IP=your_production_server_ip
   ```

5. 서버 실행:
   ```
   python main.py
   ```

   또는 uvicorn으로 직접 실행:
   ```
   uvicorn main:app --reload --log-config logging_config.py:LOGGING_CONFIG
   ```

   이 명령은 로깅 설정 파일을 사용하여 모든 로그가 콘솔에 올바르게 표시되도록 합니다.

6. API 문서 접근:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 환경 변수

다음 환경 변수를 `.env` 파일에 설정하여 애플리케이션 동작을 구성할 수 있습니다:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| PORT | 서버가 실행될 포트 | 8000 |
| ALLOWED_ORIGINS | CORS 허용 출처 (쉼표로 구분) | http://localhost:3000,http://localhost:5173,... |
| PROD_SERVER_IP | 프로덕션 서버 IP 주소 | 없음 |

### 프로덕션 배포

프로덕션 환경에 배포할 때는 다음 단계를 따르세요:

1. `.env` 파일에서 `PROD_SERVER_IP` 변수의 주석을 해제하고 실제 서버 IP로 설정합니다.
2. 프론트엔드 애플리케이션의 `.env.production` 파일에서 `VITE_API_BASE_URL`을 실제 서버 IP로 설정합니다.

## API 엔드포인트

### 자산(Assets)

- `GET /api/assets` - 모든 자산 조회
- `GET /api/assets/{asset_id}` - ID로 특정 자산 조회
- `GET /api/assets/number/{asset_number}` - 자산 번호로 특정 자산 조회
- `GET /api/assets/site/{site}` - 사이트별 자산 조회
- `GET /api/assets/type/{asset_type}` - 유형별 자산 조회
- `GET /api/assets/user/{user}` - 사용자별 자산 조회

### 자산 목록(Asset List, 필터링 및 페이지네이션 지원)

- `GET /api/assets/list` - 필터링, 페이지네이션, 정렬 기능이 있는 자산 목록 조회
- `GET /api/assets/list/{asset_id}` - ID로 특정 자산 조회
- `GET /api/assets/list/search/{query}` - 모델명, 일련번호 등으로 자산 검색
- `GET /api/assets/list/site/{site}` - 사이트별 자산 조회
- `GET /api/assets/list/type/{asset_type}` - 유형별 자산 조회
- `GET /api/assets/list/user/{user}` - 사용자별 자산 조회

### 자산 등록(Registration)

- `POST /api/registration/upload` - 자산 등록을 위한 이미지 파일 업로드
- `POST /api/registration/segment` - 관심 영역 식별을 위한 이미지 세그멘테이션 수행
- `POST /api/registration/ocr` - 세그먼트된 이미지 영역에 OCR 수행
- `POST /api/registration/register` - 제공된 정보로 새 자산 등록
- `POST /api/registration/chatbot-assist` - 자산 등록을 위한 챗봇 지원 받기
- `GET /api/registration/workflow` - 등록 워크플로우 단계 조회

### 대시보드(Dashboard)

- `GET /api/dashboard/stats` - 대시보드 통계 카드용 통계 조회
- `GET /api/dashboard/site-assets` - 데이터 테이블용 사이트별 자산 데이터 조회
- `GET /api/dashboard/chart-data` - 대시보드 차트용 데이터 조회

### 챗봇(Chatbot)

- `POST /api/chatbot/send` - 챗봇에 메시지 전송 및 응답 받기
- `GET /api/chatbot/history` - 채팅 기록 조회
- `DELETE /api/chatbot/history` - 채팅 기록 삭제
- `POST /api/chatbot/asset-assist` - 자산 등록 지원 받기

### 라벨(Labels)

- `GET /api/labels` - 모든 라벨 조회
- `GET /api/labels/{label_id}` - ID로 특정 라벨 조회
- `POST /api/labels` - 새 라벨 생성
- `PUT /api/labels/{label_id}` - 라벨 업데이트
- `DELETE /api/labels/{label_id}` - 라벨 삭제
- `GET /api/labels/{label_id}/download` - 라벨을 이미지로 다운로드
- `POST /api/labels/{label_id}/print` - 라벨을 인쇄됨으로 표시
- `GET /api/labels/asset/{asset_id}` - 자산 ID로 라벨 조회
- `GET /api/labels/batch/print` - 여러 라벨을 일괄 인쇄

## 프로젝트 구조

```
ams-back/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── asset.py
│   │   ├── chatbot.py
│   │   ├── dashboard.py
│   │   ├── label.py
│   │   ├── list_router.py
│   │   └── registration.py
│   ├── data/
│   │   ├── __init__.py
│   │   └── sample_data.py
│   └── __init__.py
├── main.py
├── requirements.txt
└── README.md
```

## 데이터 모델

### 자산 도메인

- `Asset` - 자산 번호, 모델명, 일련번호, 제조사, 사이트 등의 필드를 가진 자산
- `AssetType` - 자산 분류를 위한 열거형(노트북, 데스크탑, 모니터 등)

### 등록 도메인

- `FileUploadResponse` - 업로드된 파일에 대한 정보
- `SegmentationRequest/Response` - 이미지 세그멘테이션용
- `OCRRequest/Response` - OCR 처리용
- `AssetRegistrationRequest` - 새 자산 등록용

### 대시보드

- `StatCard` - 대시보드 통계 카드용 데이터
- `SiteAsset` - 데이터 테이블용 사이트별 자산 데이터
- `ChartData` - 차트용 데이터
- `DashboardCharts` - 대시보드용 차트 모음

### 챗봇

- `ChatMessage` - 챗봇에 전송된 메시지
- `ChatResponse` - 제안 및 자산 정보가 포함된 챗봇 응답

### 라벨

- `Label` - QR 코드 및 인쇄 상태가 포함된 자산용 라벨

### 목록

- `AssetFilter` - 자산 필터링용
- `PaginationParams` - 페이지네이션용
- `AssetListResponse` - 페이지네이션된 자산이 포함된 응답

## 자산 등록 워크플로우

1. 자산 이미지 업로드
2. 관심 영역 식별을 위한 이미지 세그멘테이션 수행
3. 세그먼트된 이미지 영역에 OCR 수행
4. OCR 결과 검토 및 편집
5. 추가 정보를 위한 챗봇 지원 받기
6. 제공된 정보로 자산 등록
7. 자산용 라벨 생성

## 참고사항

이것은 임시 구현으로 모의 데이터를 사용합니다. 실제 환경에서는 다음을 구현해야 합니다:

1. 영구 저장을 위한 데이터베이스 연결
2. 적절한 인증 및 권한 부여
3. 오류 처리 및 유효성 검사
4. 로깅 및 모니터링
5. 모든 엔드포인트에 대한 테스트
