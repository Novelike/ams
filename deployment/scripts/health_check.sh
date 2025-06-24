#!/bin/bash

# =============================================================================
# 백엔드 헬스 체크 스크립트
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
APP_NAME="ams-backend"
SERVICE_NAME="ams-backend"
BASE_URL="http://localhost:8000"
HEALTH_ENDPOINTS=(
    "/api/registration/workflow"
    "/api/registration/search/stats"
    "/api/registration/gpu-ocr/stats"
    "/api/registration/gpu-ocr/scheduler/status"
)
TIMEOUT=10
MAX_RETRIES=3
CRITICAL_MEMORY_THRESHOLD=90
CRITICAL_DISK_THRESHOLD=90
CRITICAL_CPU_THRESHOLD=95

# 헬스 체크 결과 저장
HEALTH_RESULTS=()
OVERALL_STATUS="HEALTHY"

# 함수 정의
check_service_status() {
    log_info "🔍 서비스 상태 확인 중..."
    
    local status_result="PASS"
    
    # systemd 서비스 상태 확인
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_success "systemd 서비스가 실행 중입니다"
        
        # 서비스 상세 정보
        local service_info=$(systemctl status "${SERVICE_NAME}" --no-pager -l)
        local start_time=$(systemctl show "${SERVICE_NAME}" --property=ActiveEnterTimestamp --value)
        log_info "서비스 시작 시간: ${start_time}"
        
    else
        log_error "systemd 서비스가 실행되지 않고 있습니다"
        status_result="FAIL"
        OVERALL_STATUS="UNHEALTHY"
    fi
    
    # 프로세스 확인
    local process_count=$(pgrep -f "uvicorn.*main:app" | wc -l)
    if [ "${process_count}" -gt 0 ]; then
        log_success "uvicorn 프로세스 ${process_count}개가 실행 중입니다"
        
        # 프로세스 정보 출력
        log_info "실행 중인 프로세스:"
        ps aux | grep "uvicorn.*main:app" | grep -v grep | while read line; do
            log_info "  ${line}"
        done
    else
        log_error "uvicorn 프로세스가 실행되지 않고 있습니다"
        status_result="FAIL"
        OVERALL_STATUS="UNHEALTHY"
    fi
    
    # 포트 확인
    if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        log_success "포트 8000이 열려 있습니다"
    else
        log_error "포트 8000이 열려 있지 않습니다"
        status_result="FAIL"
        OVERALL_STATUS="UNHEALTHY"
    fi
    
    HEALTH_RESULTS+=("Service Status: ${status_result}")
}

