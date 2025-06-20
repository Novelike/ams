from fastapi import APIRouter
from typing import List, Dict, Any
from app.models.schemas import StatCard, SiteAsset, DashboardCharts, ChartData
from datetime import datetime

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

@router.get("/stats", response_model=List[StatCard])
async def get_stats():
    """
    Get statistics for the dashboard stat cards.
    """
    # In a real application, this would fetch data from a database
    # For now, we'll return sample data
    stat_cards = [
        {
            "title": "총 자산",
            "value": "281",
            "change": "+10%",
            "change_text": "전월 대비 증가",
            "positive": True,
        },
        {
            "title": "신규 등록",
            "value": "21",
            "change": "+5%",
            "change_text": "전주 대비",
            "positive": True,
        },
        {
            "title": "사용자",
            "value": "85",
            "change_text": "업데이트됨",
            "no_change": True,
        },
    ]

    return stat_cards

@router.get("/site-assets", response_model=List[SiteAsset])
async def get_site_assets():
    """
    Get asset data by site for the data table.
    """
    from app.data.sample_data import site_data
    return site_data

@router.get("/chart-data", response_model=DashboardCharts)
async def get_chart_data():
    """
    Get data for the charts on the dashboard.
    """
    # In a real application, this would fetch data from a database
    # For now, we'll return sample data

    # Asset by type chart
    asset_by_type = ChartData(
        labels=["노트북", "데스크탑", "모니터", "키보드", "마우스", "패드", "가방"],
        data=[120, 45, 65, 85, 85, 75, 40]
    )

    # Asset by site chart
    asset_by_site = ChartData(
        labels=["판교 본사", "고양 지사", "압구정 LF", "마곡 LG Science Park", "역삼 GS 타워"],
        data=[95, 65, 40, 55, 26]
    )

    # Monthly registrations chart
    # Generate data for the last 6 months
    today = datetime.now()
    months = []
    data = []

    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1

        # Format as "YYYY-MM"
        months.append(f"{year}-{month:02d}")

        # Generate random-ish data that increases over time
        data.append(10 + i * 5 + (i * i))

    monthly_registrations = ChartData(
        labels=months,
        data=data
    )

    return DashboardCharts(
        asset_by_type=asset_by_type,
        asset_by_site=asset_by_site,
        monthly_registrations=monthly_registrations
    )
