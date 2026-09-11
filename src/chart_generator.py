import os
import platform
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from datetime import datetime, timedelta
import FinanceDataReader as fdr
from src.utils import ensure_dir

class ChartGenerator:
    """
    종목별 최근 40거래일 캔들차트(5/10/20일 이평선 + 범례 + 거래량) 고화질 이미지 생성기
    """

    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = ensure_dir(output_dir)
        self.font_family = self._get_korean_font()

    def _get_korean_font(self) -> str:
        """OS 환경에 적합한 한글 폰트명 반환"""
        system = platform.system()
        if system == "Windows":
            return "Malgun Gothic"
        elif system == "Darwin":
            return "AppleGothic"
        else:
            return "NanumGothic"

    def generate_40d_chart(self, ticker: str, stock_name: str, target_date: str, close_price: int, change_rate: float) -> str:
        """
        target_date 기준 최근 40거래일 일봉 차트 이미지를 생성하고 파일 경로를 반환합니다.
        (5일: 주황색, 10일: 초록색, 20일: 보라색 이평선 적용)
        """
        try:
            end_dt = datetime.strptime(target_date, "%Y%m%d")
            start_dt = end_dt - timedelta(days=100)
            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")

            df = fdr.DataReader(ticker, start=start_str, end=end_str)
            if df.empty or len(df) < 5:
                print(f"⚠️ [{ticker} - {stock_name}] 차트 데이터를 불러올 수 없습니다.")
                return ""

            df = df.tail(40).copy()
            df.index = pd.to_datetime(df.index)

            # 한국형 캔들 스타일 (상승: 빨간색, 하락: 파란색)
            mc = mpf.make_marketcolors(
                up='#e03131',
                down='#1971c2',
                edge='inherit',
                wick='inherit',
                volume={'up': '#e03131', 'down': '#1971c2'}
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle=':',
                gridcolor='#e9ecef',
                facecolor='#ffffff',
                figcolor='#ffffff',
                rc={
                    'font.family': self.font_family,
                    'axes.unicode_minus': False
                }
            )

            sign = "+" if change_rate > 0 else ""
            # 상단 제목 및 이평선 색상 범례 표시
            title_text = (
                f"{stock_name} ({ticker}) 40일봉 차트 | 종가: {close_price:,}원 ({sign}{change_rate}%)\n"
                f"━ 5일선(주황)   ━ 10일선(초록)   ━ 20일선(보라)"
            )

            file_name = f"{target_date}_{ticker}.png"
            file_path = os.path.join(self.output_dir, file_name)

            # 이평선 색상: 5일(주황 #f08c00), 10일(초록 #2f9e44), 20일(보라 #7048e8)
            mav_colors = ['#f08c00', '#2f9e44', '#7048e8']

            fig, axes = mpf.plot(
                df,
                type='candle',
                mav=(5, 10, 20),
                mavcolors=mav_colors,
                volume=True,
                style=s,
                title=dict(title=title_text, fontsize=11, weight='bold', color='#212529'),
                figsize=(10, 5.8),
                savefig=dict(fname=file_path, dpi=130, bbox_inches='tight'),
                returnfig=True
            )
            plt.close(fig)

            return file_path

        except Exception as e:
            print(f"⚠️ [{ticker} - {stock_name}] 차트 생성 중 오류: {e}")
            return ""
