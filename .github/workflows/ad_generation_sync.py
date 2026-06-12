#!/usr/bin/env python3
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from io import StringIO
import json

load_dotenv()

AD_GEN_API_BASE = "https://ad-generation.jp/api/v2"
AD_GEN_EMAIL = os.getenv("AD_GENERATION_EMAIL")
AD_GEN_PASSWORD = os.getenv("AD_GENERATION_PASSWORD")
SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_JSON_PATH", "./service_account.json")
SHEET_NAME = "AdGeneration_入力"


def get_ad_generation_token():
    print("📡 Ad Generation トークンを取得中...")
    url = f"{AD_GEN_API_BASE}/tokens.json"
    data = {"email": AD_GEN_EMAIL, "password": AD_GEN_PASSWORD}

    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise ValueError("トークンが返されませんでした")
        print("✅ トークン取得成功")
        return token
    except Exception as e:
        print(f"❌ トークン取得失敗: {e}")
        raise


def fetch_ad_generation_report(token, days=7):
    print(f"📊 Ad Generation レポートを取得中（過去{days}日分）...")

    end_date = datetime.now().date()
    begin_date = end_date - timedelta(days=days-1)

    url = f"{AD_GEN_API_BASE}/report/performances.csv"
    params = {
        "token": token,
        "currency": "JPY",
        "begin_date": begin_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        df = pd.read_csv(StringIO(response.text))
        print(f"✅ レポート取得成功（{len(df)}行）")
        return df
    except Exception as e:
        print(f"❌ レポート取得失敗: {e}")
        raise


def get_sheets_service():
    print("🔐 Google認証中...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    service_account_json_str = os.getenv("SERVICE_ACCOUNT_JSON")
    service_account_json = json.loads(service_account_json_str)

    try:
        credentials = Credentials.from_service_account_info(
            service_account_json,
            scopes=scopes
        )
        service = build("sheets", "v4", credentials=credentials)
        print("✅ Google認証成功")
        return service
    except Exception as e:
        print(f"❌ Google認証失敗: {e}")
        raise


def append_to_sheets(service, sheet_id, data_df):
    print("📝 スプレッドシートに追記中...")

    try:
        data_df = data_df.fillna("")
        values = [data_df.columns.tolist()] + data_df.values.tolist()
        values = [[str(cell) for cell in row] for row in values]

        request = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"'{SHEET_NAME}'!A:O",
            valueInputOption="RAW",
            body={"values": values}
        )
        result = request.execute()
        print(f"✅ スプレッドシート更新成功（{len(values)-1}行追記）")
        return result
    except HttpError as e:
        print(f"❌ スプレッドシート更新失敗: {e}")
        raise
    except Exception as e:
        print(f"❌ エラー: {e}")
        raise


def main():
    print("=" * 50)
    print("🚀 Ad Generation レポート自動取得を開始します")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    try:
        token = get_ad_generation_token()
        df = fetch_ad_generation_report(token, days=7)
        service = get_sheets_service()
        append_to_sheets(service, SHEETS_ID, df)

        print("=" * 50)
        print("✨ 処理完了！")
        print("=" * 50)

    except Exception as e:
        print("=" * 50)
        print(f"❌ 処理失敗: {e}")
        print("=" * 50)
        raise


if __name__ == "__main__":
    main()
