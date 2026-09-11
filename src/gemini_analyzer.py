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

    def analyze_stock_surge_reason(self, stock_info: Dict[str, Any], news_list: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        종목 시세 정보와 뉴스 목록을 Gemini에 전달하여 핵심 상승 이유와 대표 기사 2~3개를 추출합니다.
        """
        if not self.client:
            return self._generate_fallback_response(stock_info, news_list, "GEMINI_API_KEY가 설정되지 않아 수집된 뉴스를 바탕으로 기본 정리되었습니다.")

        if not news_list:
            return self._generate_fallback_response(stock_info, news_list, "당일 특정 개별 호재 기사가 확인되지 않아 수급 유입 또는 테마 동조화로 추정됩니다.")

        news_context = ""
        for i, news in enumerate(news_list, 1):
            news_context += f"[{i}] 제목: {news.get('title', '')}\n"
            news_context += f"    언론사: {news.get('media', '언론사')}\n"
            news_context += f"    요약: {news.get('description', '')}\n"
            news_context += f"    직접링크: {news.get('link', '')}\n\n"

        prompt = f"""
당신은 대한민국 주식 시장의 전문 애널리스트이자 팩트체커입니다.
아래 제공된 종목 정보와 오늘자 관련 뉴스 목록을 면밀히 분석하여, 이 종목이 오늘 급등(상한가 또는 대량거래)한 **진짜 핵심 상승 이유**를 판별해주세요.

[종목 정보]
- 종목명: {stock_info['name']} ({stock_info['code']})
- 등락률: {stock_info['change_rate']}% ({'상한가' if stock_info['is_upper_limit'] else '대량거래 급등'})
- 거래량: {stock_info['volume_str']}
- 시가총액: {stock_info['market_cap_str']}

[수집된 당일 기사 목록]
{news_context}

[분석 및 판별 가이드라인]
1. **정확한 원인 파악**: 단순 시황 브리핑('코스피 상승 마감' 등)이나 낚시성 기사는 배제하고, 주가를 직접 움직인 실질적 촉매(예: 대규모 수주, 경영권 분쟁, 호실적 공시, 정책 수혜, 신제품 개발, 엔비디아/AI/양자 등 글로벌 테마 연계)를 명확히 찾으세요.
2. 기사 목록 중 가장 신뢰도 높고 원인을 잘 다룬 **대표 기사 2~3개의 제목과 직접 링크 URL**을 선정하세요.
3. 블로그 독자가 한눈에 읽기 쉽게 핵심 1문장 및 2~3개 불렛포인트로 정리하세요.

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

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
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
            print(f"⚠️ [{stock_info['name']}] Gemini API 호출/파싱 실패: {e}")
            return self._generate_fallback_response(stock_info, news_list, f"분석 중 오류 발생 ({e})")

    def _build_top_articles_from_news(self, news_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """뉴스 목록에서 상위 2~3개 기사 추출"""
        articles = []
        for n in news_list[:3]:
            articles.append({
                "title": n.get("title", ""),
                "url": n.get("link", ""),
                "media": n.get("media", "언론사")
            })
        return articles

    def _generate_fallback_response(self, stock_info: Dict[str, Any], news_list: List[Dict[str, str]], reason: str) -> Dict[str, Any]:
        """API 미연결 시 수집된 실기사 기반 Fallback"""
        top_articles = self._build_top_articles_from_news(news_list)
        if not top_articles:
            top_articles = [{
                "title": f"{stock_info['name']} 네이버 증권 시황 바로가기",
                "url": f"https://finance.naver.com/item/main.naver?code={stock_info['code']}",
                "media": "네이버증권"
            }]

        first_title = top_articles[0]['title'] if top_articles else f"{stock_info['name']} 급등"

        return {
            "core_reason": f"{stock_info['name']} 당일 {stock_info['change_rate']}% 급등 및 거래량({stock_info['volume_str']}) 집중",
            "detail_points": [
                f"대표 보도: {first_title}",
                f"최근 실적: 매출 {stock_info.get('quarter_revenue', '-')}, 당기순익 {stock_info.get('quarter_net_income', '-')}"
            ],
            "theme_keywords": [stock_info['market'], "특징주", "급등주"],
            "top_articles": top_articles
        }
