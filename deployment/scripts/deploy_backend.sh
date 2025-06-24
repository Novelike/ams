#!/bin/bash

# =============================================================================
# 백엔드 자동 배포 스크립트
# =============================================================================

set -e  # 오류 발생 시 스크립트 중단
set -u  # 정의되지 않은 변수 사용 시 오류

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 설정 변수
BRANCH=${1:-main}
APP_NAME="ams-backend"
APP_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/backups/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="ams-backend"
NGINX_CONFIG="/etc/nginx/sites-available/ams"
LOG_FILE="/var/log/${APP_NAME}/deploy.log"
REQUIREMENTS_FILE="${APP_DIR}/requirements.txt"
HEALTH_CHECK_URL="http://localhost:8000/api/registration/workflow"
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10

# 배포 시작
log_info "🚀 백엔드 자동 배포 시작 (Branch: ${BRANCH})"
log_info "배포 대상: ${APP_NAME}"
log_info "배포 디렉토리: ${APP_DIR}"

# 로그 디렉토리 생성
mkdir -p "$(dirname "${LOG_FILE}")"

# 함수 정의
cleanup_on_error() {
    log_error "배포 중 오류 발생. 정리 작업 수행 중..."
    
    # 서비스 상태 확인 및 복구 시도
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_info "서비스가 실행 중입니다. 재시작을 시도합니다."
        sudo systemctl restart "${SERVICE_NAME}" || true
    else
        log_warning "서비스가 중지되어 있습니다. 백업에서 복구를 시도합니다."
        restore_from_backup || true
    fi
    
    exit 1
}

# 오류 발생 시 정리 함수 실행
trap cleanup_on_error ERR

create_backup() {
    log_info "📦 현재 버전 백업 생성 중..."
    
    # 백업 디렉토리 생성
    mkdir -p "${BACKUP_DIR}"
    
    # 타임스탬프 생성
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}"
    
    if [ -d "${APP_DIR}" ]; then
        # 현재 애플리케이션 백업
        cp -r "${APP_DIR}" "${BACKUP_PATH}"
        log_success "백업 생성 완료: ${BACKUP_PATH}"
        
        # 오래된 백업 정리 (7일 이상된 백업 삭제)
        find "${BACKUP_DIR}" -type d -name "backup_*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
        log_info "오래된 백업 정리 완료"
    else
        log_warning "백업할 애플리케이션 디렉토리가 없습니다: ${APP_DIR}"
    fi
}

restore_from_backup() {
    log_info "🔄 백업에서 복구 중..."
    
    # 최신 백업 찾기
    LATEST_BACKUP=$(find "${BACKUP_DIR}" -type d -name "backup_*" | sort -r | head -n 1)
    
    if [ -n "${LATEST_BACKUP}" ] && [ -d "${LATEST_BACKUP}" ]; then
        log_info "최신 백업 발견: ${LATEST_BACKUP}"
        
        # 현재 디렉토리 제거 및 백업 복원
        rm -rf "${APP_DIR}"
        cp -r "${LATEST_BACKUP}" "${APP_DIR}"
        
        # 서비스 재시작
        sudo systemctl restart "${SERVICE_NAME}"
        
        log_success "백업에서 복구 완료"
        return 0
    else
        log_error "복구할 백업을 찾을 수 없습니다"
        return 1
    fi
}

check_prerequisites() {
    log_info "🔍 사전 요구사항 확인 중..."
    
    # Git 설치 확인
    if ! command -v git &> /dev/null; then
        log_error "Git이 설치되어 있지 않습니다"
        exit 1
    fi
    
    # Python 설치 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python3이 설치되어 있지 않습니다"
        exit 1
    fi
    
    # pip 설치 확인
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3이 설치되어 있지 않습니다"
        exit 1
    fi
    
    # 디스크 공간 확인 (최소 1GB)
    AVAILABLE_SPACE=$(df "${APP_DIR%/*}" | awk 'NR==2 {print $4}')
    if [ "${AVAILABLE_SPACE}" -lt 1048576 ]; then  # 1GB in KB
        log_error "디스크 공간이 부족합니다. 최소 1GB가 필요합니다"
        exit 1
    fi
    
    log_success "사전 요구사항 확인 완료"
}

stop_services() {
    log_info "🛑 서비스 중지 중..."
    
    # 백엔드 서비스 중지
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        sudo systemctl stop "${SERVICE_NAME}"
        log_success "백엔드 서비스 중지 완료"
    else
        log_info "백엔드 서비스가 이미 중지되어 있습니다"
    fi
    
    # 프로세스 확인 및 강제 종료
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        log_warning "실행 중인 uvicorn 프로세스 발견. 강제 종료합니다."
        pkill -f "uvicorn.*main:app" || true
        sleep 2
    fi
}

