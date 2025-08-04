import websocket
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

def on_message(ws, message):
    """
    WebSocketからメッセージを受信したときに実行される関数。
    """
    print(f"受信したメッセージ: {message}")
    
    # ここにメッセージを受信したときに実行したいプログラムを書く
    # 例: 受信したメッセージに応じて異なる処理を実行する
    if message == "hello":
        print("Hello, server!")
    elif message == "ping":
        print("pong")

def on_error(ws, error):
    """
    エラーが発生したときに実行される関数。
    """
    print(f"エラー: {error}")

def on_close(ws, close_status_code, close_msg):
    """
    接続が閉じられたときに実行される関数。
    """
    print("接続が閉じられました")

def on_open(ws):
    """
    接続が確立されたときに実行される関数。
    """
    print("接続が確立されました")
    # 接続後、すぐにメッセージを送信することも可能
    ws.send("hello")

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
