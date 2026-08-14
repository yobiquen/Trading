import pyupbit
import numpy as np


#get_ror=수익률 구하는 함수
def get_ror(k=0.5):
    #8~16번줄 코드가 변동성 돌파 전략 백테스팅 코드
    df = pyupbit.get_ohlcv("KRW-BTC", count=5)
    df['range'] = (df['high'] - df['low']) * k
    df['target'] = df['open'] + df['range'].shift(1)


    fee = 0.0032
    df['ror'] = np.where(df['high'] > df['target'],
                         df['close'] / df['target'] - fee,
                         1)

    #누적 수익률 계산 코드. ror=누적 수익률
    ror = df['ror'].cumprod().iloc[-2]
    return ror

#k값을 0.1에서 1까지 0.1 간격으로 증가시켜서 k와 그에 따른 누적 수익률 ror 출력하기.
for k in np.arange(0.1, 1.0, 0.1):
    ror = get_ror(k)
    print("%.1f %f" % (k, ror))