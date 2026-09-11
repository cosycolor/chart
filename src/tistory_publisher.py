import os
import re
import base64
import requests
from typing import List, Dict, Any

class TistoryPublisher:
    """
    티스토리 블로그 자동 포스팅 및 HTML 보고서 생성기
    """

    def __init__(self):
        self.access_token = os.getenv("TISTORY_ACCESS_TOKEN", "").strip()
        self.blog_name = os.getenv("TISTORY_BLOG_NAME", "").strip()
        self.category_id = os.getenv("TISTORY_CATEGORY_ID", "0").strip()
        self.visibility = os.getenv("TISTORY_VISIBILITY", "3").strip()

    def generate_html_content(self, target_date: str, stocks: List[Dict[str, Any]], image_map: Dict[str, str], is_dry_run: bool = False) -> str:
        """
        블로그용 미려한 고품질 HTML 콘텐츠를 생성합니다.
        """
        date_formatted = f"{target_date[:4]}년 {target_date[4:6]}월 {target_date[6:]}일"
        
        # 1. 상단 요약 테이블
        summary_rows_html = ""
        for s in stocks:
            badge_limit = '<span style="background:#e03131;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:bold;margin-right:4px;">상한가</span>' if s['is_upper_limit'] else ''
            badge_vol = '<span style="background:#1971c2;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:bold;">1000만주</span>' if s['is_high_volume'] else ''
            
            rate_color = "#e03131" if s['change_rate'] > 0 else "#1971c2"
            sign = "+" if s['change_rate'] > 0 else ""
            
            summary_rows_html += f"""
            <tr style="border-bottom: 1px solid #f1f3f5; text-align: center; font-size: 13px;">
                <td style="padding: 10px 8px; font-weight: bold; text-align: left;">
                    {s['name']} <span style="font-size: 11px; color: #868e96;">({s['code']})</span><br>
                    {badge_limit}{badge_vol}
                </td>
                <td style="padding: 10px 8px; color: {rate_color}; font-weight: bold;">{sign}{s['change_rate']}%<br><span style="font-size: 11px; color: #495057;">{s['close']:,}원</span></td>
                <td style="padding: 10px 8px;">{s['volume_str']}</td>
                <td style="padding: 10px 8px;">{s['market_cap_str']}</td>
                <td style="padding: 10px 8px; font-size: 12px;">{s.get('quarter_revenue', '-')}<br><span style="font-size: 11px; color: #868e96;">({s.get('quarter_net_income', '-')})</span></td>
            </tr>
            """

        # 2. 종목별 상세 분석 카드
        stock_cards_html = ""
        for idx, s in enumerate(stocks, 1):
            code = s['code']
            img_src = image_map.get(code, "")
            
            # 차트 이미지 태그 렌더링
            img_tag = ""
            if img_src:
                if img_src.startswith("[##_Image"):
                    img_tag = f'<div style="text-align:center; margin: 15px 0;">{img_src}</div>'
                else:
                    img_tag = f'''
                    <div style="text-align:center; margin: 15px 0;">
                        <img src="{img_src}" alt="{s['name']} 40일봉 차트" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #dee2e6; box-shadow: 0 2px 8px rgba(0,0,0,0.06);" />
                        <div style="font-size: 12px; color: #495057; margin-top: 6px; font-weight: 500;">
                            ▲ {s['name']} 40일봉 차트 <span style="color:#f08c00; font-weight:bold;">[━ 5일선]</span> <span style="color:#2f9e44; font-weight:bold;">[━ 10일선]</span> <span style="color:#7048e8; font-weight:bold;">[━ 20일선]</span>
                        </div>
                    </div>
                    '''

            ai = s.get("ai_analysis", {})
            core_reason = ai.get("core_reason", "당일 수급 집중 및 시장 테마 형성")
            detail_points = ai.get("detail_points", [])
            keywords = ai.get("theme_keywords", [])
            top_articles = ai.get("top_articles", [])

            # 키워드 뱃지
            keywords_html = "".join([f'<span style="background:#edf2ff; color:#364fc7; padding:3px 8px; border-radius:12px; font-size:12px; margin-right:6px; font-weight:500;">#{kw}</span>' for kw in keywords])

            # 세부 포인트
            details_html = "".join([f'<li style="margin-bottom: 6px; line-height: 1.6; color: #343a40;">{pt}</li>' for pt in detail_points])

            # 2~3개 대표 기사 목록 렌더링
            articles_html = ""
            if top_articles:
                articles_html = '<div style="margin-top: 15px; border-top: 1px dashed #dee2e6; padding-top: 12px;"><div style="font-size: 13px; font-weight: bold; color: #495057; margin-bottom: 8px;">📰 관련 핵심 뉴스 기사</div>'
                for a_idx, art in enumerate(top_articles[:3], 1):
                    art_title = art.get("title", "").replace('"', '&quot;')
                    raw_url = art.get("url", "")
                    # 티스토리 에디터의 http:// 자동 링크 치환 버그 우회 (프로토콜 상대 URL // 적용)
                    art_url = re.sub(r'^https?:', '', raw_url)
                    art_media = art.get("media", "언론사")
                    if art_url and art_title:
                        articles_html += f'<div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; font-size: 13px;"><span style="background: #dee2e6; color: #495057; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-right: 6px; font-weight: bold;">{art_media}</span><a href="{art_url}" target="_blank" rel="noopener noreferrer" style="color: #1971c2; text-decoration: underline; font-weight: 600;">{art_title} ↗</a></div>'
                articles_html += '</div>'

            badge_text = "🔥 상한가" if s['is_upper_limit'] else "🚀 1,000만주 대량거래"
            badge_bg = "#e03131" if s['is_upper_limit'] else "#1971c2"

            stock_cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #e9ecef; border-radius: 12px; padding: 20px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
                <!-- 헤더 영역 -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f3f5; padding-bottom: 12px; margin-bottom: 15px;">
                    <div>
                        <span style="font-size: 20px; font-weight: 800; color: #212529;">{idx}. {s['name']}</span>
                        <span style="font-size: 13px; color: #868e96; margin-left: 6px;">({s['code']} · {s['market']})</span>
                    </div>
                    <div>
                        <span style="background: {badge_bg}; color: #ffffff; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{badge_text}</span>
                    </div>
                </div>

                <!-- 핵심 수치 요약 바 -->
                <div style="background: #f8f9fa; border-radius: 8px; padding: 12px 16px; margin-bottom: 15px; display: flex; flex-wrap: wrap; gap: 15px; font-size: 13px;">
                    <div><strong>종가:</strong> {s['close']:,}원 <span style="color: #e03131; font-weight: bold;">(+{s['change_rate']}%)</span></div>
                    <div><strong>거래량:</strong> {s['volume_str']}</div>
                    <div><strong>시가총액:</strong> {s['market_cap_str']}</div>
                    <div><strong>최근분기 매출:</strong> {s.get('quarter_revenue', '-')} (순익: {s.get('quarter_net_income', '-')})</div>
                </div>

                <!-- 40일봉 차트 이미지 -->
                {img_tag}

                <!-- AI 상승 이유 분석 박스 -->
                <div style="background: #fff9db; border-left: 4px solid #fcc419; padding: 14px 16px; border-radius: 4px; margin: 15px 0;">
                    <div style="font-weight: bold; color: #e67700; font-size: 14px; margin-bottom: 6px;">💡 핵심 상승 요인</div>
                    <div style="font-size: 15px; font-weight: 700; color: #212529; line-height: 1.5; margin-bottom: 8px;">{core_reason}</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px;">
                        {details_html}
                    </ul>
                </div>

                <!-- 테마 태그 -->
                <div style="margin-top: 10px;">{keywords_html}</div>

                <!-- 대표 기사 2~3개 직접 링크 영역 -->
                {articles_html}
            </div>
            """

        # 3. 전체 HTML 서식 조합
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; max-width: 800px; margin: 0 auto; color: #333333; line-height: 1.6;">
            <!-- 상단 헤더 배너 -->
            <div style="background: linear-gradient(135deg, #1864ab 0%, #0b7285 100%); color: #ffffff; padding: 25px 20px; border-radius: 12px; margin-bottom: 25px; text-align: center;">
                <h1 style="margin: 0 0 10px 0; font-size: 24px; font-weight: 800;">📊 {date_formatted} 상한가 & 1,000만주 특징주 총정리</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">한국거래소(KRX) 공식 데이터 기반 급등 원인 및 40일봉 차트 분석</p>
            </div>

            <!-- 요약 안내 문구 -->
            <p style="font-size: 14px; color: #495057; margin-bottom: 15px;">
                오늘 장 마감 기준 <strong>상한가에 도달했거나 거래량 1,000만 주 이상</strong>이 터진 핵심 특징주 <strong>총 {len(stocks)}종목</strong>의 상승 이유와 차트 흐름을 정리했습니다.
            </p>

            <!-- 1. 한눈에 보는 요약 표 -->
            <div style="background: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; overflow-x: auto; margin-bottom: 30px;">
                <table style="width: 100%; border-collapse: collapse; min-width: 500px;">
                    <thead>
                        <tr style="background: #f8f9fa; border-bottom: 2px solid #e9ecef; font-size: 12px; color: #495057;">
                            <th style="padding: 10px 8px; text-align: left;">종목명 (구분)</th>
                            <th style="padding: 10px 8px;">등락률 / 종가</th>
                            <th style="padding: 10px 8px;">거래량</th>
                            <th style="padding: 10px 8px;">시가총액</th>
                            <th style="padding: 10px 8px;">최근분기매출(순익)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_rows_html}
                    </tbody>
                </table>
            </div>

            <hr style="border: 0; height: 1px; background: #e9ecef; margin: 30px 0;" />

            <h2 style="font-size: 18px; font-weight: 800; color: #212529; margin-bottom: 20px; border-left: 4px solid #1864ab; padding-left: 10px;">
                📌 종목별 상세 분석 & 40일 차트
            </h2>

            <!-- 2. 개별 종목 상세 카드 -->
            {stock_cards_html}

            <!-- 하단 면책 조항 -->
            <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; margin-top: 30px; font-size: 12px; color: #868e96; line-height: 1.5;">
                <strong>⚠️ 투자 유의사항</strong><br>
                본 포스팅은 한국거래소(KRX) 공시 및 당일 언론사 뉴스 기사를 바탕으로 인공지능(AI)을 통해 분석·작성된 참고용 자료입니다. 종목 추천이나 매수/매도 권유가 아니며, 모든 투자의 최종 책임은 투자자 본인에게 있습니다.
            </div>
        </div>
        """
        return html

    def upload_image_to_tistory(self, image_path: str) -> str:
        """
        티스토리 파일 첨부 API를 통해 이미지를 업로드하고 치환자/URL을 반환합니다.
        """
        if not self.access_token or not self.blog_name or not os.path.exists(image_path):
            return ""

        url = "https://www.tistory.com/apis/post/attach"
        data = {
            "access_token": self.access_token,
            "blogName": self.blog_name,
            "output": "json"
        }

        try:
            with open(image_path, "rb") as f:
                files = {"uploadedfile": f}
                res = requests.post(url, data=data, files=files, timeout=15)
                if res.status_code == 200:
                    resp_json = res.json()
                    tistory_data = resp_json.get("tistory", {})
                    replacer = tistory_data.get("replacer", "")
                    img_url = tistory_data.get("url", "")
                    return replacer if replacer else img_url
                else:
                    print(f"⚠️ 티스토리 이미지 업로드 실패 ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"⚠️ 이미지 업로드 중 에러: {e}")

        return ""

    def publish_post(self, title: str, content_html: str, tag_list: List[str] = None) -> bool:
        """
        티스토리 블로그에 최종 글을 발행합니다.
        """
        if not self.access_token or not self.blog_name:
            print("⚠️ TISTORY_ACCESS_TOKEN 또는 TISTORY_BLOG_NAME이 설정되지 않아 포스팅을 건너뜁니다.")
            return False

        url = "https://www.tistory.com/apis/post/write"
        tags_str = ",".join(tag_list) if tag_list else "상한가,특징주,주식,거래량1000만주"

        payload = {
            "access_token": self.access_token,
            "blogName": self.blog_name,
            "output": "json",
            "title": title,
            "content": content_html,
            "visibility": self.visibility,
            "category": self.category_id,
            "tag": tags_str
        }

        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                resp_json = res.json()
                post_id = resp_json.get("tistory", {}).get("postId", "")
                post_url = resp_json.get("tistory", {}).get("url", "")
                print(f"🎉 티스토리 포스팅 성공! [ID: {post_id}] {post_url}")
                return True
            else:
                print(f"❌ 티스토리 포스팅 실패 ({res.status_code}): {res.text}")
                return False
        except Exception as e:
            print(f"❌ 티스토리 포스팅 요청 에러: {e}")
            return False

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        내 티스토리 블로그의 카테고리 목록과 카테고리 ID를 조회합니다.
        """
        if not self.access_token or not self.blog_name:
            print("⚠️ TISTORY_ACCESS_TOKEN 또는 TISTORY_BLOG_NAME이 설정되지 않았습니다.")
            return []

        url = "https://www.tistory.com/apis/category/list"
        params = {
            "access_token": self.access_token,
            "blogName": self.blog_name,
            "output": "json"
        }

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json().get("tistory", {}).get("item", {}).get("categories", [])
                return data
            else:
                print(f"⚠️ 카테고리 조회 실패 ({res.status_code}): {res.text}")
                return []
        except Exception as e:
            print(f"⚠️ 카테고리 조회 중 에러: {e}")
            return []
