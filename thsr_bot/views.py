# Create your views here.
from collections import defaultdict

import requests
from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookHandler, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
line_habdler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

client_id = settings.CLIENT_ID
client_secret = settings.CLIENT_SECRET


# TDX
class TDX:
    # 初始化
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.basic_url = "https://tdx.transportdata.tw/api/basic/v2"
        # 緩存 access token，避免每次查詢都重新取得
        self.access_token = None

    # 取得 access token
    def get_access_token(self):
        token_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            return self.access_token
        except requests.exceptions.HTTPError as http_error:
            print(f"HTTP error occurred while getting access token: {http_error}")
        except Exception as error:
            print(f"An error occurred while getting access token: {error}")
        return None

    # 取得 response
    def get_response(self, url, params):
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
        }
        response = requests.get(url, headers=headers, params=params)
        return response

    # 取得車站資訊
    def get_station_info(self, station_input):
        url = f"{self.basic_url}/Rail/THSR/Station"

        # 如果 station_input 是數字，則認為是車站 ID，否則認為是車站名稱
        if station_input.isdigit():
            params = {
                "$select": "StationID,StationName",
                "$filter": f"StationID eq '{station_input}'",
                "$format": "JSON",
            }
        else:
            params = {
                "$select": "StationID,StationName",
                "$filter": f"contains(StationName/Zh_tw, '{station_input}')",
                "$top": 30,
                "$format": "JSON",
            }
        try:
            response = self.get_response(url, params)
            response.raise_for_status()  # 檢查請求是否成功
            # 此時取得的 response 是 list，所以先取第一個元素回傳
            return response.json()[0]
        except requests.exceptions.HTTPError as http_error:
            print(f"HTTP error occurred: {http_error}")
        except Exception as error:
            print(f"An error occurred: {error}")

    # 取得票價
    # fare_class 預設為 1:成人票，ticket_type 預設為 1:單程票
    def get_ticket_price(
        self, station_id, destination_id, cabin_class, fare_class=1, ticket_type=1
    ):
        url = f"{self.basic_url}/Rail/THSR/ODFare/{station_id}/to/{destination_id}"
        params = {
            "$select": "Fares,OriginStationName,DestinationStationName",
            # OData 的 filter 語法，從服務器端過濾數據，只有符合條件的數據會被傳回
            # 比在客戶端過濾更高效，但只要符合單一條件的票價就會被傳回(不確定原因，因為已經用 and 連接)
            "$filter": f"Fares/any(f: f/CabinClass eq {cabin_class} and f/FareClass eq {fare_class} and f/TicketType eq {ticket_type})",
            "$format": "JSON",
        }
        try:
            response = self.get_response(url, params)
            response.raise_for_status()
            ticket_data = response.json()
            if isinstance(ticket_data, list) and len(ticket_data) > 0:
                # 從 ticket_data 中取出第一個元素，並取得 Fares 欄位的值，如果不存在則返回空列表
                fares = ticket_data[0].get("Fares", [])
                # 在客戶端過濾，較靈活，會將符合條件的票價存入 filtered_fares
                filtered_fares = [
                    fare
                    for fare in fares
                    if fare.get("CabinClass") == cabin_class
                    and fare.get("FareClass") == fare_class
                    and fare.get("TicketType") == ticket_type
                ]
                return filtered_fares[0]["Price"]
            else:
                print("未找到對應的票價")
                return None

        except requests.exceptions.HTTPError as http_error:
            print(f"HTTP error occurred: {http_error}")
        except Exception as error:
            print(f"An error occurred: {error}")
        return None


@csrf_exempt
def callback(request):
    if request.method == "POST":
        # signature 是 LINE 用於驗證請求來源的機制
        signature = request.META["HTTP_X_LINE_SIGNATURE"]
        # body 是 LINE 用戶發送的訊息
        body = request.body.decode("utf-8")

        # 使用 WebhookParser 嘗試解析 LINE webhook 請求的 body
        try:
            events = parser.parse(body, signature)
        # signature 驗證失敗，回傳 403 Forbidden
        except InvalidSignatureError:
            return http.HttpResponseForbidden()
        # 無效請求，回傳 400 Bad Request
        except LineBotApiError:
            return http.HttpResponseBadRequest()

        line_habdler.handle(body, signature)
        return http.HttpResponse()
    else:
        return http.HttpResponseBadRequest()


