from abc import ABC, abstractmethod
from typing import Dict, Any
from kiwoom import Kiwoom
from logger import logger
import datetime
from time import sleep
from main import Trading

class TradingStrategy(ABC):
    """Base abstract class for all trading strategies"""
    
    def __init__(self, kiwoom: Kiwoom):
        self.kiwoom = kiwoom
        self.trading = Trading()  # Use Trading class from main.py
        self.trading.update_options()  # Update trading options at initialization
        self.trading.set_exchange()  # Set exchange type at initialization
        self.user_stock_list = []
        self.user_stock_num = 0
        self.user_credit_stock_list = []
        self.user_credit_stock_num = 0
        self.interesting_stocks = []
        self.nxt_list = []
        
    @abstractmethod
    def execute(self, config: Dict[str, Any]) -> None:
        """Execute the trading strategy"""
        pass
        
    def get_user_stock(self, after_market=False):
        """Get user's stock information"""
        logger.debug('주식정보 가져오기')
        self.user_stock_list = self.trading.get_user_stock(after_market)
        self.user_stock_num = len(self.user_stock_list)
        
    def get_user_credit_stock(self, after_market=False):
        """Get user's credit stock information"""
        logger.debug('신용주식정보 가져오기')
        self.user_credit_stock_list = self.trading.get_user_credit_stock(after_market)
        self.user_credit_stock_num = len(self.user_credit_stock_list)

    def _sell_all_stocks(self):
        """Sell all stocks in the given list according to configured sell rates"""
        logger.debug('>>>>>>>>>>> 일괄 매도 <<<<<<<<<<<')
        for stock in self.user_stock_list:
            if self.trading.exchange == 'NXT' and stock['code'] not in self.trading.nxt_list:
                continue
            remain = int(stock['available_num'])
            for i in range(len(self.trading.sell_earning_rate)):
                if self.trading.sell_earning_rate[i] == 0:
                    break
                if remain == 0:
                    break
                remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[i], remain,
                                                self.trading.sell_stock_amount[i])
            logger.debug("남은 주식 수 : {}".format(remain))

    def _sell_all_credit_stocks(self):
        logger.debug('>>>>>>>>>>> 일괄 신용 매도 <<<<<<<<<<<')
        for stock in self.trading.user_credit_stock_list:
            if self.trading.exchange == 'NXT' and stock['code'] not in self.trading.nxt_list:
                continue
            remain = int(stock['possession_num'])
            for i in range(len(self.trading.sell_credit_hoga)):
                if self.trading.sell_credit_hoga[i] == 0:
                    break
                if remain == 0:
                    break
                remain = self.trading.sell_manual_credit_stock(stock, self.trading.sell_credit_hoga[i], remain,
                                                int(stock['possession_num'])) # 전량 매도
            logger.debug("남은 주식 수 : {}".format(remain))


class AutoFullTradingStrategy(TradingStrategy):
    """Strategy for menu '0': 자동-전체 (신용일반 주식 매도)"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        # Get regular stock info
        self.get_user_stock()
        self._sell_all_stocks()

        # Get credit stock info
        self.get_user_credit_stock()
        self._sell_all_credit_stocks()



class AutoAveragingDownStrategy(TradingStrategy):
    """Strategy for menu '1': 자동-물타기-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_stock()
        logger.debug('>>>>>>>>>>> 일괄 매수 <<<<<<<<<<<')
        self.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
        logger.debug('물타기 제외 종목 들 : {}'.format(self.trading.except_rebuy_list))
        for i in range(len(self.user_stock_list)):
                    # 보유종목의 매입금액 + 새로 매수할 금액이 MAX_AMOUNT만원이 넘는지 확인해서 MAX_AMOUNT만원에 맞추기
            stock = self.user_stock_list[i]
            buy_amount = int(stock['buy_amount'])
            if buy_amount > self.trading.max_amount:
                logger.debug("------- 종목명 : {} 보유금액({}원)이 MAX 값({})보다 큽니다.".format(stock['name'], buy_amount,
                                                                                    trade.max_amount))
                continue
            if not self.user_stock_list[i]['name'] in self.trading.except_rebuy_list:
                self.trading.rebuy_user_stock(stock)
                self.trading.rebuy_1_stock(stock)
            else:
                logger.debug("물타기 제외 종목입니다 : {}".format(stock))


class AutoSellingStrategy(TradingStrategy):
    """Strategy for menu '2': 자동-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_stock()
        self._sell_all_stocks()

class AutoNewBuyingStrategy(TradingStrategy):
    """Strategy for menu '3': 자동-신규-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_stock()
        if self.trading.new_buy_stock:
            # 사용자 관심종목으로 부터 리스트 가져오기
            self.trading.get_interesting_stock()
            # 미체결 매수주문 정보 가져오기
            self.trading.get_not_done_order()
            # 미체결 매도주문 정보 가져오기
            #self.trading.get_not_done_sell()
            logger.debug('>>>>>>>>>>>> 신규 종목 매수 <<<<<<<<<<<<<<')
            self.trading.set_buy_stock_num()
            self.trading.buy_new_stock()

