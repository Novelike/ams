# novelike/chatbot.py

import os
import openai

# OpenAI API 키 & 기본 모델명
api_key   = os.getenv("OPENAI_API_KEY", "")
modelName = "gpt-3.5-turbo"
openai.api_key = api_key

def send_message(messages: list, model: str = modelName) -> str:
	"""
	ChatCompletion 메시지 전송 헬퍼
	messages: [{"role":"user","content":"..."} , ...]
	"""
	resp = openai.ChatCompletion.create(
		model=model,
		messages=messages,
		temperature=0.7,
	)
	return resp.choices[0].message.content

def suggest_specs(model_name: str) -> str:
	"""
	모델명 기반으로 스펙 추천 요청 예시
	"""
	msgs = [
		{"role":"system", "content":"자산 관리 시스템용 스펙 추천 도우미입니다."},
		{"role":"user",   "content":f"모델명이 '{model_name}'인 노트북의 주요 스펙을 알려줘."}
	]
	return send_message(msgs)
