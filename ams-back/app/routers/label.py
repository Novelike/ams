from fastapi import APIRouter, HTTPException, Response
from typing import List, Optional, Dict, Any
from app.models.schemas import Label, Asset
import uuid
from datetime import datetime
import qrcode
from io import BytesIO
import base64

router = APIRouter(
    prefix="/api/labels",
    tags=["labels"],
    responses={404: {"description": "Not found"}},
)

# Sample data
sample_labels = [
    {
        "id": str(uuid.uuid4()),
        "asset_id": "asset-001",
        "asset_number": "AMS-2023-001",
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "label_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "created_at": datetime(2023, 1, 15, 14, 30),
        "printed": False,
        "metadata": {
            "model_name": "ThinkPad X1 Carbon",
            "site": "판교 본사"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_id": "asset-002",
        "asset_number": "AMS-2023-002",
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "label_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "created_at": datetime(2023, 2, 10, 11, 15),
        "printed": True,
        "metadata": {
            "model_name": "Dell XPS 15",
            "site": "고양 지사"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_id": "asset-003",
        "asset_number": "AMS-2023-003",
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "label_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "created_at": datetime(2023, 3, 5, 9, 45),
        "printed": False,
        "metadata": {
            "model_name": "LG Gram 17",
            "site": "마곡 LG Science Park"
        }
    }
]

# Helper function to generate QR code
def generate_qr_code(data: str) -> str:
    """
    Generate a QR code as a base64 encoded string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECTION_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"

@router.get("", response_model=List[Label])
async def get_labels():
    """
    Get all labels.
    """
    return sample_labels

@router.get("/{label_id}", response_model=Label)
async def get_label(label_id: str):
    """
    Get a specific label by ID.
    """
    for label in sample_labels:
        if label["id"] == label_id:
            return label

    raise HTTPException(status_code=404, detail="Label not found")

@router.post("", response_model=Label)
async def create_label(label: Label):
    """
    Create a new label.
    """
    # In a real application, this would save the label to a database
    # For now, we'll just return the label with a new ID
    new_label = label.dict()
    new_label["id"] = str(uuid.uuid4())

    # Generate QR code if not provided
    if not new_label.get("qr_code"):
        qr_data = f"asset:{new_label['asset_number']}"
        new_label["qr_code"] = generate_qr_code(qr_data)

    return new_label

@router.post("/generate/{asset_id}", response_model=Label)
async def generate_label_for_asset(asset_id: str):
    """
    Generate a label for an asset.
    """
    # In a real application, this would fetch the asset from a database
    # For now, we'll create a mock asset
    asset = {
        "id": asset_id,
        "asset_number": f"AMS-2023-{asset_id[-3:]}",
        "model_name": "Sample Asset",
        "site": "판교 본사"
    }

    # Generate QR code
    qr_data = f"asset:{asset['asset_number']}"
    qr_code = generate_qr_code(qr_data)

    # Create label
    label = {
        "id": str(uuid.uuid4()),
        "asset_id": asset_id,
        "asset_number": asset["asset_number"],
        "qr_code": qr_code,
        "label_image": None,  # Would be generated in a real application
        "created_at": datetime.now(),
        "printed": False,
        "metadata": {
            "model_name": asset["model_name"],
            "site": asset["site"]
        }
    }

    return label

@router.put("/{label_id}", response_model=Label)
async def update_label(label_id: str, label: Label):
    """
    Update a label.
    """
    # In a real application, this would update the label in a database
    # For now, we'll just return the updated label
    updated_label = label.dict()
    updated_label["id"] = label_id

    return updated_label

@router.delete("/{label_id}")
async def delete_label(label_id: str):
    """
    Delete a label.
    """
    # In a real application, this would delete the label from a database
    # For now, we'll just return a success message
    return {"message": f"Label {label_id} deleted successfully"}

@router.get("/{label_id}/download")
async def download_label(label_id: str):
    """
    Download a label as an image.
    """
    # Find the label
    label = None
    for l in sample_labels:
        if l["id"] == label_id:
            label = l
            break

    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    # In a real application, this would generate a label image
    # For now, we'll return a mock image

    # If label_image is not set, generate one (in a real app, this would create an actual image)
    if not label.get("label_image") or label["label_image"].endswith("..."):
        # For demo purposes, we'll just use the QR code as the label image
        label["label_image"] = label["qr_code"]

    # Extract the base64 data
    if label["label_image"].startswith("data:image/png;base64,"):
        image_data = label["label_image"].split(",")[1]
    else:
        image_data = label["label_image"]

    # Decode the base64 data
    try:
        image_bytes = base64.b64decode(image_data)
    except:
        # If the mock data can't be decoded, generate a new QR code
        qr_data = f"asset:{label['asset_number']}"
        label["label_image"] = generate_qr_code(qr_data)
        image_data = label["label_image"].split(",")[1]
        image_bytes = base64.b64decode(image_data)

    # Return the image
    return Response(content=image_bytes, media_type="image/png")

@router.post("/{label_id}/print")
async def print_label(label_id: str):
    """
    Mark a label as printed.
    """
    # Find the label
    label = None
    for i, l in enumerate(sample_labels):
        if l["id"] == label_id:
            label = l
            sample_labels[i]["printed"] = True
            break

    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    # In a real application, this would send the label to a printer
    # For now, we'll just mark it as printed

    return {"message": f"Label {label_id} sent to printer", "printed": True}

@router.get("/asset/{asset_id}")
async def get_label_by_asset(asset_id: str):
    """
    Get a label by asset ID.
    """
    # Find the label
    for label in sample_labels:
        if label["asset_id"] == asset_id:
            return label

    # If no label exists, generate one
    return await generate_label_for_asset(asset_id)

@router.get("/batch/print")
async def batch_print_labels(asset_ids: List[str]):
    """
    Print multiple labels in a batch.
    """
    # In a real application, this would send multiple labels to a printer
    # For now, we'll just return a success message

    return {"message": f"{len(asset_ids)} labels sent to printer", "printed": True}
