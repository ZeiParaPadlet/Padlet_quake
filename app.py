import websocket
from fastapi import FastAPI
from datetime import datetime
import folium
from folium.features import CustomIcon
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import os

app = FastAPI()

scale_num = [10, 20, 30, 40, 45, 50, 55, 60, 70]
scale_name = ["震度1", "震度2", "震度3", "震度4", "震度5弱", "震度5強", "震度6弱", "震度6強", "震度7"]

def scale_num2name(input):
    return scale_name[scale_num.index(input)]

@app.get("/")
async def read_root():
    return {"Hello": "World"}

def on_message(ws, message):
    if not message.id in checked_id:
        if message.code == 551:
            source = message.issue.source
            maxScale = scale_num2name(message.earthquake.maxScale)
            depth = message.earthquake.hypocenter.depth
            latitude = message.earthquake.hypocenter.latitude
            longitude = message.earthquake.hypocenter.longitude
            magnitude = message.earthquake.hypocenter.magnitude
            earthquake_name = message.earthquake.hypocenter.name
            tsunami = message.earthquake.domesticTsunami
            time = re.split('/ :', message.earthquake.time)
            dt_object = datetime.strptime(time, "%Y/%m/%d %H:%M:%S")
            time_str = dt_object.strftime("%Y年%m月%d日%H時%M分%S秒")
            points = message.points
            point_str = ""
            for point in points:
                point_str = point_str + point.pref + point.addr + ":" + scale_num2name(point.scale) + "\n"

def on_error(ws, error):
    print(f"エラー: {error}")

def on_close(ws, close_status_code, close_msg):
    print("接続が閉じられました")

def on_open(ws):
    print("接続が確立されました")

if __name__ == "__main__":
    uri = "wss://api.p2pquake.net/vs/ws" # テスト用の公開サーバー
    websocket.enableTrace(True) # デバッグログを有効にする
    
    # WebSocketAppクラスのインスタンスを作成
    ws = websocket.WebSocketApp(uri,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    # メインループを実行
    ws.run_forever()
