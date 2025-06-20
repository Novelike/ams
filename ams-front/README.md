# AMS (자산 관리 시스템)

React 기반의 자산 관리 시스템 프론트엔드 애플리케이션입니다.

## 기능

- **대시보드**: 자산 현황 및 통계 확인
  - 사이트별 자산 현황
  - 기기 종류별 총 대수
  - 여유 기기 변동 추이
  - 할당된 기기 변동 추이

- **자산 등록**: 이미지 업로드, 세그멘테이션, OCR, 챗봇 보조 입력을 통한 자산 등록
  - 이미지 업로드 및 자동 인식
  - 세그멘테이션 및 OCR 처리
  - 챗봇 보조 입력
  - 자산 정보 등록

- **자산 목록**: 자산 목록 조회, 필터링, 검색
  - 사이트별, 유형별, 사용자별 필터링
  - 검색 기능
  - 페이지네이션 및 정렬

- **자산 상세**: 자산 상세 정보 조회 및 수정
  - 자산 정보 수정
  - 이력 관리

- **챗봇**: AI 기반 자산 등록 보조 및 정보 검색
  - 모델명 기반 스펙 자동 검색
  - 관리번호 자동 생성
  - 사용자 정보 입력 보조

- **라벨**: 자산 라벨 생성, 다운로드, 프린트
  - QR 코드 생성
  - 라벨 이미지 다운로드
  - 일괄 인쇄

## 개발 환경 설정

### 필수 요구사항

- Node.js 18.0 이상
- npm 9.0 이상

### 설치 및 실행

```bash
# 의존성 설치
npm install --legacy-peer-deps

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 결과물 미리보기
npm run preview
```

## 배포

프로젝트 루트 디렉토리에 배포를 위한 스크립트가 포함되어 있습니다:

- `build-and-deploy.bat`: Windows 환경에서 빌드 및 배포를 실행하는 스크립트
- `deploy-to-front.sh`: Bastion 서버에서 Front 서버로 파일을 전송하는 스크립트
- `serve.js`: Front 서버에서 React 애플리케이션을 서비스하는 Express 서버

자세한 배포 방법은 [배포 가이드](./deployment-guide.md)를 참조하세요.

## 프로젝트 구조

```
ams-front/
├── public/             # 정적 파일
├── src/                # 소스 코드
│   ├── assets/         # 이미지, 폰트 등 자산 파일
│   ├── components/     # 재사용 가능한 컴포넌트
│   │   ├── dashboard/  # 대시보드 관련 컴포넌트
│   │   │   ├── AnalyticsOverviewSection.jsx  # 할당된 기기 변동 추이
│   │   │   ├── DataTableSection.jsx          # 사이트별 자산 현황 테이블
│   │   │   ├── PerformanceMetricsSection.jsx # 여유 기기 변동 추이
│   │   │   └── WebsiteViewsSection.jsx       # 기기 종류별 총 대수
│   │   ├── asset/      # 자산 관련 컴포넌트
│   │   ├── registration/ # 자산 등록 관련 컴포넌트
│   │   ├── chatbot/    # 챗봇 관련 컴포넌트
│   │   ├── label/      # 라벨 관련 컴포넌트
│   │   └── common/     # 공통 컴포넌트
│   ├── layouts/        # 레이아웃 컴포넌트
│   │   └── SidebarSection.jsx # 사이드바 네비게이션
│   ├── pages/          # 페이지 컴포넌트
│   │   ├── Dashboard.jsx  # 대시보드 페이지
│   │   ├── AssetList.jsx  # 자산 목록 페이지
│   │   ├── AssetDetail.jsx # 자산 상세 페이지
│   │   ├── Registration.jsx # 자산 등록 페이지
│   │   ├── Chatbot.jsx  # 챗봇 페이지
│   │   └── Label.jsx    # 라벨 페이지
│   ├── services/       # API 서비스
│   ├── utils/          # 유틸리티 함수
│   ├── App.jsx         # 애플리케이션 루트 컴포넌트
│   ├── index.jsx       # 진입점
│   └── ThemeProvider.jsx # 테마 설정
├── index.html          # HTML 템플릿
├── vite.config.js      # Vite 설정
├── package.json        # 프로젝트 메타데이터 및 의존성
└── deployment-guide.md # 배포 가이드
```

## 주요 컴포넌트

### 대시보드 컴포넌트
- **StatCards**: 총 자산, 신규 등록, 사용자 수 등의 주요 지표를 표시
- **WebsiteViewsSection**: 기기 종류별 총 대수를 바 차트로 표시
- **PerformanceMetricsSection**: 여유 기기 변동 추이를 라인 차트로 표시
- **AnalyticsOverviewSection**: 할당된 기기 변동 추이를 영역 차트로 표시
- **DataTableSection**: 사이트별 자산 현황을 테이블로 표시

### 자산 등록 컴포넌트
- **ImageUploader**: 이미지 업로드 및 미리보기
- **SegmentationViewer**: 세그멘테이션 결과 표시
- **OCRResultEditor**: OCR 결과 확인 및 편집
- **AssetForm**: 자산 정보 입력 폼

### 챗봇 컴포넌트
- **ChatInterface**: 챗봇과의 대화 인터페이스
- **MessageList**: 메시지 목록 표시
- **SuggestionChips**: 제안 응답 표시

### 라벨 컴포넌트
- **LabelGenerator**: QR 코드 및 라벨 생성
- **LabelPreview**: 라벨 미리보기
- **BatchPrintManager**: 일괄 인쇄 관리

## 기술 스택

- React 19
- React Router 7
- Material-UI (MUI) 5
- Vite 6
- React Dropzone (파일 업로드)
- React Query (데이터 페칭 및 캐싱)
- QRCode.react (QR 코드 생성)
- React Webcam (이미지 캡처)
- Chart.js (차트 시각화)
- React Hook Form (폼 관리)

## 백엔드 연동

이 프론트엔드 애플리케이션은 FastAPI로 구축된 백엔드 API와 연동됩니다. 백엔드 API에 대한 자세한 정보는 [백엔드 README](../amd-back/README.md)를 참조하세요.

### API 연결 설정

API 연결은 `src/services/api.js` 파일에서 관리됩니다. 이 파일은 다음과 같은 기능을 제공합니다:

- 모든 백엔드 API 엔드포인트에 대한 함수 제공
- 개발 및 프로덕션 환경에 따른 API 기본 URL 설정
- 요청 및 응답 인터셉터를 통한 오류 처리

#### 환경 설정

애플리케이션은 다음과 같은 환경 파일을 사용합니다:

- `.env.development`: 개발 환경 설정 (localhost:8000)
- `.env.production`: 프로덕션 환경 설정 (prod_server:8000)

로컬에서 실행 시 localhost:8000을, 서버 배포 시 자동으로 prod_server:8000을 사용합니다.

자세한 API 연결 설정 방법은 [API 서버 연결 설정 가이드](./api-configuration.md)를 참조하세요.

#### API 사용 예시

```javascript
import { assetApi, registrationApi } from '../services/api';

// 자산 목록 가져오기
const fetchAssets = async () => {
  try {
    const data = await assetApi.getAssets(1, 10, { site: '판교 본사' });
    console.log(data);
  } catch (error) {
    console.error('자산 목록을 가져오는 중 오류 발생:', error);
  }
};

// 이미지 업로드
const uploadImage = async (file) => {
  try {
    const data = await registrationApi.uploadImage(file);
    console.log(data);
  } catch (error) {
    console.error('이미지 업로드 중 오류 발생:', error);
  }
};
```
