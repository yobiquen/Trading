
# config.py: API 키, 심볼, K값, 체크 주기 같은 설정만 저장. API Key 등 파라미터 관리
# exchange.py: 빗썸 API와 통신하고, 받은 데이터를 프로그램에서 쓰기 편한 형태로 변환.
# strategy.py: 오직 "언제 사고 언제 팔 것인가"만 판단. 매매전략 구현
# main.py: 일정 시간마다 run()을 반복 실행. 실제로 실행하는 파일


# ===========================================================================


from exchange import *
from config import *

import json
import os
import time

STATE_FILE = os.path.join(
    os.path.dirname(__file__),
    "state.json"
)


# =========================
# state 저장 / 불러오기
# =========================

def load_state():

    with open(STATE_FILE, "r") as file:
        state = json.load(file)

    return state


def save_state(state):

    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=4)


# =========================
# 출력
# =========================

def print_status(price, avg, krw, coin, T,
                 avg_buy, star_buy, quarter_sell,
                 star_point, profit, holding, mode):

    print("----------------------------")

    print("현재가 :", price)
    print("평단 :", avg)

    print()

    print("KRW :", krw)
    print("BTC :", coin)

    print()

    print("Mode :", mode)
    print("T :", T)

    print("평단매수 :", avg_buy)
    print("별매수 :", star_buy)
    print("쿼터매도 :", quarter_sell)

    print()

    if mode == "normal":

        print("별지점 :",round(star_point,3),"%")

    else:

        print("리버스가격 :", round(star_point))

    print("수익률 :", round(profit, 3), "%")
    print("보유 :", holding)


# =========================
# 계산 함수
# =========================

def get_star_point(T):

    return TARGET_PROFIT - (2 * TARGET_PROFIT / SPLIT) * T


def get_profit(price, avg):

    if avg == 0:
        return 0

    return (price / avg - 1) * 100


# =========================
# 새 캔들 체크
# =========================

def check_new_candle(state):

    current_period = int(time.time()) // CHECK_INTERVAL

    last_period = state.get("last_period")

    if last_period is None:

        state["last_period"] = current_period

        save_state(state)

        print("첫 매매 주기 시작")

        return True

    if current_period != last_period:

        state["last_period"] = current_period

        state["avg_buy"] = False
        state["star_buy"] = False

        save_state(state)

        print("새 매매 주기 시작")

        return True

    return False


# =========================
# T 업데이트
# =========================

def update_T_buy(mode, T, amount):

    if mode == "normal":

        return T + amount

    if mode == "reverse":

        return T + (SPLIT - T) * 0.25


def update_T_sell(mode, T, amount):

    if mode == "normal":

        return T * 0.75

    if mode == "reverse":

        if SPLIT == 40:
            return T * 0.95

        else:
            return T * 0.90


# =========================
# 첫 진입
# =========================

def first_entry(state):

    print("첫 진입")

    result = buy_market(ONE_BUY)

    if result is None:
        return

    order_id = result["order_id"]

    if not wait_order(order_id):
        print("첫 주문 체결 실패")
        return

    # 새 사이클은 항상 normal부터 시작
    state["mode"] = "normal"

    state["T"] = update_T_buy(
        state["mode"],
        0,
        1
    )

    state["avg_buy"] = False
    state["star_buy"] = False
    state["quarter_sell"] = False

    save_state(state)

    print("첫 매수 완료")
    print("주문번호 :", order_id)


# =========================
# 1회분 매수
# =========================

def buy_one(state):

    result = buy_market(ONE_BUY)

    if result is None:

        return False

    order_id = result["order_id"]

    if not wait_order(order_id):

        return False

    state["T"] = update_T_buy(
        state["mode"],
        state["T"],
        1
    )

    save_state(state)

    print("1회차 매수 완료")
    print("주문번호 :", result["order_id"])

    return True


# =========================
# 0.5회분 매수
# =========================

