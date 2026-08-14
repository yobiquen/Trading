import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. 백테스트 설정값
# ==========================================
CSV_FILE_PATH = "btc_1m.csv"  # 보유하고 계신 1분봉 CSV 파일명 입력
INITIAL_BALANCE = 400000                  # 초기 자금 (원)
SPLIT = 60                             # 총 분할 수
TARGET_PROFIT = 0.8                      # 목표 수익률 (%)
CHECK_INTERVAL_MIN = 15                   # 180초 = 3분 주기 체크
FEE = 0.0005                              # 수수료 (0.05%)

ONE_BUY = INITIAL_BALANCE / SPLIT

# ==========================================
# 2. 로직 보조 함수
# ==========================================
def get_star_point(T):
    return TARGET_PROFIT - (2 * TARGET_PROFIT / SPLIT) * T

def update_T_buy(mode, T, amount):
    if mode == "normal":
        return T + amount
    if mode == "reverse":
        return T + max(0, (SPLIT - T)) * 0.25

def update_T_sell(mode, T):
    if mode == "normal":
        return T * 0.75
    if mode == "reverse":
        return T * 0.95

# ==========================================
# 3. 백테스트 실행 엔진
# ==========================================
def run_backtest():
    # CSV 로드
    df = pd.read_csv(CSV_FILE_PATH)
    
    # 컬럼명 소문자 정리 및 시간 정렬
    df.columns = [c.lower() for c in df.columns]
    if 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms' if df['timestamp'].iloc[0] > 1e11 else 's')
    elif 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
    
    df = df.sort_values('datetime').reset_index(drop=True)

    # 3분 주기 필터링 (CHECK_INTERVAL = 180초 반영)
    df_step = df.iloc[::CHECK_INTERVAL_MIN].copy().reset_index(drop=True)

    # 계좌 및 상태 변수 초기화
    krw = INITIAL_BALANCE
    btc = 0.0
    avg_price = 0.0
    
    state = {
        "mode": "normal",
        "T": 0,
        "avg_buy": False,
        "star_buy": False,
        "quarter_sell": False,
        "reverse_first_day": True
    }

    history = []

    for i in range(len(df_step)):
        row = df_step.iloc[i]
        price = row['close']
        time = row['datetime']

        # 자산 평가
        total_asset = krw + (btc * price)
        profit_pct = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

        # --- 매매 로직 시작 ---
        # 1. 미보유 시 첫 진입
        if btc <= 0:
            buy_krw = min(krw, ONE_BUY)
            if buy_krw >= 5000:
                buy_amount = (buy_krw * (1 - FEE)) / price
                btc += buy_amount
                krw -= buy_krw
                avg_price = price
                state["mode"] = "normal"
                state["T"] = update_T_buy("normal", 0, 1)
                state["avg_buy"] = False
                state["star_buy"] = False
                state["quarter_sell"] = False

        # 2. 보유 중일 때
        else:
            mode = state["mode"]
            T = state["T"]
            star_target = get_star_point(T)
            star_price = avg_price * (1 + star_target / 100)

            if mode == "normal":
                # 전반전 (T < 20)
                if T < SPLIT / 2:
                    if not state["avg_buy"] and price <= avg_price:
                        buy_krw = min(krw, ONE_BUY / 2)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, 0.5)
                            state["avg_buy"] = True

                    elif not state["star_buy"] and price <= star_price:
                        buy_krw = min(krw, ONE_BUY / 2)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, 0.5)
                            state["star_buy"] = True

                # 후반전 (T >= 20)
                else:
                    if not state["star_buy"] and price <= star_price:
                        buy_krw = min(krw, ONE_BUY)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, 1)
                            state["star_buy"] = True

                # 쿼터 매도 (익절 분할)
                if not state["quarter_sell"] and price >= star_price:
                    sell_btc = btc / 4
                    krw += (sell_btc * price) * (1 - FEE)
                    btc -= sell_btc
                    state["T"] = update_T_sell("normal", T)
                    state["quarter_sell"] = True

                # 전체 청산 (목표 수익률 달성)
                if profit_pct >= TARGET_PROFIT:
                    krw += (btc * price) * (1 - FEE)
                    btc = 0
                    avg_price = 0
                    state["T"] = 0
                    state["mode"] = "normal"

                # 리버스 모드 전환 조건
                elif state["T"] > SPLIT - 1:
                    state["mode"] = "reverse"
                    state["reverse_first_day"] = True

            elif mode == "reverse":
                # 리버스 모드에서는 최근 3개 캔들 종가 평균 사용
                if i >= 3:
                    ma3_price = df_step.iloc[i-2:i+1]['close'].mean()
                else:
                    ma3_price = price

                # 일반 모드 복귀 조건
                if avg_price > price * (1 - TARGET_PROFIT / 100):
                    state["mode"] = "normal"
                    state["reverse_first_day"] = True
                    state["avg_buy"] = False
                    state["star_buy"] = False
                    state["quarter_sell"] = False
                else:
                    # 별지점 매도
                    if price >= ma3_price:
                        sell_btc = btc / 20
                        krw += (sell_btc * price) * (1 - FEE)
                        btc -= sell_btc
                        state["T"] = update_T_sell("reverse", T)

                    # 별지점 매수
                    elif not state["reverse_first_day"] and price <= ma3_price:
                        buy_krw = min(krw, krw / 4)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("reverse", T, 0)

                    if state["reverse_first_day"]:
                        state["reverse_first_day"] = False

        # 턴 초기화 체크 (새 주기 마다)
        state["avg_buy"] = False
        state["star_buy"] = False

        # 자산 기록
        history.append({
            "datetime": time,
            "total_asset": total_asset,
            "price": price,
            "krw": krw,
            "btc": btc,
            "T": state["T"],
            "mode": state["mode"]
        })

    # 리포트 및 시각화
    res_df = pd.DataFrame(history)
    
    # 성과 지표 계산
    final_asset = res_df['total_asset'].iloc[-1]
    total_return = ((final_asset - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
    res_df['peak'] = res_df['total_asset'].cummax()
    res_df['dd'] = (res_df['total_asset'] - res_df['peak']) / res_df['peak'] * 100
    mdd = res_df['dd'].min()

    print("=============== 백테스트 결과 ===============")
    print(f"초기 자본금: {INITIAL_BALANCE:,.0f} 원")
    print(f"최종 자산 : {final_asset:,.0f} 원")
    print(f"누적 수익률: {total_return:.2f} %")
    print(f"최대 낙폭(MDD): {mdd:.2f} %")
    print("===========================================")

    # 그래프 출력
    plt.figure(figsize=(12, 6))
    plt.plot(res_df['datetime'], res_df['total_asset'], label='Total Asset (KRW)')
    plt.title("Backtest Result")
    plt.xlabel("Date")
    plt.ylabel("Asset")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    run_backtest()