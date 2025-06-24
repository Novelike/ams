#!/bin/bash

# =============================================================================
# 백엔드 롤백 스크립트
# =============================================================================

set -e  # 오류 발생 시 스크립트 중단

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
BACKUP_VERSION=${1:-"latest"}
APP_NAME="ams-backend"
APP_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/backups/${APP_NAME}"
SERVICE_NAME="ams-backend"
HEALTH_CHECK_URL="http://localhost:8000/api/registration/workflow"
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=10
LOG_FILE="/var/log/${APP_NAME}/rollback.log"

# 롤백 시작
log_info "🔄 백엔드 롤백 시작"
log_info "대상 백업: ${BACKUP_VERSION}"
log_info "애플리케이션 디렉토리: ${APP_DIR}"

# 로그 디렉토리 생성
mkdir -p "$(dirname "${LOG_FILE}")"

# 함수 정의
cleanup_on_error() {
    log_error "롤백 중 오류 발생. 긴급 복구를 시도합니다."
    
    # 서비스 상태 확인
    if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_warning "서비스가 중지되어 있습니다. 재시작을 시도합니다."
        sudo systemctl start "${SERVICE_NAME}" || true
    fi
    
    exit 1
}

# 오류 발생 시 정리 함수 실행
trap cleanup_on_error ERR

