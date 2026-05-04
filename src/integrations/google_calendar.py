"""
Google Calendar 客戶端
封裝事件新增、查詢，會自動處理 token 續期
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TZ = "Asia/Taipei"


class GoogleCalendarClient:
    def __init__(self, token_path: str = "token.json"):
        if not os.path.exists(token_path):
            raise FileNotFoundError(
                f"找不到 {token_path}，請先執行 python setup_google_auth.py 完成授權"
            )

        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                logger.info("Google token 已自動續期")
            else:
                raise RuntimeError("Google token 無效且無法續期，請重跑 setup_google_auth.py")

        self.service = build("calendar", "v3", credentials=creds)
        logger.info("GoogleCalendarClient ready")

    def add_event(
        self,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        if end is None:
            end = start + timedelta(hours=1)

        body = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": DEFAULT_TZ},
            "end": {"dateTime": end.isoformat(), "timeZone": DEFAULT_TZ},
        }
        if location:
            body["location"] = location
        if description:
            body["description"] = description

        event = self.service.events().insert(calendarId="primary", body=body).execute()
        logger.info(f"Calendar event 建立: {event.get('id')} {title}")
        return event

    def list_events_today(self, max_results: int = 20) -> list:
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        return self.list_events(start_of_day, end_of_day, max_results)

    def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 20,
    ) -> list:
        result = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=time_min.isoformat().replace("+00:00", "Z"),
                timeMax=time_max.isoformat().replace("+00:00", "Z"),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return result.get("items", [])
