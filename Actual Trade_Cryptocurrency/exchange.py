
# config.py: API 키, 심볼, K값, 체크 주기 같은 설정만 저장. API Key 등 파라미터 관리
# exchange.py: 빗썸 API와 통신하고, 받은 데이터를 프로그램에서 쓰기 편한 형태로 변환.
# strategy.py: 오직 "언제 사고 언제 팔 것인가"만 판단. 매매전략 구현
# main.py: 일정 시간마다 run()을 반복 실행. 실제로 실행하는 파일


# ===========================================================================


import jwt
import uuid
import time
import requests
import hashlib

from config import *


API_URL = "https://api.bithumb.com"


# =========================
# JWT 토큰 생성
# =========================

def get_headers(params=None):

    payload = {
        "access_key": API_KEY,
        "nonce": str(uuid.uuid4()),
        "timestamp": round(time.time() * 1000)
    }


    # 파라미터가 있는 Private API 요청
    if params is not None:

        query = "&".join(
            [f"{k}={v}" for k, v in params.items()]
        )

        hash_obj = hashlib.sha512()
        hash_obj.update(query.encode("utf-8"))

        payload["query_hash"] = hash_obj.hexdigest()
        payload["query_hash_alg"] = "SHA512"


    jwt_token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )


    return {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }



# =========================
# 전체 계좌 조회
# =========================

def get_accounts():

    try:

        response = requests.get(
            API_URL + "/v1/accounts",
            headers=get_headers(),
            timeout=5
        )

    except Exception as e:

        print("계좌 조회 오류 :", e)
        return []

    if response.status_code != 200:

        print("계좌 조회 실패")
        print(response.status_code)
        print(response.text)

        return []

    return response.json()



# =========================
# 계좌에서 잔고 가져오기
# =========================

def get_balance_from_accounts(accounts, currency):

    for account in accounts:

        if account["currency"] == currency:

            return float(account["balance"])

    return 0



# =========================
# 계좌에서 평균 매수가 가져오기
# =========================

def get_avg_from_accounts(accounts, currency):

    for account in accounts:

        if account["currency"] == currency:

            return float(account["avg_buy_price"])

    return 0



# =========================
# 기존 호환용 잔고 조회
# =========================

def get_balance(currency):

    accounts = get_accounts()

    return get_balance_from_accounts(
        accounts,
        currency
    )



# =========================
# 기존 호환용 평균 매수가 조회
# =========================

def get_avg_price(currency):

    accounts = get_accounts()

    return get_avg_from_accounts(
        accounts,
        currency
    )



# =========================
# 현재가 조회
# =========================

def get_current_price():

    market = f"{COIN}_{MARKET}"

    try:

        response = requests.get(
            API_URL + f"/public/ticker/{market}",
            timeout=5
        )

    except Exception as e:

        print("현재가 조회 오류 :", e)
        return None

    if response.status_code != 200:

        print("현재가 조회 실패")
        print(response.status_code)
        print(response.text)
        return None

    data = response.json()

    return float(data["data"]["closing_price"])



# =========================
# 캔들 조회
# =========================

def get_candles(count=2):

    market = f"{COIN}_{MARKET}"

    try:

        response = requests.get(
            API_URL + f"/public/candlestick/{market}/1m",
            timeout=5
        )

    except Exception as e:

        print("캔들 조회 오류 :", e)
        return []

    if response.status_code != 200:

        print("캔들 조회 실패")
        print(response.status_code)
        print(response.text)
        return []

    data = response.json()["data"]

    candles = []

    for candle in data[-count:]:

        candles.append({
            "timestamp": int(candle[0]),
            "open": float(candle[1]),
            "close": float(candle[2]),
            "high": float(candle[3]),
            "low": float(candle[4]),
            "volume": float(candle[5])
        })

    return candles



# =========================
# 시장가 매수
# =========================

def buy_market(amount_krw):

    body = {
        "market": f"{MARKET}-{COIN}",
        "side": "bid",
        "order_type": "price",
        "price": str(int(amount_krw))
    }

    try:

        response = requests.post(
            API_URL + "/v2/orders",
            json=body,
            headers=get_headers(body),
            timeout=5
        )

    except Exception as e:

        print("매수 요청 오류 :", e)
        return None

    if response.status_code != 201:

        print("매수 실패")

        try:
            print(response.json())
        except:
            print(response.text)

        return None

    # ---------- 성공 처리 ----------
    data = response.json()

    if "order_id" in data:

        print("매수 성공")
        return data

    print("응답에 order_id가 없습니다.")
    print(data)

    return None



# =========================
# 시장가 매도
# =========================

def sell_market(amount_coin):

    body = {
        "market": f"{MARKET}-{COIN}",
        "side": "ask",
        "order_type": "market",
        "volume": str(amount_coin)
    }

    try:
        response = requests.post(
            API_URL + "/v2/orders",
            json=body,
            headers=get_headers(body),
            timeout=5
        )

    except Exception as e:
        print("매도 요청 오류 :", e)
        return None

    if response.status_code != 201:

        print("매도 실패")
        print(response.status_code)

        try:
            print(response.json())
        except:
            print(response.text)

        return None

    # ---------- 성공 처리 ----------
    data = response.json()

    if "order_id" in data:
        print("매도 성공")
        return data

    print("응답에 order_id가 없습니다.")
    print(data)

    return None



# =========================
# 주문 조회
# =========================

def get_order(order_id):

    params = {
        "uuid": order_id
    }

    try:

        response = requests.get(
            API_URL + "/v1/order",
            params=params,
            headers=get_headers(params),
            timeout=5
        )

    except Exception as e:

        print("주문 조회 통신 오류 :", e)
        return {
            "error": True,
            "status": response.status_code
        }

    if response.status_code == 200:

        return response.json()

    return {"error": True}



# =========================
# 주문 체결 대기
# =========================

def wait_order(order_id, timeout=10):

    start = time.time()

    while time.time() - start < timeout:

        order = get_order(order_id)

        if "error" in order:
            print("주문 조회 실패")
            time.sleep(1)
            continue

        if not order:
            print("주문 정보가 아직 없습니다.")
            time.sleep(1)
            continue

        state = order["state"]


        if state == "done":
            print("체결 완료")
            return True

        elif state == "cancel":
            print("주문 취소")
            return False

        elif state == "wait":
            print("체결 대기중...")

        time.sleep(1)

    print("체결 대기 시간 초과")

    return False

