import os
import sys

# Windows 콘솔 UTF-8 출력 보장
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import argparse
import base64
from dotenv import load_dotenv

# .env 로드
load_dotenv()

from src.utils import get_target_date, ensure_dir
from src.collector import StockCollector
from src.chart_generator import ChartGenerator
from src.news_searcher import NewsSearcher
from src.gemini_analyzer import GeminiStockAnalyzer
from src.tistory_publisher import TistoryPublisher

def run_pipeline(date_str: str = None, dry_run: bool = False, skip_charts: bool = False, skip_ai: bool = False):
    """
    당일 상한가 & 1000만주 특징주 분석 및 티스토리 발행 전체 파이프라인
    """
    target_date = get_target_date(date_str)
    print("=" * 60)
    print(f"🚀 [한국 증시 특징주 자동화 파이프라인] 기준일자: {target_date}")
    print(f"⚙️ 모드: {'[로컬 테스트 (Dry Run)]' if dry_run else '[실제 티스토리 발행 모드]'}")
    print("=" * 60)

    # 1. 데이터 수집 (KRX 상한가 & 1,000만주)
    collector = StockCollector(target_date)
    stocks = collector.get_target_stocks()

    if not stocks:
        print(f"⚠️ [{target_date}] 분석 대상 종목이 없습니다. (휴장일이거나 조건 충족 종목 없음)")
        return

    print(f"\n📊 총 {len(stocks)}개 종목이 조건에 선정되었습니다:")
    for idx, s in enumerate(stocks, 1):
        tag_str = ", ".join(s['tags'])
        print(f"  {idx}. {s['name']} ({s['code']}) | +{s['change_rate']}% | 거래량: {s['volume_str']} [{tag_str}]")

    # 2. 40일봉 차트 생성
    image_map = {}
    if not skip_charts:
        print("\n📈 [40일봉 캔들차트 생성 중...]")
        chart_gen = ChartGenerator(output_dir="output/charts")
        for s in stocks:
            img_path = chart_gen.generate_40d_chart(
                ticker=s['code'],
                stock_name=s['name'],
                target_date=target_date,
                close_price=s['close'],
                change_rate=s['change_rate']
            )
            if img_path and os.path.exists(img_path):
                if dry_run:
                    # report_YYYYMMDD.html이 output/ 폴더에 있으므로 상대경로 charts/파일명 지정
                    rel_path = f"charts/{os.path.basename(img_path)}"
                    image_map[s['code']] = rel_path
                else:
                    image_map[s['code']] = img_path
                print(f"  ✅ 차트 완료: {s['name']} -> {img_path}")
    else:
        print("\n⏩ 차트 생성을 건너뜁니다.")

    # 3. 뉴스 스크랩 및 AI 상승이유 분석
    print("\n🔍 [뉴스 수집 및 Gemini LLM 상승 이유 팩트체크...]")
    news_searcher = NewsSearcher()
    analyzer = GeminiStockAnalyzer() if not skip_ai else None

    for idx, s in enumerate(stocks, 1):
        print(f"  [{idx}/{len(stocks)}] {s['name']} 뉴스 검색 중...")
        news_list = news_searcher.search_stock_news(s['name'], ticker=s['code'], target_date=target_date, max_count=6)
        
        if analyzer and analyzer.client:
            print(f"    🤖 Gemini AI로 상승 이유 분석 중...")
            ai_result = analyzer.analyze_stock_surge_reason(s, news_list)
            s['ai_analysis'] = ai_result
            print(f"    💡 [핵심 이유] {ai_result.get('core_reason', '')}")
        else:
            # Fallback 또는 skip_ai 모드
            top_articles = []
            for n in news_list[:3]:
                top_articles.append({
                    "title": n.get("title", ""),
                    "url": n.get("link", ""),
                    "media": n.get("media", "언론사")
                })
            
            if not top_articles:
                top_articles = [{
                    "title": f"{s['name']} 네이버 증권 시황 바로가기",
                    "url": f"https://finance.naver.com/item/main.naver?code={s['code']}",
                    "media": "네이버증권"
                }]

            first_title = top_articles[0]['title'] if top_articles else f"{s['name']} 급등"

            s['ai_analysis'] = {
                "core_reason": f"{s['name']} 당일 {s['change_rate']}% 급등 및 대량 거래량({s['volume_str']}) 유입",
                "detail_points": [
                    f"주요 보도: {first_title}",
                    f"거래량: {s['volume_str']}, 시가총액: {s['market_cap_str']}"
                ],
                "theme_keywords": [s['market'], "특징주", "급등주"],
                "top_articles": top_articles
            }

    # 4. 티스토리 발행 및 HTML 저장
    print("\n📝 [블로그 콘텐츠 생성 및 발행 처리...]")
    publisher = TistoryPublisher()

    # 실제 티스토리 업로드인 경우 이미지를 먼저 티스토리에 업로드
    if not dry_run and os.getenv("TISTORY_ACCESS_TOKEN"):
        for s in stocks:
            code = s['code']
            local_img = image_map.get(code)
            if local_img and os.path.exists(local_img):
                print(f"  📤 [{s['name']}] 티스토리 이미지 업로드 중...")
                replacer_or_url = publisher.upload_image_to_tistory(local_img)
                if replacer_or_url:
                    image_map[code] = replacer_or_url

    # HTML 템플릿 렌더링
    html_content = publisher.generate_html_content(target_date, stocks, image_map, is_dry_run=dry_run)

    # 로컬 HTML 파일 저장
    ensure_dir("output")
    report_file = f"output/report_{target_date}.html"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"💾 [미리보기 HTML 저장 완료] {os.path.abspath(report_file)}")

    # 블로그 포스팅 (Dry-run이 아닐 때만)
    if not dry_run:
        post_title = f"[{target_date[:4]}.{target_date[4:6]}.{target_date[6:]}] 오늘의 상한가 및 1,000만주 특징주 총정리 (상승이유·40일차트)"
        all_keywords = []
        for s in stocks:
            all_keywords.extend(s.get("ai_analysis", {}).get("theme_keywords", []))
            all_keywords.append(s['name'])
        unique_tags = list(dict.fromkeys(all_keywords))[:10]

        publisher.publish_post(post_title, html_content, tag_list=unique_tags)
    else:
        print("💡 Dry-Run 모드이므로 티스토리 포스팅 API는 호출하지 않았습니다.")

    print("\n✨ 모든 프로세스가 성공적으로 완료되었습니다!")

def main():
    parser = argparse.ArgumentParser(description="한국 증시 상한가/1000만주 특징주 자동화 분석 및 발행기")
    parser.add_argument("--date", type=str, default=None, help="기준 일자 (YYYYMMDD). 미입력 시 최근 영업일 자동 계산")
    parser.add_argument("--dry-run", action="store_true", help="티스토리 포스팅을 하지 않고 로컬 HTML/차트만 생성")
    parser.add_argument("--skip-charts", action="store_true", help="차트 생성 건너뛰기 (빠른 디버깅용)")
    parser.add_argument("--skip-ai", action="store_true", help="Gemini API 호출 건너뛰기 (기본값 사용)")

    args = parser.parse_args()
    run_pipeline(
        date_str=args.date,
        dry_run=args.dry_run,
        skip_charts=args.skip_charts,
        skip_ai=args.skip_ai
    )

if __name__ == "__main__":
    main()