# defaultdict 用來創建一個字典，這個字典用於管理用戶狀態或其他訊息
user_states = defaultdict(lambda: {"state": ""})

tdx = TDX(client_id, client_secret)


# 使用了 line_habdler 裝飾器的函數會被註冊為事件處理器，當事件發生時，會自動調用該函數
@line_habdler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    print("user_message:", user_message)
    print("user_states[user_id]:", user_states[user_id])
    print("user_states[user_id]['state']:", user_states[user_id]["state"])

    # if "退出" in user_message or "esc" in user_message.lower():
    #     user_states[user_id]["state"] = ""
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text="已退出高鐵查詢囉！")
    #     )

    # 查詢高鐵選項
    if user_states[user_id]["state"] == "":
        if "查詢" in user_message or "高鐵" in user_message:
            user_states[user_id]["state"] = "choose_query_type"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="[高鐵查詢]\n\n請選擇您想查詢的類型:\n1. 票價\n2. 車次"
                ),
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="嗨嗨！請輸入查詢高鐵，就可以開始查詢囉！"),
            )
    # 處理用戶選擇 - 票價查詢 / 車次查詢
    elif user_states[user_id]["state"] == "choose_query_type":
        if "票價" in user_message or "1" in user_message:
            user_states[user_id]["state"] = "ticket_price_start"
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="請輸入您的起始站：")
            )
        elif "車次" in user_message or "2" in user_message:
            # user_states[user_id]["state"] = "train_schedule_start"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="抱歉抱歉！目前車次查詢的功能還沒完成！\n如果要查詢票價請輸入1，或退出查詢請輸入3！"
                ),
            )
        elif "退出" in user_message or "3" in user_message:
            user_states[user_id]["state"] = ""
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="已退出高鐵查詢囉！")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入正確的查詢類型，或退出查詢請輸入3"),
            )
    # 票價查詢
    elif user_states[user_id]["state"] == "ticket_price_start":
        start_station_info = tdx.get_station_info(user_message)
        if start_station_info:
            # 將起始站資訊存入 user_states
            user_states[user_id]["start_station_id"] = start_station_info["StationID"]
            user_states[user_id]["state"] = "ticket_price_destination"
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="請輸入您的目的地站：")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="抱歉，找不到您輸入的起始站，請重新輸入，或者要退出查詢請輸入3！"
                ),
            )

    elif user_states[user_id]["state"] == "ticket_price_destination":
        destination_station_info = tdx.get_station_info(user_message)
        try:
            # 將目的地站資訊存入 user_states
            user_states[user_id]["destination_station_id"] = destination_station_info[
                "StationID"
            ]
            user_states[user_id]["state"] = "ticket_price_cabin"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="請選擇您的車廂等級：\n1. 標準座車廂\n2. 商務座車廂\n3. 自由座車廂"
                ),
            )
        except Exception:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="找不到目的地站，請重新輸入：")
            )

    elif user_states[user_id]["state"] == "ticket_price_cabin":
        if "1" in user_message or "標準" in user_message:
            user_states[user_id]["cabin"] = 1
        elif "2" in user_message or "商務" in user_message:
            user_states[user_id]["cabin"] = 2
        elif "3" in user_message or "自由" in user_message:
            user_states[user_id]["cabin"] = 3
        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="請輸入正確的車廂等級")
            )

        ticket_price = tdx.get_ticket_price(
            user_states[user_id]["start_station_id"],
            user_states[user_id]["destination_station_id"],
            user_states[user_id]["cabin"],
        )

        # 將車廂等級轉換為中文
        if user_states[user_id]["cabin"] == 1:
            cabin_name = "標準座車廂"
        elif user_states[user_id]["cabin"] == 2:
            cabin_name = "商務座車廂"
        else:
            cabin_name = "自由座車廂"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"[高鐵票價查詢結果]\n\n起始站：{tdx.get_station_info(user_states[user_id]['start_station_id'])['StationName']['Zh_tw']}\n目的地站：{tdx.get_station_info(user_states[user_id]['destination_station_id'])['StationName']['Zh_tw']}\n車廂等級：{cabin_name}\n\n票價為：{ticket_price}"
            ),
        )
        # 查詢結束後，將 state 歸零
        user_states.clear()
