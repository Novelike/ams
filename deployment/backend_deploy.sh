#!/bin/bash
# Backend Deployment Script for AMS
# Optimized for Linux environments

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 기본 설정
BRANCH=${1:-"main"}
REPO_URL="https://github.com/Novelike/ams.git"
BACKEND_DIR="$HOME/ams-back"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SERVICE_NAME="ams-backend"

log_info "🚀 AMS 백엔드 배포 시작 - 브랜치: $BRANCH"

# 1. 백업 생성
log_info "📦 백업 생성 중..."
if [ -d "$BACKEND_DIR" ]; then
    cp -r "$BACKEND_DIR" "$BACKEND_DIR.backup.$TIMESTAMP"
    log_success "백업 생성 완료: $BACKEND_DIR.backup.$TIMESTAMP"
fi

# 2. 백엔드 소스만 업데이트
log_info "📥 백엔드 소스 업데이트 중..."
cd "$BACKEND_DIR"

# Sparse checkout으로 ams-back만 가져오기
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
git clone --filter=blob:none --sparse "$REPO_URL" temp-repo
cd temp-repo
git sparse-checkout set ams-back
git checkout "$BRANCH"

# 백엔드 소스 복사
rsync -av --delete --ignore-missing-args ams-back/ "$BACKEND_DIR/" || {
    exit_code=$?
    if [ $exit_code -eq 24 ]; then
        log_warning "rsync warning: some files vanished during transfer (exit code 24) - continuing deployment"
    else
        log_error "rsync failed with exit code $exit_code"
        exit $exit_code
    fi
}
cd "$BACKEND_DIR"
rm -rf "$TEMP_DIR"

log_success "백엔드 소스 업데이트 완료"

# 3. 환경 설정
log_info "⚙️ 환경 설정 중..."
cat > .env << 'EOF'
ENVIRONMENT=production
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://ams.novelike.dev,http://ams.novelike.dev
PROD_SERVER_IP=10.0.3.203
EOF

log_success "환경 변수 설정 완료"

# 4. 디스크 공간 정리
log_info "🧹 배포 전 디스크 공간 정리 중..."
# pip 캐시 정리
pip cache purge || true
# 임시 파일 정리
sudo rm -rf /tmp/pip-* /tmp/tmp* || true
# 오래된 백업 정리 (1일 이상)
find "$HOME" -name "ams-back.backup.*" -type d -mtime +1 -exec rm -rf {} + || true
log_success "사전 정리 완료"

# 5. 가상환경 활성화 및 의존성 설치 (최적화)
log_info "📦 의존성 설치 중 (캐시 최적화)..."
if [ ! -d "venv" ]; then
    log_info "가상환경 생성 중..."
    python3 -m venv venv
fi

source venv/bin/activate

# pip 캐시 정리 후 최적화된 설치
pip cache purge
pip install --upgrade pip --no-cache-dir

# 임시 캐시 디렉토리 사용하여 설치
pip install -r requirements.txt \
    --cache-dir /tmp/pip-cache \
    --no-warn-script-location

# 임시 캐시 즉시 정리
rm -rf /tmp/pip-cache

log_success "의존성 설치 완료"

# 5. 서비스 재시작
log_info "🔄 서비스 재시작 중..."
sudo systemctl restart $SERVICE_NAME
sleep 5

# 6. 헬스 체크
log_info "🏥 헬스 체크 수행 중..."
for i in {1..10}; do
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "헬스 체크 성공"
        break
    fi
    if [ $i -eq 10 ]; then
        log_error "헬스 체크 실패"

        # 롤백 수행
        log_warning "롤백 수행 중..."
        if [ -d "$BACKEND_DIR.backup.$TIMESTAMP" ]; then
            rsync -av --delete --ignore-missing-args "$BACKEND_DIR.backup.$TIMESTAMP/" "$BACKEND_DIR/" || {
                exit_code=$?
                if [ $exit_code -eq 24 ]; then
                    log_warning "rsync warning during rollback: some files vanished during transfer (exit code 24) - continuing rollback"
                else
                    log_error "rsync rollback failed with exit code $exit_code"
                    exit $exit_code
                fi
            }
            if [ ! -d "venv" ]; then
                log_info "롤백용 가상환경 생성 중..."
                python3 -m venv venv
            fi
            source venv/bin/activate

            # 롤백 후 필요시 의존성 재설치
            if [ -f "requirements.txt" ]; then
                log_info "롤백 후 의존성 재설치 중..."
                pip install --upgrade pip --no-cache-dir
                pip install -r requirements.txt --cache-dir /tmp/pip-cache --no-warn-script-location
                rm -rf /tmp/pip-cache
            fi

            sudo systemctl restart $SERVICE_NAME
            log_success "롤백 완료"
        fi
        exit 1
    fi
    sleep 3
done

# 7. 서비스 상태 확인
log_info "📊 서비스 상태 확인 중..."
sudo systemctl status $SERVICE_NAME --no-pager

# 8. 외부 접근 테스트
log_info "🌐 외부 접근 테스트 중..."
if curl -f https://ams-api.novelike.dev/api/health > /dev/null 2>&1; then
    log_success "외부 접근 테스트 성공"
else
    log_warning "외부 접근 테스트 실패 (Nginx 설정 확인 필요)"
fi

log_success "🎉 백엔드 배포 완료!"
log_info "🌐 서비스 URL: https://ams-api.novelike.dev"

# 9. 배포 후 디스크 공간 정리
log_info "🧹 배포 후 디스크 공간 정리 중..."

# pip 캐시 정리
pip cache purge || true

# 임시 파일 정리
sudo rm -rf /tmp/pip-* /tmp/tmp* || true

# 오래된 백업 정리 (3일 이상으로 단축)
find "$HOME" -name "ams-back.backup.*" -type d -mtime +3 -exec rm -rf {} + || true

# 최종 디스크 사용량 확인
echo "최종 디스크 사용량:"
df -h

# 디렉토리별 사용량 확인
echo "홈 디렉토리 사용량:"
du -h --max-depth=1 "$HOME" | sort -hr | head -10

log_success "정리 완료"

# 10. 배포 정보 출력
log_info "📋 배포 정보:"
echo "  - 브랜치: $BRANCH"
echo "  - 시간: $(date)"
echo "  - 백업: $BACKEND_DIR.backup.$TIMESTAMP"
echo "  - 서비스: $SERVICE_NAME"
echo "  - 포트: 8000"
echo "  - 디스크 사용량: $(df -h / | awk 'NR==2{print $5}')"