check_http_endpoints() {
    log_info "🌐 HTTP 엔드포인트 확인 중..."
    
    local endpoint_results=()
    local failed_endpoints=0
    
    for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
        local url="${BASE_URL}${endpoint}"
        local attempt=1
        local success=false
        
        log_info "엔드포인트 테스트: ${endpoint}"
        
        while [ ${attempt} -le ${MAX_RETRIES} ] && [ "${success}" = false ]; do
            # HTTP 요청 실행
            local response=$(curl -s -w "%{http_code}|%{time_total}|%{size_download}" \
                               --max-time ${TIMEOUT} \
                               "${url}" 2>/dev/null || echo "000|0|0")
            
            local http_code=$(echo "${response}" | cut -d'|' -f1)
            local response_time=$(echo "${response}" | cut -d'|' -f2)
            local response_size=$(echo "${response}" | cut -d'|' -f3)
            
            if [ "${http_code}" = "200" ]; then
                log_success "  ✓ ${endpoint} - HTTP ${http_code} (${response_time}s, ${response_size} bytes)"
                endpoint_results+=("${endpoint}: PASS (${response_time}s)")
                success=true
            else
                if [ ${attempt} -lt ${MAX_RETRIES} ]; then
                    log_warning "  ⚠ ${endpoint} - HTTP ${http_code} (시도 ${attempt}/${MAX_RETRIES})"
                    sleep 2
                else
                    log_error "  ✗ ${endpoint} - HTTP ${http_code} (최종 실패)"
                    endpoint_results+=("${endpoint}: FAIL (HTTP ${http_code})")
                    ((failed_endpoints++))
                fi
            fi
            
            ((attempt++))
        done
    done
    
    # 결과 평가
    if [ ${failed_endpoints} -eq 0 ]; then
        log_success "모든 HTTP 엔드포인트가 정상입니다"
        HEALTH_RESULTS+=("HTTP Endpoints: PASS")
    elif [ ${failed_endpoints} -lt ${#HEALTH_ENDPOINTS[@]} ]; then
        log_warning "일부 HTTP 엔드포인트에 문제가 있습니다 (${failed_endpoints}/${#HEALTH_ENDPOINTS[@]} 실패)"
        HEALTH_RESULTS+=("HTTP Endpoints: WARNING")
        if [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
            OVERALL_STATUS="WARNING"
        fi
    else
        log_error "모든 HTTP 엔드포인트가 실패했습니다"
        HEALTH_RESULTS+=("HTTP Endpoints: FAIL")
        OVERALL_STATUS="UNHEALTHY"
    fi
    
    # 상세 결과 저장
    for result in "${endpoint_results[@]}"; do
        HEALTH_RESULTS+=("  ${result}")
    done
}

check_database_connectivity() {
    log_info "🗄️ 데이터베이스 연결 확인 중..."
    
    # 데이터베이스 연결 테스트 (애플리케이션을 통해)
    local db_test_url="${BASE_URL}/api/registration/workflow"
    local response=$(curl -s -w "%{http_code}" --max-time ${TIMEOUT} "${db_test_url}" 2>/dev/null || echo "000")
    
    if [ "${response: -3}" = "200" ]; then
        log_success "데이터베이스 연결이 정상입니다"
        HEALTH_RESULTS+=("Database: PASS")
    else
        log_error "데이터베이스 연결에 문제가 있습니다"
        HEALTH_RESULTS+=("Database: FAIL")
        OVERALL_STATUS="UNHEALTHY"
    fi
}

check_system_resources() {
    log_info "💻 시스템 리소스 확인 중..."
    
    # CPU 사용률 확인
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    local cpu_numeric=$(echo "${cpu_usage}" | sed 's/%//')
    
    if (( $(echo "${cpu_numeric} < ${CRITICAL_CPU_THRESHOLD}" | bc -l) )); then
        log_success "CPU 사용률: ${cpu_usage} (정상)"
        HEALTH_RESULTS+=("CPU Usage: PASS (${cpu_usage})")
    else
        log_warning "CPU 사용률이 높습니다: ${cpu_usage}"
        HEALTH_RESULTS+=("CPU Usage: WARNING (${cpu_usage})")
        if [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
            OVERALL_STATUS="WARNING"
        fi
    fi
    
    # 메모리 사용률 확인
    local memory_info=$(free | grep Mem)
    local total_mem=$(echo ${memory_info} | awk '{print $2}')
    local used_mem=$(echo ${memory_info} | awk '{print $3}')
    local memory_usage=$(( used_mem * 100 / total_mem ))
    
    if [ ${memory_usage} -lt ${CRITICAL_MEMORY_THRESHOLD} ]; then
        log_success "메모리 사용률: ${memory_usage}% (정상)"
        HEALTH_RESULTS+=("Memory Usage: PASS (${memory_usage}%)")
    else
        log_warning "메모리 사용률이 높습니다: ${memory_usage}%"
        HEALTH_RESULTS+=("Memory Usage: WARNING (${memory_usage}%)")
        if [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
            OVERALL_STATUS="WARNING"
        fi
    fi
    
    # 디스크 사용률 확인
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ ${disk_usage} -lt ${CRITICAL_DISK_THRESHOLD} ]; then
        log_success "디스크 사용률: ${disk_usage}% (정상)"
        HEALTH_RESULTS+=("Disk Usage: PASS (${disk_usage}%)")
    else
        log_warning "디스크 사용률이 높습니다: ${disk_usage}%"
        HEALTH_RESULTS+=("Disk Usage: WARNING (${disk_usage}%)")
        if [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
            OVERALL_STATUS="WARNING"
        fi
    fi
    
    # 로드 평균 확인
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local load_threshold=$(echo "${cpu_cores} * 2" | bc)
    
    if (( $(echo "${load_avg} < ${load_threshold}" | bc -l) )); then
        log_success "로드 평균: ${load_avg} (정상, CPU 코어: ${cpu_cores})"
        HEALTH_RESULTS+=("Load Average: PASS (${load_avg})")
    else
        log_warning "로드 평균이 높습니다: ${load_avg} (CPU 코어: ${cpu_cores})"
        HEALTH_RESULTS+=("Load Average: WARNING (${load_avg})")
        if [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
            OVERALL_STATUS="WARNING"
        fi
    fi
}

check_log_files() {
    log_info "📋 로그 파일 확인 중..."
    
    local log_dirs=(
        "/var/log/${APP_NAME}"
        "/opt/${APP_NAME}/logs"
        "deployment/logs"
    )
    
    local log_status="PASS"
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "${log_dir}" ]; then
            log_info "로그 디렉토리 확인: ${log_dir}"
            
            # 최근 에러 로그 확인
            local error_count=$(find "${log_dir}" -name "*.log" -mtime -1 -exec grep -i "error\|exception\|critical" {} \; 2>/dev/null | wc -l)
            
            if [ ${error_count} -eq 0 ]; then
                log_success "  최근 24시간 내 에러 로그 없음"
            elif [ ${error_count} -lt 10 ]; then
                log_warning "  최근 24시간 내 에러 로그 ${error_count}개 발견"
                log_status="WARNING"
            else
                log_error "  최근 24시간 내 에러 로그 ${error_count}개 발견 (많음)"
                log_status="FAIL"
            fi
            
            # 로그 파일 크기 확인
            local large_logs=$(find "${log_dir}" -name "*.log" -size +100M 2>/dev/null)
            if [ -n "${large_logs}" ]; then
                log_warning "  큰 로그 파일 발견:"
                echo "${large_logs}" | while read log_file; do
                    local file_size=$(du -h "${log_file}" | cut -f1)
                    log_warning "    ${log_file} (${file_size})"
                done
            fi
        fi
    done
    
    HEALTH_RESULTS+=("Log Files: ${log_status}")
    
    if [ "${log_status}" = "FAIL" ]; then
        OVERALL_STATUS="UNHEALTHY"
    elif [ "${log_status}" = "WARNING" ] && [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
        OVERALL_STATUS="WARNING"
    fi
}

check_external_dependencies() {
    log_info "🔗 외부 의존성 확인 중..."
    
    local deps_status="PASS"
    
    # 인터넷 연결 확인
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "인터넷 연결 정상"
    else
        log_warning "인터넷 연결에 문제가 있을 수 있습니다"
        deps_status="WARNING"
    fi
    
    # DNS 확인
    if nslookup google.com >/dev/null 2>&1; then
        log_success "DNS 해석 정상"
    else
        log_warning "DNS 해석에 문제가 있을 수 있습니다"
        deps_status="WARNING"
    fi
    
    HEALTH_RESULTS+=("External Dependencies: ${deps_status}")
    
    if [ "${deps_status}" = "WARNING" ] && [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
        OVERALL_STATUS="WARNING"
    fi
}

check_security() {
    log_info "🔒 보안 상태 확인 중..."
    
    local security_status="PASS"
    
    # 파일 권한 확인
    local app_dir="/opt/${APP_NAME}"
    if [ -d "${app_dir}" ]; then
        local world_writable=$(find "${app_dir}" -type f -perm -002 2>/dev/null | wc -l)
        if [ ${world_writable} -eq 0 ]; then
            log_success "파일 권한 정상"
        else
            log_warning "월드 쓰기 가능한 파일 ${world_writable}개 발견"
            security_status="WARNING"
        fi
    fi
    
    # SSH 키 권한 확인
    local ssh_key="/home/ubuntu/.ssh/authorized_keys"
    if [ -f "${ssh_key}" ]; then
        local key_perms=$(stat -c "%a" "${ssh_key}")
        if [ "${key_perms}" = "600" ] || [ "${key_perms}" = "644" ]; then
            log_success "SSH 키 권한 정상"
        else
            log_warning "SSH 키 권한이 안전하지 않습니다: ${key_perms}"
            security_status="WARNING"
        fi
    fi
    
    HEALTH_RESULTS+=("Security: ${security_status}")
    
    if [ "${security_status}" = "WARNING" ] && [ "${OVERALL_STATUS}" = "HEALTHY" ]; then
        OVERALL_STATUS="WARNING"
    fi
}

generate_health_report() {
    log_info "📊 헬스 체크 보고서 생성 중..."
    
    local report_file="/tmp/health_check_report_$(date '+%Y%m%d_%H%M%S').txt"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat << EOF > "${report_file}"
=============================================================================
AMS 백엔드 헬스 체크 보고서
=============================================================================
검사 시간: ${timestamp}
전체 상태: ${OVERALL_STATUS}
호스트명: $(hostname)
운영체제: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")

상세 검사 결과:
EOF
    
    for result in "${HEALTH_RESULTS[@]}"; do
        echo "${result}" >> "${report_file}"
    done
    
    cat << EOF >> "${report_file}"

시스템 정보:
- 업타임: $(uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
- 로드 평균: $(uptime | awk -F'load average:' '{print $2}')
- 메모리: $(free -h | awk 'NR==2{printf "%s/%s (%.1f%%)", $3,$2,$3*100/$2}')
- 디스크: $(df -h / | awk 'NR==2{printf "%s/%s (%s)", $3,$2,$5}')
- 프로세스 수: $(ps aux | wc -l)

네트워크 정보:
- 활성 연결: $(netstat -an | grep ESTABLISHED | wc -l)
- 리스닝 포트: $(netstat -tlnp | grep LISTEN | wc -l)

=============================================================================
EOF
    
    log_success "헬스 체크 보고서 생성 완료: ${report_file}"
    
    # 보고서 출력
    cat "${report_file}"
    
    return "${report_file}"
}

send_alert_if_needed() {
    local status="$1"
    
    if [ "${status}" = "UNHEALTHY" ]; then
        log_error "🚨 시스템이 비정상 상태입니다. 알림을 발송합니다."
        
        # 여기에 알림 로직 추가 (이메일, Slack, Discord 등)
        # 예: send_slack_alert "AMS Backend is UNHEALTHY"
        # 예: send_email_alert "admin@company.com" "AMS Backend Health Alert"
        
    elif [ "${status}" = "WARNING" ]; then
        log_warning "⚠️ 시스템에 경고 사항이 있습니다."
        
        # 경고 알림 (선택적)
        # 예: send_slack_warning "AMS Backend has warnings"
    fi
}

# 메인 헬스 체크 프로세스
main() {
    log_info "==============================================================================="
    log_info "🏥 AMS 백엔드 헬스 체크 시작"
    log_info "==============================================================================="
    
    # 1. 서비스 상태 확인
    check_service_status
    
    # 2. HTTP 엔드포인트 확인
    check_http_endpoints
    
    # 3. 데이터베이스 연결 확인
    check_database_connectivity
    
    # 4. 시스템 리소스 확인
    check_system_resources
    
    # 5. 로그 파일 확인
    check_log_files
    
    # 6. 외부 의존성 확인
    check_external_dependencies
    
    # 7. 보안 상태 확인
    check_security
    
    # 8. 보고서 생성
    generate_health_report
    
    # 9. 알림 발송 (필요한 경우)
    send_alert_if_needed "${OVERALL_STATUS}"
    
    log_info "==============================================================================="
    
    # 최종 상태에 따른 종료 코드
    case "${OVERALL_STATUS}" in
        "HEALTHY")
            log_success "✅ 전체 시스템 상태: 정상"
            exit 0
            ;;
        "WARNING")
            log_warning "⚠️ 전체 시스템 상태: 경고"
            exit 1
            ;;
        "UNHEALTHY")
            log_error "❌ 전체 시스템 상태: 비정상"
            exit 2
            ;;
        *)
            log_error "❓ 전체 시스템 상태: 알 수 없음"
            exit 3
            ;;
    esac
}

# 스크립트 실행
main "$@"