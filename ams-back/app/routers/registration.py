from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Body
from typing import List, Optional, Dict, Any
from app.models.schemas import (
	FileUploadResponse,
	SegmentationRequest,
	SegmentationResponse,
	OCRRequest,
	OCRResponse,
	AssetRegistrationRequest,
	Asset,
	AssetType
)
from datetime import datetime
import os
import uuid
import json

router = APIRouter(
	prefix="/api/registration",
	tags=["registration"],
	responses={404: {"description": "Not found"}},
)

# Directory to store uploaded files
UPLOAD_DIR = "uploads"

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_image(file: UploadFile = File(...)):
	"""
	Upload an image file for asset registration.
	"""
	if not file:
		raise HTTPException(status_code=400, detail="No file provided")

	# Check if the file is an image
	if not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="File must be an image")

	# Create a unique filename
	file_extension = os.path.splitext(file.filename)[1]
	unique_filename = f"{uuid.uuid4()}{file_extension}"
	file_path = os.path.join(UPLOAD_DIR, unique_filename)

	# Save the file
	with open(file_path, "wb") as f:
		content = await file.read()
		f.write(content)

	# Create response
	file_response = FileUploadResponse(
		filename=file.filename,
		size=len(content),
		content_type=file.content_type,
		upload_time=datetime.now(),
		file_path=file_path
	)

	return file_response

@router.post("/segment", response_model=SegmentationResponse)
async def segment_image(request: SegmentationRequest):
	"""
	Perform image segmentation to identify regions of interest.
	"""
	# Check if the file exists
	if not os.path.exists(request.image_path):
		raise HTTPException(status_code=404, detail="Image file not found")

	# In a real application, this would call an image segmentation service
	# For now, we'll return mock segmentation results

	# Mock segmentation results
	segments = {
		"model_name": {"x": 100, "y": 50, "width": 200, "height": 30},
		"serial_number": {"x": 100, "y": 100, "width": 150, "height": 30},
		"manufacturer": {"x": 100, "y": 150, "width": 100, "height": 30}
	}

	return SegmentationResponse(
		segments=segments,
		image_path=request.image_path
	)

@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
	"""
	Perform OCR on the segmented image regions.
	"""
	# Check if the file exists
	if not os.path.exists(request.image_path):
		raise HTTPException(status_code=404, detail="Image file not found")

	# In a real application, this would call an OCR service
	# For now, we'll return mock OCR results

	# Mock OCR results
	results = {
		"model_name": "ThinkPad X1 Carbon",
		"serial_number": "PF-2X4N7",
		"manufacturer": "Lenovo"
	}

	# Mock confidence scores
	confidence = {
		"model_name": 0.95,
		"serial_number": 0.87,
		"manufacturer": 0.92
	}

	return OCRResponse(
		results=results,
		confidence=confidence
	)

@router.post("/register", response_model=Asset)
async def register_asset(request: AssetRegistrationRequest):
	"""
	Register a new asset with the provided information.
	"""
	# Generate a unique asset number
	current_year = datetime.now().year
	asset_number = f"AMS-{current_year}-{str(uuid.uuid4())[:8]}"

	# Create the asset
	asset = {
		"id": str(uuid.uuid4()),
		"asset_number": asset_number,
		"model_name": request.model_name,
		"detailed_model": request.detailed_model,
		"serial_number": request.serial_number,
		"manufacturer": request.manufacturer,
		"site": request.site,
		"asset_type": request.asset_type,
		"user": request.user,
		"registration_date": datetime.now(),
		"image_path": request.image_path,
		"ocr_results": request.ocr_results,
		"segmentation_results": request.segmentation_results,
		"specs": request.specs,
		"metadata": request.metadata
	}

	# In a real application, this would save the asset to a database
	# For now, we'll just return the created asset

	return asset

@router.post("/chatbot-assist", response_model=Dict[str, Any])
async def get_chatbot_assistance(
		ocr_results: Optional[Dict[str, str]] = Body(None),
		model_name: Optional[str] = Body(None),
		serial_number: Optional[str] = Body(None)
):
	"""
	Get assistance from the chatbot for asset registration.
	"""
	# In a real application, this would call a chatbot or AI service
	# For now, we'll return mock assistance data

	# Mock specs based on model name
	specs = {}
	suggestions = []

	if model_name:
		if "thinkpad" in model_name.lower():
			specs = {
				"cpu": "Intel Core i7-1165G7",
				"ram": "16GB",
				"storage": "512GB SSD",
				"display": "14-inch FHD+"
			}
			suggestions.append("This appears to be a Lenovo ThinkPad. Would you like to set the manufacturer to 'Lenovo'?")
		elif "dell" in model_name.lower():
			specs = {
				"cpu": "Intel Core i9-11900H",
				"ram": "32GB",
				"storage": "1TB SSD",
				"display": "15.6-inch 4K OLED"
			}
			suggestions.append("This appears to be a Dell laptop. Would you like to set the manufacturer to 'Dell'?")
		elif "lg" in model_name.lower():
			specs = {
				"cpu": "Intel Core i7-1165G7",
				"ram": "16GB",
				"storage": "512GB SSD",
				"display": "17-inch WQXGA"
			}
			suggestions.append("This appears to be an LG laptop. Would you like to set the manufacturer to 'LG'?")

	# Generate asset number suggestion
	current_year = datetime.now().year
	asset_number = f"AMS-{current_year}-{str(uuid.uuid4())[:8]}"
	suggestions.append(f"Suggested asset number: {asset_number}")

	return {
		"specs": specs,
		"suggestions": suggestions,
		"asset_number": asset_number
	}

@router.get("/workflow")
async def get_registration_workflow():
	"""
	Get the registration workflow steps.
	"""
	workflow = [
		{
			"step": 1,
			"name": "image_upload",
			"description": "Upload an image of the asset"
		},
		{
			"step": 2,
			"name": "segmentation",
			"description": "Perform image segmentation to identify regions of interest"
		},
		{
			"step": 3,
			"name": "ocr",
			"description": "Perform OCR on the segmented image regions"
		},
		{
			"step": 4,
			"name": "review_and_edit",
			"description": "Review and edit the OCR results"
		},
		{
			"step": 5,
			"name": "chatbot_assist",
			"description": "Get assistance from the chatbot for additional information"
		},
		{
			"step": 6,
			"name": "register",
			"description": "Register the asset with the provided information"
		},
		{
			"step": 7,
			"name": "generate_label",
			"description": "Generate a label for the asset"
		}
	]

	return workflow