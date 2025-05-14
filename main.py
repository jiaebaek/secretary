from time import sleep
import sys
from PyQt5.QtWidgets import *
import os
from logger import LOG_FILE, logger
import logging.handlers
import datetime
from trading_strategy import TradingStrategyFactory
from config import KAKAOTALK_PATH


menu = {
    '0': "자동-전체 (신용일반 주식 매도)",
    '1': "자동-물타기-매수",
    '2': "자동-매도",
    '3': "자동-신규-매수",
    '4': "수동-매도",
    '5': "수동-물타기-매수",
    '12': "자동-신용-주식-매도",
    '12-1': "자동-신용-주식-매도-무한반복",
    '13': "자동-신용-주식-매수",
    '16': "자동-신용일반-주식-시간외NXT-매도"
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

def check_trading_time(trading_time, weekday, is_test=False):
    if is_test:
        return
    if trading_time == 'normal':
        if weekday in range(0, 5):
            now = datetime.datetime.now()
            now_tupule = now.timetuple()
            logger.debug(now_tupule)
            while now_tupule.tm_hour < 8:
                sleep(60)
                now = datetime.datetime.now()
                now_tupule = now.timetuple()
                logger.debug(now_tupule)
            if now_tupule.tm_hour > 17:
                logger.debug("장이 마감되었습니다.")
                exit(0)
        else:
            exit(0)
    elif trading_time == 'after_market':
        if weekday in range(0, 5):
            now = datetime.datetime.now()
            now_tupule = now.timetuple()
            logger.debug(now_tupule)
            while now_tupule.tm_hour < 16:
                sleep(60)
                now = datetime.datetime.now()
                now_tupule = now.timetuple()
                logger.debug(now_tupule)
            if now_tupule.tm_hour > 18:
                logger.debug("시간외 장이 마감되었습니다.")
                exit(0)
        else:
            exit(0)

if __name__ == "__main__":
    # Parse command line arguments
    menu_code = sys.argv[1]
    trading_time = sys.argv[2]  # normal or after_market or test
    menu_name = menu[menu_code]
    
    is_test = True if trading_time == 'test' else False
    # Setup logging
    setup_logging(menu_name, is_test)
    
    # Check if it's trading hours
    weekday = datetime.datetime.today().weekday()
    logger.debug(weekday)
    check_trading_time(trading_time, weekday)
    
    logger.debug('거래 시작')
    
    # Initialize PyQt application
    app = QApplication(sys.argv)
    
    try:
        # Create appropriate trading strategy
        strategy = TradingStrategyFactory.create_strategy(menu_code)
        
        # Create config dictionary based on command line arguments
        config = {
            'trading_time': trading_time
        }
        
        # Add manual trading parameters if needed
        if menu_code in ['4', '5']:
            config['earning_rate'] = sys.argv[3].strip('%')
            config['num'] = sys.argv[4].strip('ea')
        
        # Execute trading strategy
        strategy.execute(config)
    except Exception as err:
        logger.exception(err)
    
    logger.debug("완료!")
    
    # Cleanup tasks for certain menu codes
    if menu_code in ['0', '1', '2', '3', '12', '16']:
        os.system("taskkill /im KaKaoTalk.exe")
        os.system(KAKAOTALK_PATH)