list_available_backups() {
    log_info "📋 사용 가능한 백업 목록:"
    
    if [ ! -d "${BACKUP_DIR}" ]; then
        log_error "백업 디렉토리가 존재하지 않습니다: ${BACKUP_DIR}"
        exit 1
    fi
    
    local backups=($(find "${BACKUP_DIR}" -type d -name "backup_*" | sort -r))
    
    if [ ${#backups[@]} -eq 0 ]; then
        log_error "사용 가능한 백업이 없습니다"
        exit 1
    fi
    
    log_info "발견된 백업:"
    for i in "${!backups[@]}"; do
        local backup_path="${backups[$i]}"
        local backup_name=$(basename "${backup_path}")
        local backup_date=$(echo "${backup_name}" | sed 's/backup_//' | sed 's/_/ /')
        local backup_size=$(du -sh "${backup_path}" 2>/dev/null | cut -f1 || echo "Unknown")
        
        # Git 정보 추출 (가능한 경우)
        local git_info=""
        if [ -d "${backup_path}/.git" ]; then
            local commit_hash=$(git -C "${backup_path}" rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "Unknown")
            local commit_msg=$(git -C "${backup_path}" log -1 --pretty=format:"%s" 2>/dev/null || echo "Unknown")
            git_info=" (${commit_hash}: ${commit_msg})"
        fi
        
        log_info "  ${i}: ${backup_name} - ${backup_date} (${backup_size})${git_info}"
    done
    
    echo "${backups[@]}"
}

select_backup() {
    local backup_version="$1"
    local available_backups=($(list_available_backups))
    
    if [ "${backup_version}" = "latest" ]; then
        # 최신 백업 선택
        SELECTED_BACKUP="${available_backups[0]}"
        log_info "최신 백업 선택: $(basename "${SELECTED_BACKUP}")"
    elif [ "${backup_version}" = "interactive" ]; then
        # 대화형 선택
        log_info "백업을 선택하세요 (0-$((${#available_backups[@]}-1))):"
        read -p "백업 번호: " backup_index
        
        if [[ "${backup_index}" =~ ^[0-9]+$ ]] && [ "${backup_index}" -lt ${#available_backups[@]} ]; then
            SELECTED_BACKUP="${available_backups[$backup_index]}"
            log_info "선택된 백업: $(basename "${SELECTED_BACKUP}")"
        else
            log_error "잘못된 백업 번호입니다"
            exit 1
        fi
    elif [[ "${backup_version}" =~ ^[0-9]+$ ]]; then
        # 숫자 인덱스로 선택
        if [ "${backup_version}" -lt ${#available_backups[@]} ]; then
            SELECTED_BACKUP="${available_backups[$backup_version]}"
            log_info "선택된 백업: $(basename "${SELECTED_BACKUP}")"
        else
            log_error "잘못된 백업 인덱스입니다: ${backup_version}"
            exit 1
        fi
    else
        # 백업 이름으로 선택
        local backup_path="${BACKUP_DIR}/backup_${backup_version}"
        if [ -d "${backup_path}" ]; then
            SELECTED_BACKUP="${backup_path}"
            log_info "선택된 백업: $(basename "${SELECTED_BACKUP}")"
        else
            log_error "백업을 찾을 수 없습니다: ${backup_version}"
            exit 1
        fi
    fi
    
    if [ ! -d "${SELECTED_BACKUP}" ]; then
        log_error "선택된 백업 디렉토리가 존재하지 않습니다: ${SELECTED_BACKUP}"
        exit 1
    fi
}

validate_backup() {
    log_info "🔍 백업 유효성 검사 중..."
    
    local backup_path="$1"
    
    # 필수 파일 확인
    local required_files=(
        "main.py"
        "requirements.txt"
        "app"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -e "${backup_path}/${file}" ]; then
            log_error "백업에 필수 파일이 없습니다: ${file}"
            return 1
        fi
    done
    
    # 백업 크기 확인
    local backup_size=$(du -s "${backup_path}" | awk '{print $1}')
    if [ ${backup_size} -lt 1000 ]; then  # 1MB 미만
        log_warning "백업 크기가 너무 작습니다: ${backup_size}KB"
        read -p "계속 진행하시겠습니까? (y/N): " confirm
        if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
            log_info "롤백이 취소되었습니다"
            exit 0
        fi
    fi
    
    log_success "백업 유효성 검사 통과"
}

create_current_backup() {
    log_info "📦 현재 상태 백업 생성 중..."
    
    if [ -d "${APP_DIR}" ]; then
        local emergency_backup="${BACKUP_DIR}/emergency_backup_$(date '+%Y%m%d_%H%M%S')"
        mkdir -p "$(dirname "${emergency_backup}")"
        
        cp -r "${APP_DIR}" "${emergency_backup}"
        log_success "긴급 백업 생성 완료: ${emergency_backup}"
        
        # 백업 정보 저장
        cat << EOF > "${emergency_backup}/backup_info.txt"
Backup Type: Emergency (before rollback)
Created: $(date)
Original App Dir: ${APP_DIR}
Rollback Target: $(basename "${SELECTED_BACKUP}")
EOF
    else
        log_warning "현재 애플리케이션 디렉토리가 없습니다: ${APP_DIR}"
    fi
}

stop_services() {
    log_info "🛑 서비스 중지 중..."
    
    # 현재 서비스 상태 저장
    local service_was_active=false
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        service_was_active=true
        log_info "서비스가 실행 중입니다. 중지합니다."
        sudo systemctl stop "${SERVICE_NAME}"
        log_success "서비스 중지 완료"
    else
        log_info "서비스가 이미 중지되어 있습니다"
    fi
    
    # 프로세스 강제 종료
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        log_warning "실행 중인 uvicorn 프로세스 발견. 강제 종료합니다."
        pkill -f "uvicorn.*main:app" || true
        sleep 3
    fi
    
    # 포트 확인
    if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        log_warning "포트 8000이 여전히 사용 중입니다. 잠시 대기합니다."
        sleep 5
    fi
    
    echo "${service_was_active}"
}

restore_from_backup() {
    log_info "🔄 백업에서 복원 중..."
    
    local backup_path="$1"
    
    # 현재 디렉토리 제거
    if [ -d "${APP_DIR}" ]; then
        log_info "현재 애플리케이션 디렉토리 제거 중..."
        rm -rf "${APP_DIR}"
    fi
    
    # 백업에서 복원
    log_info "백업에서 파일 복사 중..."
    cp -r "${backup_path}" "${APP_DIR}"
    
    # 권한 설정
    chown -R ubuntu:ubuntu "${APP_DIR}" 2>/dev/null || true
    chmod -R 755 "${APP_DIR}" 2>/dev/null || true
    
    log_success "백업 복원 완료"
}

setup_virtual_environment() {
    log_info "🐍 가상환경 설정 중..."
    
    local venv_dir="${APP_DIR}/venv"
    
    # 기존 가상환경 제거 및 재생성
    if [ -d "${venv_dir}" ]; then
        rm -rf "${venv_dir}"
    fi
    
    # 새 가상환경 생성
    cd "${APP_DIR}"
    python3 -m venv "${venv_dir}"
    
    # 가상환경 활성화
    source "${venv_dir}/bin/activate"
    
    # pip 업그레이드
    pip install --upgrade pip
    
    # 의존성 설치
    if [ -f "requirements.txt" ]; then
        log_info "의존성 설치 중..."
        pip install -r requirements.txt
        log_success "의존성 설치 완료"
    else
        log_warning "requirements.txt 파일이 없습니다"
    fi
}

start_services() {
    log_info "🚀 서비스 시작 중..."
    
    # systemd 서비스 파일 확인
    if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
        log_warning "systemd 서비스 파일이 없습니다. 생성합니다."
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
    
    local venv_dir="${APP_DIR}/venv"
    
    cat << EOF | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null
[Unit]
Description=AMS Backend Service (Rollback)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${APP_DIR}
Environment=PATH=${venv_dir}/bin
ExecStart=${venv_dir}/bin/uvicorn main:app --host 0.0.0.0 --port 8000
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
        local response=$(curl -s -w "%{http_code}" --max-time 10 "${HEALTH_CHECK_URL}" 2>/dev/null || echo "000")
        
        if [ "${response: -3}" = "200" ]; then
            log_success "헬스 체크 성공! 롤백이 완료되었습니다."
            return 0
        fi
        
        if [ ${attempt} -lt ${max_attempts} ]; then
            log_info "${interval}초 후 재시도..."
            sleep ${interval}
        fi
        
        ((attempt++))
    done
    
    log_error "헬스 체크 실패. 롤백된 애플리케이션이 정상적으로 시작되지 않았습니다."
    return 1
}

verify_rollback() {
    log_info "✅ 롤백 검증 중..."
    
    # 서비스 상태 확인
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_success "서비스가 정상적으로 실행 중입니다"
    else
        log_error "서비스가 실행되지 않고 있습니다"
        return 1
    fi
    
    # 프로세스 확인
    if pgrep -f "uvicorn.*main:app" > /dev/null; then
        log_success "애플리케이션 프로세스가 실행 중입니다"
    else
        log_error "애플리케이션 프로세스가 실행되지 않고 있습니다"
        return 1
    fi
    
    # 포트 확인
    if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        log_success "포트 8000이 정상적으로 열려 있습니다"
    else
        log_error "포트 8000이 열려 있지 않습니다"
        return 1
    fi
    
    # 버전 정보 확인
    local backup_info="${APP_DIR}/backup_info.txt"
    if [ -f "${backup_info}" ]; then
        log_info "복원된 백업 정보:"
        cat "${backup_info}" | while read line; do
            log_info "  ${line}"
        done
    fi
    
    # Git 정보 확인 (가능한 경우)
    if [ -d "${APP_DIR}/.git" ]; then
        local current_commit=$(git -C "${APP_DIR}" rev-parse HEAD 2>/dev/null | cut -c1-8 || echo "Unknown")
        local commit_message=$(git -C "${APP_DIR}" log -1 --pretty=format:"%s" 2>/dev/null || echo "Unknown")
        log_info "현재 커밋: ${current_commit} - ${commit_message}"
    fi
    
    log_success "롤백 검증 완료"
}

generate_rollback_report() {
    log_info "📊 롤백 보고서 생성 중..."
    
    local report_file="/tmp/rollback_report_$(date '+%Y%m%d_%H%M%S').txt"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat << EOF > "${report_file}"
=============================================================================
AMS 백엔드 롤백 보고서
=============================================================================
롤백 시간: ${timestamp}
대상 백업: $(basename "${SELECTED_BACKUP}")
애플리케이션 디렉토리: ${APP_DIR}
서비스 상태: $(systemctl is-active "${SERVICE_NAME}")
헬스 체크: $(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_CHECK_URL}" 2>/dev/null || echo "FAILED")

백업 정보:
- 백업 경로: ${SELECTED_BACKUP}
- 백업 크기: $(du -sh "${SELECTED_BACKUP}" | cut -f1)
- 백업 생성 시간: $(stat -c %y "${SELECTED_BACKUP}" 2>/dev/null || echo "Unknown")

시스템 정보:
- 호스트명: $(hostname)
- 운영체제: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
- Python 버전: $(python3 --version)
- 디스크 사용량: $(df -h "${APP_DIR}" | awk 'NR==2 {print $5}')
- 메모리 사용량: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}')

롤백 성공!
=============================================================================
EOF
    
    log_success "롤백 보고서 생성 완료: ${report_file}"
    cat "${report_file}"
}

show_usage() {
    cat << EOF
사용법: $0 [BACKUP_VERSION]

BACKUP_VERSION 옵션:
  latest          - 최신 백업 사용 (기본값)
  interactive     - 대화형으로 백업 선택
  [숫자]          - 백업 인덱스로 선택 (0=최신)
  [백업명]        - 특정 백업 이름으로 선택

예시:
  $0                    # 최신 백업으로 롤백
  $0 latest             # 최신 백업으로 롤백
  $0 interactive        # 대화형 백업 선택
  $0 0                  # 첫 번째 (최신) 백업으로 롤백
  $0 20241224_143022    # 특정 백업으로 롤백

EOF
}

# 메인 롤백 프로세스
main() {
    # 도움말 표시
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    log_info "==============================================================================="
    log_info "🔄 AMS 백엔드 롤백 시작"
    log_info "==============================================================================="
    
    # 1. 백업 선택
    select_backup "${BACKUP_VERSION}"
    
    # 2. 백업 유효성 검사
    validate_backup "${SELECTED_BACKUP}"
    
    # 3. 현재 상태 백업
    create_current_backup
    
    # 4. 서비스 중지
    local service_was_active=$(stop_services)
    
    # 5. 백업에서 복원
    restore_from_backup "${SELECTED_BACKUP}"
    
    # 6. 가상환경 설정
    setup_virtual_environment
    
    # 7. 서비스 시작
    start_services
    
    # 8. 헬스 체크
    if ! health_check; then
        log_error "헬스 체크 실패. 롤백에 문제가 있습니다."
        
        # 서비스가 원래 실행 중이었다면 재시작 시도
        if [ "${service_was_active}" = "true" ]; then
            log_info "원래 서비스 상태로 복구를 시도합니다."
            sudo systemctl restart "${SERVICE_NAME}" || true
        fi
        
        exit 1
    fi
    
    # 9. 롤백 검증
    verify_rollback
    
    # 10. 보고서 생성
    generate_rollback_report
    
    log_success "==============================================================================="
    log_success "🎉 백엔드 롤백이 성공적으로 완료되었습니다!"
    log_success "==============================================================================="
}

# 스크립트 실행
main "$@"