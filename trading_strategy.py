from abc import ABC, abstractmethod
from typing import Dict, Any
from logger import logger
from time import sleep
from trading_core import Trading
import random

class TradingStrategy(ABC):
    """Base abstract class for all trading strategies"""
    
    def __init__(self):
        self.trading = Trading()  # Create Trading instance
        self.trading.update_options()  # Update trading options at initialization
        self.trading.set_exchange()  # Set exchange type at initialization
        self.user_stock_list = []
        self.user_stock_num = 0
        self.user_credit_stock_list = []
        self.user_credit_stock_num = 0
        self.log_window = None
        
    @abstractmethod
    def execute(self, config: Dict[str, Any]) -> None:
        """Execute the trading strategy"""
        self.log_window = config.get('log_window')
        pass
        
    def get_user_stock(self, after_market=False):
        """Get user's stock information"""
        logger.debug('주식정보 가져오기')
        self.user_stock_list = self.trading.get_user_stock(after_market)
        if not self.user_stock_list:
            raise Exception('주식 보유 없음')

        self.user_stock_num = len(self.user_stock_list)
        
    def get_user_credit_stock(self, after_market=False):
        """Get user's credit stock information"""
        logger.debug('신용주식정보 가져오기')
        self.user_credit_stock_list = self.trading.get_user_credit_stock(after_market)
        if not self.user_credit_stock_list:
            raise Exception('주식 보유 없음')
        self.user_credit_stock_num = len(self.user_credit_stock_list)

    def _sell_all_stocks(self):
        """Sell all stocks in the given list according to configured sell rates"""
        logger.debug('>>>>>>>>>>> 현금주식 매도 <<<<<<<<<<<')
        total_stocks = len(self.user_stock_list)
        completed = 0
        for stock in self.user_stock_list:
            if self.trading.exchange == 'NXT' and not self.trading.is_nxt_available(stock['code']):
                continue
            remain = int(stock['available_num'])
            for i in range(len(self.trading.sell_earning_rate)):
                if self.trading.sell_earning_rate[i] == 0:
                    break
                if remain == 0:
                    break
                remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[i], remain,
                                                self.trading.sell_stock_amount[i])
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)
            logger.debug("남은 주식 수 : {}".format(remain))

    def _sell_all_credit_stocks(self):
        logger.debug('>>>>>>>>>>> 신용주식 매도 <<<<<<<<<<<')
        total_stocks = len(self.user_credit_stock_list)
        completed = 0
        for stock in self.user_credit_stock_list:
            if self.trading.exchange == 'NXT' and not self.trading.is_nxt_available(stock['code']):
                continue
            remain = int(stock['possession_num'])
            for i in range(len(self.trading.sell_credit_earning_rate)):
                logger.debug(f"len : {len(self.trading.sell_credit_earning_rate)}")
                if self.trading.sell_credit_earning_rate[i] == 0:
                    break
                if remain == 0:
                    break
                    # 호가 대신 수익률로 매도
                remain = self.trading.sell_user_credit_stock(stock, self.trading.sell_credit_earning_rate[i], remain,
                                                             self.trading.sell_credit_stock_amount[i], after_market=False)
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)
            logger.debug("남은 주식 수 : {}".format(remain))

    def _sell_all_credit_stocks_finish_market(self):
        logger.debug('>>>>>>>>>>> 신용주식 매도 (장마감전 정리용) <<<<<<<<<<<')
        total_stocks = len(self.user_credit_stock_list)
        completed = 0
        for stock in self.user_credit_stock_list:
            if self.trading.exchange == 'NXT' and stock['code'] not in self.trading.nxt_list:
                continue
            remain = int(stock['possession_num'])
            for i in range(len(self.trading.sell_credit_earning_rate_finish_market)):
                logger.debug(f"len : {len(self.trading.sell_credit_earning_rate_finish_market)}")
                if self.trading.sell_credit_earning_rate_finish_market[i] == 0:
                    break
                if remain == 0:
                    break
                    # 호가 대신 수익률로 매도
                remain = self.trading.sell_user_credit_stock(stock, self.trading.sell_credit_earning_rate_finish_market[i], remain,
                                                             self.trading.sell_credit_stock_amount_finish_market[i], after_market=False)
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)
            logger.debug("남은 주식 수 : {}".format(remain))

    def _sell_all_stocks_after_market(self):
        """Sell all stocks in the given list according to configured sell rates"""
        logger.debug('>>>>>>>>>>> 현금주식 시간외 매도 <<<<<<<<<<<')
        total_stocks = len(self.user_stock_list)
        completed = 0
        
        for stock in self.user_stock_list:
            remain = int(stock['available_num'])
            remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[0], remain,
                                            self.trading.sell_stock_amount[0], after_market=True)
            remain = self.trading.sell_user_stock(stock, self.trading.sell_earning_rate[1], remain,
                                            self.trading.sell_stock_amount[1], after_market=True)
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)
            logger.debug("남은 주식 수 : {}".format(remain))
        
    def _sell_all_credit_stocks_after_market(self):
        """Sell all credit stocks in the given list according to configured sell rates"""
        logger.debug('>>>>>>>>>>> 신용주식 시간외 매도 <<<<<<<<<<<')
        total_credit_stocks = len(self.user_credit_stock_list)
        completed_credit = 0
        
        for stock in self.user_credit_stock_list:
            remain = int(stock['possession_num'])
            for i in range(len(self.trading.sell_credit_earninig_rate_after_market)):
                if self.trading.sell_credit_earninig_rate_after_market[i] == 0:
                    break
                if remain == 0:
                    break
                # 호가 대신 수익률로 매도
                remain = self.trading.sell_user_credit_stock(stock, self.trading.sell_credit_earninig_rate_after_market[i], remain,
                                                             self.trading.sell_credit_stock_amount_after_market[i], after_market=True)
            completed_credit += 1
            if self.log_window:
                self.log_window.update_progress(completed_credit, total_credit_stocks)

    def _cancel_sell_order(self):
        logger.debug('>>>>>>>>>>> 미체결 현금매도 주문 취소 <<<<<<<<<<<')
        self.trading.get_not_done_sell()
        for order in self.trading.not_done_sell:
            if "신용" not in order['type']:
                logger.debug(f"미체결 주문 : {order['name']} / {order['order_num']}")
                self.trading.cancel_not_done_sell_order(order)

    def _cancel_credit_sell_order(self):
        logger.debug('>>>>>>>>>>> 미체결 신용매도 주문 취소 <<<<<<<<<<<')
        self.trading.get_not_done_sell()
        for order in self.trading.not_done_sell:
            if "신용" in order['type']:
                logger.debug(f"미체결 신용매도주문 : {order['name']} / {order['order_num']}")
                self.trading.cancel_not_done_credit_sell_order(order)
    