update_code() {
    log_info "📥 코드 업데이트 중..."
    
    # 애플리케이션 디렉토리로 이동
    cd "${APP_DIR}"
    
    # Git 상태 확인
    if [ ! -d ".git" ]; then
        log_error "Git 저장소가 아닙니다: ${APP_DIR}"
        exit 1
    fi
    
    # 현재 브랜치 확인
    CURRENT_BRANCH=$(git branch --show-current)
    log_info "현재 브랜치: ${CURRENT_BRANCH}"
    
    # 변경사항 stash (있는 경우)
    if ! git diff --quiet; then
        log_warning "로컬 변경사항 발견. stash 처리합니다."
        git stash push -m "Auto-stash before deployment $(date)"
    fi
    
    # 원격 저장소에서 최신 코드 가져오기
    log_info "원격 저장소에서 최신 코드 가져오는 중..."
    git fetch origin
    
    # 지정된 브랜치로 체크아웃
    if [ "${CURRENT_BRANCH}" != "${BRANCH}" ]; then
        log_info "브랜치 변경: ${CURRENT_BRANCH} -> ${BRANCH}"
        git checkout "${BRANCH}"
    fi
    
    # 최신 코드로 업데이트
    git pull origin "${BRANCH}"
    
    # 현재 커밋 정보 로깅
    COMMIT_HASH=$(git rev-parse HEAD)
    COMMIT_MESSAGE=$(git log -1 --pretty=format:"%s")
    log_success "코드 업데이트 완료"
    log_info "커밋: ${COMMIT_HASH}"
    log_info "메시지: ${COMMIT_MESSAGE}"
}

setup_virtual_environment() {
    log_info "🐍 가상환경 설정 중..."
    
    # 가상환경 디렉토리 확인
    if [ ! -d "${VENV_DIR}" ]; then
        log_info "가상환경 생성 중..."
        python3 -m venv "${VENV_DIR}"
    fi
    
    # 가상환경 활성화
    source "${VENV_DIR}/bin/activate"
    
    # pip 업그레이드
    pip install --upgrade pip
    
    log_success "가상환경 설정 완료"
}

install_dependencies() {
    log_info "📦 의존성 설치 중..."
    
    # 가상환경 활성화 확인
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        source "${VENV_DIR}/bin/activate"
    fi
    
    # requirements.txt 존재 확인
    if [ ! -f "${REQUIREMENTS_FILE}" ]; then
        log_error "requirements.txt 파일을 찾을 수 없습니다: ${REQUIREMENTS_FILE}"
        exit 1
    fi
    
    # 의존성 설치
    pip install -r "${REQUIREMENTS_FILE}"
    
    log_success "의존성 설치 완료"
}

run_database_migrations() {
    log_info "🗄️ 데이터베이스 마이그레이션 실행 중..."
    
    # 가상환경 활성화 확인
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        source "${VENV_DIR}/bin/activate"
    fi
    
    # Alembic 마이그레이션 실행 (있는 경우)
    if [ -f "alembic.ini" ]; then
        log_info "Alembic 마이그레이션 실행 중..."
        alembic upgrade head
        log_success "Alembic 마이그레이션 완료"
    else
        log_info "Alembic 설정 파일이 없습니다. 마이그레이션을 건너뜁니다."
    fi
}

collect_static_files() {
    log_info "📁 정적 파일 수집 중..."
    
    # 정적 파일 디렉토리 생성
    STATIC_DIR="${APP_DIR}/static"
    mkdir -p "${STATIC_DIR}"
    
    # 정적 파일이 있는 경우 처리
    if [ -d "${APP_DIR}/app/static" ]; then
        cp -r "${APP_DIR}/app/static/"* "${STATIC_DIR}/"
        log_success "정적 파일 수집 완료"
    else
        log_info "정적 파일 디렉토리가 없습니다. 건너뜁니다."
    fi
}

start_services() {
    log_info "🚀 서비스 시작 중..."
    
    # systemd 서비스 파일 확인
    if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
        log_warning "systemd 서비스 파일이 없습니다. 수동으로 생성합니다."
        create_systemd_service
    fi
    
    # systemd 데몬 리로드
    sudo systemctl daemon-reload
    
    # 서비스 시작
    sudo systemctl start "${SERVICE_NAME}"
    
    # 서비스 자동 시작 설정
    sudo systemctl enable "${SERVICE_NAME}"
    
    log_success "서비스 시작 완료"
}

create_systemd_service() {
    log_info "📝 systemd 서비스 파일 생성 중..."
    
    cat << EOF | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null
[Unit]
Description=AMS Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${APP_DIR}
Environment=PATH=${VENV_DIR}/bin
ExecStart=${VENV_DIR}/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "systemd 서비스 파일 생성 완료"
}

