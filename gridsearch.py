import pandas as pd
import numpy as np
from itertools import product

# ==========================================
# 1. 파일 경로 지정
# ==========================================
CSV_FILE_PATH = "btc_1m.csv"  # 가지고 계신 CSV 파일명
INITIAL_BALANCE = 400000                  # 초기 자금 (원)
FEE = 0.0005                              # 수수료 (0.05%)

# ==========================================
# 2. 탐색할 파라미터 범위 설정 (Grid Search)
# ==========================================
PARAM_GRID = {
    "SPLIT": [20, 40, 60],         # 분할 횟수 후보
    "TARGET_PROFIT": [0.2, 0.3, 0.5, 1.0],  # 목표 수익률(%) 후보
    "CHECK_INTERVAL_MIN": [1, 3, 5, 10, 15, 30]  # 체크 주기(분) 후보
}

# 보조 함수
def get_star_point(T, split, target_profit):
    return target_profit - (2 * target_profit / split) * T

def update_T_buy(mode, T, split, amount):
    if mode == "normal":
        return T + amount
    if mode == "reverse":
        return T + max(0, (split - T)) * 0.25

def update_T_sell(mode, T):
    if mode == "normal":
        return T * 0.75
    if mode == "reverse":
        return T * 0.95

# 백테스트 실행 단일 함수
def run_single_backtest(df, split, target_profit, interval_min):
    one_buy = INITIAL_BALANCE / split
    df_step = df.iloc[::interval_min].copy().reset_index(drop=True)

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

    peak = INITIAL_BALANCE
    mdd = 0.0

    for i in range(len(df_step)):
        row = df_step.iloc[i]
        price = row['close']

        total_asset = krw + (btc * price)
        if total_asset > peak:
            peak = total_asset
        dd = (total_asset - peak) / peak * 100
        if dd < mdd:
            mdd = dd

        profit_pct = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

        if btc <= 0:
            buy_krw = min(krw, one_buy)
            if buy_krw >= 5000:
                bought = (buy_krw * (1 - FEE)) / price
                btc += bought
                krw -= buy_krw
                avg_price = price
                state["mode"] = "normal"
                state["T"] = update_T_buy("normal", 0, split, 1)
                state["avg_buy"] = False
                state["star_buy"] = False
                state["quarter_sell"] = False
        else:
            mode = state["mode"]
            T = state["T"]
            star_target = get_star_point(T, split, target_profit)
            star_price = avg_price * (1 + star_target / 100)

            if mode == "normal":
                if T < split / 2:
                    if not state["avg_buy"] and price <= avg_price:
                        buy_krw = min(krw, one_buy / 2)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, split, 0.5)
                            state["avg_buy"] = True
                    elif not state["star_buy"] and price <= star_price:
                        buy_krw = min(krw, one_buy / 2)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, split, 0.5)
                            state["star_buy"] = True
                else:
                    if not state["star_buy"] and price <= star_price:
                        buy_krw = min(krw, one_buy)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("normal", T, split, 1)
                            state["star_buy"] = True

                if not state["quarter_sell"] and price >= star_price:
                    sell_btc = btc / 4
                    krw += (sell_btc * price) * (1 - FEE)
                    btc -= sell_btc
                    state["T"] = update_T_sell("normal", T)
                    state["quarter_sell"] = True

                if profit_pct >= target_profit:
                    krw += (btc * price) * (1 - FEE)
                    btc = 0
                    avg_price = 0
                    state["T"] = 0
                    state["mode"] = "normal"
                elif state["T"] > split - 1:
                    state["mode"] = "reverse"
                    state["reverse_first_day"] = True

            elif mode == "reverse":
                ma3_price = df_step.iloc[max(0, i-2):i+1]['close'].mean() if i >= 1 else price

                if avg_price > price * (1 - target_profit / 100):
                    state["mode"] = "normal"
                    state["reverse_first_day"] = True
                    state["avg_buy"] = False
                    state["star_buy"] = False
                    state["quarter_sell"] = False
                else:
                    if price >= ma3_price:
                        sell_btc = btc / 20
                        krw += (sell_btc * price) * (1 - FEE)
                        btc -= sell_btc
                        state["T"] = update_T_sell("reverse", T)
                    elif not state["reverse_first_day"] and price <= ma3_price:
                        buy_krw = min(krw, krw / 4)
                        if buy_krw >= 5000:
                            bought = (buy_krw * (1 - FEE)) / price
                            avg_price = ((btc * avg_price) + (bought * price)) / (btc + bought)
                            btc += bought
                            krw -= buy_krw
                            state["T"] = update_T_buy("reverse", T, split, 0)

                    if state["reverse_first_day"]:
                        state["reverse_first_day"] = False

        state["avg_buy"] = False
        state["star_buy"] = False

    final_asset = krw + (btc * df_step.iloc[-1]['close'])
    total_return = ((final_asset - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
    
    return {
        "SPLIT": split,
        "TARGET_PROFIT": target_profit,
        "INTERVAL(min)": interval_min,
        "Final Asset(KRW)": round(final_asset),
        "Return(%)": round(total_return, 2),
        "MDD(%)": round(mdd, 2)
    }

# ==========================================
# 3. 최적화 탐색 메인
# ==========================================
if __name__ == "__main__":
    # 데이터 불러오기
    df = pd.read_csv(CSV_FILE_PATH)
    df.columns = [c.lower() for c in df.columns]

    keys, values = zip(*PARAM_GRID.items())
    permutations_dicts = [dict(zip(keys, v)) for v in product(*values)]

    results = []
    print(f"총 {len(permutations_dicts)}개 파라미터 조합 백테스트 시작...\n")

    for p in permutations_dicts:
        res = run_single_backtest(df, p["SPLIT"], p["TARGET_PROFIT"], p["CHECK_INTERVAL_MIN"])
        results.append(res)

    # 결과 정리 및 출력
    res_df = pd.DataFrame(results)
    
    # 수익률 높고, MDD 적은 순서로 정렬
    sorted_df = res_df.sort_values(by=["Return(%)", "MDD(%)"], ascending=[False, False])

    print("=================== 🏆 TOP 5 최적 파라미터 🏆 ===================")
    print(sorted_df.head(5).to_string(index=False))
    print("==================================================================")