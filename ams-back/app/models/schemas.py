from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
from uuid import UUID

# Asset domain schemas
class AssetType(str, Enum):
	LAPTOP = "laptop"
	DESKTOP = "desktop"
	MONITOR = "monitor"
	KEYBOARD = "keyboard"
	MOUSE = "mouse"
	PAD = "pad"
	BAG = "bag"
	OTHER = "other"

class Asset(BaseModel):
	id: str
	asset_number: str  # 관리번호
	model_name: str  # 모델명
	detailed_model: Optional[str] = None  # 상세모델명
	serial_number: Optional[str] = None  # S/N
	manufacturer: Optional[str] = None  # 제조사
	site: str  # SITE(지점)
	asset_type: AssetType  # ASSET_TYPE(기기종류)
	user: Optional[str] = None  # 사용자
	registration_date: datetime = Field(default_factory=datetime.now)  # 등록일
	image_path: Optional[str] = None  # 업로드된 이미지 경로
	ocr_results: Optional[Dict[str, Any]] = None  # OCR 결과
	segmentation_results: Optional[Dict[str, Any]] = None  # 세그멘테이션 결과
	specs: Optional[Dict[str, Any]] = None  # 기기 스펙 정보
	metadata: Optional[Dict[str, Any]] = None  # 추가 메타데이터

# Registration domain schemas
class FileUploadResponse(BaseModel):
	filename: str
	size: int
	content_type: str
	upload_time: datetime
	file_path: str

class SegmentationRequest(BaseModel):
	image_path: str

class SegmentationResponse(BaseModel):
	segments: Dict[str, Any]
	image_path: str

class OCRRequest(BaseModel):
	image_path: str
	segments: Optional[Dict[str, Any]] = None

class OCRResponse(BaseModel):
	results: Dict[str, str]
	confidence: Dict[str, float]

class AssetRegistrationRequest(BaseModel):
	model_name: str
	detailed_model: Optional[str] = None
	serial_number: Optional[str] = None
	manufacturer: Optional[str] = None
	site: str
	asset_type: AssetType
	user: Optional[str] = None
	image_path: Optional[str] = None
	ocr_results: Optional[Dict[str, Any]] = None
	segmentation_results: Optional[Dict[str, Any]] = None
	specs: Optional[Dict[str, Any]] = None
	metadata: Optional[Dict[str, Any]] = None

# Dashboard schemas
class StatCard(BaseModel):
	title: str
	value: str
	change: Optional[str] = None
	change_text: str
	positive: Optional[bool] = None
	no_change: Optional[bool] = None

class SiteAsset(BaseModel):
	name: str
	laptop: int
	keyboard: int
	mouse: int
	pad: int
	bag: int
	desktop: int
	monitor: int
	total: int
	amount: int

class ChartData(BaseModel):
	labels: List[str]
	data: List[int]

class DashboardCharts(BaseModel):
	asset_by_type: ChartData
	asset_by_site: ChartData
	monthly_registrations: ChartData

# Chatbot schemas
class ChatMessage(BaseModel):
	content: str
	role: str = "user"  # "user" or "assistant"
	timestamp: datetime = Field(default_factory=datetime.now)
	context: Optional[Dict[str, Any]] = None  # For storing context like OCR results, model info, etc.

class ChatResponse(BaseModel):
	message: str
	timestamp: datetime = Field(default_factory=datetime.now)
	suggestions: Optional[List[str]] = None  # Suggested actions or responses
	asset_info: Optional[Dict[str, Any]] = None  # Asset information if relevant

# Label schemas
class Label(BaseModel):
	id: str
	asset_id: str
	asset_number: str
	qr_code: Optional[str] = None
	label_image: Optional[str] = None
	created_at: datetime = Field(default_factory=datetime.now)
	printed: bool = False
	metadata: Optional[Dict[str, Any]] = None

# Job status schemas
class JobStatus(str, Enum):
	QUEUED = "queued"
	PROCESSING = "processing"
	COMPLETED = "completed"
	FAILED = "failed"

class JobResponse(BaseModel):
	job_id: str
	status: JobStatus = JobStatus.QUEUED

class JobStage(str, Enum):
	SEGMENT_START = "segment_start"
	SEGMENT_DONE = "segment_done"
	OCR_START = "ocr_start"
	OCR_PREPROCESSING = "ocr_preprocessing"
	OCR_DETECTION = "ocr_detection"
	OCR_RECOGNITION = "ocr_recognition"
	OCR_POSTPROCESSING = "ocr_postprocessing"
	OCR_DONE = "ocr_done"
	REGISTER_START = "register_start"
	REGISTER_DONE = "register_done"

class JobStatusEvent(BaseModel):
	stage: JobStage
	message: str
	timestamp: datetime = Field(default_factory=datetime.now)
	data: Optional[Dict[str, Any]] = None

# List schemas
class AssetFilter(BaseModel):
	site: Optional[str] = None
	asset_type: Optional[AssetType] = None
	user: Optional[str] = None
	manufacturer: Optional[str] = None
	registration_date_from: Optional[datetime] = None
	registration_date_to: Optional[datetime] = None
	search_term: Optional[str] = None

class PaginationParams(BaseModel):
	page: int = 1
	page_size: int = 10
	sort_by: Optional[str] = None
	sort_desc: bool = False

class AssetListResponse(BaseModel):
	items: List[Asset]
	total: int
	page: int
	page_size: int
	total_pages: int
