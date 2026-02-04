from config import DB_PATH, KIWOOM_APPKEY, KIWOOM_APPSECRET
from kiwoom_rest import KiwoomREST
from logger import logger
import sqlite3
from time import sleep
import random
import datetime
from nxt_stock_list import NXT_STOCK_LIST

# Constants moved from main.py
ORDER_INTERVAL = "주문간격(초)"
BUY_NEW_STOCK_AMOUNT = "신규매수주식금액"
BUY_NEW_STOCK_NUM = "신규매수주식개수"
REBUY_STOCK_AMOUNT = "물타기매수주식금액"
SELL_STOCK_AMOUNT_1 = "1차 매도주식금액"
SELL_STOCK_AMOUNT_2 = "2차 매도주식금액"
SELL_STOCK_AMOUNT_3 = "3차 매도주식금액"
SELL_STOCK_AMOUNT_4 = "4차 매도주식금액"
SELL_STOCK_AMOUNT_5 = "5차 매도주식금액"
SELL_STOCK_AMOUNT_6 = "6차 매도주식금액"
SELL_STOCK_AMOUNT_7 = "7차 매도주식금액"
SELL_STOCK_AMOUNT_8 = "8차 매도주식금액"
SELL_STOCK_AMOUNT_9 = "9차 매도주식금액"
SELL_STOCK_AMOUNT_10 = "10차 매도주식금액"
REBUY_EARNING_RATE = "물타기 기준(%)"
REBUY_1_STOCK_EARNING_RATE = "1주 매수 기준(%)"
SELL_EARNING_RATE_1 = "1차 매도 기준(%)"
SELL_EARNING_RATE_2 = "2차 매도 기준(%)"
SELL_EARNING_RATE_3 = "3차 매도 기준(%)"
SELL_EARNING_RATE_4 = "4차 매도 기준(%)"
SELL_EARNING_RATE_5 = "5차 매도 기준(%)"
SELL_EARNING_RATE_6 = "6차 매도 기준(%)"
SELL_EARNING_RATE_7 = "7차 매도 기준(%)"
SELL_EARNING_RATE_8 = "8차 매도 기준(%)"
SELL_EARNING_RATE_9 = "9차 매도 기준(%)"
SELL_EARNING_RATE_10 = "10차 매도 기준(%)"
SELL_1_STOCK_EARNING_RATE = "1주 매도 기준(%)"
SELL_HOGA_1 = "1차 매도 기준(호가단위)"
MAX_AMOUNT = "종목별 매수 최대 금액(원)"
DEFAULT_BUY_NEW_STOCK_NUM = "기본 보유종목 개수"
STATUS = "운영상태"
EXCEPT_REBUY = "물타기 제외 종목"
BUY_NEW_STOCK = "신규종목매수"
REBUY_CREDIT_EARNING_RATE = "신용 물타기 기준(%)"
REBUY_CREDIT_STOCK_AMOUNT = "신용 물타기 매수금액"
EXCEPT_CREDIT_REBUY = "신용 물타기 제외 종목"
CREDIT_MAX_AMOUNT = "신용 물타기 최대금액"
MAX_TRADING_DIFF = "당일매수매도차이금액"

# Sleep intervals
TR_REQ_TIME_INTERVAL = 0.3  # TR 요청 간격
ORDER_SLEEP_INTERVAL = 0.4  # 주문 후 대기 시간

ORDERTYPE = {'KRX매수': 1, 'KRX매도': 2, 'KRX매수취소': 3, 'KRX매도취소': 4,
             'SOR매수': 11, 'SOR매도': 12, 'SOR취소': 13, 'SOR정정': 15,
             'NXT매수': 21, 'NXT매도': 22, 'NXT매수취소': 23, 'NXT매도취소': 24, 'NXT정정': 25}
HOGATYPE = {'지정가': "0", '시장가': "03", '시간외단일가': "62"}
HOGAUNIT = {2000: 1, 5000: 5, 20000: 10, 50000: 50, 200000: 100, 500000: 500, 2000000: 1000}

