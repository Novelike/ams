const express = require('express');
const path = require('path');
const app = express();
const PORT = 3000;

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'dist')));

// API 라우트가 있다면 여기에 추가
// app.use('/api', apiRoutes);

// React Router를 위한 히스토리 API 지원
// 모든 요청을 index.html로 라우팅 (단, 파일 확장자가 있는 요청은 제외)
app.get(/^(?!.*\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$).*$/, (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// 404 처리
app.use((req, res) => {
  res.status(404).sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// 에러 처리
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다.`);
  console.log(`PID: ${process.pid}`);
  console.log(`현재 시간: ${new Date().toISOString()}`);
});

// 프로세스 종료 시 정리
process.on('SIGTERM', () => {
  console.log('SIGTERM 신호를 받았습니다. 서버를 종료합니다.');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT 신호를 받았습니다. 서버를 종료합니다.');
  process.exit(0);
});