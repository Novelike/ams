from app.models.schemas import AssetType
from datetime import datetime
import uuid

# Sample assets data
sample_assets = [
    {
        "id": str(uuid.uuid4()),
        "asset_number": "AMS-2023-001",
        "model_name": "ThinkPad X1 Carbon",
        "detailed_model": "X1 Carbon Gen 9",
        "serial_number": "PF-2X4N7",
        "manufacturer": "Lenovo",
        "site": "판교 본사",
        "asset_type": AssetType.LAPTOP,
        "user": "김철수",
        "registration_date": datetime(2023, 1, 15, 14, 30),
        "image_path": "/uploads/laptop_001.jpg",
        "specs": {
            "cpu": "Intel Core i7-1165G7",
            "ram": "16GB",
            "storage": "512GB SSD",
            "display": "14-inch FHD+"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_number": "AMS-2023-002",
        "model_name": "Dell XPS 15",
        "detailed_model": "XPS 15 9510",
        "serial_number": "DL-9X5T7",
        "manufacturer": "Dell",
        "site": "고양 지사",
        "asset_type": AssetType.LAPTOP,
        "user": "이영희",
        "registration_date": datetime(2023, 2, 10, 11, 15),
        "image_path": "/uploads/laptop_002.jpg",
        "specs": {
            "cpu": "Intel Core i9-11900H",
            "ram": "32GB",
            "storage": "1TB SSD",
            "display": "15.6-inch 4K OLED"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_number": "AMS-2023-003",
        "model_name": "LG Gram 17",
        "detailed_model": "17Z90P",
        "serial_number": "LG-17Z90P-K",
        "manufacturer": "LG",
        "site": "마곡 LG Science Park",
        "asset_type": AssetType.LAPTOP,
        "user": "박지민",
        "registration_date": datetime(2023, 3, 5, 9, 45),
        "image_path": "/uploads/laptop_003.jpg",
        "specs": {
            "cpu": "Intel Core i7-1165G7",
            "ram": "16GB",
            "storage": "512GB SSD",
            "display": "17-inch WQXGA"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_number": "AMS-2023-004",
        "model_name": "Dell UltraSharp",
        "detailed_model": "U2720Q",
        "serial_number": "DL-U2720Q-1",
        "manufacturer": "Dell",
        "site": "판교 본사",
        "asset_type": AssetType.MONITOR,
        "user": "김철수",
        "registration_date": datetime(2023, 1, 15, 14, 35),
        "image_path": "/uploads/monitor_001.jpg",
        "specs": {
            "size": "27-inch",
            "resolution": "4K UHD (3840 x 2160)",
            "panel": "IPS",
            "refresh_rate": "60Hz"
        }
    },
    {
        "id": str(uuid.uuid4()),
        "asset_number": "AMS-2023-005",
        "model_name": "Logitech MX Keys",
        "detailed_model": "MX Keys Advanced",
        "serial_number": "LG-MXK-123",
        "manufacturer": "Logitech",
        "site": "고양 지사",
        "asset_type": AssetType.KEYBOARD,
        "user": "이영희",
        "registration_date": datetime(2023, 2, 10, 11, 20),
        "image_path": "/uploads/keyboard_001.jpg",
        "specs": {
            "type": "Wireless",
            "layout": "한글",
            "backlight": "Yes"
        }
    }
]

# Sample site data for dashboard
site_data = [
    {
        "name": "판교 본사",
        "laptop": 32,
        "keyboard": 38,
        "mouse": 38,
        "pad": 38,
        "bag": 32,
        "desktop": 20,
        "monitor": 20,
        "total": 20,
        "amount": 20,
    },
    {
        "name": "고양 지사",
        "laptop": 32,
        "keyboard": 38,
        "mouse": 38,
        "pad": 38,
        "bag": 32,
        "desktop": 20,
        "monitor": 20,
        "total": 20,
        "amount": 20,
    },
    {
        "name": "압구정 LF",
        "laptop": 32,
        "keyboard": 38,
        "mouse": 38,
        "pad": 38,
        "bag": 32,
        "desktop": 20,
        "monitor": 20,
        "total": 20,
        "amount": 20,
    },
    {
        "name": "마곡 LG Science Park",
        "laptop": 32,
        "keyboard": 38,
        "mouse": 38,
        "pad": 38,
        "bag": 32,
        "desktop": 20,
        "monitor": 20,
        "total": 20,
        "amount": 20,
    },
    {
        "name": "역삼 GS 타워",
        "laptop": 32,
        "keyboard": 38,
        "mouse": 38,
        "pad": 38,
        "bag": 32,
        "desktop": 20,
        "monitor": 20,
        "total": 20,
        "amount": 20,
    },
]