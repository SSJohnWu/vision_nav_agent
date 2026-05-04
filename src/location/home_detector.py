"""
家裡座標 + 回家偵測（geofence + streak）

判定規則：
  距離家 < 20m，且持續 5 分鐘 → 觸發「回家」事件
  之後距離家 > 20m 一次 → 觸發「出門」事件，重置狀態
"""
import json
import logging
import math
import os
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_HOME_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "home.json"
)
HOME_RADIUS_M = 20.0
ARRIVE_STREAK_SECONDS = 5 * 60


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """兩 GPS 座標間距離（公尺）"""
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class HomeDetector:
    def __init__(
        self,
        home_path: str = DEFAULT_HOME_PATH,
        radius_m: float = HOME_RADIUS_M,
        arrive_streak_seconds: float = ARRIVE_STREAK_SECONDS,
        on_arrive_home: Optional[Callable[[float], None]] = None,
        on_leave_home: Optional[Callable[[float], None]] = None,
    ):
        self.home_path = home_path
        self.radius_m = radius_m
        self.arrive_streak_seconds = arrive_streak_seconds
        self.on_arrive_home = on_arrive_home
        self.on_leave_home = on_leave_home

        # 家裡座標
        self.home_lat: Optional[float] = None
        self.home_lng: Optional[float] = None
        self._load_home()

        # 偵測狀態
        self._lock = threading.Lock()
        self._streak_start_ts: Optional[float] = None  # 進入半徑那一刻
        self._is_home: bool = False  # 已觸發 arrived_home，等待 left_home

    # ---- home location ----
    def _load_home(self):
        if not os.path.exists(self.home_path):
            logger.info("尚未設定家裡座標")
            return
        try:
            with open(self.home_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.home_lat = data["lat"]
            self.home_lng = data["lng"]
            logger.info(f"家裡座標載入: ({self.home_lat}, {self.home_lng})")
        except Exception as e:
            logger.error(f"讀取 home.json 失敗: {e}")

    def set_home(self, lat: float, lng: float):
        os.makedirs(os.path.dirname(os.path.abspath(self.home_path)), exist_ok=True)
        with open(self.home_path, "w", encoding="utf-8") as f:
            json.dump({"lat": lat, "lng": lng}, f, ensure_ascii=False, indent=2)
        self.home_lat = lat
        self.home_lng = lng
        # 重置偵測狀態
        with self._lock:
            self._streak_start_ts = None
            self._is_home = False
        logger.info(f"家裡座標已設定: ({lat}, {lng})")

    def has_home(self) -> bool:
        return self.home_lat is not None and self.home_lng is not None

    # ---- detection ----
    def ingest(self, ts: float, lat: float, lng: float) -> dict:
        """
        傳入一個 GPS 點，回傳當前狀態 dict：
          {
            "distance_m": float | None,
            "is_home": bool,
            "streak_seconds": float,  # 在半徑內已連續多久
            "event": "arrived_home" | "left_home" | None,
          }
        """
        if not self.has_home():
            return {"distance_m": None, "is_home": False, "streak_seconds": 0.0, "event": None}

        dist = haversine_m(lat, lng, self.home_lat, self.home_lng)
        event: Optional[str] = None

        with self._lock:
            within = dist < self.radius_m

            if within:
                if self._streak_start_ts is None:
                    self._streak_start_ts = ts
                streak = ts - self._streak_start_ts

                # 連續 5 分鐘且還沒觸發 → 觸發 arrived_home
                if streak >= self.arrive_streak_seconds and not self._is_home:
                    self._is_home = True
                    event = "arrived_home"
            else:
                # 跑出半徑就重置 streak
                self._streak_start_ts = None
                streak = 0.0

                # 如果之前是「在家」狀態 → 觸發 left_home
                if self._is_home:
                    self._is_home = False
                    event = "left_home"

        # callbacks 在鎖外呼叫，避免長時間任務鎖住下個 ingest
        if event == "arrived_home" and self.on_arrive_home:
            try:
                self.on_arrive_home(ts)
            except Exception as e:
                logger.error(f"on_arrive_home callback failed: {e}")
        elif event == "left_home" and self.on_leave_home:
            try:
                self.on_leave_home(ts)
            except Exception as e:
                logger.error(f"on_leave_home callback failed: {e}")

        return {
            "distance_m": round(dist, 1),
            "is_home": self._is_home,
            "streak_seconds": round(streak, 1),
            "event": event,
        }
