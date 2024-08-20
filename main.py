from time import sleep, time
import sys
from PyQt5.QtWidgets import *
from kiwoom import Kiwoom, logger
import random
import datetime
import sqlite3
import csv
import os

ORDER_INTERVAL = "주문간격(초)"  # 주문 간격
BUY_NEW_STOCK_AMOUNT = "신규매수주식금액"  # 신규매수 주식 금액
REBUY_STOCK_AMOUNT = "물타기매수주식금액"  # 물타기매수 주식 금액
SELL_STOCK_AMOUNT = "1차 매도주식금액"  # 매도 주식 금액
SELL_STOCK_AMOUNT_2 = "2차 매도주식금액"  # 매도 주식 금액
SELL_STOCK_AMOUNT_3 = "3차 매도주식금액"  # 매도 주식 금액
REBUY_EARNING_RATE = "물타기 기준(%)"  # 물타기 기준
REBUY_1_STOCK_EARNING_RATE = "1주 매수 기준(%)" # 1주 매수 기준
SELL_EARNING_RATE = "매도 기준(%)"  # 매도 기준
SELL_EARNING_RATE_2 = "2차 매도 기준(%)"  # 매도 기준
SELL_EARNING_RATE_3 = "3차 매도 기준(%)"  # 매도 기준
SELL_1_STOCK_EARNING_RATE = "1주 매도 기준(%)" # 1주 매도 기준
SELL_ALL_EARNING_RATE = 10  # 사용안함
MAX_AMOUNT = "종목별 매수 최대 금액(원)"  # 종목별 매수 최대 금액
REMAIN_MONEY_BUY_NEW_STOCK_UP_RATE = {30000000: 200,
                                      10000000: 150}  # 예수금: 종목갯수 ( 예수금 이상일 때 종목갯수만큼 보유종목 유지)
REMAIN_MONEY_BUY_NEW_STOCK_DOWN_RATE = {10000000: 100}  # 예수금: 종목갯수 ( 예수금 이하일 때 종목갯수만큼 보유종목 유지)
DEFAULT_BUY_NEW_STOCK_NUM = "기본 보유종목 개수"  # 기본 보유종목 갯수
STATUS = "운영상태"
EXCEPT_REBUY = "물타기 제외 종목"
BUY_NEW_STOCK = "신규종목매수"

TR_REQ_TIME_INTERVAL = 0.6

ORDERTYPE = {'신규매수': 1, '신규매도': 2, '매수취소': 3, '매도취소': 4}
HOGATYPE = {'지정가': "00", '시장가': "03"}

HOGAUNIT = {1000: 1, 5000: 5, 10000: 10, 50000: 50, 100000: 100, 500000: 500, 0: 1000}

