import json
import subprocess
import time
from datetime import datetime
import os
import platform
import threading
import sys
import sqlite3

from telegram_bot import send_telegram_msg
from config import DB_PATH


class StrategyScheduler:
    def __init__(
            self,
            config_path='strategy_config.json',
            terminal_mode=False,
            auto_config_path='auto_strategy_config.json',
    ):
        self.config_path = config_path
        self.terminal_mode = terminal_mode  # 터미널 모드 설정
        self.auto_config_path = auto_config_path
        self.system = platform.system()
        self.current_dir = os.getcwd()
        self.load_config()
        self.executed = set()
        self.auto_thread = None
        self.auto_thread_lock = threading.Lock()

        self.ensure_scheduler_flags_table()

    def ensure_scheduler_flags_table(self):
        """
        오토모드 활성 여부 같은 상태를 DB로 공유하기 위한 테이블.
        """
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

    def get_flag_int(self, key: str, default: int = 0) -> int:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT value FROM scheduler_flags WHERE key = ?", (key,))
            row = cur.fetchone()
            conn.close()
            if row is None:
                return default
            return int(row[0])
        except Exception:
            # DB 장애 시 기본값으로 fallback
            return default

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {}

    def load_auto_config(self):
        try:
            if not os.path.exists(self.auto_config_path):
                return {'auto_mode_enabled': False, 'auto_groups': []}
            with open(self.auto_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            err_msg = f'오토모드 설정 로드 실패: {e}'
            print(f'[Scheduler] {err_msg}')
            self.log_scheduler_event(err_msg)
            return {'auto_mode_enabled': False, 'auto_groups': []}

    def _parse_hhmm(self, hhmm: str) -> int:
        parts = (hhmm or '').split(':')
        if len(parts) != 2:
            raise ValueError(f'invalid time format: {hhmm}')
        hh = int(parts[0])
        mm = int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError(f'invalid time value: {hhmm}')
        return hh * 60 + mm

    def is_time_in_window(self, now_dt: datetime, start_hhmm: str, end_hhmm: str) -> bool:
        """
        [start, end) 기준으로 오토그룹 시간구간 판정.
        """
        start_m = self._parse_hhmm(start_hhmm)
        end_m = self._parse_hhmm(end_hhmm)
        now_m = now_dt.hour * 60 + now_dt.minute

        if start_m <= end_m:
            return start_m <= now_m < end_m
        # 자정을 넘기는 구간
        return now_m >= start_m or now_m < end_m

    def get_active_auto_group(self, auto_cfg: dict, now_dt: datetime):
        groups = auto_cfg.get('auto_groups') or []
        for group in groups:
            start = group.get('start')
            end = group.get('end')
            if not start or not end:
                continue
            try:
                if self.is_time_in_window(now_dt, start, end):
                    return group
            except Exception:
                continue
        return None

    def log_scheduler_event(self, message):
        if not os.path.exists('logs'):
            os.makedirs('logs')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_str = datetime.now().strftime('%Y%m%d')
        log_path = os.path.join('logs', f'scheduler_{date_str}.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'[{now}] {message}\n')

    def execute_strategy_in_terminal(self, time_key, strategy_names):
        """터미널에서 전략 실행"""
        try:
            # 여러 전략이 있을 수 있으므로 모든 전략을 하나의 터미널에서 실행
            strategies_str = ' '.join(strategy_names)
            current_dir = os.getcwd()
            
            if self.system == "Windows":
                # Windows에서 새 cmd 창 열기
                cmd = f'start "스케줄 실행: {time_key}" cmd /k "cd /d {current_dir} && python main.py --time {time_key} & echo. & echo 전략 실행 완료! & pause"'
                os.system(cmd)
                
            elif self.system == "Darwin":  # macOS
                # macOS에서 터미널 열기
                script = f'''
                tell application "Terminal"
                    do script "cd '{current_dir}' && python main.py --time {time_key} && echo '전략 실행 완료!' && read -p 'Press Enter to close...'"
                    activate
                end tell
                '''
                subprocess.run(["osascript", "-e", script])
                
            elif self.system == "Linux":
                # Linux에서 터미널 열기
                try:
                    subprocess.Popen([
                        "gnome-terminal", "--title", f"스케줄 실행: {time_key}",
                        "--", "bash", "-c", 
                        f"cd '{current_dir}' && python main.py --time {time_key} && echo '전략 실행 완료!' && read -p 'Press Enter to close...'"
                    ])
                except FileNotFoundError:
                    # gnome-terminal이 없으면 xterm 시도
                    subprocess.Popen([
                        "xterm", "-title", f"스케줄 실행: {time_key}",
                        "-e", f"cd '{current_dir}' && python main.py --time {time_key} && echo '전략 실행 완료!' && read -p 'Press Enter to close...'"
                    ])
            
            return True
            
        except Exception as e:
            err_msg = f'터미널 실행 실패: {e}'
            print(f'[Scheduler] {err_msg}')
            self.log_scheduler_event(err_msg)
            return False

    def execute_strategy_background(self, time_key):
        """백그라운드에서 전략 실행 (기존 방식)"""
        try:
            subprocess.Popen([
                'python', 'main.py', '--time', time_key
            ], env=os.environ.copy())
            return True
        except Exception as e:
            err_msg = f'백그라운드 실행 실패: {e}'
            print(f'[Scheduler] {err_msg}')
            self.log_scheduler_event(err_msg)
            return False

    def spawn_strategy_by_name(self, strategy_name: str) -> subprocess.Popen:
        """
        `python main.py --name <strategy_name>` 실행 (exit code로 성공/실패 판별).
        """
        args = [sys.executable, 'main.py', '--name', strategy_name]
        env = os.environ.copy()

        if self.system == 'Windows':
            # 새 콘솔 창에서 실행(사용자가 진행상황을 볼 수 있게)
            return subprocess.Popen(
                args,
                cwd=self.current_dir,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        return subprocess.Popen(args, cwd=self.current_dir, env=env)

    def run_auto_group(self, group: dict):
        """
        오토모드 그룹 실행:
        - 전략(설정된 순서)을 순차 실행
        - exit code != 0 이면 해당 전략만 재시도(성공할 때까지)
        - 시간구간 종료 시: 새 전략 시작은 중단하고, 현재 실행 중 프로세스가 끝날 때까지 기다린 뒤 종료
        - UI에서 `auto_mode_enabled`를 off로 바꾸면: 현재 실행 중 전략이 끝날 때까지 기다린 뒤 종료
        """
        group_name = group.get('group_name') or 'auto_group'
        start_hhmm = group.get('start')
        end_hhmm = group.get('end')
        retry_interval_sec = int(group.get('retry_interval_sec') or 10)

        strategies = group.get('strategies') or []
        if isinstance(strategies, str):
            strategies = [strategies]

        msg = f'[오토모드:{group_name}] 시작 (구간 {start_hhmm} ~ {end_hhmm}, 전략수={len(strategies)})'
        print(f'[Scheduler] {msg}')
        self.log_scheduler_event(msg)
        send_telegram_msg(msg)

        try:
            while True:
                auto_cfg = self.load_auto_config()
                if not auto_cfg.get('auto_mode_enabled', False):
                    return

                now_dt = datetime.now()
                if not self.is_time_in_window(now_dt, start_hhmm, end_hhmm):
                    return

                for strategy_name in strategies:
                    # 전략 단위 재시도(성공(exit_code==0)할 때까지)
                    while True:
                        auto_cfg = self.load_auto_config()
                        if not auto_cfg.get('auto_mode_enabled', False):
                            return

                        now_dt = datetime.now()
                        if not self.is_time_in_window(now_dt, start_hhmm, end_hhmm):
                            return

                        start_msg = f'[오토모드:{group_name}] 전략 실행: {strategy_name}'
                        print(f'[Scheduler] {start_msg}')
                        self.log_scheduler_event(start_msg)

                        rc = -1
                        try:
                            proc = self.spawn_strategy_by_name(strategy_name)
                            rc = proc.wait()
                        except Exception as e:
                            self.log_scheduler_event(f'[오토모드:{group_name}] 전략 실행 실패: {strategy_name}, err={e}')
                            rc = -1

                        # 전략 프로세스가 끝났을 때, 시간/오토모드 상태를 재확인
                        auto_cfg = self.load_auto_config()
                        now_dt = datetime.now()
                        if (not auto_cfg.get('auto_mode_enabled', False)) or (not self.is_time_in_window(now_dt, start_hhmm, end_hhmm)):
                            return

                        if rc == 0:
                            break

                        fail_msg = (
                            f'[오토모드:{group_name}] 전략 에러 종료: {strategy_name}, exit_code={rc} '
                            f'-> {retry_interval_sec}초 후 재시도'
                        )
                        print(f'[Scheduler] {fail_msg}')
                        self.log_scheduler_event(fail_msg)
                        send_telegram_msg(fail_msg)
                        time.sleep(retry_interval_sec)

                loop_msg = f'[오토모드:{group_name}] 묶음 성공 -> 다시 처음부터 반복'
                print(f'[Scheduler] {loop_msg}')
                self.log_scheduler_event(loop_msg)

        except Exception as e:
            err_msg = f'[오토모드:{group_name}] 실행 중 예외: {e}'
            print(f'[Scheduler] {err_msg}')
            self.log_scheduler_event(err_msg)
            send_telegram_msg(err_msg)
        finally:
            end_msg = f'[오토모드:{group_name}] 종료'
            print(f'[Scheduler] {end_msg}')
            self.log_scheduler_event(end_msg)
            send_telegram_msg(end_msg)

    def run(self):
        mode_str = "터미널 모드" if self.terminal_mode else "백그라운드 모드"
        print(f'[Scheduler] 시작 ({mode_str}, OS: {self.system})')
        msg = f'스케줄러 시작 - {mode_str}'
        send_telegram_msg(msg)  # 텔레그램 발송 추가
        self.log_scheduler_event(msg)

        while True:
            now_dt = datetime.now()
            now = now_dt.strftime('%H:%M')
            self.load_config()  # config 실시간 반영

            # 자정이 지나면 executed 초기화 (다음 날 같은 시간에 다시 실행 가능)
            if now == "00:00":
                self.executed.clear()
                print(f'[Scheduler] 새로운 날 시작 - 실행 기록 초기화')
                self.log_scheduler_event('새로운 날 시작 - 실행 기록 초기화')

            # 새 구조: 오토모드는 별도 프로세스(auto_scheduler.py)가 DB 플래그를 관리합니다.
            # auto_mode_active가 1이면, 해당 minute의 time_key 실행은 스킵하되 executed에는 기록합니다.
            auto_active = self.get_flag_int('auto_mode_active', default=0)

            # 기본 스케줄 실행
            for time_key, strategy_names in self.config.items():
                if now == time_key and time_key not in self.executed:
                    # strategy_names가 리스트가 아니면 리스트로 변환
                    if isinstance(strategy_names, str):
                        strategy_names = [strategy_names]

                    strategies_str = ', '.join(strategy_names)
                    if auto_active == 1:
                        skip_msg = f'{now} - 오토모드 활성 -> time_key 스킵(실행 기록 유지): {strategies_str}'
                        print(f'[Scheduler] {skip_msg}')
                        self.log_scheduler_event(skip_msg)
                        self.executed.add(time_key)
                        continue

                    msg = f'{now} - 전략 실행: {strategies_str}'
                    print(f'[Scheduler] {msg}')
                    self.log_scheduler_event(msg)

                    # 터미널 모드 또는 백그라운드 모드 선택
                    if self.terminal_mode:
                        success = self.execute_strategy_in_terminal(time_key, strategy_names)
                        if success:
                            print(f'[Scheduler] 터미널에서 실행됨: {time_key}')
                        else:
                            print(f'[Scheduler] 터미널 실행 실패, 백그라운드로 대체 실행')
                            self.execute_strategy_background(time_key)
                    else:
                        success = self.execute_strategy_background(time_key)
                        if success:
                            print(f'[Scheduler] 백그라운드에서 실행됨: {time_key}')

                    self.executed.add(time_key)

            time.sleep(30)  # 30초마다 체크

def main():
    import argparse
    parser = argparse.ArgumentParser(description='전략 스케줄러')
    parser.add_argument('--terminal', action='store_true', 
                        help='터미널 모드로 실행 (기본값: 백그라운드)')
    args = parser.parse_args()
    
    scheduler = StrategyScheduler(terminal_mode=args.terminal)
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print('\n[Scheduler] 종료됨')

if __name__ == '__main__':
    main()