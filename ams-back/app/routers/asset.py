from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import Asset, AssetType
from app.data.sample_data import sample_assets

router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=List[Asset])
async def get_assets():
    """
    Get all assets.
    """
    return sample_assets

@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
    """
    Get a specific asset by ID.
    """
    for asset in sample_assets:
        if asset["id"] == asset_id:
            return asset

    raise HTTPException(status_code=404, detail="Asset not found")

@router.get("/number/{asset_number}", response_model=Asset)
async def get_asset_by_number(asset_number: str):
    """
    Get a specific asset by asset number.
    """
    for asset in sample_assets:
        if asset["asset_number"] == asset_number:
            return asset

    raise HTTPException(status_code=404, detail="Asset not found")

@router.get("/site/{site}", response_model=List[Asset])
async def get_assets_by_site(site: str):
    """
    Get assets by site.
    """
    assets = [asset for asset in sample_assets if asset["site"] == site]
    return assets

@router.get("/type/{asset_type}", response_model=List[Asset])
async def get_assets_by_type(asset_type: AssetType):
    """
    Get assets by type.
    """
    assets = [asset for asset in sample_assets if asset["asset_type"] == asset_type]
    return assets

@router.get("/user/{user}", response_model=List[Asset])
async def get_assets_by_user(user: str):
    """
    Get assets by user.
    """
    assets = [asset for asset in sample_assets if asset["user"] == user]
    return assets
