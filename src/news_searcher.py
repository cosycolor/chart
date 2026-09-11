import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

class NewsSearcher:
    """
    종목별 당일 주요 뉴스 기사 및 특징주 소식을 수집하는 모듈
    (다음 실시간 뉴스 검색 + 네이버 증권 뉴스 + 네이버 공식 검색 API 지원)
    """

    def __init__(self):
        self.naver_client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
        self.naver_client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def search_stock_news(self, stock_name: str, ticker: str = "", target_date: str = "", max_count: int = 6) -> List[Dict[str, str]]:
        """
        종목의 당일 급등/상승 관련 뉴스를 검색하여 기사 목록(헤드라인, 요약, 직접 링크)을 반환합니다.
        """
        all_news = []

        # 1. 다음 실시간 뉴스 검색 (가장 안정적으로 직접 링크 제공)
        daum_news = self._search_daum_news(stock_name, max_count=6)
        all_news.extend(daum_news)

        # 2. 네이버 모바일 증권 종목별 뉴스 (보조)
        if len(all_news) < 3 and ticker:
            stock_news = self._search_naver_stock_api(ticker, max_count=4)
            all_news.extend(stock_news)

        # 3. 네이버 공식 검색 API (키 있을 시)
        if self.naver_client_id and self.naver_client_secret:
            naver_api_news = self._search_via_naver_api(stock_name, max_count=4)
            all_news.extend(naver_api_news)

        # 중복 및 불필요한 링크 필터링
        unique_news = []
        seen_urls = set()
        seen_titles = set()

        # 제외할 키워드
        junk_titles = ["동영상 첨부된 문서", "포토", "사진", "인사", "부고", "동정"]

        for item in all_news:
            title = item.get("title", "").strip()
            link = item.get("link", "").strip()

            if not link or not title or len(title) < 6:
                continue
            if any(junk in title for junk in junk_titles):
                continue
            if link in seen_urls:
                continue
            
            # 제목 정규화 (공백/괄호 정리)
            clean_title = re.sub(r'\s+', ' ', title)
            if clean_title in seen_titles:
                continue

            seen_urls.add(link)
            seen_titles.add(clean_title)
            unique_news.append({
                "title": clean_title,
                "link": link,
                "description": item.get("description", ""),
                "media": item.get("media", "뉴스")
            })

        return unique_news[:max_count]

    def _search_daum_news(self, query: str, max_count: int) -> List[Dict[str, str]]:
        """다음 실시간 뉴스 검색 (v.daum.net 직접 링크)"""
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
                    title = a.text.strip()
                    if "v.daum.net/v/" in href and len(title) >= 8 and href not in seen_in_page:
                        seen_in_page.add(href)
                        results.append({
                            "title": title,
                            "link": href,
                            "description": "",
                            "media": "포털뉴스"
                        })
                        if len(results) >= max_count:
                            break
        except Exception:
            pass
        return results

    def _search_naver_stock_api(self, ticker: str, max_count: int) -> List[Dict[str, str]]:
        """네이버 모바일 증권 뉴스 API"""
        url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize={max_count}&page=1"
        results = []
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", []) if isinstance(data, dict) else []
                for item in items:
                    title = item.get("title", "") or item.get("titleFull", "")
                    link = item.get("mobileNewsUrl", "")
                    media = item.get("officeName", "네이버증권")
                    if title and link:
                        results.append({
                            "title": title,
                            "link": link,
                            "description": item.get("body", ""),
                            "media": media
                        })
        except Exception:
            pass
        return results

    def _search_via_naver_api(self, stock_name: str, max_count: int) -> List[Dict[str, str]]:
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
                    title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                    link = item.get("originallink") or item.get("link", "")
                    results.append({
                        "title": title,
                        "link": link,
                        "description": re.sub(r'<[^>]+>', '', item.get("description", "")),
                        "media": "네이버뉴스"
                    })
        except Exception:
            pass
        return results