health_check() {
    log_info "🏥 헬스 체크 수행 중..."
    
    local attempt=1
    local max_attempts=${MAX_HEALTH_CHECK_ATTEMPTS}
    local interval=${HEALTH_CHECK_INTERVAL}
    
    while [ ${attempt} -le ${max_attempts} ]; do
        log_info "헬스 체크 시도 ${attempt}/${max_attempts}..."
        
        # HTTP 상태 코드 확인
        if curl -s -o /dev/null -w "%{http_code}" "${HEALTH_CHECK_URL}" | grep -q "200"; then
            log_success "헬스 체크 성공! 애플리케이션이 정상적으로 실행 중입니다."
            return 0
        fi
        
        if [ ${attempt} -lt ${max_attempts} ]; then
            log_info "${interval}초 후 재시도..."
            sleep ${interval}
        fi
        
        ((attempt++))
    done
    
    log_error "헬스 체크 실패. 애플리케이션이 정상적으로 시작되지 않았습니다."
    return 1
}

update_nginx_config() {
    log_info "🌐 Nginx 설정 업데이트 중..."
    
    # Nginx 설정 파일 존재 확인
    if [ -f "${NGINX_CONFIG}" ]; then
        # Nginx 설정 테스트
        if sudo nginx -t; then
            # Nginx 리로드
            sudo systemctl reload nginx
            log_success "Nginx 설정 업데이트 완료"
        else
            log_error "Nginx 설정 오류 발견"
            return 1
        fi
    else
        log_warning "Nginx 설정 파일이 없습니다: ${NGINX_CONFIG}"
    fi
}

cleanup_deployment() {
    log_info "🧹 배포 후 정리 작업 중..."
    
    # 임시 파일 정리
    find "${APP_DIR}" -name "*.pyc" -delete 2>/dev/null || true
    find "${APP_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # 로그 파일 로테이션 (100MB 이상인 경우)
    if [ -f "${LOG_FILE}" ] && [ $(stat -f%z "${LOG_FILE}" 2>/dev/null || stat -c%s "${LOG_FILE}") -gt 104857600 ]; then
        mv "${LOG_FILE}" "${LOG_FILE}.old"
        touch "${LOG_FILE}"
        log_info "로그 파일 로테이션 완료"
    fi
    
    log_success "정리 작업 완료"
}

generate_deployment_report() {
    log_info "📊 배포 보고서 생성 중..."
    
    local report_file="/tmp/deployment_report_$(date '+%Y%m%d_%H%M%S').txt"
    
    cat << EOF > "${report_file}"
=============================================================================
AMS 백엔드 배포 보고서
=============================================================================
배포 시간: $(date)
브랜치: ${BRANCH}
커밋: $(git -C "${APP_DIR}" rev-parse HEAD)
커밋 메시지: $(git -C "${APP_DIR}" log -1 --pretty=format:"%s")
배포 디렉토리: ${APP_DIR}
서비스 상태: $(systemctl is-active "${SERVICE_NAME}")
헬스 체크: $(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_CHECK_URL}" 2>/dev/null || echo "FAILED")

시스템 정보:
- 호스트명: $(hostname)
- 운영체제: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
- Python 버전: $(python3 --version)
- 디스크 사용량: $(df -h "${APP_DIR}" | awk 'NR==2 {print $5}')
- 메모리 사용량: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')

배포 성공!
=============================================================================
EOF
    
    log_success "배포 보고서 생성 완료: ${report_file}"
    cat "${report_file}"
}

# 메인 배포 프로세스
main() {
    log_info "==============================================================================="
    log_info "AMS 백엔드 자동 배포 시작"
    log_info "==============================================================================="
    
    # 1. 사전 요구사항 확인
    check_prerequisites
    
    # 2. 백업 생성
    create_backup
    
    # 3. 서비스 중지
    stop_services
    
    # 4. 코드 업데이트
    update_code
    
    # 5. 가상환경 설정
    setup_virtual_environment
    
    # 6. 의존성 설치
    install_dependencies
    
    # 7. 데이터베이스 마이그레이션
    run_database_migrations
    
    # 8. 정적 파일 수집
    collect_static_files
    
    # 9. 서비스 시작
    start_services
    
    # 10. 헬스 체크
    if ! health_check; then
        log_error "헬스 체크 실패. 롤백을 수행합니다."
        restore_from_backup
        exit 1
    fi
    
    # 11. Nginx 설정 업데이트
    update_nginx_config
    
    # 12. 정리 작업
    cleanup_deployment
    
    # 13. 배포 보고서 생성
    generate_deployment_report
    
    log_success "==============================================================================="
    log_success "🎉 백엔드 배포가 성공적으로 완료되었습니다!"
    log_success "==============================================================================="
}

# 스크립트 실행
main "$@"