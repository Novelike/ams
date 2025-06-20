#!/bin/bash
echo "=== Front 서버로 빌드 파일 전송 ==="
ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63 "mkdir -p /home/ubuntu/ams/dist"
scp -i /home/ubuntu/kjh-bastion.pem -r /home/ubuntu/ams-build/* ubuntu@10.0.0.63:/home/ubuntu/ams/dist/

echo "=== Front 서버에서 애플리케이션 재시작 ==="
ssh -i /home/ubuntu/kjh-bastion.pem ubuntu@10.0.0.63 "cd /home/ubuntu/ams && pm2 restart ams || pm2 start /home/ubuntu/ams/serve.js --name ams"

echo "=== 배포 완료 ==="