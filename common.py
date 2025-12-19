# ============================================================
# common.py의 get_latest_news_from_gsheet 함수를 교체하세요
# (701-745번 줄)
# ============================================================

def get_latest_news_from_gsheet(limit: int = 5):
    """
    구글 시트에서 최신 뉴스 N개 조회
    
    Args:
        limit: 가져올 뉴스 개수 (기본 5개)
    
    Returns:
        뉴스 리스트 (딕셔너리 형태)
    """
    global gsheet_worksheet
    
    if not gsheet_worksheet:
        logger.warning("⚠️ Google Sheets not initialized")
        return []
    
    try:
        # 전체 레코드 가져오기
        all_records = gsheet_worksheet.get_all_records()
        
        if not all_records:
            logger.warning("⚠️ No records in Google Sheets")
            return []
        
        # 최신순 정렬 (timestamp 기준)
        sorted_records = sorted(
            all_records,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        # 상위 limit개 추출 및 변환
        latest_news = []
        for record in sorted_records[:limit]:
            # relevance_score 확인 (점수 없으면 0)
            score = record.get('relevance_score', 0)
            if isinstance(score, str):
                try:
                    score = int(score)
                except:
                    score = 0
            
            # 점수 필터링 (75점 이상만)
            if score >= 75:
                latest_news.append({
                    'title': record.get('title', ''),
                    'description': record.get('description', ''),
                    'link': record.get('url', ''),  # ✅ url→link 변환!
                    'url': record.get('url', ''),   # ✅ url도 포함
                    'originallink': record.get('url', ''),  # ✅ originallink도 포함
                    'relevance_score': score,
                    'keywords': record.get('keywords', '').split(',') if record.get('keywords') else [],
                    'region': record.get('region', ''),
                    'category': record.get('category', ''),
                    'has_price': record.get('has_price', False),
                    'has_policy': record.get('has_policy', False),
                    'timestamp': record.get('timestamp', ''),
                    'is_relevant': True
                })
            
            # limit개 채우면 중단
            if len(latest_news) >= limit:
                break
        
        logger.info(f"✅ 구글 시트 조회: {len(latest_news)}개 (전체 {len(all_records)}개 중)")
        
        return latest_news
        
    except Exception as e:
        logger.error(f"❌ 최신 뉴스 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
