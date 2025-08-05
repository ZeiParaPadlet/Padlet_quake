import websocket
import json
import re
from fastapi import FastAPI
from datetime import datetime
import folium
from folium.features import CustomIcon
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import os
import asyncio
import threading

app = FastAPI()

# データを格納するためのスレッドセーフなコンテナ
# 実際のアプリケーションでは、データベースなどを使うべきです
earthquake_data = {}
earthquake_image_path = ""

scale_num = [10, 20, 30, 40, 45, 50, 55, 60, 70]
scale_name = ["震度1", "震度2", "震度3", "震度4", "震度5弱", "震度5強", "震度6弱", "震度6強", "震度7"]

def scale_num2name(input):
    try:
        return scale_name[scale_num.index(input)]
    except ValueError:
        return "不明"

@app.get("/")
async def read_root():
    return {"message": "WebSocketクライアントが実行されています。/get_quake_551で最新の地震情報を取得できます。"}

@app.get("/get_quake_551")
async def get_quake_551():
    global earthquake_data
    return earthquake_data

@app.get("/get_quake_image")
async def get_quake_image():
    global earthquake_image_path
    if not earthquake_image_path or not os.path.exists(earthquake_image_path):
        return {"error": "画像がまだ生成されていません。"}
    return {"image_path": earthquake_image_path}

def on_message(ws, message):
    global earthquake_data, earthquake_image_path
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        print("Received invalid JSON")
        return

    # ここではidによる重複チェックは省略

    if data.get("code") == 551:
        issue = data.get("issue", {})
        earthquake = data.get("earthquake", {})
        hypocenter = earthquake.get("hypocenter", {})
        points = data.get("points", [])

        source = issue.get("source")
        maxScale = scale_num2name(earthquake.get("maxScale"))
        depth = hypocenter.get("depth")
        latitude = hypocenter.get("latitude")
        longitude = hypocenter.get("longitude")
        magnitude = hypocenter.get("magnitude")
        earthquake_name = hypocenter.get("name")
        tsunami = earthquake.get("domesticTsunami")
        time_str_raw = earthquake.get("time")

        if time_str_raw:
            try:
                dt_object = datetime.strptime(time_str_raw, "%Y/%m/%d %H:%M:%S")
                time_str = dt_object.strftime("%Y年%m月%d日%H時%M分%S秒")
            except ValueError:
                time_str = "日時解析エラー"
        else:
            time_str = "日時不明"

        point_str = ""
        for point in points:
            point_str += f"{point.get('pref')}{point.get('addr')}: {scale_num2name(point.get('scale'))}\n"
        
        # データをグローバル変数に格納
        earthquake_data = {
            "source": source,
            "maxScale": maxScale,
            "depth": depth,
            "latitude": latitude,
            "longitude": longitude,
            "magnitude": magnitude,
            "earthquake_name": earthquake_name,
            "tsunami": tsunami,
            "time": time_str,
            "points": point_str.strip()
        }
        
        # 地図画像の生成
        if latitude and longitude:
            try:
                icon_image_path = 'icon.png'
                m = folium.Map(location=[latitude, longitude], zoom_start=10)
                icon = CustomIcon(icon_image=icon_image_path, icon_size=(50, 50))
                folium.Marker(location=[latitude, longitude], tooltip="震源", icon=icon).add_to(m)
                
                for point in points:
                    if 'latitude' in point and 'longitude' in point:
                         folium.Marker(
                             location=[point.get('latitude'), point.get('longitude')],
                             tooltip=f"{point.get('pref')} {point.get('addr')}: {scale_num2name(point.get('scale'))}",
                             icon=folium.Icon(color='red', icon='info-sign')
                         ).add_to(m)

                html_file_path = "map.html"
                m.save(html_file_path)

                options = Options()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--window-size=800,600")

                driver = webdriver.Chrome(options=options)
                driver.get(f"file://{os.path.abspath(html_file_path)}")
                screenshot_path = "map_with_custom_icon.png"
                driver.save_screenshot(screenshot_path)
                driver.quit()

                earthquake_image_path = screenshot_path
                print("地震画像が更新されました。")

            except Exception as e:
                print(f"地図画像の生成中にエラーが発生しました: {e}")

def on_error(ws, error):
    print(f"エラー: {error}")

def on_close(ws, close_status_code, close_msg):
    print("接続が閉じられました")

def on_open(ws):
    print("接続が確立されました")

def run_websocket():
    uri = "wss://api.p2pquake.net/v2/ws"
    ws = websocket.WebSocketApp(uri,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

# FastAPIの起動前にWebSocketクライアントを別スレッドで実行
websocket_thread = threading.Thread(target=run_websocket)
websocket_thread.daemon = True
websocket_thread.start()
