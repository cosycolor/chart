import os
import sys
import re
import requests
import pandas as pd
import FinanceDataReader as fdr
from typing import List, Dict, Any
from src.utils import format_korean_number, format_volume

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class StockCollector:
    """
    한국거래소(KRX) 및 네이버 금융에서 상한가/1000만주 이상 종목과 재무데이터를 추출하는 수집기
    """

    def __init__(self, target_date: str = None):
        self.target_date = target_date  # YYYYMMDD

    def get_target_stocks(self) -> List[Dict[str, Any]]:
        """
        당일 상한가 종목(등락률 >= 29.5%) 또는 거래량 1,000만주 이상 종목을 선별하여 기본 시세 및 재무정보와 함께 반환합니다.
        """
        print(f"[{self.target_date or '오늘'}] 한국거래소(KRX) 전종목 시세 데이터 조회 중...")
        
        try:
            df = fdr.StockListing('KRX')
            if df.empty:
                print("⚠️ 거래소 종목 시세 데이터를 불러올 수 없습니다.")
                return []

            # KOSPI, KOSDAQ 필터링
            df = df[df['Market'].isin(['KOSPI', 'KOSDAQ'])].copy()

            df['ChagesRatio'] = pd.to_numeric(df['ChagesRatio'], errors='coerce').fillna(0)
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce').fillna(0)
            df['Marcap'] = pd.to_numeric(df['Marcap'], errors='coerce').fillna(0)
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

            # 1차 후보 필터링: 상한가 근접(28.0% 이상) OR 거래량 950만주 이상
            is_candidate_limit = df['ChagesRatio'] >= 28.0
            is_candidate_vol = df['Volume'] >= 9_500_000

            candidates_df = df[is_candidate_limit | is_candidate_vol].copy()
            print(f"🔍 1차 후보 종목 수: {len(candidates_df)}개 (실제 당일 확정 시세 정밀 검증 시작...)")

            result = []
            for _, row in candidates_df.iterrows():
                ticker = str(row['Code']).zfill(6)
                name = str(row['Name'])
                market = str(row['Market'])
                close_price = int(row['Close'])
                change_rate = round(float(row['ChagesRatio']), 2)
                volume = int(row['Volume'])
                marcap = int(row['Marcap'])
                amount = int(row['Amount'])

                # [중요] 2차 정밀 검증: DataReader를 통한 당일 최종 확정 일봉 시세 교차 검증
                # (KRX 장중 고가 시점 왜곡 및 미정산 데이터 방지)
                try:
                    daily_df = fdr.DataReader(ticker).tail(1)
                    if not daily_df.empty:
                        last_row = daily_df.iloc[-1]
                        real_close = int(last_row['Close'])
                        real_change = round(float(last_row.get('Change', 0)) * 100, 2)
                        real_volume = int(last_row['Volume'])

                        # 확정 시세로 데이터 갱신
                        close_price = real_close
                        change_rate = real_change
                        volume = real_volume
                except Exception as e:
                    pass

                # 최종 확정 조건 검증: 상한가(29.5% 이상) OR 당일 최종 거래량 1,000만주 이상
                is_limit = bool(change_rate >= 29.5)
                is_vol = bool(volume >= 10_000_000)

                if not (is_limit or is_vol):
                    # 장중 일시 급등 후 종가 하락 등으로 조건을 불충족한 종목 제외
                    continue

                tags = []
                if is_limit:
                    tags.append("상한가")
                if is_vol:
                    tags.append("1,000만주 돌파")

                stock_info = {
                    "code": ticker,
                    "name": name,
                    "market": market,
                    "close": close_price,
                    "change_rate": change_rate,
                    "volume": volume,
                    "trading_value": amount,
                    "market_cap": marcap,
                    "is_upper_limit": is_limit,
                    "is_high_volume": is_vol,
                    "tags": tags,
                    "volume_str": format_volume(volume),
                    "market_cap_str": format_korean_number(marcap),
                }

                # 재무 정보 수집 (최근 확정 분기 매출액, 당기순익)
                financials = self.get_financials(ticker)
                stock_info.update(financials)

                result.append(stock_info)

            # 정렬: 상한가 우선, 이후 거래량 순
            result.sort(key=lambda x: (x['is_upper_limit'], x['change_rate'], x['volume']), reverse=True)
            print(f"🎯 최종 확정 특징주: 총 {len(result)}개")
            return result

        except Exception as e:
            print(f"❌ 데이터 수집 중 에러 발생: {e}")
            return []

    def get_financials(self, ticker: str) -> Dict[str, str]:
        """
        네이버 모바일 증권 API에서 최근 확정 분기 매출액과 당기순이익을 추출합니다.
        """
        url = f"https://m.stock.naver.com/api/stock/{ticker}/finance/quarter"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        financials = {
            "quarter_revenue": "-",
            "quarter_net_income": "-",
            "quarter_period": ""
        }

        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code != 200:
                return financials

            data = res.json()
            info = data.get("financeInfo", {})
            title_list = info.get("trTitleList", [])
            if not title_list:
                return financials

            # 컨센서스(추정치 E)가 아닌 가장 최근 실제 확정 분기 선택
            actual_titles = [t for t in title_list if t.get("isConsensus") == "N"]
            selected_period = actual_titles[-1] if actual_titles else title_list[-1]
            
            period_key = selected_period.get("key", "")
            period_title = selected_period.get("title", "").strip()
            financials["quarter_period"] = period_title

            row_list = info.get("rowList", [])
            for row in row_list:
                row_title = row.get("title", "")
                cols = row.get("columns", {})
                period_val = cols.get(period_key, {}).get("value", "")

                if "매출액" in row_title and period_val and period_val != "-":
                    financials["quarter_revenue"] = f"{period_val}억원"
                elif "당기순이익" in row_title and period_val and period_val != "-":
                    financials["quarter_net_income"] = f"{period_val}억원"

        except Exception:
            pass

        return financials
