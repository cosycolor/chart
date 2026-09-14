import os
import json
import re
from typing import Dict, List, Any

class GeminiStockAnalyzer:
    """
    Google Gemini LLM을 활용하여 당일 수집된 뉴스를 바탕으로
    종목의 상승/상한가 원인을 정확하게 분석하고 2~3개의 대표 기사를 선정하는 모듈
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            print(f"⚠️ google-genai 초기화 실패: {e}")

    def analyze_stock_surge_reason(self, stock_info: Dict[str, Any], news_list: List[Dict[str, str]], target_date: str = "") -> Dict[str, Any]:
        """
        종목 시세 정보와 뉴스 목록을 Gemini에 전달하여 핵심 상승 이유와 대표 기사 2~3개를 추출합니다.
        """
        if not self.client:
            return self._generate_fallback_response(stock_info, news_list, "GEMINI_API_KEY가 설정되지 않아 수집된 뉴스를 바탕으로 기본 정리되었습니다.")

        if not news_list:
            return self._generate_fallback_response(stock_info, news_list, "당일 특정 개별 호재 기사가 확인되지 않아 수급 유입 또는 테마 동조화로 추정됩니다.")

        news_context = ""
        for i, news in enumerate(news_list, 1):
            date_info = f" ({news.get('date')})" if news.get('date') else ""
            news_context += f"[{i}] 제목: {news.get('title', '')}\n"
            news_context += f"    언론사: {news.get('media', '언론사')}{date_info}\n"
            news_context += f"    요약: {news.get('description', '')}\n"
            news_context += f"    직접링크: {news.get('link', '')}\n\n"

        target_date_formatted = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}" if (target_date and len(target_date) == 8) else target_date

        change_rate = stock_info['change_rate']
        rate_sign = "+" if change_rate > 0 else ""
        
        if stock_info['is_upper_limit']:
            trend_type = "상한가"
            task_desc = "이 종목이 **상한가에 도달한 진짜 핵심 상승 이유**를 분석해주세요."
            reason_hint = "핵심 상승 이유 (1문장, 예: AI 데이터센터 증설에 따른 전력 변압기 공급 계약 체결로 실적 성장 기대감 부각)"
        elif change_rate > 0:
            trend_type = f"주가 상승(+{change_rate}%) 및 1,000만주 이상 대량거래"
            task_desc = f"이 종목이 **당일 주가 상승(+{change_rate}%) 및 대량 거래가 터진 핵심 상승 이유**를 분석해주세요."
            reason_hint = f"핵심 상승 이유 (1문장, 예: 신규 수주 확대 및 3분기 흑자전환 기대감에 따른 매수세 유입)"
        elif change_rate < 0:
            trend_type = f"주가 하락({change_rate}%) 및 1,000만주 이상 대량거래"
            task_desc = f"이 종목이 **당일 주가 하락({change_rate}%)을 기록하며 대량 거래가 터진 핵심 원인(차익실현 매물, 유상증자/CB, 단기 과열 해소, 악재 공시 등)**을 분석해주세요."
            reason_hint = f"핵심 변동/하락 원인 (1문장, 예: 전일 급등에 따른 차익실현 매물 출회 및 대규모 거래량 유입)"
        else:
            trend_type = "보합(0.0%) 및 1,000만주 이상 대량거래"
            task_desc = "이 종목이 **당일 대량 거래를 동반하며 치열한 매공방을 벌인 핵심 배경**을 분석해주세요."
            reason_hint = "핵심 거래 요인 (1문장, 예: 테마 형성 기대감과 차익 실현 매물이 맞물리며 대량 거래량 수반)"

        prompt = f"""
당신은 대한민국 주식 시장의 전문 애널리스트입니다.
아래 제공된 종목 정보와 관련 뉴스 목록을 면밀히 분석하여, 기준일자({target_date_formatted}) 당일 {task_desc}

[종목 정보]
- 종목명: {stock_info['name']} ({stock_info['code']})
- 기준일자: {target_date_formatted}
- 당일 등락률: {rate_sign}{change_rate}% ({trend_type})
- 당일 거래량: {stock_info['volume_str']}
- 시가총액: {stock_info['market_cap_str']}

[수집된 기사 목록]
{news_context}

[분석 및 판별 가이드라인 (엄격 준수)]
1. **기사의 직접적 연관성 및 주체 검증 (노이즈 배제)**:
   - 기사의 핵심 주인공(주어)이 반드시 대상 종목 '{stock_info['name']}'이어야 합니다.
   - **타 종목의 급등 기사 본문 끝에 단순히 동종업계나 관련주로 종목명이 스쳐 지나간 기사는 대상 종목의 원인으로 삼지 마세요.**
   - **지수 종합 브리핑(코스피/코스닥 마감 등), 타사 실적/IPO 기사, 증시 일정 등 단순 나열식 기사는 절대 채택하지 마세요.**
2. **직접 호재/악재 부재 시 억지 추론 금지**:
   - 수집된 기사 중 대상 종목 자체의 직접적인 원인이 확인되지 않는 경우, **절대로 무관한 타 종목 기사를 엮어서 지어내지 마세요.**
   - 이 경우 반드시 **"당일 특정 개별 공시는 확인되지 않으며, 대량 거래량 유입에 따른 기술적 수급 변동으로 추정"**과 같이 사실대로 서술하고 `top_articles`는 반드시 빈 배열 `[]`로 반환하세요.