def buy_half(state):

    print("buy_half() 호출") #테스트용

    result = buy_market(ONE_BUY / 2)

    if result is None:

        return False

    order_id = result["order_id"]

    if not wait_order(order_id):

        return False

    state["T"] = update_T_buy(
        state["mode"],
        state["T"],
        0.5
    )

    save_state(state)

    print("0.5회차 매수 완료")
    print("주문번호 :", result["order_id"])

    return True


# =========================
# 1/4 매도
# =========================

def sell_quarter(state, coin):

    amount = coin / 4

    result = sell_market(amount)

    if result is None:

        return False

    order_id = result["order_id"]

    if not wait_order(order_id):

        return False

    state["T"] = update_T_sell(
        state["mode"],
        state["T"],
        0.25
    )

    state["quarter_sell"] = True

    save_state(state)

    print("1/4 매도 완료")
    print("주문번호 :", result["order_id"])

    return True


# =========================
# 잔량 매도
# =========================

def sell_rest(state, coin):

    if coin <= 0:
        print("잔량 매도할 BTC가 없습니다.")
        return False

    result = sell_market(coin)

    if result is None:
        return False

    order_id = result["order_id"]

    if not wait_order(order_id):
        return False

    # 사이클 초기화
    state["T"] = 0
    state["mode"] = "normal"
    state["reverse_first_day"] = True

    state["avg_buy"] = False
    state["star_buy"] = False
    state["quarter_sell"] = False

    # 같은 매매 주기 안에서 재진입하는 것을 방지
    state["last_period"] = int(time.time()) // CHECK_INTERVAL

    save_state(state)

    print("잔량 매도 완료")
    print("주문번호 :", order_id)

    return True


# =========================
# 리버스 분할매도
# =========================

def sell_reverse(state, coin):

    if SPLIT == 40:
        amount = coin / 20
    else:
        amount = coin / 10

    result = sell_market(amount)

    if result is None:
    
        return False
    
    order_id = result["order_id"]
    
    if not wait_order(order_id):
    
        return False

    state["T"] = update_T_sell(
        "reverse",
        state["T"],
        amount
    )

    save_state(state)

    print("리버스 매도 완료")
    print("주문번호 :", result["order_id"])

    return True


# =========================
# 리버스 분할매수
# =========================

def buy_reverse(state, krw):

    amount = krw / 4

    result = buy_market(amount)

    if result is None:
    
        return False
    
    order_id = result["order_id"]
    
    if not wait_order(order_id):
  
        return False

    state["T"] = update_T_buy(
        "reverse",
        state["T"],
        0
    )

    save_state(state)

    print("리버스 매수 완료")
    print("주문번호 :", result["order_id"])

    return True


# =========================
# 일반모드
# =========================

def normal_mode(state, price, avg, coin):

    T = state["T"]

    avg_buy = state["avg_buy"]
    star_buy = state["star_buy"]
    quarter_sell = state["quarter_sell"]

    profit = get_profit(price, avg)

    star = get_star_point(T)

    star_price = avg * (1 + star / 100)


    # =====================================================
    # 전반전
    # =====================================================

    if T < SPLIT / 2:

        print(price, avg)

        # ---------------------------------------------
        # 평단 매수
        # ---------------------------------------------

        if (not avg_buy) and price <= avg:

            if buy_half(state):

                state["avg_buy"] = True
                save_state(state)

                # 매수 후에는 여기서 끝낸다.
                # 같은 run에서 다른 조건을 연속 실행하지 않도록 한다.
                return


        # ---------------------------------------------
        # 별지점 매수
        # ---------------------------------------------

        elif (not star_buy) and price <= star_price:

            if buy_half(state):

                state["star_buy"] = True
                save_state(state)

                return


    # =====================================================
    # 후반전
    # =====================================================

    else:

        if (not star_buy) and price <= star_price:

            if buy_one(state):

                state["star_buy"] = True
                save_state(state)

                return


    # =====================================================
    # 별지점 1/4 매도
    # =====================================================

    if (not quarter_sell) and price >= star_price:

        if sell_quarter(state, coin):

            print("1/4 매도 후 상태 갱신")

            # 여기서 return
            #
            # 이유:
            # 방금 coin의 1/4을 팔았으므로
            # 현재 run의 coin 변수는 이미 낡은 값이다.
            #
            # 다음 run에서 실제 계좌 잔고를 다시 조회한다.

            return


    # =====================================================
    # 목표수익률 잔량 매도
    # =====================================================

    if profit >= TARGET_PROFIT:

        # 여기서도 현재 coin을 그대로 쓰지 않는다.
        #
        # 안전하게 실제 계좌 잔고를 다시 가져온다.

        accounts = get_accounts()

        if not accounts:

            print("잔량 매도 전 계좌 조회 실패")

            return

        current_coin = get_balance_from_accounts(
            accounts,
            COIN
        )

        if current_coin <= 0:

            print("매도할 BTC가 없습니다.")

            return


        if sell_rest(state, current_coin):

            print("사이클 종료")

            return


    # =====================================================
    # 리버스모드 진입
    # =====================================================

    T = state["T"]

    if T > SPLIT - 1:

        state["mode"] = "reverse"

        state["reverse_first_day"] = True

        save_state(state)

        print("리버스모드 진입")


