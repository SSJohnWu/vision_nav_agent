"""
SQLite 資料層
存 GPS 軌跡、回家事件、(未來) 拍照記錄
"""
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "tracks.db"
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    accuracy REAL
);
CREATE INDEX IF NOT EXISTS idx_locations_timestamp ON locations(timestamp);

CREATE TABLE IF NOT EXISTS home_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('arrived_home', 'left_home'))
);
CREATE INDEX IF NOT EXISTS idx_home_events_timestamp ON home_events(timestamp);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    file_path TEXT NOT NULL,
    lat REAL,
    lng REAL,
    product_name TEXT,
    price TEXT,
    summary TEXT,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_photos_timestamp ON photos(timestamp);
"""

# sqlite3 連線預設不能跨執行緒共用，FastAPI ThreadPool 會多執行緒呼叫
# 用 threading.Lock 包寫入，連線本身用 check_same_thread=False
_lock = threading.Lock()


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info(f"Database ready at {db_path}")

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        with _lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            finally:
                cur.close()

    # ---- locations ----
    def insert_location(self, timestamp: float, lat: float, lng: float, accuracy: Optional[float] = None) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO locations (timestamp, lat, lng, accuracy) VALUES (?, ?, ?, ?)",
                (timestamp, lat, lng, accuracy),
            )
            return cur.lastrowid

    def fetch_locations_between(self, ts_min: float, ts_max: float) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT timestamp, lat, lng, accuracy FROM locations "
                "WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                (ts_min, ts_max),
            )
            return [dict(r) for r in cur.fetchall()]

    # ---- home events ----
    def insert_home_event(self, timestamp: float, event_type: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO home_events (timestamp, event_type) VALUES (?, ?)",
                (timestamp, event_type),
            )
            return cur.lastrowid

    def latest_home_event(self) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT timestamp, event_type FROM home_events ORDER BY timestamp DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None

    # ---- photos ----
    def insert_photo(
        self,
        timestamp: float,
        file_path: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        product_name: Optional[str] = None,
        price: Optional[str] = None,
        summary: Optional[str] = None,
        raw_json: Optional[str] = None,
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO photos (timestamp, file_path, lat, lng, product_name, price, summary, raw_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (timestamp, file_path, lat, lng, product_name, price, summary, raw_json),
            )
            return cur.lastrowid

    def fetch_photos_between(self, ts_min: float, ts_max: float) -> list:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, timestamp, file_path, lat, lng, product_name, price, summary "
                "FROM photos WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                (ts_min, ts_max),
            )
            return [dict(r) for r in cur.fetchall()]

    def fetch_photo(self, photo_id: int) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, timestamp, file_path, lat, lng, product_name, price, summary, raw_json "
                "FROM photos WHERE id = ?",
                (photo_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self):
        self._conn.close()


# Singleton instance
_db: Optional[Database] = None

def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
