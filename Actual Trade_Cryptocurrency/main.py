
# config.py: API 키, 심볼, K값, 체크 주기 같은 설정만 저장. API Key 등 파라미터 관리
# exchange.py: 빗썸 API와 통신하고, 받은 데이터를 프로그램에서 쓰기 편한 형태로 변환.
# strategy.py: 오직 "언제 사고 언제 팔 것인가"만 판단. 매매전략 구현
# main.py: 일정 시간마다 run()을 반복 실행. 실제로 실행하는 파일


# ===========================================================================


import time

from strategy_Infinite import run
from config import CHECK_INTERVAL

print("Bot Start")  

while True : 
    try : 
        run()
    except Exception as e : 
        print("ERROR :", e)
    time.sleep(CHECK_INTERVAL)

