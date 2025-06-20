from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# Import routers
from app.routers import asset, dashboard, registration, label, chatbot, list_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
	title="AMS API",
	description="API for Asset Management System",
	version="1.0.0"
)

# Configure CORS
# Get allowed origins from environment variable or use default values
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
origins = allowed_origins.split(",")

# Add production server origin if PROD_SERVER_IP is set
prod_server_ip = os.getenv("PROD_SERVER_IP")
if prod_server_ip:
	origins.append(f"http://{prod_server_ip}")
	origins.append(f"https://{prod_server_ip}")

# Log the allowed origins
print(f"Allowed CORS origins: {origins}")

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router)
app.include_router(asset.router)
app.include_router(registration.router)
app.include_router(chatbot.router)
app.include_router(list_router.router)
app.include_router(label.router)

@app.get("/")
async def root():
	return {"message": "Welcome to AMS API"}

if __name__ == "__main__":
	port = int(os.getenv("PORT", 8000))
	uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
