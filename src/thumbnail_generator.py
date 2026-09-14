import os
import sys
import platform
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Dict, Any
from src.utils import ensure_dir

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class ThumbnailGenerator:
    """
    티스토리 블로그 및 SNS 공유에 최적화된 고품질 대표 썸네일(1200x630 px) 자동 생성기
    """

    def __init__(self, output_dir: str = "output/thumbnails"):
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

    def generate_thumbnail(self, target_date: str, stocks: List[Dict[str, Any]]) -> str:
        """
        당일 날짜와 주요 특징주 목록을 바탕으로 세련된 블로그 대표 썸네일 이미지를 생성합니다.
        예: '9월 14일 상한가 및 특징주 총정리'
        """
        try:
            # 날짜 포맷 (예: 20260914 -> 9월 14일)
            month = int(target_date[4:6])
            day = int(target_date[6:8])
            date_korean = f"{month}월 {day}일"
            year = target_date[:4]

            # 주요 종목명 추출 (최대 4개)
            top_stocks = [s['name'] for s in stocks[:4]]
            stocks_preview = "  |  ".join(top_stocks) if top_stocks else "전종목 시세 분석"

            # 1200 x 630 px 규격 (12 x 6.3 inch, 100 dpi)
            fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
            fig.patch.set_facecolor('#0b132b')  # 딥 미드나잇 블루 배경
            ax.set_facecolor('#0b132b')

            # 1. 상단 네온 악센트 바
            rect_accent = patches.Rectangle((0.05, 0.91), 0.9, 0.012, color='#38bdf8', transform=ax.transAxes)
            ax.add_patch(rect_accent)

            # 2. 내부 메인 카드 박스 (다크 글래스모피즘 톤)
            card = patches.FancyBboxPatch(
                (0.05, 0.08), 0.9, 0.81,
                boxstyle="round,pad=0.03,rounding_size=0.04",
                facecolor='#1c2541',
                edgecolor='#3a506b',
                linewidth=1.5,
                transform=ax.transAxes
            )
            ax.add_patch(card)

            # 3. 상단 카테고리 뱃지
            badge = patches.FancyBboxPatch(
                (0.10, 0.77), 0.35, 0.07,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                facecolor='#e03131',
                edgecolor='none',
                transform=ax.transAxes
            )
            ax.add_patch(badge)

            ax.text(
                0.12, 0.80,
                f"KRX 주식 시장 일일 브리핑",
                fontsize=13,
                fontweight='bold',
                color='#ffffff',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 4. 우측 상단 날짜 및 시장 라벨
            ax.text(
                0.88, 0.80,
                f"{year}.{target_date[4:6]}.{target_date[6:]} (KOSPI · KOSDAQ)",
                fontsize=13,
                fontweight='bold',
                color='#94a3b8',
                ha='right',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 5. 메인 타이틀 (예: 9월 14일 상한가 및 특징주)
            ax.text(
                0.10, 0.56,
                f"{date_korean} 상한가 및 특징주",
                fontsize=36,
                fontweight='bold',
                color='#ffffff',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 6. 서브 헤드라인
            ax.text(
                0.10, 0.43,
                "당일 급등 테마 분석 · 40일 차트 & 핵심 원인 총정리",
                fontsize=18,
                fontweight='bold',
                color='#f59e0b',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 7. 하단 주요 종목 태그 박스
            tag_box = patches.FancyBboxPatch(
                (0.10, 0.17), 0.80, 0.17,
                boxstyle="round,pad=0.02,rounding_size=0.03",
                facecolor='#0b132b',
                edgecolor='#475569',
                linewidth=1,
                transform=ax.transAxes
            )
            ax.add_patch(tag_box)

            ax.text(
                0.13, 0.24,
                f"주요 종목  ▶  {stocks_preview}",
                fontsize=15,
                fontweight='bold',
                color='#e2e8f0',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            ax.axis('off')
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

            file_name = f"thumbnail_{target_date}.png"
            file_path = os.path.join(self.output_dir, file_name)

            plt.savefig(file_path, dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close(fig)

            print(f"🖼️ [대표 썸네일 생성 완료] {file_path}")
            return file_path

        except Exception as e:
            print(f"⚠️ 썸네일 생성 중 오류 발생: {e}")
            return ""
