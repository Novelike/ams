# 프론트엔드 배포 가이드

## 서버 구성 정보

### 서버 아키텍처
- **Bastion 서버**: 공개 IP(210.109.54.75)를 가진 서버로, 외부에서 접근 가능하며 Nginx와 SSL이 이미 구성되어 있음
- **Front 서버**: 비공개 IP(10.0.0.63)를 가진 서버로, React 애플리케이션이 실행될 서버

```
[사용자] <--HTTPS--> [Bastion 서버(210.109.54.75)] <--HTTP--> [Front 서버(10.0.0.63)]
```

### SSH 접속 정보
- **SSH 키 위치**: `D:\CLOUD\KakaoCloud\key\kjh-bastion.pem`
- **Bastion 서버 접속**: `ssh -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75`
- **Front 서버 접속**: Bastion 서버를 통해 접속
  ```bash
  # Bastion 서버에 접속 후
  ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63
  ```

## 배포 준비

### 1. SSH 키 복사
Bastion 서버에 SSH 키를 복사하여 Front 서버에 접속할 수 있도록 설정합니다.

```bash
# 로컬에서 Bastion 서버로 SSH 키 복사
scp -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75:/home/ubuntu/
```

### 2. Front 서버 환경 설정
Front 서버에 Node.js와 필요한 패키지를 설치합니다.

```bash
# Bastion 서버에 접속
ssh -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75

# Front 서버에 접속
ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63

# Node.js 설치 (Front 서버)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# PM2 설치 (프로세스 관리자)
sudo npm install -g pm2

# 애플리케이션 디렉토리 생성
mkdir -p /home/ubuntu/ams
```

## 배포 스크립트

### 1. 로컬 빌드 스크립트 (build-and-deploy.bat)
로컬 환경에서 React 애플리케이션을 빌드하고 Bastion 서버로 전송하는 스크립트입니다.

```batch
@echo off
echo === React 애플리케이션 빌드 시작 ===
call npm run build

echo === 빌드 파일 Bastion 서버로 전송 ===
scp -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" -r dist/* ubuntu@210.109.54.75:/home/ubuntu/ams-build/

echo === Bastion 서버에서 배포 스크립트 실행 ===
ssh -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75 "bash /home/ubuntu/deploy-to-front.sh"

echo === 배포 완료 ===
```

### 2. Bastion 서버 배포 스크립트 (deploy-to-front.sh)
Bastion 서버에서 Front 서버로 빌드 파일을 전송하고 애플리케이션을 재시작하는 스크립트입니다.

```bash
#!/bin/bash
echo "=== Front 서버로 빌드 파일 전송 ==="
ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63 "mkdir -p /home/ubuntu/ams/dist"
scp -i /home/ubuntu/kjh-bastion.pem -r /home/ubuntu/ams-build/* ubuntu@10.0.0.63:/home/ubuntu/ams/dist/

echo "=== Front 서버에서 애플리케이션 재시작 ==="
ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63 "cd /home/ubuntu/ams && pm2 restart ams || pm2 start /home/ubuntu/ams/serve.js --name ams"

echo "=== 배포 완료 ==="
```

### 3. Front 서버 서비스 스크립트 (serve.js)
Front 서버에서 React 애플리케이션을 서비스하는 Node.js 스크립트입니다.

```javascript
const express = require('express');
const path = require('path');
const app = express();
const PORT = 3000;

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'dist')));

// 모든 요청을 index.html로 라우팅 (SPA를 위한 설정)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다.`);
});
```

## Nginx 설정 (Bastion 서버)

Bastion 서버의 Nginx 설정을 수정하여 Front 서버로 요청을 프록시합니다.

```bash
# Bastion 서버에 접속
ssh -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75

# Nginx 설정 파일 편집
sudo nano /etc/nginx/sites-available/default
```

다음과 같이 Nginx 설정을 수정합니다:

```nginx
server {
    listen 80;
    server_name _;

    # HTTP를 HTTPS로 리다이렉트
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    # SSL 인증서 설정 (이미 구성되어 있음)
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    # Front 서버로 프록시
    location / {
        proxy_pass http://10.0.0.63:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

설정을 저장하고 Nginx를 재시작합니다:

```bash
sudo nginx -t  # 설정 문법 검사
sudo systemctl restart nginx
```

## 초기 설정 및 배포 절차

### 1. 초기 설정

1. Bastion 서버에 필요한 디렉토리 생성:
   ```bash
   ssh -i "D:\CLOUD\KakaoCloud\key\kjh-bastion.pem" ubuntu@210.109.54.75
   mkdir -p /home/ubuntu/ams-build
   ```

2. Bastion 서버에 배포 스크립트 생성:
   ```bash
   nano /home/ubuntu/deploy-to-front.sh
   # 위의 'Bastion 서버 배포 스크립트' 내용 붙여넣기
   chmod +x /home/ubuntu/deploy-to-front.sh
   ```

3. Front 서버에 서비스 스크립트 생성:
   ```bash
   ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63
   mkdir -p /home/ubuntu/ams
   nano /home/ubuntu/ams/serve.js
   # 위의 'Front 서버 서비스 스크립트' 내용 붙여넣기

   # Express 설치
   cd /home/ubuntu/ams
   npm init -y
   npm install express
   ```

### 2. 배포 실행

1. 로컬 환경에서 배포 스크립트 생성:
   ```batch
   # build-and-deploy.bat 파일 생성
   # 위의 '로컬 빌드 스크립트' 내용 붙여넣기
   ```

2. 배포 실행:
   ```bash
   # 로컬 환경에서 실행
   build-and-deploy.bat
   ```

## 문제 해결

### 1. SSH 연결 문제
- SSH 키 권한 확인: `chmod 400 kjh-bastion.pem`
- 방화벽 설정 확인: Bastion 서버가 Front 서버에 접속할 수 있는지 확인

### 2. Nginx 프록시 문제
- Nginx 로그 확인: `sudo tail -f /var/log/nginx/error.log`
- Front 서버 접근성 확인: `curl http://10.0.0.63:3000`

### 3. React 라우팅 문제
- 브라우저 콘솔 오류 확인
- Front 서버의 serve.js 스크립트가 모든 경로를 index.html로 리다이렉트하는지 확인
