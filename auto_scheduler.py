import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import platform
from datetime import datetime

from telegram_bot import send_telegram_msg
from config import DB_PATH


AUTO_CONFIG_FILE_DEFAULT = "auto_strategy_config.json"


class AutoModeScheduler:
    """
    오토모드 전담 스케줄러:
    - auto_strategy_config.json 설정을 읽어
    - 전략 묶음을 순차 실행
    - 전략 프로세스 exit_code != 0 이면 해당 전략만 성공할 때까지 재시도
    - [start, end) 시간이 끝나면 새 전략 시작을 중단하고, 현재 실행 중인 프로세스가 끝날 때까지 기다린 뒤 종료
    - 종료 후 DB flag `auto_mode_active`를 0으로 내림
    """

    FLAG_KEY = "auto_mode_active"

    def __init__(self, auto_config_path: str, poll_interval_sec: int = 10):
        self.auto_config_path = auto_config_path
        self.poll_interval_sec = poll_interval_sec
        self.system = platform.system()
        self.current_dir = os.getcwd()
        self.ensure_scheduler_flags_table()

    def ensure_scheduler_flags_table(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduler_flags (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def set_flag_int(self, key: str, value: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO scheduler_flags (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, int(value), now_str),
        )
        conn.commit()
        conn.close()

    def load_auto_config(self) -> dict:
        try:
            if not os.path.exists(self.auto_config_path):
                return {"auto_mode_enabled": False, "auto_groups": []}
            with open(self.auto_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            msg = f"[AutoScheduler] auto config load 실패: {e}"
            print(msg)
            self.log_to_scheduler(msg)
            return {"auto_mode_enabled": False, "auto_groups": []}

    def log_to_scheduler(self, message: str):
        # 기존 scheduler가 이미 logs/에 적고 있으니 같은 디렉토리 사용
        if not os.path.exists("logs"):
            os.makedirs("logs")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.now().strftime("%Y%m%d")
        log_path = os.path.join("logs", f"auto_scheduler_{date_str}.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] {message}\n")

    def _parse_hhmm(self, hhmm: str) -> int:
        parts = (hhmm or "").split(":")
        if len(parts) != 2:
            raise ValueError(f"invalid time format: {hhmm}")
        hh = int(parts[0])
        mm = int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError(f"invalid time value: {hhmm}")
        return hh * 60 + mm

    def is_time_in_window(self, now_dt: datetime, start_hhmm: str, end_hhmm: str) -> bool:
        """
        [start, end) 기준 판정.
        - end 시간에 도달하면 새 시도는 시작하지 않음.
        """
        start_m = self._parse_hhmm(start_hhmm)
        end_m = self._parse_hhmm(end_hhmm)
        now_m = now_dt.hour * 60 + now_dt.minute

        if start_m <= end_m:
            return start_m <= now_m < end_m
        return now_m >= start_m or now_m < end_m

    def get_active_auto_group(self, auto_cfg: dict, now_dt: datetime):
        groups = auto_cfg.get("auto_groups") or []
        for group in groups:
            start = group.get("start")
            end = group.get("end")
            if not start or not end:
                continue
            try:
                if self.is_time_in_window(now_dt, start, end):
                    return group
            except Exception:
                continue
        return None

    def spawn_strategy_by_name(self, strategy_name: str) -> subprocess.Popen:
        """
        오토모드 전담 프로세스가 가진 콘솔을 그대로 상속하도록,
        Windows에서도 CREATE_NEW_CONSOLE를 사용하지 않습니다.
        """
        args = [sys.executable, "main.py", "--name", strategy_name]
        env = os.environ.copy()
        return subprocess.Popen(args, cwd=self.current_dir, env=env)

    def run_auto_group(self, group: dict):
        group_name = group.get("group_name") or "auto_group"
        start_hhmm = group.get("start")
        end_hhmm = group.get("end")
        retry_interval_sec = int(group.get("retry_interval_sec") or 10)

        strategies = group.get("strategies") or []
        if isinstance(strategies, str):
            strategies = [strategies]

        start_msg = f"[AutoScheduler:{group_name}] 시작 (구간 {start_hhmm} ~ {end_hhmm}, 전략수={len(strategies)})"
        print(start_msg)
        self.log_to_scheduler(start_msg)
        send_telegram_msg(start_msg)

        self.set_flag_int(self.FLAG_KEY, 1)
        try:
            while True:
                auto_cfg = self.load_auto_config()
                if not auto_cfg.get("auto_mode_enabled", False):
                    return

                now_dt = datetime.now()
                if not self.is_time_in_window(now_dt, start_hhmm, end_hhmm):
                    return

                for strategy_name in strategies:
                    # 전략 단위 재시도: 성공(exit_code==0)할 때까지 반복
                    while True:
                        auto_cfg = self.load_auto_config()
                        if not auto_cfg.get("auto_mode_enabled", False):
                            return
                        now_dt = datetime.now()
                        if not self.is_time_in_window(now_dt, start_hhmm, end_hhmm):
                            return

                        run_msg = f"[AutoScheduler:{group_name}] 전략 실행: {strategy_name}"
                        print(run_msg)
                        self.log_to_scheduler(run_msg)

                        rc = -1
                        proc = None
                        try:
                            proc = self.spawn_strategy_by_name(strategy_name)
                            rc = proc.wait()
                        except Exception as e:
                            self.log_to_scheduler(
                                f"[AutoScheduler:{group_name}] 전략 실행 예외: {strategy_name}, err={e}"
                            )
                            rc = -1

                        # 프로세스가 끝났을 때 상태 재확인
                        auto_cfg = self.load_auto_config()
                        now_dt = datetime.now()
                        if (not auto_cfg.get("auto_mode_enabled", False)) or (
                            not self.is_time_in_window(now_dt, start_hhmm, end_hhmm)
                        ):
                            return

                        if rc == 0:
                            # 다음 전략으로 이동
                            break

                        fail_msg = (
                            f"[AutoScheduler:{group_name}] 전략 에러 종료(exit_code={rc}): {strategy_name} -> "
                            f"{retry_interval_sec}초 후 재시도"
                        )
                        print(fail_msg)
                        self.log_to_scheduler(fail_msg)
                        send_telegram_msg(fail_msg)
                        time.sleep(retry_interval_sec)

                # 묶음 성공 -> 다시 처음부터 반복
                repeat_msg = f"[AutoScheduler:{group_name}] 묶음 성공 -> 다시 처음부터 반복"
                print(repeat_msg)
                self.log_to_scheduler(repeat_msg)

        finally:
            end_msg = f"[AutoScheduler:{group_name}] 종료"
            print(end_msg)
            self.log_to_scheduler(end_msg)
            send_telegram_msg(end_msg)
            self.set_flag_int(self.FLAG_KEY, 0)

    def run_forever(self):
        while True:
            auto_cfg = self.load_auto_config()
            if not auto_cfg.get("auto_mode_enabled", False):
                # 오토모드가 꺼져있으면, 혹시 남아있던 active 플래그가 있더라도 0으로 정리
                self.set_flag_int(self.FLAG_KEY, 0)
                time.sleep(self.poll_interval_sec)
                continue

            now_dt = datetime.now()
            active_group = self.get_active_auto_group(auto_cfg, now_dt)
            if active_group is None:
                time.sleep(self.poll_interval_sec)
                continue

            # 여기 도달하면 active group이므로 실행 시작(블로킹)
            self.run_auto_group(active_group)
            # run_auto_group이 종료되면 active 플래그는 0으로 내려가 있음.
            time.sleep(self.poll_interval_sec)


def main():
    parser = argparse.ArgumentParser(description="오토모드 전용 스케줄러")
    parser.add_argument("--auto_config", type=str, default=AUTO_CONFIG_FILE_DEFAULT)
    parser.add_argument("--poll", type=int, default=10, help="자동 스케줄러 폴링 간격(초)")
    args = parser.parse_args()

    scheduler = AutoModeScheduler(auto_config_path=args.auto_config, poll_interval_sec=args.poll)
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        print("\n[AutoScheduler] 종료됨")


if __name__ == "__main__":
    main()

