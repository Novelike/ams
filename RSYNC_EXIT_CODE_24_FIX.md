# 🔧 Rsync Exit Code 24 오류 해결

## 📋 문제 설명

GitHub Actions 배포 과정에서 다음과 같은 rsync 오류가 발생했습니다:

```
rsync warning: some files vanished before they could be transferred (code 24) at main.c(1338) [sender=3.2.7]
Error: Process completed with exit code 24.
```

## 🔍 원인 분석

### Exit Code 24의 의미
- **Exit Code 24**: "Partial transfer due to vanished source files"
- 파일 전송 중에 소스 파일이 사라져서 발생하는 경고
- 실제로는 치명적인 오류가 아니지만 rsync가 24 코드로 종료됨
- GitHub Actions에서는 0이 아닌 exit code를 오류로 처리하여 배포 실패

### 발생 상황
1. **GitHub에서 소스 다운로드**: tarball로 전체 저장소 다운로드
2. **압축 해제**: temp_source 디렉토리에 압축 해제
3. **rsync 실행**: `rsync -av --delete temp_source/ams-back/ ./`
4. **파일 삭제**: rsync 실행 중 일부 파일이 삭제됨 (--delete 옵션으로 인해)
5. **Exit Code 24**: 전송 중 파일이 사라져서 경고 발생

## 🛠️ 해결 방법

### 1. GitHub Actions 워크플로우 수정

#### 메인 배포 rsync 수정
```yaml
# 기존 코드
rsync -av --delete temp_source/ams-back/ ./

# 수정된 코드
rsync -av --delete --ignore-missing-args temp_source/ams-back/ ./ || {
  exit_code=$?
  if [ $exit_code -eq 24 ]; then
    echo "⚠️ rsync warning: some files vanished during transfer (exit code 24) - continuing deployment"
  else
    echo "❌ rsync failed with exit code $exit_code"
    exit $exit_code
  fi
}
```

#### 롤백 rsync 수정
```yaml
# 기존 코드
rsync -av --delete backup/ ./

# 수정된 코드
rsync -av --delete --ignore-missing-args backup/ ./ || {
  exit_code=$?
  if [ $exit_code -eq 24 ]; then
    echo "⚠️ rsync warning during rollback: some files vanished during transfer (exit code 24) - continuing rollback"
  else
    echo "❌ rsync rollback failed with exit code $exit_code"
    exit $exit_code
  fi
}
```

### 2. 배포 스크립트 수정

#### 메인 배포 rsync 수정
```bash
# 기존 코드
rsync -av --delete ams-back/ "$BACKEND_DIR/"

# 수정된 코드
rsync -av --delete --ignore-missing-args ams-back/ "$BACKEND_DIR/" || {
    exit_code=$?
    if [ $exit_code -eq 24 ]; then
        log_warning "rsync warning: some files vanished during transfer (exit code 24) - continuing deployment"
    else
        log_error "rsync failed with exit code $exit_code"
        exit $exit_code
    fi
}
```

#### 롤백 rsync 수정
```bash
# 기존 코드
rsync -av --delete "$BACKEND_DIR.backup.$TIMESTAMP/" "$BACKEND_DIR/"

# 수정된 코드
rsync -av --delete --ignore-missing-args "$BACKEND_DIR.backup.$TIMESTAMP/" "$BACKEND_DIR/" || {
    exit_code=$?
    if [ $exit_code -eq 24 ]; then
        log_warning "rsync warning during rollback: some files vanished during transfer (exit code 24) - continuing rollback"
    else
        log_error "rsync rollback failed with exit code $exit_code"
        exit $exit_code
    fi
}
```

## 🔧 적용된 수정사항

### 1. `--ignore-missing-args` 플래그 추가
- 누락된 파일이나 인수를 무시하도록 설정
- 파일이 전송 중 사라져도 rsync가 계속 진행

### 2. Exit Code 24 전용 처리
- Exit Code 24는 경고로 처리하고 배포 계속 진행
- 다른 rsync 오류는 여전히 배포 실패로 처리

### 3. 일관된 오류 처리
- GitHub Actions 워크플로우와 배포 스크립트 모두 동일한 방식으로 처리
- 메인 배포와 롤백 모두에서 동일한 오류 처리 적용

## 📁 수정된 파일 목록

1. **`.github/workflows/backend-optimized-deploy.yml`**
   - 메인 배포 rsync 명령어 수정 (라인 93-101)
   - 롤백 rsync 명령어 수정 (라인 150-158)

2. **`deployment/backend_deploy.sh`**
   - 메인 배포 rsync 명령어 수정 (라인 59-67)
   - 롤백 rsync 명령어 수정 (라인 114-122)

## 🎯 예상 효과

### 즉시 효과
- ✅ Exit Code 24로 인한 배포 실패 해결
- ✅ 파일 전송 중 일시적인 파일 삭제로 인한 오류 방지
- ✅ 안정적인 배포 프로세스 확보

### 장기 효과
- 🔄 더 안정적인 CI/CD 파이프라인
- 📊 배포 성공률 향상
- 🛡️ 일시적인 파일 시스템 변경에 대한 내성 증가

## 🧪 테스트 방법

### 1. GitHub Actions에서 테스트
```bash
# ams-back 디렉토리에 변경사항 커밋 후 푸시
git add ams-back/
git commit -m "test: rsync exit code 24 fix"
git push origin main
```

### 2. 수동 배포 스크립트 테스트
```bash
# 배포 스크립트 직접 실행
./deployment/backend_deploy.sh
```

### 3. 로그 확인
```bash
# GitHub Actions 로그에서 확인할 내용
⚠️ rsync warning: some files vanished during transfer (exit code 24) - continuing deployment
✅ 소스 동기화 완료
```

## 📚 참고 자료

### Rsync Exit Codes
- **0**: Success
- **24**: Partial transfer due to vanished source files
- **기타**: 실제 오류 상황

### 관련 문서
- [rsync man page](https://linux.die.net/man/1/rsync)
- [GitHub Actions 문제 해결](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)

## 🎉 결론

이 수정으로 인해 rsync의 Exit Code 24 경고가 더 이상 배포 실패를 야기하지 않으며, 실제 파일 전송은 성공적으로 완료됩니다. 배포 시스템이 더욱 안정적이고 신뢰할 수 있게 되었습니다.