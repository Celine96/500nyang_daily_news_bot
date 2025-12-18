"""
오백냥(500nyang) 부동산 뉴스봇 서버
- 카카오톡으로 최신 부동산 뉴스 제공
- 구글 시트 기반 뉴스 조회
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

# 공통 함수 임포트
from common import (
    get_latest_news_from_gsheet,
    init_google_sheets,
    init_csv_file
)

# ================================================================================
# 로깅 설정
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="오백냥 - 부동산 뉴스봇",
    description="카카오톡 부동산 뉴스 제공 서비스",
    version="1.0.0"
)

# ================================================================================
# Pydantic 모델
# ================================================================================

class UserInfo(BaseModel):
    id: str

class UserRequest(BaseModel):
    user: UserInfo
    utterance: Optional[str] = ""

class RequestBody(BaseModel):
    userRequest: UserRequest

# ================================================================================
# API 엔드포인트
# ================================================================================

@app.post("/news")
async def news_bot(request: RequestBody):
    """
    부동산 뉴스봇 - 최신 뉴스 5개 제공
    
    카카오톡 스킬 서버 엔드포인트
    """
    logger.info("=" * 50)
    logger.info("📰 News bot request")
    
    try:
        # 사용자 ID 추출
        user_id = request.userRequest.user.id
        logger.info(f"   User: {user_id}")
        
        # 구글 시트에서 최신 뉴스 5개 조회
        news_items = get_latest_news_from_gsheet(limit=5)
        
        if not news_items or len(news_items) == 0:
            logger.warning("⚠️ 구글 시트에 뉴스 없음")
            return {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {"simpleText": {"text": "최신 뉴스를 준비 중입니다. 잠시 후 다시 시도해주세요."}}
                    ]
                }
            }
        
        logger.info(f"✅ 구글 시트 조회 완료: {len(news_items)}개")
        
        # 로깅
        for idx, item in enumerate(news_items, 1):
            logger.info(
                f"   [{idx}] {item['title'][:40]}... "
                f"(점수: {item.get('relevance_score', 0)})"
            )
        
        # 뉴스 리스트 텍스트 생성
        news_list = f"📰 오늘의 부동산 뉴스 (총 {len(news_items)}건)\n\n"
        
        for idx, item in enumerate(news_items, 1):
            title = item.get('title', '제목 없음')
            url = item.get('link', '')
            
            # URL 확인
            if not url:
                logger.warning(f"   ⚠️ 뉴스 {idx} URL 없음: {title[:30]}")
                url = "(URL 정보 없음)"
            
            # 제목 + URL
            news_list += f"{idx}. {title}\n{url}\n\n"
        
        logger.info(f"✅ 응답 완료")
        
        # 카카오톡 응답
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": news_list.strip()
                        }
                    }
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ News bot error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": "뉴스를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}}
                ]
            }
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "오백냥 부동산 뉴스봇",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health/ping")
async def health_ping():
    """Simple ping endpoint"""
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat()
    }

# ================================================================================
# Startup & Shutdown
# ================================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("=" * 70)
    logger.info("🚀 Starting 오백냥 뉴스봇 서버...")
    logger.info("=" * 70)
    
    # CSV/Sheets 초기화
    csv_success = init_csv_file()
    gsheet_success = init_google_sheets()
    
    if csv_success:
        logger.info("✅ CSV logging enabled")
    if gsheet_success:
        logger.info("✅ Google Sheets logging enabled")
    
    logger.info("=" * 70)
    logger.info("✅ 오백냥 뉴스봇 서버 시작 완료!")
    logger.info("   - 서비스: 부동산 뉴스 제공")
    logger.info("   - 엔드포인트: /news")
    logger.info("=" * 70)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    logger.info("👋 Shutting down 오백냥 뉴스봇...")
    logger.info("✅ Shutdown complete")
