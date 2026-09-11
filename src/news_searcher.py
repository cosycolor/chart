import os
import re
import html
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

class NewsSearcher:
    """
    종목별 당일 주요 뉴스 기사 및 특징주 소식을 수집하는 모듈
    (네이버 증권 종목코드 전용 뉴스 1순위 + 다음 실시간 특징주 검색 2순위)
    """

    def __init__(self):
        self.naver_client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
        self.naver_client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def search_stock_news(self, stock_name: str, ticker: str = "", target_date: str = "", max_count: int = 6) -> List[Dict[str, str]]:
        """
        종목의 당일 급등/상승 관련 뉴스를 검색하여 기사 목록(헤드라인, 요약, 직접 링크, 발행일)을 반환합니다.
        기준일자(target_date) 당일 및 최근 1~2일 이내의 기사만 필터링합니다.
        """
        all_news = []

        # 1. [1순위] 네이버 모바일 증권 종목코드(ticker) 전용 뉴스 (동음이의어 노이즈 0% 차단)
        if ticker:
            stock_news = self._search_naver_stock_api(ticker, target_date=target_date, max_count=6)
            all_news.extend(stock_news)

        # 2. [2순위] 다음 실시간 뉴스 검색 ('종목명 특징주' / '종목명 주가' 타겟팅)
        if len(all_news) < 3:
            daum_news = self._search_daum_news(f"{stock_name} 특징주", target_date=target_date, max_count=4)
            if not daum_news:
                daum_news = self._search_daum_news(f"{stock_name} 주가", target_date=target_date, max_count=4)
            all_news.extend(daum_news)

        # 3. [3순위] 네이버 공식 검색 API (키 있을 시)
        if self.naver_client_id and self.naver_client_secret and len(all_news) < 3:
            naver_api_news = self._search_via_naver_api(stock_name, target_date=target_date, max_count=4)
            all_news.extend(naver_api_news)

        # 중복 및 불필요한 링크 필터링 & 연관도 점수 계산
        unique_news = []
        seen_urls = set()
        seen_titles = set()

        junk_titles = ["동영상 첨부된 문서", "포토", "사진", "인사", "부고", "동정", "[서울데이터랩]코스피", "[증시키워드]", "IPO 명가"]

        for item in all_news:
            raw_title = item.get("title", "").strip()
            link = item.get("link", "").strip()

            # HTML 엔티티 디코딩 (&quot; -> ", &amp; -> & 등)
            title = html.unescape(raw_title)

            if not link or not title or len(title) < 6:
                continue
            if any(junk in title for junk in junk_titles):
                continue
            if link in seen_urls:
                continue
            
            clean_title = re.sub(r'\s+', ' ', title).strip()
            if clean_title in seen_titles:
                continue

            seen_urls.add(link)
            seen_titles.add(clean_title)

            # 연관도 점수 계산: 종목명이 제목에 직접 포함되어 있는지
            relevance_score = 0
            if stock_name in clean_title:
                relevance_score += 10
            elif any(part in clean_title for part in stock_name.split() if len(part) >= 2):
                relevance_score += 5
            
            desc = item.get("description", "")
            if stock_name in desc:
                relevance_score += 2

            unique_news.append({
                "title": clean_title,
                "link": link,
                "description": desc,
                "media": item.get("media", "뉴스"),
                "date": item.get("date", ""),
                "score": relevance_score
            })

        # 종목명 연관도가 높은 순서로 우선 정렬
        unique_news.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique_news[:max_count]

    def _search_naver_stock_api(self, ticker: str, target_date: str = "", max_count: int = 6) -> List[Dict[str, str]]:
        """네이버 모바일 증권 종목별 뉴스 API (해당 종목 전용 기사 매핑 + 기준일 필터링)"""
        url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize=10&page=1"
        results = []
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                group_list = data if isinstance(data, list) else [data]
                for group in group_list:
                    for item in group.get("items", []):
                        raw_title = item.get("titleFull") or item.get("title") or ""
                        title = html.unescape(raw_title)
                        link = item.get("mobileNewsUrl", "")
                        media = item.get("officeName", "증권뉴스")
                        dt_str = str(item.get("datetime", ""))  # 예: "202609110935"

                        # 날짜 필터링: target_date(YYYYMMDD)가 주어진 경우 오래된 기사(3일 이전 등) 제외
                        article_date_str = ""
                        if dt_str and len(dt_str) >= 8:
                            article_ymd = dt_str[:8]
                            article_date_str = f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}"
                            if target_date:
                                try:
                                    from datetime import datetime
                                    t_dt = datetime.strptime(target_date, "%Y%m%d")
                                    a_dt = datetime.strptime(article_ymd, "%Y%m%d")
                                    diff_days = (t_dt - a_dt).days
                                    # 기준일보다 미래이거나, 기준일보다 3일 이상 과거인 기사는 제외
                                    if diff_days > 2 or diff_days < 0:
                                        continue
                                except Exception:
                                    pass

                        if title and link:
                            results.append({
                                "title": title,
                                "link": link,
                                "description": item.get("body", ""),
                                "media": media,
                                "date": article_date_str
                            })
                            if len(results) >= max_count:
                                break
        except Exception:
            pass
        return results

    def _search_daum_news(self, query: str, target_date: str = "", max_count: int = 4) -> List[Dict[str, str]]:
        """다음 실시간 뉴스 검색 (URL 내 YYYYMMDD 파싱 및 날짜 검증)"""
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.daum.net/search?w=news&q={encoded_query}&sort=recency"
        results = []
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                seen_in_page = set()
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    raw_title = a.text.strip()
                    title = html.unescape(raw_title)
                    if "v.daum.net/v/" in href and len(title) >= 8 and href not in seen_in_page:
                        # URL 예시: http://v.daum.net/v/20260911094724489
                        date_match = re.search(r'/v/(\d{8})', href)
                        article_date_str = ""
                        if date_match and target_date:
                            article_ymd = date_match.group(1)
                            article_date_str = f"{article_ymd[:4]}-{article_ymd[4:6]}-{article_ymd[6:]}"
                            try:
                                from datetime import datetime
                                t_dt = datetime.strptime(target_date, "%Y%m%d")
                                a_dt = datetime.strptime(article_ymd, "%Y%m%d")
                                diff_days = (t_dt - a_dt).days
                                if diff_days > 2 or diff_days < 0:
                                    continue
                            except Exception:
                                pass

                        seen_in_page.add(href)
                        results.append({
                            "title": title,
                            "link": href,
                            "description": "",
                            "media": "포털뉴스",
                            "date": article_date_str
                        })
                        if len(results) >= max_count:
                            break
        except Exception:
            pass
        return results

    def _search_via_naver_api(self, stock_name: str, target_date: str = "", max_count: int = 4) -> List[Dict[str, str]]:
        """네이버 공식 뉴스 검색 API"""
        query = f"{stock_name} 특징주"
        url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(query)}&display={max_count}&sort=sim"
        headers = {
            "X-Naver-Client-Id": self.naver_client_id,
            "X-Naver-Client-Secret": self.naver_client_secret
        }

        results = []
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("items", []):
                    title = html.unescape(re.sub(r'<[^>]+>', '', item.get("title", "")))
                    link = item.get("originallink") or item.get("link", "")
                    results.append({
                        "title": title,
                        "link": link,
                        "description": re.sub(r'<[^>]+>', '', item.get("description", "")),
                        "media": "네이버뉴스",
                        "date": ""
                    })
        except Exception:
            pass
        return results