class AutoBothSellingStrategy(TradingStrategy):
    """Strategy for menu '0': 자동-전체 (신용일반 주식 매도)"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        
        # Get regular stock info and sell
        self.get_user_stock()
        self._sell_all_stocks()

        # Get credit stock info
        self.get_user_credit_stock()
        self._sell_all_credit_stocks()


class AutoAveragingDownStrategy(TradingStrategy):
    """Strategy for menu '1': 자동-물타기-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_stock()
        logger.debug('>>>>>>>>>>> 현금주식 추가 매수 <<<<<<<<<<<')
        self.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
        logger.debug('물타기 제외 종목 들 : {}'.format(self.trading.except_rebuy_list))
        
        total_stocks = len(self.user_stock_list)
        completed = 0
        
        for i in range(len(self.user_stock_list)):
            stock = self.user_stock_list[i]
            buy_amount = int(stock['buy_amount'])
            if buy_amount > self.trading.max_amount:
                logger.debug("------- 종목명 : {} 보유금액({}원)이 MAX 값({})보다 큽니다.".format(stock['name'], buy_amount,
                                                                                    self.trading.max_amount))
                continue
            if not self.user_stock_list[i]['name'] in self.trading.except_rebuy_list:
                self.trading.rebuy_user_stock(stock)
                self.trading.rebuy_1_stock(stock)
            else:
                logger.debug("물타기 제외 종목입니다 : {}".format(stock))
            
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)


class AutoSellingStrategy(TradingStrategy):
    """Strategy for menu '2': 자동-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_stock()
        self._sell_all_stocks()


class AutoNewBuyingStrategy(TradingStrategy):
    """Strategy for menu '3': 자동-신규-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_stock()
        if self.trading.new_buy_stock:
            self.trading.get_interesting_stock()
            self.trading.get_not_done_order()
            
            logger.debug('>>>>>>>>>>>> 현금주식 신규 매수 <<<<<<<<<<<<<<')
            self.trading.set_buy_stock_num()
            self.trading.buy_new_stock()


class ManualSellingStrategy(TradingStrategy):
    """Strategy for menu '4': 수동-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_stock()
        earning_rate = config.get('earning_rate')
        num = config.get('num')
        logger.debug('>>>>>>>>>>> 수동 설정 현금주식 매도 <<<<<<<<<<<')
        total_stocks = len(self.user_stock_list)
        completed = 0
        
        for stock in self.user_stock_list:
            remain = int(stock['available_num'])
            self.trading.sell_manual_stock(stock, earning_rate, remain, num)
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)


class ManualAveragingDownStrategy(TradingStrategy):
    """Strategy for menu '5': 수동-물타기-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_stock()
        self.user_stock_list.sort(key=lambda stock: float(stock["earning_rate"]))
        logger.debug('물타기 제외 종목 들 : {}'.format(self.trading.except_rebuy_list))
        earning_rate = config.get('earning_rate')
        num = config.get('num')
        logger.debug('>>>>>>>>>>> 수동 설정 현금주식 물타기 매수 <<<<<<<<<<<')
        total_stocks = len(self.user_stock_list)
        completed = 0
        
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
            completed += 1
            if self.log_window:
                self.log_window.update_progress(completed, total_stocks)


