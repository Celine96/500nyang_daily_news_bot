"""
오백냥(500nyang) 부동산 뉴스봇 서버
- 카테고리별 뉴스 제공
- /new와 /news 모두 지원
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

# 현재 작동 중인 common.py에서 import
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
    description="카카오톡 부동산 뉴스 제공 서비스 (카테고리별)",
    version="2.0.1"
)

# ================================================================================
# 카테고리 매핑
# ================================================================================

CATEGORY_MAP = {
    "정책": "정책·제도",
    "제도": "정책·제도",
    "정책제도": "정책·제도",
    
    "시장": "시장 동향·시황",
    "동향": "시장 동향·시황",
    "시황": "시장 동향·시황",
    "시장동향": "시장 동향·시황",
    
    "분양": "분양·청약",
    "청약": "분양·청약",
    "분양청약": "분양·청약",
    
    "개발": "개발·재건축·재개발",
    "재건축": "개발·재건축·재개발",
    "재개발": "개발·재건축·재개발",
    "개발재건축": "개발·재건축·재개발",
    
    "금융": "금융·대출·금리",
    "대출": "금융·대출·금리",
    "금리": "금융·대출·금리",
    "금융대출": "금융·대출·금리",
    
    "세금": "세금·법률·규제",
    "법률": "세금·법률·규제",
    "규제": "세금·법률·규제",
    "세금법률": "세금·법률·규제",
}

CATEGORY_EMOJI = {
    "정책·제도": "📋",
    "시장 동향·시황": "📊",
    "분양·청약": "🏗️",
    "개발·재건축·재개발": "🏢",
    "금융·대출·금리": "💰",
    "세금·법률·규제": "⚖️",
}

# ================================================================================
# Pydantic 모델
# ================================================================================

class UserInfo(BaseModel):
    id: str
    properties: Optional[Dict[str, Any]] = None

class UserRequest(BaseModel):
    user: UserInfo
    utterance: Optional[str] = ""
    params: Optional[Dict[str, Any]] = {}
    block: Optional[Dict[str, Any]] = {}
    lang: Optional[str] = None

class Action(BaseModel):
    name: Optional[str] = None
    clientExtra: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = {}
    detailParams: Optional[Dict[str, Any]] = {}
    id: Optional[str] = None

class Bot(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None

class RequestBody(BaseModel):
    userRequest: UserRequest
    action: Optional[Action] = None
    bot: Optional[Bot] = None
    contexts: Optional[list] = []

# ================================================================================
# 카테고리 감지 함수
# ================================================================================

def detect_category(user_message: str) -> Optional[str]:
    """
    사용자 발화에서 카테고리 감지
    
    Args:
        user_message: 사용자 발화 내용
        
    Returns:
        감지된 카테고리 또는 None
    """
    if not user_message:
        return None
    
    # 공백 제거 후 소문자 변환
    message = user_message.replace(" ", "").lower()
    
    # 카테고리 매핑에서 찾기
    for keyword, category in CATEGORY_MAP.items():
        if keyword in message:
            logger.info(f"🎯 카테고리 감지: '{keyword}' → '{category}'")
            return category
    
    return None

def normalize_category(category: str) -> str:
    """
    카테고리 문자열 정규화 (공백, 특수문자 통일)
    """
    if not category:
        return ""
    # 앞뒤 공백 제거, 소문자 변환
    normalized = category.strip()
    return normalized

def get_news_by_category(category: str, limit: int = 3) -> list:
    """
    특정 카테고리의 최신 뉴스 조회
    
    Args:
        category: 카테고리명
        limit: 조회할 뉴스 개수
        
    Returns:
        뉴스 리스트
    """
    try:
        # 전체 뉴스 조회 (더 많이 가져오기)
        all_news = get_latest_news_from_gsheet(limit=200)
        
        if not all_news:
            logger.warning("⚠️ 구글 시트에 뉴스가 없습니다")
            return []
        
        # 정규화된 카테고리로 비교
        normalized_target = normalize_category(category)
        logger.info(f"🔍 찾으려는 카테고리: '{normalized_target}'")
        
        # 카테고리 필터링 (대소문자 구분 없이)
        filtered_news = []
        
        # 디버깅: 모든 카테고리 출력
        all_categories = set()
        for news in all_news:
            news_category = normalize_category(news.get('category', ''))
            all_categories.add(news_category)
            
            # 카테고리 비교 (대소문자 구분 없이)
            if news_category.lower() == normalized_target.lower():
                filtered_news.append(news)
        
        logger.info(f"📊 구글 시트의 모든 카테고리: {all_categories}")
        logger.info(f"📊 카테고리 '{normalized_target}': {len(filtered_news)}개 (전체 {len(all_news)}개 중)")
        
        # 디버깅: 매칭된 뉴스 로그
        for idx, news in enumerate(filtered_news[:5]):
            logger.info(
                f"   [{idx+1}] {news.get('title', '')[:40]}... "
                f"(카테고리: '{news.get('category', 'N/A')}')"
            )
        
        # 상위 N개만 반환
        return filtered_news[:limit]
        
    except Exception as e:
        logger.error(f"❌ 카테고리별 뉴스 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

# ================================================================================
# 뉴스봇 핸들러 (공통 로직)
# ================================================================================

async def handle_news_request(request: RequestBody):
    """
    뉴스봇 요청 처리 (공통 로직)
    """
    logger.info("=" * 50)
    logger.info("📰 News bot request")
    
    try:
        # 사용자 정보
        user_id = request.userRequest.user.id
        user_message = request.userRequest.utterance
        
        logger.info(f"   User: {user_id}")
        logger.info(f"   Message: '{user_message}'")
        
        # 카테고리 감지
        category = detect_category(user_message)
        
        if category:
            # 카테고리별 뉴스 조회
            news_items = get_news_by_category(category, limit=3)
            category_emoji = CATEGORY_EMOJI.get(category, "📰")
            
            if not news_items:
                # 카테고리는 감지했지만 해당 뉴스가 없는 경우
                logger.warning(f"⚠️ '{category}' 카테고리 뉴스 없음")
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": f"{category_emoji} '{category}' 카테고리의 최신 뉴스가 아직 없습니다.\n\n잠시 후 다시 시도해주시거나, 다른 카테고리를 선택해주세요."
                                }
                            }
                        ]
                    }
                }
            
            title_text = f"{category_emoji} {category} 뉴스 (총 {len(news_items)}건)"
        else:
            # 전체 최신 뉴스 5개 조회
            news_items = get_latest_news_from_gsheet(limit=5)
            title_text = f"📰 오늘의 부동산 뉴스 (총 {len(news_items)}건)"
        
        if not news_items:
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
                f"   [{idx}] {item.get('title', '')[:40]}... "
                f"(카테고리: {item.get('category', 'N/A')}, 점수: {item.get('relevance_score', 0)})"
            )
        
        # 뉴스 리스트 텍스트 생성
        news_list = f"{title_text}\n\n"
        
        for idx, item in enumerate(news_items, 1):
            title = item.get('title', '제목 없음')
            # url, link, originallink 모두 확인
            url = item.get('url') or item.get('link') or item.get('originallink', '')
            
            if not url:
                logger.warning(f"   ⚠️ 뉴스 {idx} URL 없음")
                url = "(URL 정보 없음)"
            else:
                logger.info(f"   뉴스 {idx}: URL = {url[:50]}")
            
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

# ================================================================================
# API 엔드포인트
# ================================================================================

@app.post("/news")
async def news_bot(request: RequestBody):
    """
    부동산 뉴스봇 - 카테고리별 뉴스 3개 제공 (/news)
    """
    return await handle_news_request(request)

@app.post("/new")
async def news_bot_legacy(request: RequestBody):
    """
    부동산 뉴스봇 - 카테고리별 뉴스 3개 제공 (/new - 하위 호환)
    """
    logger.warning("⚠️ /new 엔드포인트 사용됨 (deprecated, /news 사용 권장)")
    return await handle_news_request(request)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "오백냥 부동산 뉴스봇",
        "version": "2.0.1",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health/ping")
async def health_ping():
    """Simple ping endpoint"""
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "오백냥 부동산 뉴스봇",
        "version": "2.0.1",
        "endpoints": {
            "news": "/news (권장)",
            "new": "/new (하위 호환)",
            "health": "/health"
        }
    }

# ================================================================================
# Startup & Shutdown
# ================================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("=" * 70)
    logger.info("🚀 Starting 오백냥 뉴스봇 서버 (카테고리별)...")
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
    logger.info("   - 서비스: 카테고리별 부동산 뉴스 제공")
    logger.info("   - 엔드포인트: /news (권장), /new (하위 호환)")
    logger.info("   - 카테고리:")
    for cat in CATEGORY_EMOJI.keys():
        logger.info(f"      • {cat}")
    logger.info("=" * 70)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    logger.info("👋 Shutting down 오백냥 뉴스봇...")
    logger.info("✅ Shutdown complete")
