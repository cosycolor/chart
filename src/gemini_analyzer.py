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

        prompt = f"""
당신은 대한민국 주식 시장의 전문 애널리스트입니다.
아래 제공된 종목 정보와 관련 뉴스 목록을 면밀히 분석하여, 기준일자({target_date_formatted}) 당일 이 종목이 급등(상한가 또는 대량거래)한 **진짜 핵심 상승 이유**를 판별해주세요.

[종목 정보]
- 종목명: {stock_info['name']} ({stock_info['code']})
- 기준일자: {target_date_formatted}
- 당일 등락률: {stock_info['change_rate']}% ({'상한가' if stock_info['is_upper_limit'] else '대량거래 급등'})
- 당일 거래량: {stock_info['volume_str']}
- 시가총액: {stock_info['market_cap_str']}

[수집된 기사 목록]
{news_context}

[분석 및 판별 가이드라인 (엄격 준수)]
1. **기사 최신성 및 당일 재료 필수 검증**:
   - 반드시 **기준일자({target_date_formatted}) 당일 또는 직전 1~2거래일 이내**에 발생한 직접적인 최신 뉴스/호재/공시(예: 수주, 실적, 신사업, 정책, 테마 등)만을 상승 이유로 채택하세요.
   - **절대 수주 전 또는 수개월 전(과거) 기사를 오늘의 상승 이유로 설명하지 마세요.**
2. **종목과의 직접적인 연관성 검증 (노이즈 배제)**:
   - 기사의 핵심 내용이 대상 종목 '{stock_info['name']}'과 직접적으로 관련된 기사만 채택하세요.
   - **증권사 비리/IPO 논란, 지수 종합 브리핑, 타사 실적 기사 등 단순히 본문에 종목명이 스쳐 지나가는 무관한 기사는 절대 채택하지 마세요.**
   - 만약 수집된 기사 중 대상 종목의 직접적인 호재 기사가 없는 경우, 억지로 무관한 기사를 엮지 말고 **"당일 특정 개별 호재 공시는 확인되지 않으며, 대량 거래량 유입 및 관련 테마 순환매에 따른 기술적 수급 집중으로 추정"**과 같이 사실대로 정확하게 기술하세요.
3. **대표 기사(`top_articles`) 엄선**:
   - 대상 종목과 직접적인 연관성이 확인된 신뢰할 수 있는 기사만 1~2개 포함하세요.
   - 연관성이 낮거나 무관한 기사만 있을 경우 `top_articles`를 빈 리스트 `[]`로 남겨두세요.
4. 블로그 독자가 한눈에 읽기 쉽게 핵심 1문장 및 2~3개 불렛포인트로 정리하세요.

반드시 아래 JSON 형식으로만 답변하세요:
```json
{{
  "core_reason": "핵심 상승 이유 (1문장, 예: 젠슨 황 CEO의 AI 보안 발언에 따른 차세대 양자암호 보안 기술 수혜 부각)",
  "detail_points": [
    "상세 이유 및 배경 1",
    "상세 이유 및 배경 2",
    "상세 이유 및 배경 3 (필요시)"
  ],
  "theme_keywords": ["보안", "AI", "양자암호"],
  "top_articles": [
    {{
      "title": "기사 헤드라인 제목 1",
      "url": "기사 직접 링크 URL 1",
      "media": "언론사명 1"
    }},
    {{
      "title": "기사 헤드라인 제목 2",
      "url": "기사 직접 링크 URL 2",
      "media": "언론사명 2"
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
                # top_articles 보장
                if "top_articles" not in parsed or not parsed["top_articles"]:
                    parsed["top_articles"] = self._build_top_articles_from_news(news_list)
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
        """뉴스 목록에서 유효한 최근 기사만 추출, 없으면 네이버 증권 시황 링크 제공"""
        articles = []
        for n in news_list[:3]:
            # 기사 제목과 URL이 유효하고, 종목명 연관도 점수가 있거나 적절한 기사만
            if n.get("title") and n.get("link"):
                # 점수가 0 이하이고 무관한 제목인 경우 건너뛰기
                if stock_name and stock_name not in n.get("title", "") and n.get("score", 0) <= 0:
                    continue
                articles.append({
                    "title": n.get("title", ""),
                    "url": n.get("link", ""),
                    "media": n.get("media", "언론사")
                })
        
        if not articles and stock_code:
            articles = [{
                "title": f"{stock_name or '종목'} 네이버 증권 실시간 시황 바로가기",
                "url": f"https://finance.naver.com/item/main.naver?code={stock_code}",
                "media": "네이버증권"
            }]
        return articles

    def _generate_fallback_response(self, stock_info: Dict[str, Any], news_list: List[Dict[str, str]], reason: str) -> Dict[str, Any]:
        """API 미연결 시 수집된 실기사 기반 Fallback"""
        top_articles = self._build_top_articles_from_news(news_list, stock_code=stock_info.get('code', ''), stock_name=stock_info.get('name', ''))
        
        first_title = ""
        for art in top_articles:
            if "시황 바로가기" not in art.get('title', ''):
                first_title = art.get('title', '')
                break

        detail_points = [
            f"당일 등락률: +{stock_info['change_rate']}% (거래량: {stock_info['volume_str']})",
            f"최근 실적: 매출 {stock_info.get('quarter_revenue', '-')}, 당기순익 {stock_info.get('quarter_net_income', '-')}"
        ]
        if first_title:
            detail_points.insert(0, f"관련 주요 보도: {first_title}")

        return {
            "core_reason": f"{stock_info['name']} 당일 {stock_info['change_rate']}% 급등 및 대량 거래량({stock_info['volume_str']}) 유입",
            "detail_points": detail_points,
            "theme_keywords": [stock_info['market'], "특징주", "급등주"],
            "top_articles": top_articles
        }
