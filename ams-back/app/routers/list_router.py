from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from app.models.schemas import Asset, AssetType, PaginationParams, AssetListResponse
from app.data.sample_data import sample_assets

router = APIRouter(
	prefix="/api/assets/list",
	tags=["asset-list"],
	responses={404: {"description": "Not found"}},
)

def get_pagination_params(
		page: int = Query(1, ge=1, description="Page number"),
		page_size: int = Query(10, ge=1, le=100, description="Items per page"),
		sort_by: Optional[str] = Query(None, description="Field to sort by"),
		sort_desc: bool = Query(False, description="Sort in descending order")
) -> PaginationParams:
	return PaginationParams(
		page=page,
		page_size=page_size,
		sort_by=sort_by,
		sort_desc=sort_desc
	)

@router.get("", response_model=AssetListResponse)
async def get_assets(
		pagination: PaginationParams = Depends(get_pagination_params),
		site: Optional[str] = None,
		asset_type: Optional[AssetType] = None,
		user: Optional[str] = None,
		manufacturer: Optional[str] = None,
		search: Optional[str] = None
):
	"""
	Get a list of assets with filtering, pagination, and sorting.
	"""
	# Filter assets
	filtered_assets = sample_assets

	if site:
		filtered_assets = [a for a in filtered_assets if a["site"] == site]

	if asset_type:
		filtered_assets = [a for a in filtered_assets if a["asset_type"] == asset_type]

	if user:
		filtered_assets = [a for a in filtered_assets if a["user"] and user.lower() in a["user"].lower()]

	if manufacturer:
		filtered_assets = [a for a in filtered_assets if a["manufacturer"] and manufacturer.lower() in a["manufacturer"].lower()]

	if search:
		search = search.lower()
		filtered_assets = [a for a in filtered_assets if
		                   (a["model_name"] and search in a["model_name"].lower()) or
		                   (a["detailed_model"] and search in a["detailed_model"].lower()) or
		                   (a["serial_number"] and search in a["serial_number"].lower()) or
		                   (a["asset_number"] and search in a["asset_number"].lower())
		                   ]

	# Sort assets
	if pagination.sort_by:
		try:
			filtered_assets = sorted(
				filtered_assets,
				key=lambda x: x.get(pagination.sort_by, ""),
				reverse=pagination.sort_desc
			)
		except:
			# If sorting fails, ignore it
			pass

	# Calculate pagination
	total = len(filtered_assets)
	total_pages = (total + pagination.page_size - 1) // pagination.page_size

	start_idx = (pagination.page - 1) * pagination.page_size
	end_idx = start_idx + pagination.page_size

	paginated_assets = filtered_assets[start_idx:end_idx]

	return AssetListResponse(
		items=paginated_assets,
		total=total,
		page=pagination.page,
		page_size=pagination.page_size,
		total_pages=total_pages
	)

@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
	"""
	Get a specific asset by ID.
	"""
	for asset in sample_assets:
		if asset["id"] == asset_id:
			return asset

	raise HTTPException(status_code=404, detail="Asset not found")

@router.get("/search/{query}", response_model=List[Asset])
async def search_assets(query: str):
	"""
	Search for assets by model name, serial number, asset number, etc.
	"""
	query = query.lower()
	results = []

	for asset in sample_assets:
		if ((asset["model_name"] and query in asset["model_name"].lower()) or
				(asset["detailed_model"] and query in asset["detailed_model"].lower()) or
				(asset["serial_number"] and query in asset["serial_number"].lower()) or
				(asset["asset_number"] and query in asset["asset_number"].lower()) or
				(asset["manufacturer"] and query in asset["manufacturer"].lower())):
			results.append(asset)

	return results

@router.get("/site/{site}", response_model=List[Asset])
async def get_assets_by_site(site: str):
	"""
	Get assets by site.
	"""
	return [a for a in sample_assets if a["site"] == site]

@router.get("/type/{asset_type}", response_model=List[Asset])
async def get_assets_by_type(asset_type: AssetType):
	"""
	Get assets by type.
	"""
	return [a for a in sample_assets if a["asset_type"] == asset_type]

@router.get("/user/{user}", response_model=List[Asset])
async def get_assets_by_user(user: str):
	"""
	Get assets by user.
	"""
	return [a for a in sample_assets if a["user"] and user.lower() in a["user"].lower()]