class Trading:
    def __init__(self):
        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()  # log in
        self.user_stock_num = 0
        self.user_stock_list = []
        self.interesting_stocks = []
        self.not_done_orders_num = 0
        self.not_done_orders = []
        self.not_done_sell_num = 0
        self.not_done_sell = []
        self.buy_code_list = []
        self.buy_new_stock_num = 100
        self.order_interval = 150
        self.buy_new_stock_amount = 300000
        self.rebuy_stock_amount = 300000
        self.sell_stock_amount_1 = 320000
        self.sell_stock_amount_2 = 620000
        self.sell_stock_amount_3 = 820000
        self.rebuy_earning_rate = -8
        self.sell_earning_rate = [4, 8, 12]
        self.sell_1_stock_earning_rate = 3
        self.rebuy_1_stock_earning_rate = -3
        self.max_amount = 10000000
        self.default_buy_new_stock_num = 100
        self.remain_money_buy_new_stock_down_rate = {}
        self.remain_money_buy_new_stock_up_rate = {}
        self.running_state = 1
        self.except_rebuy_list = []
        self.new_buy_stock = True

    def set_status_running(self):
        conn = sqlite3.connect("../secretary_web/db.sqlite3")
        cur = conn.cursor()

        sql = '''update secretary_setup set value=1 where key="운영상태"'''
        cur.execute(sql)
        conn.close()

    def get_status_running(self):
        conn = sqlite3.connect("../secretary_web/db.sqlite3")
        cur = conn.cursor()

        cur.execute("select value from secretary_setup where key=\"운영상태\"")
        rows = cur.fetchall()
        self.running_state = rows[0][0]
        conn.close()

    def update_options(self):
        conn = sqlite3.connect("../secretary_web/db.sqlite3")
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
            elif row[2] == SELL_STOCK_AMOUNT:
                self.sell_stock_amount_1 = row[1]
            elif row[2] == SELL_STOCK_AMOUNT_2:
                self.sell_stock_amount_2 = row[1]
            elif row[2] == SELL_STOCK_AMOUNT_3:
                self.sell_stock_amount_3 = row[1]
            elif row[2] == REBUY_EARNING_RATE:
                self.rebuy_earning_rate = row[1]
            elif row[2] == SELL_EARNING_RATE:
                self.sell_earning_rate[0] = row[1]
            elif row[2] == SELL_EARNING_RATE_2:
                self.sell_earning_rate[1] = row[1]
            elif row[2] == SELL_EARNING_RATE_3:
                self.sell_earning_rate[2] = row[1]
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

        cur.execute("select * from secretary_stockdownrate")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                break
            self.remain_money_buy_new_stock_down_rate[row[1]] = row[2] # must be one

        cur.execute("select * from secretary_stockuprate")
        rows = cur.fetchall()
        for row in rows:
            if not row[1]:
                break
            self.remain_money_buy_new_stock_up_rate[row[1]] = row[2]
        self.remain_money_buy_new_stock_up_rate = sorted(self.remain_money_buy_new_stock_up_rate.items(), reverse=True)

        conn.close()

    def get_user_stock(self):
        # 사용자 계정의 보유 주식 개수 확인
        self.account = self.kiwoom.get_login_info()
        self.account = self.account.split(';')[0]
        logger.debug('계좌번호 : {}'.format(self.account))

        self.kiwoom.set_input_value("계좌번호", self.account)
        self.kiwoom.comm_rq_data("잔고조회", "opw00018", 0, "0101")
        self.user_stock_num = self.kiwoom.ret_cnt
        self.user_stock_list = self.kiwoom.ret_multi_data

        while self.kiwoom.remained_data:
            logger.debug("다음 잔고조회")
            sleep(TR_REQ_TIME_INTERVAL)
            self.kiwoom.set_input_value("계좌번호", self.account)
            self.kiwoom.comm_rq_data("잔고조회", "opw00018", 2, "0101")
            self.user_stock_num += self.kiwoom.ret_cnt
            self.user_stock_list.extend(self.kiwoom.ret_multi_data)

        logger.debug('user stock cnt : {}'.format(self.user_stock_num))
        logger.debug(self.user_stock_list)

    def get_user_remain(self):
        # 예수금 조회
        self.kiwoom.set_input_value("계좌번호", self.account)
        self.kiwoom.set_input_value("상장폐지조회구분", "0")
        self.kiwoom.comm_rq_data("계좌평가현황요청", "opw00004", 0, "0101")
        logger.debug('예수금 조회 : {}'.format(self.kiwoom.ret_data))
        sleep(TR_REQ_TIME_INTERVAL)
        return int(self.kiwoom.ret_data['remain'])

    def get_interesting_stock(self):
        self.kiwoom.get_condition_load()
        sleep(TR_REQ_TIME_INTERVAL)
        if self.kiwoom.condition:
            for key in self.kiwoom.condition.keys():
                self.kiwoom.send_condition("0101", self.kiwoom.condition[key], key, 0)
                self.interesting_stocks.extend(self.kiwoom.code_list)
                logger.debug("관심종목 : {}".format(self.interesting_stocks))
                sleep(TR_REQ_TIME_INTERVAL)
            '''[04056, 34567, 12233, ...]'''
        stocks_set = set(self.interesting_stocks)
        self.interesting_stocks = list(stocks_set)
        logger.debug(len(self.interesting_stocks))

    def get_current_price(self, code):
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.comm_rq_data("주식기본정보", "opt10001", 0, "0101")
        logger.debug('현재가 조회 : {}'.format(self.kiwoom.ret_data))
        sleep(TR_REQ_TIME_INTERVAL)
        return int(self.kiwoom.ret_data['current_price']), self.kiwoom.ret_data['name']

    def is_stock_in_user_stock(self, code):
        for i in range(self.user_stock_num):
            if code == self.user_stock_list[i]['code']:
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
        self.kiwoom.set_input_value("계좌번호", self.account)
        self.kiwoom.set_input_value("체결구분", 1)
        self.kiwoom.set_input_value("매매구분", 2)
        self.kiwoom.comm_rq_data("실시간체결", "opt10075", 0, "0101")
        self.not_done_orders_num = self.kiwoom.ret_cnt
        self.not_done_orders = self.kiwoom.ret_multi_data
        logger.debug("미체결 매수주문: {}".format(self.not_done_orders))
        sleep(TR_REQ_TIME_INTERVAL)

    def get_not_done_sell(self):  # 미체결 매도
        self.kiwoom.set_input_value("계좌번호", self.account)
        self.kiwoom.set_input_value("체결구분", 1)
        self.kiwoom.set_input_value("매매구분", 1)
        self.kiwoom.comm_rq_data("실시간체결", "opt10075", 0, "0101")
        self.not_done_sell_num = self.kiwoom.ret_cnt
        self.not_done_sell = self.kiwoom.ret_multi_data
        logger.debug("미체결 매도주문: {}".format(self.not_done_sell))
        sleep(TR_REQ_TIME_INTERVAL)

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
                        or self.is_stock_in_not_done_order(self.interesting_stocks[key])\
                        or key in bought_key:
                    logger.debug('이미 보유하고 있거나 신규매수한 종목입니다. skip!! [{}]'.format(self.interesting_stocks[key]))
                    continue
                bought_key.append(key)
                logger.debug(" - 현재가 정보 요청")
                price, name = self.get_current_price(self.interesting_stocks[key])
                logger.debug("현재가 정보 요청 완료")
                # -1프로로 매수 예약
                if self._buy_designated_price(self.interesting_stocks[key], self.buy_new_stock_amount, -1, price):
                    buy_cnt += 1
                logger.debug('보유주식개수(주문내역포함):{}'.format(buy_cnt + self.user_stock_num))
                sleep(0.7)
        else:
            logger.debug('보유주식이 {}개이므로 더이상 신규매수할수 없습니다.'.format(self.user_stock_num))

    def _buy_current_price(self, stock_code, amount, buy_amount=None):
        # 일정 금액(amount)만큼 현재가로 매수
        if 'J' in stock_code:
            return
        if '*' in stock['name']:
            return

        logger.debug(" - 현재가 정보 요청")
        price, name = self.get_current_price(stock_code)
        # num = int(buy_amount / price)
        if amount == 0:
            num = 1
        else:
            num = int(amount / price)
        if buy_amount: # 보유금액
            if buy_amount + (num * price) > self.max_amount:
                num = int((self.max_amount - buy_amount) / price)
        if num == 0:
            logger.debug("------- 매수 할 수 있는 수량이 0 입니다.")
            return False

        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매수'], stock_code,
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 현재가로 매수!! 종목명 : {} 추가매수가 : {}원 수량 : {}개 매입금액 : {}원".format(name,  price, num, num * price))
        return True

    def _buy_current_price_num(self, stock_code, num, buy_amount=None):
        # 일정 금액(amount)만큼 현재가로 매수
        if 'J' in stock_code:
            return
        if '*' in stock['name']:
            return

        logger.debug(" - 현재가 정보 요청")
        price, name = self.get_current_price(stock_code)
        if buy_amount: # 보유금액
            if buy_amount + (num * price) > self.max_amount:
                num = int((self.max_amount - buy_amount) / price)
        if num == 0:
            logger.debug("------- 매수 할 수 있는 수량이 0 입니다.")
            return False
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매수'], stock_code,
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 현재가로 매수!! 종목명 : {} 추가매수가 : {}원 수량 : {}개 매입금액 : {}원".format(name,  price, num, num * price))
        return True

    def _buy_designated_price(self, stock_code, amount, earning_rate, base_price, buy_amount=None):
        # 수익률(earning_rate) 지정가로 예약 매수
        if 'J' in stock_code:
            return
        if '*' in stock['name']:
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
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매수'], stock_code,
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 지정가로 매수!! 추가매수가 : {}원 수량 : {}개 매입금액 : {}원".format(price, num, num * price))
        return True

    def _sell_current_price(self, stock, remain, sell_stock_amount):
        # 매도#
        '''
        #보유종목의 수익률이 10이상인 경우 전량 매도
        if float(stock["earning_rate"]) >= SELL_ALL_EARNING_RATE \
                and not self.is_stock_in_not_done_sell(stock['code']):
            logger.debug("###현재가 정보 요청### : {}".format(stock))
            price, name = self.get_current_price(stock['code'])
            num = int(stock['possession_num'])
            self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                                   num, price, HOGATYPE['지정가'], "")
            sleep(1)
            logger.debug("### 전량 매도!! 수량 : {}".format(num))'''
        # 보유종목의 수익률이 3 이상인 경우 현재가로 매도
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
            return

        logger.debug(" - 현재가 정보 요청 : {}".format(stock))
        price, name = self.get_current_price(stock['code'])
        num = int(sell_stock_amount / price)
        if num == 0:
            num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 현재가로 매도!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def _sell_designated_price(self, stock, sell_earning_rate, remain, sell_stock_amount):
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
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
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def _sell_1_stock_current_price(self, stock, remain):
        # 매도#
        # 보유종목의 수익률이 3 이상인 경우 현재가로 매도
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
            return

        logger.debug(" - 현재가 정보 요청 : {}".format(stock))
        price, name = self.get_current_price(stock['code'])
        num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 현재가로 매도!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def _sell_1_stock_designated_price(self, stock, sell_earning_rate, remain):
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.5) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1 # 올림
        price = int(price * unit)
        num = 1
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 일괄 1주 매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def _sell_2_stock_designated_price(self, stock, sell_earning_rate, remain):
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
            return

        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 0.5) / 100))
        for pr, un in HOGAUNIT.items():
            if price < pr:
                unit = un
                break
        price = int(price / unit) + 1 # 올림
        price = int(price * unit)
        num = 2
        if num > remain:
            num = remain
        if num == 0:
            logger.debug("매도 가능 수량 : 0")
            return remain - num
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 일괄 2주 매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def _sell_designated_price_num(self, stock, sell_earning_rate, remain, num):
        if 'J' in stock['code']:
            return
        if '*' in stock['name']:
            return
        price = int(stock['buy_price']) * (1 + ((sell_earning_rate + 1) / 100))
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
        self.kiwoom.send_order("수동주문", "0101", self.account, ORDERTYPE['신규매도'], stock['code'],
                               num, price, HOGATYPE['지정가'], "")
        sleep(0.7)
        logger.debug("------- 일괄매도예약주문!! 매도가 : {}원 수량 : {}개 매도금액 : {}원".format(price, num, num * price))
        return remain - num

    def rebuy_user_stock(self, stock):
        # 물타기 매수#

        logger.debug("### 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(self.rebuy_earning_rate, stock['name'], stock['earning_rate'], int(stock['buy_price']),
                                                                               int(stock['buy_amount'])))

        if float(stock["earning_rate"]) <= self.rebuy_earning_rate:
            self._buy_current_price(stock['code'], self.rebuy_stock_amount, int(stock['buy_amount']))

    def rebuy_1_stock(self, stock):
        # 물타기 매수#

        logger.debug("### 1주 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(self.rebuy_1_stock_earning_rate, stock['name'], stock['earning_rate'], int(stock['buy_price']),
                                                                               int(stock['buy_amount'])))

        self._buy_designated_price(stock['code'], 0, self.rebuy_1_stock_earning_rate, stock['buy_price'], int(stock['buy_amount']))

    def rebuy_manual_stock(self, stock, earning_rate, buy_stock_num):
        # 물타기 매수#

        logger.debug("### 매수 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원###".format(float(earning_rate), stock['name'], stock['earning_rate'], int(stock['buy_price']),
                                                                               int(stock['buy_amount'])))

        if float(stock["earning_rate"]) <= float(earning_rate):
            self._buy_current_price_num(stock['code'], int(buy_stock_num), int(stock['buy_amount']))

    def sell_user_stock(self, stock, sell_earning_rate, remain, sell_stock_amount):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate, stock['name'],
                                                                               stock['earning_rate'],
                                                                               int(stock['buy_price']),
                                                                                int(stock['buy_amount']),
                                                                                remain))

        return self._sell_designated_price(stock, sell_earning_rate, remain, sell_stock_amount)

    def sell_1_stock(self, stock, sell_earning_rate, remain):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 1주 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate, stock['name'],
                                                                               stock['earning_rate'],
                                                                               int(stock['buy_price']),
                                                                                int(stock['buy_amount']),
                                                                                remain))
        return self._sell_1_stock_designated_price(stock, sell_earning_rate, remain)

    def sell_current_1_stock(self, stock, remain):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 1주 현재가 매도 종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(stock['name'],
                                                                               stock['earning_rate'],
                                                                               int(stock['buy_price']),
                                                                                int(stock['buy_amount']),
                                                                                remain))
        return self._sell_1_stock_current_price(stock, remain)

    def sell_2_stock(self, stock, sell_earning_rate, remain):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 2주 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate, stock['name'],
                                                                               stock['earning_rate'],
                                                                               int(stock['buy_price']),
                                                                                int(stock['buy_amount']),
                                                                                remain))
        return self._sell_2_stock_designated_price(stock, sell_earning_rate, remain)

    def sell_manual_stock(self, stock, sell_earning_rate, remain, sell_stock_num):
        # 매도#
        # 지정 수익률 이상 가격으로 매도

        logger.debug("### 매도 기준 : {}%  종목명 : {} 현재수익률 : {}% 매입가 : {}원 보유금액 : {}원 매도 가능 수량 : {}개###".format(sell_earning_rate, stock['name'],
                                                                               stock['earning_rate'],
                                                                               int(stock['buy_price']),
                                                                                int(stock['buy_amount']),
                                                                                remain))

        return self._sell_designated_price_num(stock, int(sell_earning_rate), remain, int(sell_stock_num))

