from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# 로깅 설정 임포트
from app.utils.logging import setup_logger

# Import routers
from app.routers import asset, dashboard, registration, label, chatbot, list_router

# Load environment variables
load_dotenv()

# 메인 로거 설정
logger = setup_logger("app.main", level=logging.INFO)
logger.info("애플리케이션 시작 중...")

# Create FastAPI app
app = FastAPI(
	title="AMS API",
	description="API for Asset Management System",
	version="1.0.0"
)
logger.info("FastAPI 애플리케이션 생성 완료")

# Configure CORS
# Get allowed origins from environment variable or use default values
allowed_origins = os.getenv("ALLOWED_ORIGINS",
                            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
origins = allowed_origins.split(",")

# Add production server origin if PROD_SERVER_IP is set
prod_server_ip = os.getenv("PROD_SERVER_IP")
if prod_server_ip:
	origins.append(f"http://{prod_server_ip}")
	origins.append(f"https://{prod_server_ip}")

# Log the allowed origins
logger.info(f"허용된 CORS 출처: {origins}")

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# 파일 크기 제한 미들웨어 추가
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and "/upload" in str(request.url):
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            max_size = 200 * 1024 * 1024  # 50MB
            if content_length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"파일 크기가 너무 큽니다. 최대 {max_size // (1024*1024)}MB까지 허용됩니다."}
                )

    response = await call_next(request)
    return response

# Include routers
logger.info("라우터 등록 중...")
app.include_router(dashboard.router)
app.include_router(asset.router)
app.include_router(registration.router)
app.include_router(chatbot.router)
app.include_router(list_router.router)
app.include_router(label.router)
logger.info("모든 라우터 등록 완료")

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
	return {"message": "Welcome to AMS API"}


@app.get("/api/health")
async def health_check():
	"""
	Health check endpoint for monitoring and deployment scripts
	"""
	return {
		"status": "healthy",
		"timestamp": datetime.now().isoformat(),
		"service": "AMS Backend API",
		"version": "1.0.0"
	}


if __name__ == "__main__":
	port = int(os.getenv("PORT", 8000))
	# 환경 변수로 개발/프로덕션 모드 구분
	is_development = os.getenv("ENVIRONMENT", "production").lower() == "development"

	logger.info(f"서버 시작 중... (포트: {port}, 개발모드: {is_development})")
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=port,
		reload=is_development,  # 개발 환경에서만 reload 활성화
		log_config=None
	)
