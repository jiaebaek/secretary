import json
import os

CONFIG_FILE = 'strategy_config.json'

def load_strategy_name(time_key: str):
    """
    주어진 시간대에 해당하는 전략 이름(들)을 불러온다.
    """
    if not os.path.exists(CONFIG_FILE):
        return None

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config.get(time_key)

def save_strategy_config(config: dict):
    """
    전략 설정을 strategy_config.json 파일에 저장한다.
    """
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)