3. **기사 최신성 검증**:
   - 반드시 **기준일자({target_date_formatted}) 당일 또는 직전 1~2거래일 이내**에 발생한 직접적인 최신 뉴스/공시만 채택하세요. 과거(수주 전, 수개월 전) 기사는 오늘의 이유로 설명하지 마세요.
4. **대표 기사(`top_articles`) 엄선**:
   - 대상 종목 '{stock_info['name']}'이 제목 또는 본문의 핵심 주체로서 직접적인 호재/원인이 확인된 기사만 최대 2개 포함하세요.
   - 직접 연관성이 떨어지는 기사만 있다면 **반드시 빈 리스트 `[]`**로 두세요.

반드시 아래 JSON 형식으로만 답변하세요:
```json
{{
  "core_reason": "{reason_hint}",
  "detail_points": [
    "상세 이유 및 배경 1",
    "상세 이유 및 배경 2",
    "상세 이유 및 배경 3 (필요시)"
  ],
  "theme_keywords": ["테마1", "테마2", "테마3"],
  "top_articles": [
    {{
      "title": "기사 헤드라인 제목 1",
      "url": "기사 직접 링크 URL 1",
      "media": "언론사명 1"
    }}
  ]
}}
```
"""

        models_to_try = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite']
        
        for attempt, model_name in enumerate(models_to_try):
            try:
                import time
                time.sleep(1.2)  # 무료 티어 Rate limit(RPM) 방지 딜레이
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                
                raw_text = response.text.strip()
                cleaned_json = re.sub(r'^```json\s*', '', raw_text, flags=re.MULTILINE)
                cleaned_json = re.sub(r'\s*```$', '', cleaned_json, flags=re.MULTILINE).strip()
                
                parsed = json.loads(cleaned_json)
                
                # top_articles 검증: LLM이 반환하지 않았거나 누락된 경우에만 안전하게 처리
                if "top_articles" not in parsed:
                    parsed["top_articles"] = []
                else:
                    # 반환된 기사들 중에서도 종목명 연관성이 유효한 기사만 최종 필터링
                    valid_articles = []
                    for art in parsed.get("top_articles", []):
                        art_title = art.get("title", "")
                        art_url = art.get("url", "")
                        if art_title and art_url:
                            valid_articles.append(art)
                    parsed["top_articles"] = valid_articles

                return parsed

            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [{stock_info['name']}] 모델 {model_name} 실패: {err_str[:100]}...")
                if "RESOURCE_EXHAUSTED" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "503" in err_str:
                    import time
                    time.sleep(3)  # 잠시 대기 후 대체 모델로 재시도
                    continue
                else:
                    break

        print(f"⚠️ [{stock_info['name']}] 모든 Gemini 모델 시도 실패, Fallback 적용")
        return self._generate_fallback_response(stock_info, news_list, "분석 중 오류 발생")

    def _build_top_articles_from_news(self, news_list: List[Dict[str, str]], stock_code: str = "", stock_name: str = "") -> List[Dict[str, str]]:
        """뉴스 목록에서 종목명과 직접 연관된 기사만 추출"""
        articles = []
        for n in news_list[:3]:
            title = n.get("title", "")
            link = n.get("link", "")
            if title and link:
                if stock_name and stock_name in title:
                    articles.append({
                        "title": title,
                        "url": link,
                        "media": n.get("media", "언론사")
                    })
                elif n.get("score", 0) >= 10:
                    articles.append({
                        "title": title,
                        "url": link,
                        "media": n.get("media", "언론사")
                    })
        
        return articles[:2]

    def _generate_fallback_response(self, stock_info: Dict[str, Any], news_list: List[Dict[str, str]], reason: str) -> Dict[str, Any]:
        """API 미연결 시 수집된 실기사 기반 Fallback"""
        top_articles = self._build_top_articles_from_news(news_list, stock_code=stock_info.get('code', ''), stock_name=stock_info.get('name', ''))
        
        first_title = ""
        for art in top_articles:
            if "시황 바로가기" not in art.get('title', ''):
                first_title = art.get('title', '')
                break

        change_rate = stock_info['change_rate']
        rate_sign = "+" if change_rate > 0 else ""

        detail_points = [
            f"당일 등락률: {rate_sign}{change_rate}% (거래량: {stock_info['volume_str']})",
            f"최근 실적: 매출 {stock_info.get('quarter_revenue', '-')}, 당기순익 {stock_info.get('quarter_net_income', '-')}"
        ]
        if first_title:
            detail_points.insert(0, f"관련 주요 보도: {first_title}")

        if change_rate > 0:
            core_reason = f"{stock_info['name']} 당일 +{change_rate}% 상승 및 대량 거래량({stock_info['volume_str']}) 유입"
            theme_kw = [stock_info['market'], "특징주", "급등주"]
        elif change_rate < 0:
            core_reason = f"{stock_info['name']} 당일 {change_rate}% 하락 및 대량 거래량({stock_info['volume_str']}) 발생"
            theme_kw = [stock_info['market'], "특징주", "대량거래"]
        else:
            core_reason = f"{stock_info['name']} 당일 보합 마감 및 대량 거래량({stock_info['volume_str']}) 발생"
            theme_kw = [stock_info['market'], "특징주", "대량거래"]

        return {
            "core_reason": core_reason,
            "detail_points": detail_points,
            "theme_keywords": theme_kw,
            "top_articles": top_articles
        }
