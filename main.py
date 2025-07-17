from time import sleep
import sys
import logging

from config import LOGO_PATH
from logger import LOG_FILE, logger
import logging.handlers
import datetime
from trading_strategy import TradingStrategyFactory


menu = {
    '0': "장중-신용현금-매도",
    '1': "자동-물타기-매수",
    '2': "장중-현금-매도",
    '3': "장중-현금-신규-매수",
    '4': "수동-매도",
    '5': "수동-물타기-매수",
    '7': "시간외-현금-매도",
    '12': "장중-신용-매도",
    '12-1': "장중-신용-매도-무한반복",
    '13': "장중-신용-신규매수",
    '16': "시간외NXT-신용현금-매도",
    '17': "시간외-신용-매도",
    '22': "시간외-신용현금-매도",
    '18': "장마감-신용-매도",
    '30': "미체결-현금매도-주문-취소",
    '31': "미체결-신용매도-주문-취소"
}

def setup_logging(menu_name, test=False):
    formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    
    test_log_filename = LOG_FILE+'{}_{}_test.txt'.format(datetime.datetime.now().strftime('%Y-%m-%d'), menu_name)
    log_filename = LOG_FILE + '{}_{}.txt'.format(datetime.datetime.now().strftime('%Y-%m-%d'), menu_name)
    
    if test:
        fileHandler = logging.FileHandler(test_log_filename)
    else:
        fileHandler = logging.FileHandler(log_filename)
    streamHandler = logging.StreamHandler()

    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)

    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)

if __name__ == "__main__":
    # Parse command line arguments
    menu_code = sys.argv[1]
    trading_time = sys.argv[2]  # normal or after_market or test
    menu_name = menu[menu_code]
    is_test = True if trading_time == 'test' else False

    setup_logging(menu_name, is_test)

    logger.debug('거래 시작')

    try:
        # Create appropriate trading strategy
        strategy = TradingStrategyFactory.create_strategy(menu_code)
        # Create config dictionary based on command line arguments
        config = {
            'trading_time': trading_time,
        }
        # Add manual trading parameters if needed
        if menu_code in ['4', '5']:
            config['earning_rate'] = sys.argv[3].strip('%')
            config['num'] = sys.argv[4].strip('ea')
        # Execute trading strategy
        strategy.execute(config)
        logger.info("Trading completed")
    except Exception as err:
        logger.exception(err)
        logger.info("Error occurred")

    logger.debug("완료!")