# =========================
# 리버스모드
# =========================

def reverse_mode(state, price, avg, krw, coin):

    print("리버스모드")

    T = state["T"]

    reverse_first_day = state["reverse_first_day"]

    candles = get_candles(3)

    if len(candles) < 3:
        return

    closes = []

    for candle in candles:

        closes.append(candle["close"])

    star_price = sum(closes) / len(closes)


    # --------------------
    # 일반모드 복귀
    # --------------------

    if avg > price * (1 - TARGET_PROFIT / 100):

        state["mode"] = "normal"
        state["reverse_first_day"]=True

        state["avg_buy"] = False
        state["star_buy"] = False
        state["quarter_sell"] = False

        save_state(state)

        print("일반모드 복귀")

        return


    # --------------------
    # 별지점 매도
    # --------------------

    if price >= star_price:

        if sell_reverse(state, coin):

            print("리버스 분할매도 완료")

            return

    # --------------------
    # 첫날은 매수 안함
    # --------------------

    if reverse_first_day:

        state["reverse_first_day"] = False

        save_state(state)

        print("첫날 매수 생략")

        return


    # --------------------
    # 별지점 매수
    # --------------------

    if price <= star_price:

        if buy_reverse(state, krw):

            print("리버스 분할매수 완료")

            return

# =========================
# 메인 실행
# =========================

def run():

    # -------------------------
    # state 불러오기
    # -------------------------

    state = load_state()

    check_new_candle(state)

    state = load_state()

    mode = state["mode"]
    T = state["T"]

    avg_buy = state["avg_buy"]
    star_buy = state["star_buy"]
    quarter_sell = state["quarter_sell"]

    # -------------------------
    # 현재 정보 조회
    # -------------------------

    price = get_current_price()

    if price is None:
        print("현재가 조회 실패")
        return

    accounts = get_accounts()

    if not accounts:
        print("계좌 조회 실패")
        return

    krw = get_balance_from_accounts(accounts, MARKET)
    coin = get_balance_from_accounts(accounts, COIN)
    avg = get_avg_from_accounts(accounts, COIN)

    # -------------------------
    # 계산
    # -------------------------

    star_point = get_star_point(T)
    profit = get_profit(price, avg)
    holding = coin > 0

    # -------------------------
    # 출력
    # -------------------------

    print_status(
        price,
        avg,
        krw,
        coin,
        T,
        avg_buy,
        star_buy,
        quarter_sell,
        star_point,
        profit,
        holding,
        mode
    )

    # -------------------------
    # 첫 진입
    # -------------------------

    if not holding:

        first_entry(state)

        return

    # -------------------------
    # 보유 중 로직
    # -------------------------

    if mode == "normal":

        normal_mode(
            state,
            price,
            avg,
            coin
        )

    else:

        reverse_mode(
            state,
            price,
            avg,
            krw,
            coin
        )