class AutoCreditSellingStrategy(TradingStrategy):
    """Strategy for menu '12': 자동-신용-주식-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_credit_stock()
        self._sell_all_credit_stocks()


class AutoCreditBuyingStrategy(TradingStrategy):
    """Strategy for menu '13': 자동-신용-주식-매수"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_credit_stock()
        self.get_user_stock()
        
        logger.debug('>>>>>>>>>>>> 신용주식 신규 매수 <<<<<<<<<<<<<<')
        self.trading.get_interesting_stock()
        self.trading.buy_new_credit_stock()


class AutoAfterMarketNXTTradingStrategy(TradingStrategy):
    """Strategy for menu '16': 자동-신용일반-주식-시간외NXT-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        
        # After market credit stock selling
        self.get_user_credit_stock(after_market=True)
        self._sell_all_credit_stocks_after_market()
        
        # After market regular stock selling
        self.get_user_stock(after_market=True)
        self._sell_all_stocks_after_market()

        self.get_user_stock()
        self._sell_all_stocks()

        self.get_user_credit_stock()
        self._sell_all_credit_stocks()


class AutoCreditAfterMarketStrategy(TradingStrategy):
    """Strategy for menu '17': 자동-신용-주식-시간외-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        
        # After market credit stock selling
        self.get_user_credit_stock(after_market=True)
        self._sell_all_credit_stocks_after_market()


class AutoCreditBeforeFinishMarketSellingStrategy(TradingStrategy):
    """Strategy for menu '18': 자동-신용-주식-장마감전-매도"""

    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self.get_user_credit_stock()
        self._sell_all_credit_stocks_finish_market()

class AutoAfterMarketStrategy(TradingStrategy):
    """Strategy for menu '7': 자동-일반-주식-시간외-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')

        # After market regular stock selling
        self.get_user_stock(after_market=True)
        self._sell_all_stocks_after_market()


class AutoBothAfterMarketStrategy(TradingStrategy):
    """Strategy for menu '22': 자동-일반-신용-주식-시간외-매도"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')

        # After market credit stock selling
        self.get_user_credit_stock(after_market=True)
        self._sell_all_credit_stocks_after_market()
        
        # After market regular stock selling
        self.get_user_stock(after_market=True)
        self._sell_all_stocks_after_market()


class AutoCreditSellingLoopStrategy(TradingStrategy):
    """Strategy for menu '12-1': 자동-신용-주식-매도-무한반복"""
    
    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        while True:
            self.get_user_credit_stock()
            self._sell_all_credit_stocks()
            logger.debug('>>>>>>>>>>> 신용주식 매도 주문 완료, 다음 매도를 위해 대기중... <<<<<<<<<<<')


class CancelSellOrderStrategy(TradingStrategy):
    """Strategy for menu '30': 미체결 현금매도주문 취소"""

    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self._cancel_sell_order()

class CancelCreditSellOrderStrategy(TradingStrategy):
    """Strategy for menu '31': 미체결 신용매도주문 취소"""

    def execute(self, config: Dict[str, Any]) -> None:
        self.log_window = config.get('log_window')
        self._cancel_credit_sell_order()


class TradingStrategyFactory:
    """Factory class to create appropriate trading strategy"""
    
    _strategies = {
        '0': AutoBothSellingStrategy,
        '1': AutoAveragingDownStrategy,
        '2': AutoSellingStrategy,
        '3': AutoNewBuyingStrategy,
        '4': ManualSellingStrategy,
        '5': ManualAveragingDownStrategy,
        '7': AutoAfterMarketStrategy,
        '12': AutoCreditSellingStrategy,
        '12-1': AutoCreditSellingLoopStrategy,
        '13': AutoCreditBuyingStrategy,
        '16': AutoAfterMarketNXTTradingStrategy,
        '17': AutoCreditAfterMarketStrategy,
        '18': AutoCreditBeforeFinishMarketSellingStrategy,
        '22': AutoBothAfterMarketStrategy,
        '30': CancelSellOrderStrategy,
        '31': CancelCreditSellOrderStrategy
    }
    
    @classmethod
    def create_strategy(cls, menu_code: str) -> TradingStrategy:
        strategy_class = cls._strategies.get(menu_code)
        if not strategy_class:
            raise ValueError(f"Invalid menu code: {menu_code}")
        return strategy_class() 