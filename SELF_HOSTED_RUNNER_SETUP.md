# Self-Hosted Runner 설정 가이드

## 개요
이 문서는 AMS 프로젝트에서 GitHub Actions Self-Hosted Runner를 사용하기 위한 설정 가이드입니다.

## 변경 사항

### 1. CI/CD 워크플로우 수정
다음 작업들이 self-hosted runner를 사용하도록 변경되었습니다:

- **deploy-dev**: 개발 환경 배포
- **deploy-prod**: 프로덕션 환경 배포 (Blue-Green)
- **performance-test**: 성능 테스트
- **setup-monitoring**: 모니터링 설정
- **cleanup**: 정리 작업

### 2. Runner 라벨 설정
모든 self-hosted 작업에 다음 라벨이 적용되었습니다:
```yaml
runs-on: [self-hosted, windows, deployment]
```

### 3. Windows 호환성 개선
- k6 설치 스크립트를 Windows용으로 변경
- PowerShell 명령어 사용 (`Get-Date` 등)
- 파일 경로 처리 개선

## Self-Hosted Runner 설정 방법

### 1. Runner 라벨 추가
GitHub Actions Runner 서비스에 다음 라벨을 추가해야 합니다:

```bash
# Runner 서비스 중지
.\svc.sh stop

# 라벨 추가하여 Runner 재구성
.\config.cmd remove --token YOUR_REMOVAL_TOKEN
.\config.cmd --url https://github.com/YOUR_USERNAME/YOUR_REPO --token YOUR_TOKEN --labels self-hosted,windows,deployment

# 서비스 재시작
.\svc.sh start
```

### 2. 필수 소프트웨어 설치 확인

#### Python 3.9+
```powershell
python --version
pip --version
```

#### Git
```powershell
git --version
```

#### Docker (선택사항)
```powershell
docker --version
```

#### Node.js 18+ (성능 테스트용)
```powershell
node --version
npm --version
```

### 3. 환경 변수 설정
다음 환경 변수들이 설정되어 있는지 확인하세요:

```powershell
# Python이 PATH에 포함되어 있는지 확인
$env:PATH -split ';' | Where-Object { $_ -like '*Python*' }

# Git이 PATH에 포함되어 있는지 확인
$env:PATH -split ';' | Where-Object { $_ -like '*Git*' }
```

## 테스트 방법

### 1. 자동 테스트 워크플로우 실행
테스트 워크플로우를 수동으로 실행하여 runner 설정을 확인할 수 있습니다:

1. GitHub 저장소의 Actions 탭으로 이동
2. "Test Self-Hosted Runner" 워크플로우 선택
3. "Run workflow" 버튼 클릭
4. 실행 결과 확인

### 2. 테스트 브랜치 생성
```bash
git checkout -b test-runner
git push origin test-runner
```

테스트 브랜치에 푸시하면 자동으로 테스트 워크플로우가 실행됩니다.

## GitHub Secrets 설정

다음 secrets이 설정되어 있는지 확인하세요:

### 배포 관련
- `SSH_PRIVATE_KEY`: SSH 개인 키
- `BASTION_HOST`: Bastion 호스트 주소
- `BACKEND_HOST`: 백엔드 서버 주소
- `SSH_USER`: SSH 사용자명

### Docker 관련
- `DOCKER_USERNAME`: Docker Hub 사용자명
- `DOCKER_PASSWORD`: Docker Hub 비밀번호

### 모니터링 관련 (선택사항)
- `GRAFANA_API_KEY`: Grafana API 키
- `PROMETHEUS_URL`: Prometheus URL

### 알림 관련 (선택사항)
- `SLACK_WEBHOOK_URL`: Slack 웹훅 URL

## 문제 해결

### 1. Runner가 작업을 받지 못하는 경우
- Runner 라벨이 올바르게 설정되었는지 확인
- Runner 서비스가 실행 중인지 확인
- GitHub 저장소 설정에서 Runner가 등록되어 있는지 확인

### 2. Python 관련 오류
```powershell
# Python 경로 확인
Get-Command python
Get-Command pip

# 가상환경 사용 (권장)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. 권한 관련 오류
- PowerShell 실행 정책 확인: `Get-ExecutionPolicy`
- 필요시 정책 변경: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 4. 네트워크 연결 문제
```powershell
# GitHub 연결 테스트
Test-NetConnection -ComputerName github.com -Port 443

# Docker Hub 연결 테스트
Test-NetConnection -ComputerName docker.io -Port 443
```

## 모니터링

### Runner 상태 확인
```powershell
# 서비스 상태 확인
Get-Service | Where-Object { $_.Name -like '*actions*' }

# 로그 확인
Get-Content "C:\actions-runner\_diag\Runner_*.log" -Tail 50
```

### 성능 모니터링
- CPU 사용률
- 메모리 사용률
- 디스크 공간
- 네트워크 대역폭

## 보안 고려사항

1. **Runner 격리**: Self-hosted runner는 신뢰할 수 있는 환경에서만 실행
2. **네트워크 보안**: 필요한 포트만 열어두기
3. **정기 업데이트**: Runner 소프트웨어 정기 업데이트
4. **로그 모니터링**: 비정상적인 활동 감지

## 추가 리소스

- [GitHub Actions Self-hosted runners 공식 문서](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Windows에서 Self-hosted runner 설정](https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners)
- [Runner 라벨 관리](https://docs.github.com/en/actions/hosting-your-own-runners/using-labels-with-self-hosted-runners)