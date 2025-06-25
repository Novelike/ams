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

# 1. 빠른 배포 전 체크
log_info "⚡ 빠른 배포 전 체크..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
log_info "현재 디스크 사용량: ${DISK_USAGE}%"

if [ $DISK_USAGE -gt 90 ]; then
    log_warning "디스크 사용량이 90% 초과, 긴급 정리 실행..."
    pip cache purge || true
    sudo rm -rf /tmp/pip-* /tmp/tmp* || true
    log_success "긴급 정리 완료"
else
    log_success "디스크 공간 충분, 정리 건너뜀"
fi

# 2. 백엔드 소스 업데이트 (백업 없이)
log_info "📥 백엔드 소스 업데이트 중 (백업 없이 빠른 배포)..."
cd "$BACKEND_DIR"

# Sparse checkout으로 ams-back만 가져오기
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
git clone --filter=blob:none --sparse "$REPO_URL" temp-repo
cd temp-repo
git sparse-checkout set ams-back
git checkout "$BRANCH"

# 중요 파일들 보존
cd "$BACKEND_DIR"
if [ -f ".env" ]; then
    cp .env .env.backup
fi

# 백엔드 소스 복사 (venv와 .env 제외)
rsync -av --delete --ignore-missing-args \
    --exclude='venv/' \
    --exclude='.env' \
    "$TEMP_DIR/temp-repo/ams-back/" ./ || {
    exit_code=$?
    if [ $exit_code -eq 24 ]; then
        log_warning "rsync warning: some files vanished during transfer (exit code 24) - continuing deployment"
    else
        log_error "rsync failed with exit code $exit_code"
        exit $exit_code
    fi
}

# .env 복원
if [ -f ".env.backup" ]; then
    mv .env.backup .env
fi

rm -rf "$TEMP_DIR"
log_success "백엔드 소스 업데이트 완료 (백업 없이)"

# 3. 환경 설정
log_info "⚙️ 환경 설정 중..."
cat > .env << 'EOF'
ENVIRONMENT=production
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://ams.novelike.dev,http://ams.novelike.dev
PROD_SERVER_IP=10.0.3.203
EOF

log_success "환경 변수 설정 완료"

# 4. 스마트 의존성 체크
log_info "🔍 의존성 변경 확인 중..."

NEED_INSTALL=false

# 가상환경 존재 확인
if [ ! -d "venv" ]; then
    log_info "가상환경이 없습니다. 새로 생성합니다."
    NEED_INSTALL=true
else
    log_success "기존 가상환경 발견"

    # requirements.txt 변경 확인
    if [ -f "requirements.txt.last" ]; then
        if cmp -s requirements.txt requirements.txt.last; then
            log_success "requirements.txt 변경 없음 - 의존성 설치 건너뜀"
            NEED_INSTALL=false
        else
            log_info "requirements.txt 변경 감지 - 의존성 재설치 필요"
            NEED_INSTALL=true
        fi
    else
        log_info "첫 배포 또는 이전 기록 없음 - 의존성 설치 필요"
        NEED_INSTALL=true
    fi
fi

# 5. 조건부 의존성 설치
if [ "$NEED_INSTALL" = true ]; then
    log_info "📦 의존성 설치 시작..."

    # 가상환경 생성 또는 정리
    if [ ! -d "venv" ]; then
        log_info "가상환경 생성 중..."
        python3 -m venv venv
    else
        log_info "기존 가상환경 정리 중..."
        rm -rf venv
        python3 -m venv venv
    fi

    source venv/bin/activate

    # pip 업그레이드 및 의존성 설치
    log_info "pip 업그레이드 중..."
    pip install --upgrade pip --no-cache-dir

    log_info "의존성 설치 중..."
    pip install -r requirements.txt --no-cache-dir --no-warn-script-location

    # requirements.txt 백업 (다음 배포 시 비교용)
    cp requirements.txt requirements.txt.last

    log_success "의존성 설치 완료"
else
    log_success "의존성 설치 건너뜀 - 기존 환경 재사용"
    source venv/bin/activate
fi

# 5. 서비스 재시작
log_info "🔄 서비스 재시작 중..."
sudo systemctl restart $SERVICE_NAME
sleep 5

# 6. 빠른 헬스 체크
log_info "🏥 빠른 헬스 체크 중..."
for i in {1..5}; do
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "헬스 체크 성공 (${i}회 시도)"
        break
    fi
    if [ $i -eq 5 ]; then
        log_error "헬스 체크 실패 (5회 시도 후)"

        # 간단 롤백 (서비스 재시작만)
        log_warning "간단 롤백 수행 중 (서비스 재시작)..."

        # 서비스 상태 확인
        log_info "현재 서비스 상태:"
        sudo systemctl status $SERVICE_NAME --no-pager || true

        # 서비스 재시작 시도
        log_info "서비스 재시작 중..."
        sudo systemctl restart $SERVICE_NAME
        sleep 3

        # 간단한 헬스 체크
        log_info "롤백 후 헬스 체크..."
        for j in {1..3}; do
            if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
                log_success "롤백 후 서비스 정상 (${j}회 시도)"
                break
            fi
            if [ $j -eq 3 ]; then
                log_error "롤백 후에도 서비스 문제 지속"
                log_info "서비스 로그 확인:"
                sudo journalctl -u $SERVICE_NAME --since "5 minutes ago" --no-pager | tail -20
                exit 1
            fi
            sleep 2
        done

        log_success "간단 롤백 완료"
        exit 1
    fi
    log_info "헬스 체크 재시도 중... (${i}/5)"
    sleep 2
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

# 9. 간단한 배포 후 정리
log_info "🧹 간단한 정리 중..."

# 필수 정리만 수행 (pip 캐시만)
pip cache purge || true

log_success "정리 완료"

# 10. 배포 완료 정보
log_info "📋 배포 완료:"
echo "  - 브랜치: $BRANCH"
echo "  - 시간: $(date)"
echo "  - 서비스: $SERVICE_NAME"
