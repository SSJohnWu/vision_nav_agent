"""
Google Calendar OAuth 一次性授權腳本

使用方式：
    1. 先到 Google Cloud Console 下載 OAuth Client (Desktop App) 的 credentials.json，
       放到專案根目錄
    2. python setup_google_auth.py
    3. 瀏覽器會跳出 Google 登入畫面，完成授權後 token.json 會存到專案根目錄
    4. 之後 web_main.py 啟動時會自動讀取 token.json (含 refresh token，會自動續期)
"""
import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"[X] 找不到 {CREDENTIALS_FILE}")
        print()
        print("請先到 Google Cloud Console 完成以下步驟：")
        print("  1. 建立專案 → 啟用 Google Calendar API")
        print("  2. 建立 OAuth 2.0 Client ID → 類型選『Desktop app』")
        print("  3. 下載 JSON 檔，重新命名為 credentials.json，放到專案根目錄")
        print("  4. 重新執行本腳本")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.valid:
        print(f"[OK] {TOKEN_FILE} 已存在且有效，無需重新授權")
        return

    if creds and creds.expired and creds.refresh_token:
        print("[..] Token 過期，使用 refresh token 續期...")
        creds.refresh(Request())
    else:
        print("[..] 開啟瀏覽器進行 OAuth 授權...")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"[OK] 授權完成，token 已存到 {TOKEN_FILE}")


if __name__ == "__main__":
    main()
