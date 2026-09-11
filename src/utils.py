import os
import datetime
from datetime import datetime, timedelta

def get_target_date(input_date: str = None) -> str:
    """
    대상 기준일을 반환합니다 (YYYYMMDD 형식).
    input_date가 주어지면 그대로 검증 후 반환하고,
    없으면 오늘 날짜를 기준으로 장마감(15:30) 이전이거나 주말인 경우 가장 최근 평일로 보정합니다.
    """
    now = datetime.now()
    if input_date:
        # 형식 정리 (예: 2026-09-11 -> 20260911)
        cleaned = input_date.replace("-", "").replace(".", "").strip()
        if len(cleaned) == 8:
            return cleaned

    # 현재 시각 기준
    # 15:30 이전이면 전일자 기준, 이후면 오늘자 기준 (주말 제외)
    target = now
    if target.hour < 15 or (target.hour == 15 and target.minute < 30):
        target = target - timedelta(days=1)

    # 토요일(5) -> 금요일(-1)
    if target.weekday() == 5:
        target = target - timedelta(days=1)
    # 일요일(6) -> 금요일(-2)
    elif target.weekday() == 6:
        target = target - timedelta(days=2)

    return target.strftime("%Y%m%d")

def format_korean_number(val: float, unit: str = "원") -> str:
    """
    숫자를 한국어 단위(조, 억, 만)로 가독성 높게 변환합니다.
    예: 1250000000000 -> 1조 2,500억원
    """
    if val is None or val == 0:
        return "-"
    
    is_negative = val < 0
    val = abs(val)

    if val >= 1_000_000_000_000:
        cho = int(val // 1_000_000_000_000)
        eok = int((val % 1_000_000_000_000) // 100_000_000)
        res = f"{cho}조 {eok:,}억" if eok > 0 else f"{cho}조"
    elif val >= 100_000_000:
        eok = int(val // 100_000_000)
        res = f"{eok:,}억"
    elif val >= 10_000:
        man = int(val // 10_000)
        res = f"{man:,}만"
    else:
        res = f"{int(val):,}"

    prefix = "-" if is_negative else ""
    return f"{prefix}{res}{unit}"

def format_volume(volume: int) -> str:
    """
    거래량을 1,000만주 단위 등으로 표기합니다.
    """
    if not volume:
        return "0주"
    if volume >= 10_000_000:
        man = volume / 10_000
        return f"{man:,.0f}만 주"
    elif volume >= 10_000:
        man = volume / 10_000
        return f"{man:,.1f}만 주"
    return f"{volume:,}주"

def ensure_dir(dir_path: str) -> str:
    """디렉토리가 없으면 생성합니다."""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path