if __name__ == "__main__":
    argument = sys.argv  # 0: 물타기매수/신규매수/매도 1: 물타기매수 2: 매도 3: 신규매수

    if argument[2] != 'test':
        weekday = datetime.datetime.today().weekday()
        logger.debug(weekday)
        if weekday in range(0, 5):
            now = datetime.datetime.now()
            now_tupule = now.timetuple()
            logger.debug(now_tupule)
            while now_tupule.tm_hour < 9:
                sleep(60)
                now = datetime.datetime.now()
                now_tupule = now.timetuple()
                logger.debug(now_tupule)
            if now_tupule.tm_hour > 16:
                logger.debug("장이 마감되었습니다.")
                exit(0)
        else:
            exit(0)

    logger.debug('거래 시작')

    app = QApplication(sys.argv)
    for _ in range(2):
        try:
            trade = Trading()
            if trade:
                break
        except Exception as err:
            logger.exception(err)


    #trade.set_status_running()
    # db에서 설정값 가져오기
    try:
        logger.debug('DB 접속')
        trade.update_options()

        logger.debug('주식정보 가져오기')
        trade.get_user_stock()

        with open("D:\\OneDrive\\문서\\주식현황.csv", "a", encoding='utf-8', newline='') as f:
            wr = csv.writer(f)
            wr.writerow(["{}".format(datetime.datetime.today().strftime("%Y/%m/%d")), "{}".format(trade.user_stock_num)])

        ## ---------------------------------- manual ------------------------------------------ ##

        if argument[1] == '4':
            logger.debug('>>>>>>>>>>>> 수동 매도 <<<<<<<<<<<<<<')
            earning_rate = argument[3].strip('%')
            num = argument[4].strip('ea')
            for stock in trade.user_stock_list:
                remain = int(stock['available_num'])
                trade.sell_manual_stock(stock, earning_rate, remain, num)

        if argument[1] == '5':
            logger.debug('>>>>>>>>>>>>수동 매수 <<<<<<<<<<<<<<')
            trade.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
            logger.debug('물타기 제외 종목 들 : {}'.format(trade.except_rebuy_list))
            earning_rate = argument[3].strip('%')
            num = argument[4].strip('ea')
            for i in range(len(trade.user_stock_list)):
                # 보유종목의 매입금액 + 새로 매수할 금액이 MAX_AMOUNT만원이 넘는지 확인해서 MAX_AMOUNT만원에 맞추기
                stock = trade.user_stock_list[i]
                buy_amount = int(stock['buy_amount'])
                if buy_amount > trade.max_amount:
                    logger.debug("------- 종목명 : {} 보유금액({}원)이 MAX 값({})보다 큽니다.".format(stock['name'], buy_amount,
                                                                                       trade.max_amount))
                    continue
                if not trade.user_stock_list[i]['name'] in trade.except_rebuy_list:
                    trade.rebuy_manual_stock(stock, earning_rate, num)
                else:
                    logger.debug("물타기 제외 종목입니다 : {}".format(stock))

        ## ---------------------------------- auto ------------------------------------------ ##

        if argument[1] == '1':
            trade.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
            logger.debug('>>>>>>>>>>>> 일괄 매수 <<<<<<<<<<<<<<')
            logger.debug('물타기 제외 종목 들 : {}'.format(trade.except_rebuy_list))
            for i in range(len(trade.user_stock_list)):
                # 보유종목의 매입금액 + 새로 매수할 금액이 MAX_AMOUNT만원이 넘는지 확인해서 MAX_AMOUNT만원에 맞추기
                stock = trade.user_stock_list[i]
                buy_amount = int(stock['buy_amount'])
                if buy_amount > trade.max_amount:
                    logger.debug("------- 종목명 : {} 보유금액({}원)이 MAX 값({})보다 큽니다.".format(stock['name'], buy_amount,
                                                                                       trade.max_amount))
                    continue
                if not trade.user_stock_list[i]['name'] in trade.except_rebuy_list:
                    trade.rebuy_user_stock(stock)
                    trade.rebuy_1_stock(stock)
                else:
                    logger.debug("물타기 제외 종목입니다 : {}".format(stock))

            sleep(0.5)
            trade.get_user_stock()
            
        if argument[1] == '3':
            if trade.new_buy_stock == 1:
                # 사용자 관심종목으로 부터 리스트 가져오기
                trade.get_interesting_stock()
                # 미체결 매수주문 정보 가져오기
                trade.get_not_done_order()
                # 미체결 매도주문 정보 가져오기
                #trade.get_not_done_sell()
                logger.debug('>>>>>>>>>>>> 신규 종목 매수 <<<<<<<<<<<<<<')
                trade.set_buy_stock_num()
                trade.buy_new_stock()

                sleep(0.5)
                trade.get_user_stock()

        if argument[1] == '0' or argument[1] == '2':
            logger.debug('>>>>>>>>>>>> 일괄 매도 <<<<<<<<<<<<<<')
            for stock in trade.user_stock_list:
                remain = int(stock['available_num'])
                # 1주 매도
                for i in range(trade.sell_1_stock_earning_rate):
                    earning_rate = i + 1
                    if remain:
                        remain = trade.sell_1_stock(stock, earning_rate, remain)
                if remain:
                    remain = trade.sell_user_stock(stock, trade.sell_earning_rate[0], remain, trade.sell_stock_amount_1)
                if remain:
                    remain = trade.sell_user_stock(stock, trade.sell_earning_rate[1], remain, trade.sell_stock_amount_2)
                if remain:
                    remain = trade.sell_user_stock(stock, trade.sell_earning_rate[2], remain, trade.sell_stock_amount_3)
                logger.debug("남은 주식 수 : {}".format(remain))


    except Exception as err:
        logger.exception(err)

    if argument[1] in ['0', '1', '2', '3']:
        os.system("taskkill /im KaKaoTalk.exe")
        os.system("C:\\PycharmProjects\\secretary\\카카오톡.lnk")

    '''

    # db에서 동작여부 확인하기

    logger.debug(
        '==================================================================================================')
    try:
        trade.get_user_stock()
        # 미체결 매수주문 정보 가져오기
        #trade.get_not_done_order()
        # 미체결 매도주문 정보 가져오기
        #trade.get_not_done_sell()
        #logger.debug('>>>>>>>>>>>> 신규매수 <<<<<<<<<<<<<<')
        #trade.set_buy_stock_num()
        #trade.buy_new_stock()
        logger.debug('>>>>>>>>>>>> 종목별 추가매수 / 매도 <<<<<<<<<<<<<<')
        for i in range(len(trade.user_stock_list)):
            trade.buy_user_stock(trade.user_stock_list[i])
            #trade.sell_user_stock(trade.user_stock_list[i])
        logger.debug('>>>>>>>>>>>> 모든 주식 체크 완료 <<<<<<<<<<<<<<')
    except Exception as err:
        logger.debug(err)
'''
