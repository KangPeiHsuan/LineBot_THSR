# Create your views here.
from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


# 測試用 -  echo
@csrf_exempt
def callback(request):
    if request.method == "POST":
        signature = request.META["HTTP_X_LINE_SIGNATURE"]
        body = request.body.decode("utf-8")

        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return http.HttpResponseForbidden()
        except LineBotApiError:
            return http.HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):
                mtext = event.message.text
                message = []
                if isinstance(event.message, TextMessage):
                    message.append(TextSendMessage(text=mtext))
                    line_bot_api.reply_message(event.reply_token, message)
                else:
                    message.append(
                        TextSendMessage(text="嗨嗨～有什麼事情想跟我說的嗎？")
                    )
                    line_bot_api.reply_message(event.reply_token, message)

        return http.HttpResponse()
    else:
        return http.HttpResponseBadRequest()


# @csrf_exempt
# def callback(request):
#     if request.method == "POST":
#         # 先建立一個 message 空串列，準備存放回傳的訊息
#         message = []
#         # signature 是 LINE 用於驗證請求來源的機制
#         signature = request.META["HTTP_X_LINE_SIGNATURE"]
#         # body 是 LINE 用戶發送的訊息
#         body = request.body.decode("utf-8")

#         # 嘗試解析 LINE webhook 請求的 body
#         try:
#             events = parser.parse(body, signature)
#         # signature 驗證失敗，回傳 403 Forbidden
#         except InvalidSignatureError:
#             return http.HttpResponseForbidden()
#         # 無效請求，回傳 400 Bad Request
#         except LineBotApiError:
#             return http.HttpResponseBadRequest()

#         for event in events:
#             mtext = event.message.text
#             message.append(TextSendMessage(text=mtext))

#             if isinstance(event, MessageEvent):
#                 print(MessageEvent)
#                 print(event.message.type)
#                 # 用 isinstance 判斷 event.message 是否是 TextMessage 類型
#                 # 類型檢查 比 屬性檢查 event.message.type 更為嚴謹
#                 if isinstance(event.message, TextMessage):
#                     message.append(TextSendMessage(text=event.message.text))
#                     line_bot_api.reply_message(event.reply_token, message)
#                 elif isinstance(event.message, ImageMessage):
#                     message.append(TextSendMessage(text="謝謝你分享的圖片！"))
#                     line_bot_api.reply_message(event.reply_token, message)
#                 elif isinstance(event.message, StickerMessage):
#                     message.append(TextSendMessage(text="謝謝你分享的貼圖！"))
#                     line_bot_api.reply_message(event.reply_token, message)
#                 else:
#                     message.append(TextSendMessage(text="heyyy"))
#                     line_bot_api.reply_message(event.reply_token, message)

#         return http.HttpResponse()