class Trading:
    def __init__(self):
        self.kiwoom = KiwoomREST(KIWOOM_APPKEY, KIWOOM_APPSECRET)
        self.user_stock_num = 0
        self.user_stock_list = []
        self.user_credit_stock_num = 0
        self.user_credit_stock_list = []
        self.interesting_stocks = []
        self.not_done_orders_num = 0
        self.not_done_orders = []
        self.not_done_sell_num = 0
        self.not_done_sell = []
        self.buy_code_list = []
        self.buy_new_stock_num = 100
        self.order_interval = 150
        self.buy_new_credit_stock_amount = 300000
        self.buy_new_credit_stock_num = 10
        self.buy_new_stock_amount = 300000
        self.rebuy_stock_amount = 300000
        self.sell_stock_amount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.rebuy_earning_rate = -8
        self.sell_earning_rate = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.sell_credit_earning_rate = [0, 0]
        self.sell_credit_earning_rate_finish_market = [0, 0]
        self.sell_credit_earninig_rate_after_market = [0, 0]
        self.sell_credit_stock_amount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.sell_credit_stock_amount_finish_market = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.sell_credit_stock_amount_after_market = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.rebuy_1_stock_earning_rate = -3
        self.max_amount = 1000000  # 현금 물타기 한도
        self.credit_max_amount = 1000000  # 신용 물타기 한도
        self.default_buy_new_stock_num = 100
        self.remain_money_buy_new_stock_down_rate = {}
        self.remain_money_buy_new_stock_up_rate = {}
        self.running_state = 1
        self.except_rebuy_list = []
        self.new_buy_stock = True
        self.exchange = "KRX"
        self.nxt_list = NXT_STOCK_LIST
        self.rebuy_credit_earning_rate = -10  # 기본값
        self.rebuy_credit_stock_amount = 500000  # 기본값
        self.except_credit_rebuy_list = []
        self.max_trading_diff = 30000000  # 기본값 설정

    def update_options(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("select * from secretary_setup")
        rows = cur.fetchall()
        for row in rows:
            if row[2] == ORDER_INTERVAL:
                self.order_interval = row[1]
            elif row[2] == BUY_NEW_STOCK_AMOUNT:
                self.buy_new_stock_amount = row[1]
            elif row[2] == REBUY_STOCK_AMOUNT:
                self.rebuy_stock_amount = row[1]
            elif row[2] == REBUY_EARNING_RATE:
                self.rebuy_earning_rate = row[1]
            elif row[2] == SELL_1_STOCK_EARNING_RATE:
                self.sell_1_stock_earning_rate = row[1]
            elif row[2] == REBUY_1_STOCK_EARNING_RATE:
                self.rebuy_1_stock_earning_rate = row[1]
            elif row[2] == MAX_AMOUNT:
                self.max_amount = row[1]
            elif row[2] == DEFAULT_BUY_NEW_STOCK_NUM:
                self.default_buy_new_stock_num = row[1]
            elif row[2] == STATUS:
                self.running_state = row[1]
            elif row[2] == EXCEPT_REBUY:
                self.except_rebuy_list = row[1].split('/')
            elif row[2] == BUY_NEW_STOCK:
                self.new_buy_stock = row[1]
            elif row[2] == REBUY_CREDIT_EARNING_RATE:
                self.rebuy_credit_earning_rate = float(row[1])
            elif row[2] == REBUY_CREDIT_STOCK_AMOUNT:
                self.rebuy_credit_stock_amount = int(row[1])
            elif row[2] == EXCEPT_CREDIT_REBUY:
                self.except_credit_rebuy_list = row[1].split('/')
            elif row[2] == CREDIT_MAX_AMOUNT:
                self.credit_max_amount = int(row[1])
            if row[2] == MAX_TRADING_DIFF:
                self.max_trading_diff = row[1]  # DB에서 설정값 로드

        cur.execute("select * from 매도설정")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                continue
            if row[0] == SELL_EARNING_RATE_1:
                self.sell_earning_rate[0] = row[1]
            elif row[0] == SELL_EARNING_RATE_2:
                self.sell_earning_rate[1] = row[1]
            elif row[0] == SELL_EARNING_RATE_3:
                self.sell_earning_rate[2] = row[1]
            elif row[0] == SELL_EARNING_RATE_4:
                self.sell_earning_rate[3] = row[1]
            elif row[0] == SELL_EARNING_RATE_5:
                self.sell_earning_rate[4] = row[1]
            elif row[0] == SELL_EARNING_RATE_6:
                self.sell_earning_rate[5] = row[1]
            elif row[0] == SELL_EARNING_RATE_7:
                self.sell_earning_rate[6] = row[1]
            elif row[0] == SELL_EARNING_RATE_8:
                self.sell_earning_rate[7] = row[1]
            elif row[0] == SELL_EARNING_RATE_9:
                self.sell_earning_rate[8] = row[1]
            elif row[0] == SELL_EARNING_RATE_10:
                self.sell_earning_rate[9] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_1:
                self.sell_stock_amount[0] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_2:
                self.sell_stock_amount[1] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_3:
                self.sell_stock_amount[2] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_4:
                self.sell_stock_amount[3] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_5:
                self.sell_stock_amount[4] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_6:
                self.sell_stock_amount[5] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_7:
                self.sell_stock_amount[6] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_8:
                self.sell_stock_amount[7] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_9:
                self.sell_stock_amount[8] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_10:
                self.sell_stock_amount[9] = row[1]

        cur.execute("select * from 신용매수설정")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                continue
            if row[0] == BUY_NEW_STOCK_NUM:
                self.buy_new_credit_stock_num = row[1]
            elif row[0] == BUY_NEW_STOCK_AMOUNT:
                self.buy_new_credit_stock_amount = row[1]

        cur.execute("select * from 신용매도설정")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                continue
            if row[0] == SELL_EARNING_RATE_1:  # 호가 대신 수익률로 변경
                self.sell_credit_earning_rate[0] = row[1]
            elif row[0] == SELL_EARNING_RATE_2:
                self.sell_credit_earning_rate[1] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_1:
                self.sell_credit_stock_amount[0] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_2:
                self.sell_credit_stock_amount[1] = row[1]

        cur.execute("select * from 신용장마감매도설정")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                continue
            if row[0] == SELL_EARNING_RATE_1:  # 호가 대신 수익률로 변경
                self.sell_credit_earning_rate_finish_market[0] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_1:
                self.sell_credit_stock_amount_finish_market[0] = row[1]

        cur.execute("select * from 신용시간외매도설정")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                continue
            if row[0] == SELL_EARNING_RATE_1:  # 호가 대신 수익률로 변경
                self.sell_credit_earninig_rate_after_market[0] = row[1]
            elif row[0] == SELL_EARNING_RATE_2:
                self.sell_credit_earninig_rate_after_market[1] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_1:
                self.sell_credit_stock_amount_after_market[0] = row[1]
            elif row[0] == SELL_STOCK_AMOUNT_2:
                self.sell_credit_stock_amount_after_market[1] = row[1]

        cur.execute("select * from secretary_stockdownrate")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                break
            self.remain_money_buy_new_stock_down_rate[row[1]] = row[2]  # must be one

        cur.execute("select * from secretary_stockuprate")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                break
            self.remain_money_buy_new_stock_up_rate[row[1]] = row[2]
        self.remain_money_buy_new_stock_up_rate = sorted(self.remain_money_buy_new_stock_up_rate.items(), reverse=True)

        conn.close()

    def get_user_stock(self, after_market=False):
        # 잔고조회 (REST)
        market = "KRX" if after_market else self.exchange
        result = self.kiwoom.get_balance(qry_tp='1', dmst_stex_tp=market)
        self.user_stock_list = result.get('acnt_evlt_remn_indv_tot', [])
        self.user_stock_num = len(self.user_stock_list)
        logger.debug(f'user stock cnt : {self.user_stock_num}')
        logger.debug(self.user_stock_list)
        return self.user_stock_list

    def get_user_credit_stock(self, after_market=False):
        # 신용잔고조회 (REST)
        market = "KRX" if after_market else self.exchange

        # 1) 신용잔고 평가 조회
        result_eval = self.kiwoom.get_account_evaluation(qry_tp='0', dmst_stex_tp=market)
        self.user_credit_stock_list = result_eval.get('stk_acnt_evlt_prst', [])

        # 2) 신용잔고 상세 (대출일별 보유수량/매도가능수량 포함)
        result = self.kiwoom.get_balance(qry_tp='2', dmst_stex_tp=market, include_credit=True)
        balance_list = result.get('acnt_evlt_remn_indv_tot', [])

        # 3) (종목명 + 대출일) 로 매핑
        balance_map = {
            (item['name'], item.get('loan_date', '')): item.get('available_num', 0)
            for item in balance_list
        }

        for stock in self.user_credit_stock_list:
            key = (stock['name'], stock.get('loan_date', ''))
            stock['available_num'] = balance_map.get(key, 0)

        self.user_credit_stock_num = len(self.user_credit_stock_list)
        logger.debug(f'user credit stock cnt : {self.user_credit_stock_num}')
        logger.debug(self.user_credit_stock_list)
        return self.user_credit_stock_list

    def get_user_remain(self, after_market=False):
        # 예수금 조회 (REST)
        market = "KRX" if after_market else self.exchange
        result = self.kiwoom.get_account_evaluation(qry_tp='0', dmst_stex_tp=market)
        remain = int(result.get('entr', 0))
        logger.debug(f'예수금 조회 : {remain}')
        return remain  # 예수금(REST 응답 필드)

    def get_interesting_stock(self):
        # 관심종목 조회 (REST)
        all_codes = []
        for seq in ['0', '1']:
            try:
                codes = self.kiwoom.get_condition_stocks(seq)
                if codes:
                    all_codes.extend(codes)
            except Exception as e:
                logger.warning(f"[조건식 {seq}] 실행 실패: {e}")
                continue

        # 중복 제거
        self.interesting_stocks = list(set(all_codes))
        logger.debug(f'관심종목 : {self.interesting_stocks}')


    def get_current_price(self, code):
        # 현재가 조회 (REST)
        if self.exchange == 'NXT':
            code += '_NX'
        result = self.kiwoom.get_stock_price(code)
        price_str = result['cur_prc'].lstrip("+-")
        if price_str == "":  # 빈 문자열 처리
            logger.error("[ERROR] 현재가 정보가 없습니다!!!!")
            price = 0
        else:
            price = int(float(price_str))  # 'cur_prc'가 현재가 필드명
        name = result.get('stk_nm', '')  # 종목명 필드명
        return price, name

    def is_stock_in_user_stock(self, code):
        for i, _ in enumerate(self.user_stock_list):
            if code == self.user_stock_list[i]['code']:
                return True
        return False

    def is_stock_in_user_credit_stock(self, code):
        for i, _ in enumerate(self.user_credit_stock_list):
            if code == self.user_credit_stock_list[i]['code']:
                return True
        return False

    def is_stock_in_not_done_order(self, code):
        for i in range(self.not_done_orders_num):
            if code == self.not_done_orders[i]['code']:
                return True
        return False

    def is_stock_in_not_done_sell(self, code):
        for i in range(self.not_done_sell_num):
            if code == self.not_done_sell[i]['code']:
                return True
        return False

    def get_not_done_order(self):  # 미체결 매수
        # REST 미체결 주문 조회
        result = self.kiwoom.get_unfilled_orders('', all_stk_tp='0', tr_type='2',
                                                 stex_tp='0')
        self.not_done_orders = result.get('oso', [])
        self.not_done_orders_num = len(self.not_done_orders)
        logger.debug(f"미체결 매수주문: {self.not_done_orders}")

    def get_not_done_sell(self):  # 미체결 매도
        # REST 미체결 주문 조회
        result = self.kiwoom.get_unfilled_orders('', all_stk_tp='0', tr_type='1',
                                                 stex_tp='0')
        self.not_done_sell = result.get('oso', [])
        self.not_done_sell_num = len(self.not_done_sell)
        logger.debug(f"미체결 매도주문: {self.not_done_sell}")

    def disconnect_real_data(self):
        self.kiwoom.disconnect_real_data("0101")

    def set_buy_stock_num(self):
        user_remain = self.get_user_remain()
        for remain_price, stock_num in self.remain_money_buy_new_stock_up_rate:
            if user_remain > remain_price:
                self.buy_new_stock_num = stock_num
                logger.debug("예수금 : {} 보유해야할 주식 개수 : {}".format(user_remain, self.buy_new_stock_num))
                return

        for remain_price, stock_num in self.remain_money_buy_new_stock_down_rate.items():
            if user_remain < remain_price:
                self.buy_new_stock_num = stock_num
                logger.debug("예수금 : {} 보유해야할 주식 개수 : {}".format(user_remain, self.buy_new_stock_num))
                return
        # self.buy_new_stock_num = self.default_buy_new_stock_num

    def buy_new_stock(self):
        # 신규종목 매수#
        logger.debug("신규매수 주식 개수: {}".format(self.buy_new_stock_num))
        logger.debug("보유 주식 개수: {}".format(self.user_stock_num))
        if not self.interesting_stocks:
            logger.debug("관심종목이 없습니다.")
            return
        random.seed(self.user_stock_num)
        if self.user_stock_num < self.buy_new_stock_num:
            buy_cnt = 0
            bought_key = []
            # 관심종목을 랜덤으로 정렬
            random.shuffle(self.interesting_stocks)
            for key in range(len(self.interesting_stocks)):
                if buy_cnt + self.user_stock_num >= self.buy_new_stock_num:
                    break
                # 해당 종목이 이미 보유중인지 확인
                if self.is_stock_in_user_stock(self.interesting_stocks[key]) \
                        or self.is_stock_in_not_done_order(self.interesting_stocks[key]) \
                        or key in bought_key:
                    logger.debug('이미 보유하고 있거나 신규매수한 종목입니다. skip!! [{}]'.format(self.interesting_stocks[key]))
                    continue
                bought_key.append(key)
                logger.debug(" - 현재가 정보 요청")
                price, name = self.get_current_price(self.interesting_stocks[key])
                if price == 0:
                    logger.error(f"매수 주문 실패: 현재가 정보 없음")
                    continue
                logger.debug("현재가 정보 요청 완료")
                # -1프로로 매수 예약
                if self._buy_designated_price(self.interesting_stocks[key], self.buy_new_stock_amount, -1, price):
                    buy_cnt += 1
                logger.debug('보유주식개수(주문내역포함):{}'.format(buy_cnt + self.user_stock_num))
        else:
            logger.debug('보유주식이 {}개이므로 더이상 신규매수할수 없습니다.'.format(self.user_stock_num))

    def buy_new_credit_stock(self):
        # 신규종목 매수#
        if not self.interesting_stocks:
            logger.debug("관심종목이 없습니다.")
            return
        random.seed(self.user_stock_num)
        buy_cnt = 0
        bought_key = []
        # 관심종목을 랜덤으로 정렬
        random.shuffle(self.interesting_stocks)
        for key in range(len(self.interesting_stocks)):
            if key >= self.buy_new_credit_stock_num:
                break
            # 해당 종목이 이미 보유중인지 확인
            if self.is_stock_in_user_credit_stock(self.interesting_stocks[key]) \
                    or self.is_stock_in_user_stock(self.interesting_stocks[key]) \
                    or key in bought_key:
                logger.debug('이미 보유하고 있는 종목입니다. skip!! [{}]'.format(self.interesting_stocks[key]))
                continue
            bought_key.append(key)
            logger.debug(" - 현재가 정보 요청")
            price, name = self.get_current_price(self.interesting_stocks[key])
            if price == 0:
                logger.error(f"매수 주문 실패: 현재가 정보 없음")
                continue
            logger.debug("현재가 정보 요청 완료")
            # -1프로로 매수 예약
            if self._buy_credit_designated_price(self.interesting_stocks[key], self.buy_new_credit_stock_amount, -0.1,
                                                 price):
                buy_cnt += 1
            logger.debug('보유주식개수(주문내역포함):{}'.format(buy_cnt + self.user_stock_num))

    def _buy_current_price(self, stock_code, amount, buy_amount=None):
        if 'J' in stock_code:
            return
        price, name = self.get_current_price(stock_code)
        if price == 0:
            logger.error(f"매수 주문 실패: 현재가 정보 없음")
            return False
        num = int(amount / price) if amount else 1
        if buy_amount and (buy_amount + (num * price) > self.max_amount):
            num = int((self.max_amount - buy_amount) / price)
        if num == 0:
            logger.debug("------- 매수 할 수 있는 수량이 0 입니다.")
            return False
        # REST 매수 주문
        success, detail = self.kiwoom.place_cash_buy_order(
            stock_code, num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug(f"------- 현재가로 매수!! 종목명 : {name} 추가매수가 : {price}원 수량 : {num}개 매입금액 : {num * price}원")
        if success:
            return True
        else:
            msg = detail
            logger.error(f"매수 주문 실패: {msg}")
            return False

    def _buy_credit_current_price(self, stock_code, amount, skip_max_check=False, buy_amount=None):
        if 'J' in stock_code:
            return

        price, name = self.get_current_price(stock_code)
        if price == 0:
            logger.error(f"매수 주문 실패: 현재가 정보 없음")
            return False

        num = int(amount / price) if amount else 1

        # 신용용 MAX 체크
        if not skip_max_check and buy_amount:
            if buy_amount + (num * price) > self.credit_max_amount:
                num = int((self.credit_max_amount - buy_amount) / price)

        if num <= 0:
            logger.debug(
                f"------- 매수 할 수 있는 수량이 0 입니다. "
                f"(보유금액: {buy_amount}, max: {self.credit_max_amount}, 현재가: {price})"
            )
            return False

        success, detail = self.kiwoom.place_credit_buy_order(
            stock_code, num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug(
            f"------- 신용 현재가 매수!! 종목명 : {name} 매수가 : {price}원 "
            f"수량 : {num}개 매입금액 : {num * price}원"
        )
        if success:
            return True
        else:
            msg = detail
            logger.error(f"매수 주문 실패: {msg}")
            return False

    def _buy_designated_price(self, stock_code, amount, earning_rate, base_price, buy_amount=None):
        # 수익률(earning_rate) 지정가로 예약 매수
        if 'J' in stock_code:
            return

        price = int(base_price) * (1 + ((earning_rate) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit)
        price = int(price * unit)
        if amount == 0:
            num = 1
        else:
            num = int(amount / price)
        if buy_amount:
            if buy_amount + (num * price) > self.max_amount:
                num = int((self.max_amount - buy_amount) / price)
        if num == 0:
            logger.debug("------- 매수 할 수 있는 수량이 0 입니다.")
            return False

        success, detail = self.kiwoom.place_cash_buy_order(
            stock_code, num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug("------- 지정가로 매수!! 추가매수가 : {}원 수량 : {}개 매입금액 : {}원".format(price, num, num * price))
        if success:
            return True
        else:
            msg = detail
            logger.error(f"지정가 매수 주문 실패: {msg}")
            return False

    def _buy_credit_designated_price(self, stock_code, amount, earning_rate, base_price, buy_amount=None):
        # 수익률(earning_rate) 지정가로 예약 매수
        if 'J' in stock_code:
            return

        price = int(base_price) * (1 + ((earning_rate) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit)
        price = int(price * unit)
        if amount == 0:
            num = 1
        else:
            num = int(amount / price)
        if buy_amount:
            if buy_amount + (num * price) > self.max_amount:
                num = int((self.max_amount - buy_amount) / price)
        if num == 0:
            logger.debug("------- 매수 할 수 있는 수량이 0 입니다.")
            return False

        success, detail = self.kiwoom.place_credit_buy_order(
            stock_code, num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug("------- 지정가로 매수!! 추가매수가 : {}원 수량 : {}개 매입금액 : {}원".format(price, num, num * price))
        if success:
            return True
        else:
            msg = detail
            logger.error(f"신용 지정가 매수 주문 실패: {msg}")
            return False

    def _sell_current_price(self, stock, remain, sell_stock_amount):
        # 매도#
        if 'J' in stock['code']:
            return

        logger.debug(" - 현재가 정보 요청 : {}".format(stock))
        price, name = self.get_current_price(stock['code'])
        if price == 0:
            logger.error(f"매도 주문 실패: 현재가 정보 없음")
            return remain

        num = int(sell_stock_amount / price)
        if num == 0:
            num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        success, detail = self.kiwoom.place_cash_sell_order(
            stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug("------- 현재가로 매도!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_designated_price(self, stock, sell_earning_rate, remain, sell_stock_amount, after_market):
        if 'J' in stock['code']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 1) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1
        price = int(price * unit)
        num = int(sell_stock_amount / price)
        if num == 0:
            num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        if after_market:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market='KRX', tr_type=HOGATYPE['시간외단일가']
            )
        else:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
            )
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 지정가/시간외 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_1_stock_current_price(self, stock, remain):
        # 매도#
        if 'J' in stock['code']:
            return

        logger.debug(" - 현재가 정보 요청 : {}".format(stock))
        price, name = self.get_current_price(stock['code'])
        if price == 0:
            logger.error(f"매도 주문 실패: 현재가 정보 없음")
            return remain
        num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        success, detail = self.kiwoom.place_cash_sell_order(
            stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug("------- 현재가로 매도!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 1주 현재가 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_2_stock_designated_price(self, stock, sell_earning_rate, remain, after_market):
        if 'J' in stock['code']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.5) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1  # 올림
        price = int(price * unit)
        num = 2
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        if after_market:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market='KRX', tr_type=HOGATYPE['시간외단일가']
            )
        else:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
            )
        logger.debug("------- 일괄 2주 매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 2주 지정가/시간외 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_1_stock_designated_price(self, stock, sell_earning_rate, remain, after_market):
        if 'J' in stock['code']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.5) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1  # 올림
        price = int(price * unit)
        num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        if after_market:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market='KRX', tr_type=HOGATYPE['시간외단일가']
            )
        else:
            success, detail = self.kiwoom.place_cash_sell_order(
                stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
            )
        logger.debug("------- 일괄 1주 매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 1주 지정가/시간외 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_designated_price_num(self, stock, sell_earning_rate, remain, num):
        if 'J' in stock['code']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.5) / 100))  # 0.5 = 수수료
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1
        price = int(price * unit)
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        success, detail = self.kiwoom.place_cash_sell_order(
            stock['code'], num, price=price, market=self.exchange, tr_type=HOGATYPE['지정가']
        )
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 현금 일괄 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_credit_designated_price(self, stock, sell_earning_rate, remain, sell_stock_amount, after_market):
        if 'J' in stock['code']:
            return

        interest = float(stock['interest']) / int(
            stock['possession_num']) if 'interest' in stock and 'possession_num' in stock else 0
        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.3) / 100)) + interest  # 0.3 = 수수료
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1
        price = int(price * unit)
        num = int(sell_stock_amount / price)
        if num == 0:
            num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num

        if after_market:
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market='KRX',
                tr_type=HOGATYPE['시간외단일가'], crd_loan_dt=stock['loan_date']
            )
        else:
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market=self.exchange,
                tr_type=HOGATYPE['지정가'], crd_loan_dt=stock['loan_date']
            )
        logger.debug("------- 신용 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 신용 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_credit_designated_price_num(self, stock, sell_earning_rate, remain, num, after_market):
        if 'J' in stock['code']:
            return

        interest = float(stock['interest']) / int(
            stock['possession_num']) if 'interest' in stock and 'possession_num' in stock else 0
        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.3) / 100)) + interest  # 0.3 = 수수료
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1
        price = int(price * unit)
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        if after_market:  # 시간외 단일가
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market='KRX',
                tr_type=HOGATYPE['시간외단일가'], crd_loan_dt=stock['loan_date']
            )
        else:
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market=self.exchange,
                tr_type=HOGATYPE['지정가'], crd_loan_dt=stock['loan_date']
            )
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 신용 일괄 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def _sell_credit_hoga_num(self, stock, hoga, remain, num, after_market):
        if 'J' in stock['code']:
            return

        interest = float(stock['interest']) / int(
            stock['possession_num']) if 'interest' in stock and 'possession_num' in stock else 0
        price = int(stock['buy_price']) * (1 + (0.3 / 100)) + interest  # 0.5 = 수수료
        price = int(price)
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        logger.debug(f"손익분기 금액 : {price} 호가 : {unit}")
        price = int(price / unit)
        price = int(price * unit)
        logger.debug(f"손익분기 버린 금액 : {price} 호가 : {unit}")
        price += unit * hoga
        logger.debug(f"매도금액 : {price}")
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        if after_market:  # 시간외 단일가
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market='KRX',
                tr_type=HOGATYPE['시간외단일가'], crd_loan_dt=stock['loan_date']
            )
        else:
            success, detail = self.kiwoom.place_credit_sell_order(
                stock['code'], num, price=price, market=self.exchange,
                tr_type=HOGATYPE['지정가'], crd_loan_dt=stock['loan_date']
            )
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        if success:
            # 신용 호가 지정 매도 주문 히스토리 저장
            self.save_local_order_history(
                detail,
                stock.get('name', ''),
                stock.get('loan_date', ''),
                int(stock.get('buy_price', 0)),
            )
            return remain - num
        else:
            msg = detail
            logger.error(f"매도 주문 실패: {msg}")
            return remain

    def rebuy_user_credit_stock(self, stock, is_cash_stock=False):
        logger.debug(
            f"### 신용 물타기 매수 기준 : {self.rebuy_credit_earning_rate}% "
            f"종목명 : {stock['name']} 현재수익률 : {stock['earning_rate']}%"
        )
        if float(stock["earning_rate"]) <= self.rebuy_credit_earning_rate:
            self._buy_credit_current_price(
                stock['code'],
                self.rebuy_credit_stock_amount,
                skip_max_check=is_cash_stock,
                buy_amount=int(stock['buy_amount'])  # 보유 금액 전달
            )

    def rebuy_user_stock(self, stock):
        # 물타기 매수#

        logger.debug("### 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(self.rebuy_earning_rate,
                                                                                            stock['name'],
                                                                                            stock['earning_rate'],
                                                                                            int(stock['buy_price']),
                                                                                            int(stock['buy_amount'])))

        if float(stock["earning_rate"]) <= self.rebuy_earning_rate:
            self._buy_current_price(stock['code'], self.rebuy_stock_amount, int(stock['buy_amount']))

    def rebuy_1_stock(self, stock):
        # 물타기 매수#

        logger.debug(
            "### 1주 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(self.rebuy_1_stock_earning_rate,
                                                                                      stock['name'],
                                                                                      stock['earning_rate'],
                                                                                      int(stock['buy_price']),
                                                                                      int(stock['buy_amount'])))

        self._buy_designated_price(stock['code'], 0, self.rebuy_1_stock_earning_rate, stock['buy_price'],
                                   int(stock['buy_amount']))

    def rebuy_manual_stock(self, stock, earning_rate, buy_stock_num):
        # 물타기 매수#

        logger.debug(
            "### 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(float(earning_rate), stock['name'],
                                                                                   stock['earning_rate'],
                                                                                   int(stock['buy_price']),
                                                                                   int(stock['buy_amount'])))

        if float(stock["earning_rate"]) <= float(earning_rate):
            self._buy_current_price_num(stock['code'], int(buy_stock_num), int(stock['buy_amount']))

    def sell_user_stock(self, stock, sell_earning_rate, remain, sell_stock_amount, after_market=False):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                  stock['name'],
                                                                                                  stock['earning_rate'],
                                                                                                  int(stock[
                                                                                                          'buy_price']),
                                                                                                  int(stock[
                                                                                                          'buy_amount']),
                                                                                                  remain))

        return self._sell_designated_price(stock, sell_earning_rate, remain, sell_stock_amount, after_market)

    def sell_user_credit_stock(self, stock, sell_earning_rate, remain, sell_stock_amount, after_market=False):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                  stock['name'],
                                                                                                  stock['earning_rate'],
                                                                                                  int(stock[
                                                                                                          'buy_price']),
                                                                                                  int(stock[
                                                                                                          'buy_amount']),
                                                                                                  remain))

        return self._sell_credit_designated_price(stock, sell_earning_rate, remain, sell_stock_amount, after_market)

    def sell_1_stock(self, stock, sell_earning_rate, remain, after_market=False):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 1주 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                     stock['name'],
                                                                                                     stock[
                                                                                                         'earning_rate'],
                                                                                                     int(stock[
                                                                                                             'buy_price']),
                                                                                                     int(stock[
                                                                                                             'buy_amount']),
                                                                                                     remain))
        return self._sell_1_stock_designated_price(stock, sell_earning_rate, remain, after_market)

    def sell_current_1_stock(self, stock, remain):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 1주 현재가 매도 종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(stock['name'],
                                                                                                        stock[
                                                                                                            'earning_rate'],
                                                                                                        int(stock[
                                                                                                                'buy_price']),
                                                                                                        int(stock[
                                                                                                                'buy_amount']),
                                                                                                        remain))
        return self._sell_1_stock_current_price(stock, remain)

    def sell_2_stock(self, stock, sell_earning_rate, remain, after_market=False):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 2주 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                     stock['name'],
                                                                                                     stock[
                                                                                                         'earning_rate'],
                                                                                                     int(stock[
                                                                                                             'buy_price']),
                                                                                                     int(stock[
                                                                                                             'buy_amount']),
                                                                                                     remain))
        return self._sell_2_stock_designated_price(stock, sell_earning_rate, remain, after_market)

    def sell_manual_credit_stock(self, stock, sell_earning_rate, remain, sell_stock_num, after_market=False):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                  stock['name'],
                                                                                                  stock['earning_rate'],
                                                                                                  int(stock[
                                                                                                          'buy_price']),
                                                                                                  int(stock[
                                                                                                          'buy_amount']),
                                                                                                  remain))

        return self._sell_credit_designated_price_num(stock, int(sell_earning_rate), remain, int(sell_stock_num),
                                                      after_market)

    def sell_manual_stock(self, stock, sell_earning_rate, remain, sell_stock_num):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug(
            "### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate,
                                                                                                  stock['name'],
                                                                                                  stock['earning_rate'],
                                                                                                  int(stock[
                                                                                                          'buy_price']),
                                                                                                  int(stock[
                                                                                                          'buy_amount']),
                                                                                                  remain))

        return self._sell_designated_price_num(stock, int(sell_earning_rate), remain, int(sell_stock_num))

    def cancel_not_done_sell_order(self, order):
        logger.debug("### 미체결 현금주문 취소")

        # REST API 방식으로 주문 취소
        return self.kiwoom.cancel_order(
            orig_order_no=order['ord_no'],
            stock_code=order['stk_cd'],
            quantity=int(order['oso_qty']),
            market=order['stex_tp_txt']
        )

    def cancel_not_done_credit_sell_order(self, order):
        logger.debug("### 미체결 신용주문 취소")

        # REST API 방식으로 신용 주문 취소
        return self.kiwoom.cancel_credit_order(
            orig_order_no=order['ord_no'],
            stock_code=order['stk_cd'],
            quantity=int(order['oso_qty']),
            market=order['stex_tp_txt']
        )

    def set_exchange(self):
        now = datetime.datetime.now()
        now_tupule = now.timetuple()
        logger.debug(now_tupule)
        hour = now_tupule.tm_hour
        minute = now_tupule.tm_min
        
        # 8시 30분 이전: NXT
        if hour < 8 or (hour == 8 and minute < 30):
            self.exchange = "NXT"
        # 8시 30분부터 14시 59분까지: KRX
        elif hour < 15:
            self.exchange = "KRX"
        # 15시 00분 이후: NXT
        else:
            self.exchange = "NXT"
        logger.debug(f"거래소 : {self.exchange}")

    def is_nxt_available(self, stock_code):
        code = stock_code[1:] if stock_code.startswith('A') else stock_code
        return code in self.nxt_list

    def get_today_trading_diff(self):
        """ka10074 API를 사용하여 (총 매수 - 총 매도) 금액을 계산합니다."""
        try:
            res = self.kiwoom.get_realized_profit_loss()
            # API 응답: "tot_buy_amt", "tot_sell_amt"
            buy_amt = int(res.get('tot_buy_amt', 0))
            sell_amt = int(res.get('tot_sell_amt', 0))

            diff = buy_amt - sell_amt
            logger.debug(f"[실현손익 데이터 확인] 총 매수: {buy_amt}, 총 매도: {sell_amt}, 차이: {diff}")
            return diff
        except Exception as e:
            logger.error(f"거래 차이 계산 실패: {e}")
            return 999999999  # 안전을 위해 매수 제한값이 넘는 큰 값 반환

    def save_local_order_history(self, order_no, stock_name, loan_date, buy_price):
        """
        로컬 히스토리용 주문 기록 저장
        - order_no: 주문번호
        - stock_name: 종목 이름
        - loan_date: 대출일자 (신용거래가 아닌 경우 빈 문자열 허용)
        - buy_price: 주문 시 기준 매입가/평단가 (int 또는 str)
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            # 테이블이 없으면 생성
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_no TEXT,
                    stock_name TEXT,
                    loan_date TEXT,
                    buy_price INTEGER,
                    created_at TEXT
                )
                """
            )

            from datetime import datetime
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                """
                INSERT INTO local_order_history
                (order_no, stock_name, loan_date, buy_price, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(order_no), stock_name, str(loan_date or ""), int(buy_price), created_at),
            )

            conn.commit()
            conn.close()
            logger.debug(
                f"[LOCAL_HISTORY] 기록 저장 - ord_no={order_no}, name={stock_name}, "
                f"loan_date={loan_date}, buy_price={buy_price}"
            )
        except Exception as e:
            logger.error(f"[LOCAL_HISTORY] 저장 실패: {e}")
