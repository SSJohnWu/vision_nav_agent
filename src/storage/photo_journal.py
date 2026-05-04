"""
PhotoJournal：把使用者拍的商品照片寫進磁碟，並把 metadata 存進 SQLite

檔案結構：
  data/photos/YYYY-MM-DD/<timestamp>_<rand>.jpg
"""
import json
import logging
import os
import secrets
import time
from datetime import datetime
from typing import Optional

from .db import get_db

logger = logging.getLogger(__name__)

PHOTOS_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "photos")


def _build_photo_path(ts: float) -> str:
    """產生 data/photos/YYYY-MM-DD/<ts>_<rand>.jpg 的絕對路徑"""
    dt = datetime.fromtimestamp(ts)
    day_dir = os.path.join(PHOTOS_ROOT, dt.strftime("%Y-%m-%d"))
    os.makedirs(day_dir, exist_ok=True)
    fname = f"{int(ts)}_{secrets.token_hex(3)}.jpg"
    return os.path.join(day_dir, fname)


def save_photo(
    image_bytes: bytes,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    recognition: Optional[dict] = None,
    timestamp: Optional[float] = None,
) -> dict:
    """
    存圖檔 + 寫一筆 photos row。
    回傳 {id, file_path, timestamp}
    """
    ts = timestamp if timestamp else time.time()
    path = _build_photo_path(ts)
    with open(path, "wb") as f:
        f.write(image_bytes)

    product_name = price = summary = raw_json = None
    if recognition:
        if isinstance(recognition, dict):
            product_name = recognition.get("product_name")
            price = recognition.get("price")
            summary = recognition.get("summary")
            raw_json = json.dumps(recognition, ensure_ascii=False)
        else:
            raw_json = json.dumps({"raw": str(recognition)}, ensure_ascii=False)

    photo_id = get_db().insert_photo(
        timestamp=ts,
        file_path=path,
        lat=lat,
        lng=lng,
        product_name=product_name,
        price=price,
        summary=summary,
        raw_json=raw_json,
    )

    logger.info(f"PhotoJournal 寫入 #{photo_id} → {path}")
    return {"id": photo_id, "file_path": path, "timestamp": ts}
