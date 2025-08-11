import websocket
import json
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
from fastapi.responses import JSONResponse
import scratchattach as sa
import requests

username = os.getenv("USERNAME")
session_id = os.getenv("SESSION_ID")
project_id = os.getenv("PROJECT_ID")
print(username)
print(session_id)
print(project_id)

app = FastAPI()

images_id = 0
quake_list = []
quake_image_list = []
# データを格納するためのスレッドセーフなコンテナ
# 実際のアプリケーションでは、データベースなどを使うべきです
earthquake_data = {}
earthquake_image_path = ""
id_list = []

scale_num = [10, 20, 30, 40, 45, 50, 55, 60, 70]
scale_name = ["震度1", "震度2", "震度3", "震度4", "震度5弱", "震度5強", "震度6弱", "震度6強", "震度7"]

# Scratch接続用のグローバル変数を初期化
session = None
cloud = None

def scale_num2name(input):
    try:
        return scale_name[scale_num.index(input)]
    except ValueError:
        return "不明"

@app.get("/")
async def read_root():
    content = {"message": "WebSocketクライアントが実行されています。/get_quake_551で最新の地震情報を取得できます。"}
    return JSONResponse(content=content, media_type="application/json; charset=utf-8")

@app.get("/get_quake_551")
async def get_quake_551():
    global quake_list
    if not quake_list:
        return {"error": "情報がまだ生成されていません。"}
    return quake_list[-1]

@app.get("/get_quake_image")
async def get_quake_image():
    global quake_image_list
    if not quake_image_list or not os.path.exists(quake_image_list[-1]):
        return {"error": "画像がまだ生成されていません。"}
    return {"image_path": earthquake_image_path[-1]}

def init_scratch_connection():
    """Scratchクラウド接続を初期化するヘルパー関数"""
    global session, cloud
    try:
        if not session or not cloud:
            print("Scratchへの接続を試みます...")
            session = sa.login_by_id(session_id, username=username)
            cloud = session.connect_cloud(project_id)
            print("Scratchクラウド接続を確立しました。")
    except Exception as e:
        print(f"Scratchへの接続中にエラーが発生しました: {e}")
        session = None
        cloud = None

def on_message(ws, message):
    global quake_list, quake_image_list, id_list
    init_scratch_connection()
    
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        print("Received invalid JSON")
        return

    # IDの重複チェック
    message_id = data.get("_id")
    if message_id in id_list:
        print(f"ID {message_id} は既に処理済みです。")
        return
    else:
        id_list.append(message_id)

    if data.get("code") == 551:
        print(str(message))
        issue = data.get("issue", {})
        earthquake = data.get("earthquake", {})
        hypocenter = earthquake.get("hypocenter", {})
        points = data.get("points", [])

        source = issue.get("source")
        maxScale_num = earthquake.get("maxScale")
        maxScale = scale_num2name(maxScale_num)
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
        quake_list.append({
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
        })

        # Scratchクラウド変数への送信処理
        if cloud:
            try:
                responce = requests.get(f"https://api.zeipara.f5.si/kanji?context={earthquake_name}")
                kanji_data = responce.text
                
                # スケールが不明の場合は0に設定
                max_scale_value = maxScale_num if maxScale_num else 0
                
                cloud.set_var("1", f"{kanji_data}00000{depth}00000{magnitude * 10}00000{max_scale_value * 10}")
            except Exception as e:
                print(f"Scratchクラウド変数更新中にエラーが発生しました: {e}")
                cloud = None
        else:
            print("Scratchクラウドに接続されていません。変数を送信できません。")
            
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
                screenshot_path = f"map_with_custom_icon{images_id}.png"
                driver.save_screenshot(screenshot_path)
                driver.quit()

                quake_image_list.append(screenshot_path)
                print("地震画像が更新されました。")

            except Exception as e:
                print(f"地図画像の生成中にエラーが発生しました: {e}")

def on_error(ws, error):
    print(f"エラー: {error}")

def on_close(ws, close_status_code, close_msg):
    global session, cloud
    print("接続が閉じられました")
    if cloud:
        try:
            cloud.disconnect()
            print("Scratch接続を切断しました。")
        except Exception as e:
            print(f"Scratch切断中にエラーが発生しました: {e}")
        cloud = None
    session = None
    
def on_open(ws):
    print("WebSocket接続が確立されました")
    init_scratch_connection()

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
