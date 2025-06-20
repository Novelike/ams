@echo off
echo === 백엔드 API 서버 연결 확인 ===
curl -s -o nul -w "%%{http_code}" http://prod_server:8000/api/health > temp.txt
set /p STATUS=<temp.txt
del temp.txt

if "%STATUS%" == "200" (
    echo 백엔드 API 서버 연결 성공! (상태 코드: %STATUS%)
) else (
    echo 백엔드 API 서버 연결 실패! (상태 코드: %STATUS%)
    echo 로컬 개발 환경에서는 localhost:8000을 사용하고, 서버 배포 시에는 prod_server:8000을 사용합니다.
    echo 서버 연결 상태를 확인하고 다시 시도하세요.
    pause
    exit /b 1
)

echo === React 애플리케이션 빌드 시작 ===
call npm run build

if %ERRORLEVEL% neq 0 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo === PEM 키 파일 권한 확인 ===
icacls "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem"

echo === 빌드 파일 Bastion 서버로 전송 ===
scp -o StrictHostKeyChecking=no -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" -r dist/* ubuntu@210.109.82.8:/home/ubuntu/ams-build/

if %ERRORLEVEL% neq 0 (
    echo 파일 전송 실패!
    pause
    exit /b 1
)

echo === Bastion 서버에서 배포 스크립트 실행 ===
ssh -o StrictHostKeyChecking=no -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.82.8 "bash /home/ubuntu/deploy-to-front.sh"

if %ERRORLEVEL% neq 0 (
    echo 배포 스크립트 실행 실패!
    pause
    exit /b 1
)

echo === 배포 완료 ===
pause
