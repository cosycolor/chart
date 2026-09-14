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
from src.email_sender import EmailSender

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
        sign = "+" if s['change_rate'] > 0 else ""
        print(f"  {idx}. {s['name']} ({s['code']}) | {sign}{s['change_rate']}% | 거래량: {s['volume_str']} [{tag_str}]")

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
                # 로컬 HTML 및 이메일 클라이언트(네이버/Gmail 등)에서 엑박 없이 바로 보이도록 Base64 인라인 인코딩
                with open(img_path, "rb") as img_f:
                    b64_data = base64.b64encode(img_f.read()).decode("utf-8")
                    image_map[s['code']] = f"data:image/png;base64,{b64_data}"
                print(f"  ✅ 차트 완료: {s['name']} -> {img_path}")
    else:
        print("\n⏩ 차트 생성을 건너뜁니다.")

    # 3. 뉴스 스크랩 및 AI 상승이유 분석
    print("\n🔍 [뉴스 수집 및 Gemini LLM 상승 이유 분석...]")
    news_searcher = NewsSearcher()
    analyzer = GeminiStockAnalyzer() if not skip_ai else None

    for idx, s in enumerate(stocks, 1):
        print(f"  [{idx}/{len(stocks)}] {s['name']} 뉴스 검색 중...")
        news_list = news_searcher.search_stock_news(s['name'], ticker=s['code'], target_date=target_date, max_count=6)
        
        if analyzer and analyzer.client:
            print(f"    🤖 Gemini AI로 상승 이유 분석 중...")
            ai_result = analyzer.analyze_stock_surge_reason(s, news_list, target_date=target_date)
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

            rate = s['change_rate']
            rate_sign = "+" if rate > 0 else ""
            first_title = top_articles[0]['title'] if top_articles else f"{s['name']} 특징주"

            if rate > 0:
                core_reason = f"{s['name']} 당일 +{rate}% 상승 및 대량 거래량({s['volume_str']}) 유입"
                theme_kw = [s['market'], "특징주", "급등주"]
            elif rate < 0:
                core_reason = f"{s['name']} 당일 {rate}% 하락 및 대량 거래량({s['volume_str']}) 발생"
                theme_kw = [s['market'], "특징주", "대량거래"]
            else:
                core_reason = f"{s['name']} 당일 보합 마감 및 대량 거래량({s['volume_str']}) 발생"
                theme_kw = [s['market'], "특징주", "대량거래"]

            detail_pts = [
                f"당일 등락률: {rate_sign}{rate}% (거래량: {s['volume_str']})",
                f"최근 실적: 매출 {s.get('quarter_revenue', '-')}, 당기순익 {s.get('quarter_net_income', '-')}"
            ]
            if first_title and "시황 바로가기" not in first_title:
                detail_pts.insert(0, f"주요 보도: {first_title}")

            s['ai_analysis'] = {
                "core_reason": core_reason,
                "detail_points": detail_pts,
                "theme_keywords": theme_kw,
                "top_articles": top_articles
            }

    # 4. 티스토리 발행 및 HTML 저장
    print("\n📝 [블로그 콘텐츠 생성 및 발행 처리...]")
    publisher = TistoryPublisher()

    # 실제 티스토리 업로드인 경우 이미지를 먼저 티스토리에 업로드
    if not dry_run and os.getenv("TISTORY_ACCESS_TOKEN"):
        for s in stocks:
            code = s['code']
            local_img = f"output/charts/{target_date}_{code}.png"
            if os.path.exists(local_img):
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

    # 5. 이메일 발송 (네이버/Gmail 등)
    if os.getenv("EMAIL_SENDER") and os.getenv("EMAIL_PASSWORD"):
        print("\n📬 [이메일 리포트 발송 처리...]")
        
        # SEO 최적화 제목 및 태그 자동 생성
        date_formatted = f"{target_date[:4]}.{target_date[4:6]}.{target_date[6:]}"
        top_stock_names = [s['name'] for s in stocks[:3]]
        
        # 주요 테마 키워드 수집
        all_keywords = []
        for s in stocks:
            all_keywords.extend(s.get("ai_analysis", {}).get("theme_keywords", []))
            all_keywords.append(s['name'])
        unique_tags = list(dict.fromkeys(all_keywords))[:12]
        
        highlight_keywords = [k for k in unique_tags if k not in top_stock_names and k not in ["KOSPI", "KOSDAQ", "특징주", "급등주"]][:2]
        theme_str = f" {', '.join(highlight_keywords)}" if highlight_keywords else ""
        stocks_str = "·".join(top_stock_names)
        
        seo_title = f"[{date_formatted}] 오늘의 상한가 및 특징주 총정리 ({stocks_str}{theme_str} 상승이유)"
        seo_tags = ", ".join(unique_tags)

        emailer = EmailSender()
        emailer.send_report_email(target_date, html_content, attachment_path=report_file, seo_title=seo_title, seo_tags=seo_tags)

    print("\n✨ 모든 프로세스가 성공적으로 완료되었습니다!")

def main():
    parser = argparse.ArgumentParser(description="한국 증시 상한가/1000만주 특징주 자동화 분석 및 발행기")
    parser.add_argument("--date", type=str, default=None, help="기준 일자 (YYYYMMDD). 미입력 시 최근 영업일 자동 계산")
    parser.add_argument("--dry-run", action="store_true", help="티스토리 포스팅을 하지 않고 로컬 HTML/차트만 생성")
    parser.add_argument("--skip-charts", action="store_true", help="차트 생성 건너뛰기 (빠른 디버깅용)")
    parser.add_argument("--skip-ai", action="add_to_main_ai", default=False, help="Gemini API 호출 건너뛰기 (기본값 사용)") if hasattr(argparse, "add_to_main_ai") else parser.add_argument("--skip-ai", action="store_true", help="Gemini API 호출 건너뛰기 (기본값 사용)")
    parser.add_argument("--list-categories", action="store_true", help="연결된 티스토리 블로그의 카테고리 목록 및 ID 조회")

    args = parser.parse_args()

    if args.list_categories:
        publisher = TistoryPublisher()
        categories = publisher.get_categories()
        if categories:
            print("\n📂 [티스토리 블로그 카테고리 목록]")
            print("-" * 50)
            print(f"{'카테고리 ID':<15} | {'카테고리 이름'}")
            print("-" * 50)
            for c in categories:
                print(f"{c.get('id', ''):<15} | {c.get('name', '')} (글 {c.get('entries', '0')}개)")
            print("-" * 50)
            print("💡 특정 카테고리에 글을 올리려면 위 ID 번호를 .env의 TISTORY_CATEGORY_ID에 입력하세요.")
        return

    run_pipeline(
        date_str=args.date,
        dry_run=args.dry_run,
        skip_charts=args.skip_charts,
        skip_ai=args.skip_ai
    )

if __name__ == "__main__":
    main()
