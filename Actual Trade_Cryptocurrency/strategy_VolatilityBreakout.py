
# config.py: API 키, 심볼, K값, 체크 주기 같은 설정만 저장. API Key 등 파라미터 관리
# exchange.py: 빗썸 API와 통신하고, 받은 데이터를 프로그램에서 쓰기 편한 형태로 변환.
# strategy.py: 오직 "언제 사고 언제 팔 것인가"만 판단.
# main.py: 일정 시간마다 run()을 반복 실행.


# ===========================================================================


from exchange import *
from config import *

position = "NONE"

def get_target_price():
    candles = get_candles(count=2)

    prev = candles[0]

    open_price = prev["open"]
    high = prev["high"]
    low = prev["low"]
    close = prev["close"]

    target = open_price + (high - low) * K

    return target


def run():

    global position
    target = get_target_price()
    current = get_current_price()
    krw = get_balance(MARKET)
    btc = get_balance(COIN)


    print("----------------------------")
    print("Target :", target)
    print("Current :", current)
    print("KRW :", krw)
    print("BTC :", btc)


    if current > target:

        if position == "NONE" and krw > MIN_KRW:

            print("BUY")

            result = buy_market(krw)

            if result is not None:
                position = "LONG"
                print(result)
                print("주문번호 :", result["order_id"])

    elif current < target:

        if position == "LONG" and btc > 0:
            print("SELL")
            result = sell_market(btc)
            if result is not None:
                position = "NONE"
                print(result)
                print("주문번호 :", result["order_id"])            



# ===========================================================================


# 예전 CCXT 버전 코드


# from exchange import *
# from config import *

# def get_target_price() :
#     candles = get_ohlcv(SYMBOL, "1m", 2)
#     timestamp, open_price, high, low, close, volume = candles[0]
#     target = close + (high - low) * K
#     return target


# def run() : 
#     target = get_target_price()
#     current = get_current_price(SYMBOL)
#     print("------------------------------")
#     print("Target :", target)
#     print("Current :", current)
#     if current > target : 
#         krw = get_balance("KRW")
#         print("KRW : ", krw)
#         if krw > MIN_KRW : 
#             print("BUY")
#             buy_market(
#                 SYMBOL,
#                 krw * 0.9995
#             )
#     else : 
#         btc = get_balance("BTC")
#         if btc > 0 : 
#             print("SELL")
#             sell_market(
#                 SYMBOL,
#                 btc * 0.9995
#             )
