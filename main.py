"""
오백냥(500nyang) 부동산 뉴스봇 서버 (카테고리 지원)
- 카카오톡으로 최신 부동산 뉴스 제공
- 카테고리별 뉴스 필터링
- 구글 시트 기반 뉴스 조회
"""

import logging
import os
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI
from pydantic import BaseModel

# 공통 함수 임포트
from common import (
    get_latest_news_from_gsheet,
    init_google_sheets,
    init_csv_file,
    gsheet_worksheet
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
    description="카카오톡 부동산 뉴스 제공 서비스 (카테고리 지원)",
    version="2.0.0"
)

# ================================================================================
# 카테고리 정의
# ================================================================================

CATEGORIES = {
    "정책·제도": ["정책", "제도", "규제"],
    "시장 동향·시황": ["시장", "동향", "시황", "가격", "상승", "하락"],
    "분양·청약": ["분양", "청약"],
    "개발·재건축·재개발": ["개발", "재건축", "재개발"],
    "금융·대출·금리": ["금융", "대출", "금리"],
    "세금·법률·규제": ["세금", "법률", "취득세", "양도세"]
}

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
# Helper Functions
# ================================================================================

def detect_category(message: str) -> Optional[str]:
    """
    사용자 메시지에서 카테고리 감지
    
    Args:
        message: 사용자 발화
    
    Returns:
        감지된 카테고리명 또는 None
    """
    message_lower = message.lower().replace(" ", "")
    
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in message_lower:
                logger.info(f"✅ 카테고리 감지: '{message}' → {category}")
                return category
    
    return None

def get_news_by_category(category: str, limit: int = 5) -> List[dict]:
    """
    구글 시트에서 특정 카테고리 뉴스 조회
    
    Args:
        category: 카테고리명
        limit: 최대 개수
    
    Returns:
        뉴스 리스트
    """
    try:
        if not gsheet_worksheet:
            logger.warning("⚠️ Google Sheets not initialized")
            return []
        
        # 전체 데이터 조회
        all_records = gsheet_worksheet.get_all_records()
        
        # 카테고리 필터링
        filtered = [
            record for record in all_records
            if record.get('category') == category
        ]
        
        # 최신순 정렬 (timestamp 기준)
        filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"📂 [{category}] {len(filtered)}개 → 상위 {limit}개")
        
        return filtered[:limit]
        
    except Exception as e:
        logger.error(f"❌ 카테고리 조회 실패: {e}")
        return []

def format_news_list(news_items: List[dict], category: Optional[str] = None) -> str:
    """
    뉴스 리스트를 카카오톡 메시지 포맷으로 변환
    
    Args:
        news_items: 뉴스 리스트
        category: 카테고리명 (Optional)
    
    Returns:
        포맷된 텍스트
    """
    if category:
        emoji_map = {
            "정책·제도": "📋",
            "시장 동향·시황": "📈",
            "분양·청약": "🏗️",
            "개발·재건축·재개발": "🔨",
            "금융·대출·금리": "💰",
            "세금·법률·규제": "⚖️"
        }
        emoji = emoji_map.get(category, "📰")
        news_list = f"{emoji} {category} 뉴스 (총 {len(news_items)}건)\n\n"
    else:
        news_list = f"📰 오늘의 부동산 뉴스 (총 {len(news_items)}건)\n\n"
    
    for idx, item in enumerate(news_items, 1):
        title = item.get('title', '제목 없음')
        url = item.get('link', item.get('url', ''))
        
        # URL 확인
        if not url:
            logger.warning(f"   ⚠️ 뉴스 {idx} URL 없음: {title[:30]}")
            url = "(URL 정보 없음)"
        
        # 제목 + URL
        news_list += f"{idx}. {title}\n{url}\n\n"
    
    # 카테고리 메뉴 추가 (전체 뉴스일 경우)
    if not category:
        news_list += "\n💡 카테고리별 보기:\n정책, 시장, 분양, 재건축, 대출, 세금"
    
    return news_list.strip()

# ================================================================================
# API 엔드포인트
# ================================================================================

@app.post("/news")
async def news_bot(request: RequestBody):
    """
    부동산 뉴스봇 - 최신 뉴스 또는 카테고리별 뉴스 제공
    
    사용자 발화 예시:
    - "부동산 뉴스" → 전체 뉴스 5개
    - "정책 뉴스" → 정책·제도 카테고리 뉴스
    - "시장 동향" → 시장 동향·시황 카테고리 뉴스
    """
    logger.info("=" * 50)
    logger.info("📰 News bot request")
    
    try:
        # 사용자 정보 추출
        user_id = request.userRequest.user.id
        user_message = request.userRequest.utterance
        
        logger.info(f"   User: {user_id}")
        logger.info(f"   Message: '{user_message}'")
        
        # 카테고리 감지
        detected_category = detect_category(user_message)
        
        # 뉴스 조회
        if detected_category:
            # 특정 카테고리 뉴스
            news_items = get_news_by_category(detected_category, limit=5)
            
            if not news_items:
                logger.warning(f"⚠️ [{detected_category}] 뉴스 없음")
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {"simpleText": {
                                "text": f"{detected_category} 관련 뉴스가 아직 없습니다.\n\n"
                                        "전체 뉴스를 보시려면 '부동산 뉴스'를 입력해주세요."
                            }}
                        ]
                    }
                }
        else:
            # 전체 뉴스
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
        
        logger.info(f"✅ 뉴스 조회 완료: {len(news_items)}개")
        
        # 로깅
        for idx, item in enumerate(news_items, 1):
            logger.info(
                f"   [{idx}] {item.get('title', '')[:40]}... "
                f"(점수: {item.get('relevance_score', 0)})"
            )
        
        # 뉴스 리스트 텍스트 생성
        news_text = format_news_list(news_items, detected_category)
        
        logger.info(f"✅ 응답 완료")
        
        # 카카오톡 응답
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": news_text
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
        "version": "2.0.0",
        "features": ["news", "category"],
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
    
    # 카테고리 출력
    logger.info("📂 지원 카테고리:")
    for category in CATEGORIES.keys():
        logger.info(f"   - {category}")
    
    logger.info("=" * 70)
    logger.info("✅ 오백냥 뉴스봇 서버 시작 완료!")
    logger.info("   - 서비스: 부동산 뉴스 제공")
    logger.info("   - 엔드포인트: /news")
    logger.info("   - 카테고리: 지원")
    logger.info("=" * 70)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    logger.info("👋 Shutting down 오백냥 뉴스봇...")
    logger.info("✅ Shutdown complete")
