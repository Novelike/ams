from fastapi import APIRouter, Body
from typing import List, Optional, Dict, Any
from app.models.schemas import ChatMessage, ChatResponse
from datetime import datetime

router = APIRouter(
    prefix="/api/chatbot",
    tags=["chatbot"],
    responses={404: {"description": "Not found"}},
)

# Sample chat history for demonstration
chat_history = []

@router.post("/send", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """
    Send a message to the chatbot and get a response.
    """
    # Store the message in chat history
    chat_history.append(message.dict())
    
    # Process the message and generate a response
    user_message = message.content.lower()
    context = message.context or {}
    
    # Initialize response variables
    response_text = ""
    suggestions = []
    asset_info = None
    
    # Handle different types of queries
    if "안녕" in user_message or "hello" in user_message or "hi" in user_message:
        response_text = "안녕하세요! AMS 챗봇입니다. 자산 등록 및 관리를 도와드릴게요. 어떻게 도와드릴까요?"
        suggestions = ["자산 등록 도움", "모델명으로 스펙 검색", "자산 현황 보기"]
    
    elif "자산" in user_message and ("등록" in user_message or "추가" in user_message):
        response_text = "자산 등록을 도와드릴게요. 이미지를 업로드하시면 OCR을 통해 정보를 자동으로 인식합니다. 또는 모델명을 알려주시면 스펙 정보를 찾아드릴 수 있어요."
        suggestions = ["이미지 업로드하기", "모델명 직접 입력하기"]
    
    elif "모델" in user_message or "스펙" in user_message:
        # Check if there's a model name in the context
        model_name = None
        if "ocr_results" in context and "model_name" in context["ocr_results"]:
            model_name = context["ocr_results"]["model_name"]
        
        if model_name:
            response_text = f"{model_name}에 대한 스펙 정보를 찾아보겠습니다."
            
            # Mock spec lookup based on model name
            if "thinkpad" in model_name.lower():
                asset_info = {
                    "model_name": model_name,
                    "manufacturer": "Lenovo",
                    "specs": {
                        "cpu": "Intel Core i7-1165G7",
                        "ram": "16GB",
                        "storage": "512GB SSD",
                        "display": "14-inch FHD+"
                    }
                }
                response_text = f"{model_name}의 스펙 정보입니다:\n- CPU: Intel Core i7-1165G7\n- RAM: 16GB\n- 저장공간: 512GB SSD\n- 디스플레이: 14-inch FHD+"
            elif "dell" in model_name.lower() or "xps" in model_name.lower():
                asset_info = {
                    "model_name": model_name,
                    "manufacturer": "Dell",
                    "specs": {
                        "cpu": "Intel Core i9-11900H",
                        "ram": "32GB",
                        "storage": "1TB SSD",
                        "display": "15.6-inch 4K OLED"
                    }
                }
                response_text = f"{model_name}의 스펙 정보입니다:\n- CPU: Intel Core i9-11900H\n- RAM: 32GB\n- 저장공간: 1TB SSD\n- 디스플레이: 15.6-inch 4K OLED"
            elif "lg" in model_name.lower() or "gram" in model_name.lower():
                asset_info = {
                    "model_name": model_name,
                    "manufacturer": "LG",
                    "specs": {
                        "cpu": "Intel Core i7-1165G7",
                        "ram": "16GB",
                        "storage": "512GB SSD",
                        "display": "17-inch WQXGA"
                    }
                }
                response_text = f"{model_name}의 스펙 정보입니다:\n- CPU: Intel Core i7-1165G7\n- RAM: 16GB\n- 저장공간: 512GB SSD\n- 디스플레이: 17-inch WQXGA"
            else:
                response_text = f"죄송합니다. {model_name}에 대한 스펙 정보를 찾을 수 없습니다. 제조사와 상세 모델명을 알려주시면 더 정확한 정보를 찾을 수 있어요."
                suggestions = ["제조사 입력하기", "상세 모델명 입력하기"]
        else:
            response_text = "어떤 모델의 스펙 정보가 필요하신가요? 모델명을 알려주시면 찾아드릴게요."
            suggestions = ["ThinkPad X1 Carbon", "Dell XPS 15", "LG Gram 17"]
    
    elif "관리번호" in user_message or "asset number" in user_message:
        # Generate a sample asset number
        from datetime import datetime
        import uuid
        current_year = datetime.now().year
        asset_number = f"AMS-{current_year}-{str(uuid.uuid4())[:8]}"
        
        response_text = f"새로운 자산의 관리번호로 '{asset_number}'를 생성했습니다. 이 번호를 사용하시겠어요?"
        suggestions = ["예, 사용하겠습니다", "아니오, 다른 번호를 생성해주세요"]
        asset_info = {"asset_number": asset_number}
    
    elif "사용자" in user_message or "user" in user_message:
        response_text = "자산의 사용자 정보를 입력해주세요. 이름 또는 사원번호를 입력하시면 됩니다."
        suggestions = ["사용자 검색하기"]
    
    elif "site" in user_message or "지점" in user_message or "위치" in user_message:
        response_text = "자산이 위치한 지점을 선택해주세요."
        suggestions = ["판교 본사", "고양 지사", "압구정 LF", "마곡 LG Science Park", "역삼 GS 타워"]
    
    elif "도움" in user_message or "help" in user_message:
        response_text = "다음과 같은 도움을 드릴 수 있습니다:\n- 자산 등록 과정 안내\n- 모델명으로 스펙 정보 검색\n- 관리번호 자동 생성\n- 사용자 정보 입력 도움\n- 지점 정보 입력 도움"
        suggestions = ["자산 등록 도움", "모델명으로 스펙 검색", "관리번호 생성", "사용자 정보 입력", "지점 정보 입력"]
    
    else:
        response_text = "죄송합니다. 질문을 이해하지 못했습니다. 자산 등록, 스펙 검색, 관리번호 생성 등에 대해 물어보시면 도움을 드릴 수 있어요."
        suggestions = ["자산 등록 도움", "모델명으로 스펙 검색", "관리번호 생성"]
    
    # Create and return the response
    response = ChatResponse(
        message=response_text,
        timestamp=datetime.now(),
        suggestions=suggestions,
        asset_info=asset_info
    )
    
    # Store the response in chat history
    chat_history.append(response.dict())
    
    return response

@router.get("/history")
async def get_chat_history():
    """
    Get the chat history.
    """
    return chat_history

@router.delete("/history")
async def clear_chat_history():
    """
    Clear the chat history.
    """
    chat_history.clear()
    return {"message": "Chat history cleared"}

@router.post("/asset-assist")
async def get_asset_assistance(
    model_name: Optional[str] = Body(None),
    serial_number: Optional[str] = Body(None),
    manufacturer: Optional[str] = Body(None)
):
    """
    Get assistance for asset registration based on model name, serial number, etc.
    """
    response = {
        "suggestions": [],
        "specs": {},
        "asset_number": None
    }
    
    # Generate asset number
    from datetime import datetime
    import uuid
    current_year = datetime.now().year
    response["asset_number"] = f"AMS-{current_year}-{str(uuid.uuid4())[:8]}"
    
    # Process model name if provided
    if model_name:
        if "thinkpad" in model_name.lower():
            response["specs"] = {
                "cpu": "Intel Core i7-1165G7",
                "ram": "16GB",
                "storage": "512GB SSD",
                "display": "14-inch FHD+"
            }
            if not manufacturer:
                response["suggestions"].append("제조사를 'Lenovo'로 설정하시겠어요?")
        elif "dell" in model_name.lower() or "xps" in model_name.lower():
            response["specs"] = {
                "cpu": "Intel Core i9-11900H",
                "ram": "32GB",
                "storage": "1TB SSD",
                "display": "15.6-inch 4K OLED"
            }
            if not manufacturer:
                response["suggestions"].append("제조사를 'Dell'로 설정하시겠어요?")
        elif "lg" in model_name.lower() or "gram" in model_name.lower():
            response["specs"] = {
                "cpu": "Intel Core i7-1165G7",
                "ram": "16GB",
                "storage": "512GB SSD",
                "display": "17-inch WQXGA"
            }
            if not manufacturer:
                response["suggestions"].append("제조사를 'LG'로 설정하시겠어요?")
    
    # Add general suggestions
    response["suggestions"].append("자산 유형을 선택해주세요")
    response["suggestions"].append("지점 정보를 입력해주세요")
    response["suggestions"].append("사용자 정보를 입력해주세요")
    
    return response