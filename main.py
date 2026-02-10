import argparse

from telegram_bot import send_telegram_msg
from trading_strategy import TradingStrategyFactory
from utils import load_strategy_name
from strategy_definitions import STRATEGY_NAME_TO_CODE
from config import LOG_FILE_PATH
import logging
from logger import logger

def setup_logger_for_strategy(strategy_name):
    import re
    from datetime import datetime
    import os
    safe_strategy = re.sub(r'[\\/:*?"<>|]', '_', strategy_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file_path = os.path.join(LOG_FILE_PATH, f"{timestamp}_{safe_strategy}.log")
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    file_handler.setFormatter(formatter)
    logger.handlers = []  # 기존 핸들러 제거
    logger.addHandler(file_handler)
    # (선택) 콘솔 핸들러도 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, help="전략 이름 (단일 실행용)")
    parser.add_argument("--time", type=str, help="등록된 시간대 실행용")
    args = parser.parse_args()

    if args.name:
        setup_logger_for_strategy(args.name)
        menu_code = STRATEGY_NAME_TO_CODE.get(args.name)
        strategy = TradingStrategyFactory.create_strategy(menu_code)
        strategy.execute({})
        return

    if args.time:
        strategy_names = load_strategy_name(args.time)
        if not strategy_names:
            logger.error(f"{args.time}에 등록된 전략이 없습니다.")
            return

        if isinstance(strategy_names, str):
            strategy_names = [strategy_names]

        for strategy_name in strategy_names:
            setup_logger_for_strategy(strategy_name)
            menu_code = STRATEGY_NAME_TO_CODE.get(strategy_name)
            if not menu_code:
                logger.warning(f"전략명 '{strategy_name}'에 해당하는 코드가 없습니다.")
                continue
            try:
                msg = f"[{strategy_name}] 시작"
                send_telegram_msg(msg)  # 텔레그램 발송 추가
                strategy = TradingStrategyFactory.create_strategy(menu_code)
                strategy.execute({'trading_time': args.time})
                msg = f"[{strategy_name}] 실행 완료"
                logger.info(msg)
                send_telegram_msg(msg)  # 텔레그램 발송 추가
            except Exception as e:
                err_msg = f"[{strategy_name}] 실행 중 예외 발생: {e}"
                logger.exception(err_msg)
                send_telegram_msg(err_msg)  # 텔레그램 발송 추가
                continue

if __name__ == '__main__':
    main()
    