class ManualSellingStrategy(TradingStrategy):
    """Strategy for menu '4': 수동-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_stock()
        earning_rate = config.get('earning_rate')
        num = config.get('num')
        logger.debug('>>>>>>>>>>> 수동 매도 <<<<<<<<<<<')
        for stock in self.user_stock_list:
            remain = int(stock['available_num'])
            self.trading.sell_manual_stock(stock, earning_rate, remain, num)

class ManualAveragingDownStrategy(TradingStrategy):
    """Strategy for menu '5': 수동-물타기-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_stock()
        self.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
        logger.debug('물타기 제외 종목 들 : {}'.format(self.trading.except_rebuy_list))
        earning_rate = config.get('earning_rate')
        num = config.get('num')
        logger.debug('>>>>>>>>>>> 수동 매수 <<<<<<<<<<<')
        for i in range(len(self.user_stock_list)):
            # 보유종목의 매입금액 + 새로 매수할 금액이 MAX_AMOUNT만원이 넘는지 확인해서 MAX_AMOUNT만원에 맞추기
            stock = self.user_stock_list[i]
            buy_amount = int(stock['buy_amount'])
            if buy_amount > self.trading.max_amount:
                logger.debug("------- 종목명 : {} 보유금액({}원)이 MAX 값({})보다 큽니다.".format(stock['name'], buy_amount,
                                                                                    self.trading.max_amount))
                continue
            if not self.user_stock_list[i]['name'] in self.trading.except_rebuy_list:
                self.trading.rebuy_manual_stock(stock, earning_rate, num)
            else:
                logger.debug("물타기 제외 종목입니다 : {}".format(stock))

class AutoCreditSellingStrategy(TradingStrategy):
    """Strategy for menu '12': 자동-신용-주식-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_credit_stock()
        self._sell_all_credit_stocks()

class AutoCreditBuyingStrategy(TradingStrategy):
    """Strategy for menu '13': 자동-신용-주식-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.get_user_credit_stock()
        self.get_user_stock()
        logger.debug('>>>>>>>>>>>> 신규 신용 종목 매수 <<<<<<<<<<<<<<')
        self.trading.get_interesting_stock()
        self.trading.buy_new_credit_stock()
        sleep(0.5)

class AutoCreditAfterMarketStrategy(TradingStrategy):
    """Strategy for menu '16': 자동-신용일반-주식-시간외NXT-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        # After market credit stock selling
        self.get_user_credit_stock(after_market=True)
        logger.debug('>>>>>>>>>>> 일괄 신용 시간외 매도 <<<<<<<<<<<')
        for stock in self.trading.user_credit_stock_list:
            remain = int(stock['possession_num'])
            for i in range(len(self.trading.sell_credit_hoga_after_market)):
                if self.trading.sell_credit_hoga_after_market[i] == 0:
                    break
                if remain == 0:
                    break
                remain = self.trading.sell_manual_credit_stock(stock, self.trading.sell_credit_hoga_after_market[i], remain,
                                                int(stock['possession_num']), after_market=True)  # 전량 매도
            logger.debug("남은 주식 수 : {}".format(remain))
        
        # After market regular stock selling
        self.get_user_stock(after_market=True)
        logger.debug('>>>>>>>>>>> 일괄 시간외 매도 <<<<<<<<<<<')
        for stock in self.trading.user_stock_list:
            remain = int(stock['available_num'])
            logger.debug(remain)
            remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[0], remain,
                                            self.trading.sell_stock_amount[0], after_market=True)
            remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[1], remain,
                                            self.trading.sell_stock_amount[1], after_market=True)
            
        self.get_user_stock()
        self._sell_all_stocks()

        self.get_user_credit_stock()
        self._sell_all_credit_stocks()

class AutoCreditSellingLoopStrategy(TradingStrategy):
    """Strategy for menu '12-1': 자동-신용-주식-매도-무한반복"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        while True:
            self.get_user_credit_stock()
            self._sell_all_credit_stocks()
            logger.debug('>>>>>>>>>>> 매도 주문 완료, 다음 매도를 위해 대기중... <<<<<<<<<<<')
            sleep(self.trading.order_interval)

class TradingStrategyFactory:
    """Factory class to create appropriate trading strategy"""
    
    _strategies = {
        '0': AutoFullTradingStrategy,
        '1': AutoAveragingDownStrategy,
        '2': AutoSellingStrategy,
        '3': AutoNewBuyingStrategy,
        '4': ManualSellingStrategy,
        '5': ManualAveragingDownStrategy,
        '12': AutoCreditSellingStrategy,
        '12-1': AutoCreditSellingLoopStrategy,
        '13': AutoCreditBuyingStrategy,
        '16': AutoCreditAfterMarketStrategy
    }
    
    @classmethod
    def create_strategy(cls, menu_code: str, kiwoom: Kiwoom) -> TradingStrategy:
        strategy_class = cls._strategies.get(menu_code)
        if not strategy_class:
            raise ValueError(f"Invalid menu code: {menu_code}")
        return strategy_class(kiwoom) 