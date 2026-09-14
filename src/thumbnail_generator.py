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
    티스토리 블로그 목록(1:1 정방형) 및 카카오톡·SNS 공유에 최적화된 고품질 대표 썸네일(1000x1000 px) 자동 생성기
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
        티스토리 스킨 크롭(1:1 및 직사각형)에 완벽 대응하는 중앙 집중형 정방형 썸네일을 생성합니다.
        """
        try:
            month = int(target_date[4:6])
            day = int(target_date[6:8])
            year = target_date[:4]

            # 주요 종목명 추출 (최대 4개)
            top_stocks = [s['name'] for s in stocks[:4]]
            stocks_preview = "  ·  ".join(top_stocks) if top_stocks else "전종목 시세 분석"

            # 1:1 정방형 규격 (1000 x 1000 px, 100 dpi)
            fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
            fig.patch.set_facecolor('#0f172a')  # 다크 슬레이트 네이비
            ax.set_facecolor('#0f172a')

            # 1. 외곽 은은한 테두리 카드 박스
            outer_card = patches.FancyBboxPatch(
                (0.06, 0.06), 0.88, 0.88,
                boxstyle="round,pad=0.03,rounding_size=0.05",
                facecolor='#1e293b',
                edgecolor='#334155',
                linewidth=2.0,
                transform=ax.transAxes
            )
            ax.add_patch(outer_card)

            # 2. 상단 네온 블루 액센트 바
            accent_bar = patches.Rectangle((0.15, 0.88), 0.70, 0.012, color='#38bdf8', transform=ax.transAxes)
            ax.add_patch(accent_bar)

            # 3. 상단 뱃지 (KRX 주식 시장 일일 브리핑)
            badge = patches.FancyBboxPatch(
                (0.30, 0.78), 0.40, 0.065,
                boxstyle="round,pad=0.01,rounding_size=0.03",
                facecolor='#e03131',
                edgecolor='none',
                transform=ax.transAxes
            )
            ax.add_patch(badge)

            ax.text(
                0.50, 0.81,
                f"KRX 주식 시장 일일 브리핑",
                fontsize=15,
                fontweight='bold',
                color='#ffffff',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 4. 메인 날짜 (예: 2026.09.14)
            ax.text(
                0.50, 0.67,
                f"{month}월 {day}일",
                fontsize=34,
                fontweight='bold',
                color='#38bdf8',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 5. 메인 타이틀 (상한가 및 특징주)
            ax.text(
                0.50, 0.53,
                "상한가 및 특징주",
                fontsize=46,
                fontweight='bold',
                color='#ffffff',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 6. 서브 헤드라인
            ax.text(
                0.50, 0.41,
                "당일 급등 테마 & 핵심 원인 총정리",
                fontsize=20,
                fontweight='bold',
                color='#f59e0b',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            # 7. 하단 주요 종목 태그 박스 (중앙 집중)
            tag_box = patches.FancyBboxPatch(
                (0.12, 0.17), 0.76, 0.16,
                boxstyle="round,pad=0.02,rounding_size=0.03",
                facecolor='#0f172a',
                edgecolor='#475569',
                linewidth=1.5,
                transform=ax.transAxes
            )
            ax.add_patch(tag_box)

            ax.text(
                0.50, 0.27,
                "주요 종목 분석",
                fontsize=13,
                fontweight='bold',
                color='#94a3b8',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            ax.text(
                0.50, 0.21,
                stocks_preview,
                fontsize=16,
                fontweight='bold',
                color='#e2e8f0',
                ha='center',
                va='center',
                fontfamily=self.font_family,
                transform=ax.transAxes
            )

            ax.axis('off')
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

            file_name = f"thumbnail_{target_date}.png"
            file_path = os.path.join(self.output_dir, file_name)

            plt.savefig(file_path, dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close(fig)

            print(f"🖼️ [티스토리 최적화 1:1 썸네일 생성 완료] {file_path}")
            return file_path

        except Exception as e:
            print(f"⚠️ 썸네일 생성 중 오류 발생: {e}")
            return ""
