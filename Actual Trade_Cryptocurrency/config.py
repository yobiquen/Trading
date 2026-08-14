
# config.py: API 키, 심볼, K값, 체크 주기 같은 설정만 저장. API Key 등 파라미터 관리
# exchange.py: 빗썸 API와 통신하고, 받은 데이터를 프로그램에서 쓰기 편한 형태로 변환.
# strategy.py: 오직 "언제 사고 언제 팔 것인가"만 판단. 매매전략 구현
# main.py: 일정 시간마다 run()을 반복 실행. 실제로 실행하는 파일


# ===========================================================================


API_KEY = "5bb30b70a59e020c83b3f4772984b54648ade254d632b1e6"
SECRET_KEY = "NDIyYzg5ZTk4OTM3NDljMzBiNzJhMzljMDMwYzgzYzQ4NDcxMjY4ZmIxNDk0OGEzZTQ1NmQ3MzFiOWVkZTUz"

COIN = "BTC"
MARKET = "KRW"
K = 0.5                    # 변동성 돌파 전략용 변수
CHECK_INTERVAL = 900
TIMEFRAME_MINUTES = CHECK_INTERVAL // 60

MIN_KRW = 5000

SPLIT = 40                 # 총 분할수
T = 0                      # 현재 분할 진행도
TARGET_PROFIT = 0.1    # 목표 수익률(%)
TOTAL_MONEY = 400000       # 총 투자금
ONE_BUY = TOTAL_MONEY / SPLIT