# telegram_bot.py
import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from logger import logger

def send_telegram_msg(message):
    """텔레그램으로 메세지를 전송합니다."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"[주식비서 알림]\n{message}"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"텔레그램 전송 실패: {response.text}")
    except Exception as e:
        logger.error(f"텔레그램 통신 에러: {e}")
