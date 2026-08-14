import python_bithumb
import pandas as pd
import time
from datetime import datetime


# ==========================================
# 설정
# ==========================================

TICKER = "KRW-BTC"

INTERVAL = "minute1"

START_DATE = "2025-01-01"
END_DATE = "2026-08-13"

SAVE_FILE = "btc_1m.csv"


# ==========================================
# 날짜 설정
# ==========================================

start = pd.Timestamp(START_DATE)
end = pd.Timestamp(END_DATE)


# ==========================================
# 다운로드
# ==========================================

all_data = []

to = end

while True:

    print(
        "다운로드 :",
        to.strftime("%Y-%m-%d %H:%M:%S")
    )

    try:

        df = python_bithumb.get_ohlcv(
            TICKER,
            interval=INTERVAL,
            count=200,
            to=to.strftime("%Y-%m-%d %H:%M:%S"),
            period=0.1
        )

    except Exception as e:

        print("오류 :", e)
        time.sleep(3)
        continue


    if df is None or len(df) == 0:

        print("더 이상 데이터가 없습니다.")
        break


    # 현재 받은 데이터 저장
    all_data.append(df)


    # 가장 오래된 캔들 확인
    oldest = df.index.min()

    print(
        "  받은 데이터 :",
        df.index.min(),
        "~",
        df.index.max(),
        f"({len(df)}개)"
    )


    # 시작 날짜보다 과거로 내려갔으면 종료
    if oldest <= start:

        break


    # 다음 요청은 현재 가장 오래된 캔들보다 이전으로
    to = oldest - pd.Timedelta(minutes=1)

    time.sleep(0.2)


# ==========================================
# 합치기
# ==========================================

if not all_data:

    print("다운로드된 데이터가 없습니다.")
    exit()


df = pd.concat(all_data)


# 중복 제거
df = df[~df.index.duplicated(keep="first")]


# 시간순 정렬
df = df.sort_index()


# ==========================================
# 날짜 범위 자르기
# ==========================================

df = df[
    (df.index >= start) &
    (df.index < end)
]


# ==========================================
# CSV 저장
# ==========================================

df.to_csv(SAVE_FILE)


# ==========================================
# 결과 출력
# ==========================================

print()
print("======================================")
print("다운로드 완료")
print("======================================")

print("파일 :", SAVE_FILE)
print("데이터 개수 :", len(df))

if len(df) > 0:

    print("시작 :", df.index[0])
    print("끝   :", df.index[-1])

print("======================================")