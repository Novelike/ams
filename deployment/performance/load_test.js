// K6 성능 테스트 스크립트 - AMS Backend
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 커스텀 메트릭 정의
export let errorRate = new Rate('errors');
export let responseTime = new Trend('response_time');

// 테스트 설정
export let options = {
  stages: [
    // 점진적 부하 증가
    { duration: '2m', target: 20 },   // 2분 동안 20명까지 증가
    { duration: '5m', target: 20 },   // 5분 동안 20명 유지
    { duration: '2m', target: 50 },   // 2분 동안 50명까지 증가
    { duration: '5m', target: 50 },   // 5분 동안 50명 유지
    { duration: '2m', target: 100 },  // 2분 동안 100명까지 증가
    { duration: '5m', target: 100 },  // 5분 동안 100명 유지
    { duration: '2m', target: 0 },    // 2분 동안 0명까지 감소
  ],
  thresholds: {
    // 성능 임계값 설정
    http_req_duration: ['p(95)<1000'], // 95%의 요청이 1초 이내
    http_req_failed: ['rate<0.1'],     // 오류율 10% 미만
    errors: ['rate<0.1'],              // 커스텀 오류율 10% 미만
  },
};

// 테스트 데이터
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// 테스트할 엔드포인트 목록
const endpoints = [
  { path: '/api/health', weight: 30 },
  { path: '/api/registration/workflow', weight: 20 },
  { path: '/api/registration/verification/stats', weight: 15 },
  { path: '/api/dashboard/stats', weight: 10 },
  { path: '/api/assets/list', weight: 15 },
  { path: '/api/chatbot/health', weight: 10 }
];

// 가중치 기반 엔드포인트 선택
function selectEndpoint() {
  const totalWeight = endpoints.reduce((sum, ep) => sum + ep.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (let endpoint of endpoints) {
    random -= endpoint.weight;
    if (random <= 0) {
      return endpoint.path;
    }
  }
  
  return endpoints[0].path; // 기본값
}

// 메인 테스트 함수
export default function() {
  // 랜덤 엔드포인트 선택
  const endpoint = selectEndpoint();
  const url = `${BASE_URL}${endpoint}`;
  
  // HTTP 요청 옵션
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test/1.0',
    },
    timeout: '30s',
  };
  
  // 요청 시작 시간
  const startTime = new Date().getTime();
  
  // HTTP 요청 실행
  let response = http.get(url, params);
  
  // 응답 시간 계산
  const endTime = new Date().getTime();
  const duration = endTime - startTime;
  responseTime.add(duration);
  
  // 응답 검증
  const isSuccess = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2000ms': (r) => r.timings.duration < 2000,
    'response has body': (r) => r.body && r.body.length > 0,
  });
  
  // 오류율 추적
  errorRate.add(!isSuccess);
  
  // 특정 엔드포인트별 추가 검증
  if (endpoint === '/api/health') {
    check(response, {
      'health check has status field': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.status !== undefined;
        } catch (e) {
          return false;
        }
      }
    });
  }
  
  if (endpoint === '/api/registration/workflow') {
    check(response, {
      'workflow has steps': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body) && body.length > 0;
        } catch (e) {
          return false;
        }
      }
    });
  }
  
  // 요청 간 대기 시간 (1-3초 랜덤)
  sleep(Math.random() * 2 + 1);
}

// 테스트 시작 시 실행
export function setup() {
  console.log('🚀 AMS Backend 성능 테스트 시작');
  console.log(`📍 대상 URL: ${BASE_URL}`);
  console.log('📊 테스트 시나리오:');
  console.log('  - 점진적 부하 증가 (20 → 50 → 100 사용자)');
  console.log('  - 총 테스트 시간: 23분');
  console.log('  - 성능 임계값: 95% 요청 1초 이내, 오류율 10% 미만');
  
  // 기본 연결 테스트
  const healthCheck = http.get(`${BASE_URL}/api/health`);
  if (healthCheck.status !== 200) {
    console.error('❌ 서버 연결 실패 - 테스트를 중단합니다');
    throw new Error('Server health check failed');
  }
  
  console.log('✅ 서버 연결 확인 완료');
  return { baseUrl: BASE_URL };
}

// 테스트 종료 시 실행
export function teardown(data) {
  console.log('🏁 AMS Backend 성능 테스트 완료');
  console.log('📈 결과 요약은 k6 리포트를 확인하세요');
}

// 체크포인트 함수 (각 스테이지 전환 시 호출)
export function handleSummary(data) {
  return {
    'performance-results.json': JSON.stringify(data, null, 2),
    'performance-summary.html': generateHtmlReport(data),
  };
}

// HTML 리포트 생성
function generateHtmlReport(data) {
  const metrics = data.metrics;
  
  return `
<!DOCTYPE html>
<html>
<head>
    <title>AMS Backend 성능 테스트 결과</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .metric { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .warning { background-color: #fff3cd; border-color: #ffeaa7; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 AMS Backend 성능 테스트 결과</h1>
        <p>테스트 완료 시간: ${new Date().toISOString()}</p>
    </div>
    
    <div class="metric ${metrics.http_req_duration.values.p95 < 1000 ? 'success' : 'error'}">
        <h3>📊 응답 시간</h3>
        <p>평균: ${metrics.http_req_duration.values.avg.toFixed(2)}ms</p>
        <p>95th 백분위수: ${metrics.http_req_duration.values.p95.toFixed(2)}ms</p>
        <p>최대: ${metrics.http_req_duration.values.max.toFixed(2)}ms</p>
    </div>
    
    <div class="metric ${metrics.http_req_failed.values.rate < 0.1 ? 'success' : 'error'}">
        <h3>🎯 성공률</h3>
        <p>총 요청 수: ${metrics.http_reqs.values.count}</p>
        <p>실패율: ${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%</p>
        <p>성공율: ${((1 - metrics.http_req_failed.values.rate) * 100).toFixed(2)}%</p>
    </div>
    
    <div class="metric">
        <h3>⚡ 처리량</h3>
        <p>초당 요청 수: ${metrics.http_reqs.values.rate.toFixed(2)} req/s</p>
        <p>테스트 지속 시간: ${(data.state.testRunDurationMs / 1000).toFixed(0)}초</p>
    </div>
    
    <div class="metric">
        <h3>📈 가상 사용자</h3>
        <p>최대 동시 사용자: ${metrics.vus_max.values.max}</p>
        <p>평균 동시 사용자: ${metrics.vus.values.avg.toFixed(0)}</p>
    </div>
</body>
</html>
  `;
}