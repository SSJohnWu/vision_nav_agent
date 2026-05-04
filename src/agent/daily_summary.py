"""
每日總結
回家事件觸發後，串接：
  - Google Calendar 今日事件
  - GPS 軌跡 (SQLite locations)
  - 拍照記錄 (SQLite photos)
然後請龍蝦 (OpenClaw) 寫一段總結文字，推到 Telegram
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from location.home_detector import haversine_m
from storage.db import get_db

logger = logging.getLogger(__name__)


def _today_bounds() -> tuple:
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return start.timestamp(), end.timestamp()


def gather_today_data() -> dict:
    """整理今天所有資料成 dict（給 LLM 看）"""
    ts_start, ts_end = _today_bounds()
    db = get_db()

    # GPS
    points = db.fetch_locations_between(ts_start, ts_end)
    total_dist = 0.0
    if len(points) >= 2:
        for a, b in zip(points, points[1:]):
            total_dist += haversine_m(a["lat"], a["lng"], b["lat"], b["lng"])

    # photos
    photos = db.fetch_photos_between(ts_start, ts_end)

    # calendar (lazy import 避免沒授權時 import 就死)
    events = []
    try:
        import os
        from integrations.google_calendar import GoogleCalendarClient
        token_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
        if os.path.exists(token_path):
            cal = GoogleCalendarClient(token_path=token_path)
            events = cal.list_events_today()
    except Exception as e:
        logger.warning(f"讀 Google Calendar 失敗: {e}")

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "events": events,
        "gps_count": len(points),
        "gps_total_distance_m": round(total_dist, 1),
        "gps_first": points[0] if points else None,
        "gps_last": points[-1] if points else None,
        "photos": photos,
    }


def build_prompt(data: dict) -> str:
    """把 dict 轉成給龍蝦看的提示詞"""
    lines = [
        "你是視障使用者的個人生活助理。請根據下列今日資料，用繁體中文寫一段親切的「今日總結」，",
        "字數 150-250 字。內容請涵蓋：今天主要去了哪些地方（從行程與 GPS 推測）、",
        "是否完成行程上的事項、拍下了哪些商品。語氣溫暖簡潔，不要列點，用自然口語的段落。",
        "",
        f"=== 日期：{data['date']} ===",
        "",
        "【今日行事曆】",
    ]
    if data["events"]:
        for e in data["events"]:
            title = e.get("summary", "(無標題)")
            start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")
            location = e.get("location", "")
            lines.append(f"- {start} {title}" + (f" @ {location}" if location else ""))
    else:
        lines.append("(沒有任何事件)")

    lines.append("")
    lines.append("【GPS 軌跡】")
    lines.append(
        f"今天共記錄 {data['gps_count']} 個位置點，總移動距離約 {data['gps_total_distance_m']} 公尺"
    )

    lines.append("")
    lines.append("【今日拍下的商品】")
    if data["photos"]:
        for p in data["photos"]:
            ts = datetime.fromtimestamp(p["timestamp"]).strftime("%H:%M")
            name = p.get("product_name") or "(辨識中或失敗)"
            price = p.get("price") or "?"
            loc = ""
            if p.get("lat") and p.get("lng"):
                loc = f" @ ({p['lat']:.5f}, {p['lng']:.5f})"
            lines.append(f"- {ts} {name} 價格 {price}{loc}")
    else:
        lines.append("(今天沒拍商品)")

    return "\n".join(lines)


def run(vision_analyzer, telegram_client) -> Optional[str]:
    """
    執行每日總結。回傳 LLM 產出的文字（或 None）。
    被 _on_arrive_home callback 叫，也可以被 /api/daily_summary/run 手動叫。
    """
    data = gather_today_data()

    has_anything = data["events"] or data["gps_count"] > 0 or data["photos"]
    if not has_anything:
        logger.info("今天沒任何資料，跳過每日總結")
        return None

    prompt = build_prompt(data)
    logger.info(f"DailySummary prompt 長度 {len(prompt)} 字元")
    logger.info(f"DailySummary prompt 預覽:\n{prompt[:500]}...")

    summary_text = vision_analyzer.chat_text(prompt)

    if not summary_text:
        # 龍蝦掛了，至少把原始資料推 Telegram，讓使用者知道有資料
        fallback = (
            f"⚠️ 今日總結 ({data['date']})：龍蝦無法生成摘要\n\n"
            f"行事曆 {len(data['events'])} 筆\n"
            f"GPS {data['gps_count']} 點，移動 {data['gps_total_distance_m']} m\n"
            f"拍照 {len(data['photos'])} 張"
        )
        telegram_client.send_message(fallback)
        return None

    msg = f"📝 今日總結 ({data['date']})\n\n{summary_text}"
    telegram_client.send_message(msg)
    logger.info(f"DailySummary 已送出: {summary_text[:120]}...")
    return summary_text
