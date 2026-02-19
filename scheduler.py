import json
import subprocess
import time
from datetime import datetime
import os
import platform

from telegram_bot import send_telegram_msg


class StrategyScheduler:
    def __init__(self, config_path='strategy_config.json', terminal_mode=False):
        self.config_path = config_path
        self.terminal_mode = terminal_mode  # 터미널 모드 설정
        self.system = platform.system()
        self.load_config()
        self.executed = set()

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {}

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

    def run(self):
        mode_str = "터미널 모드" if self.terminal_mode else "백그라운드 모드"
        print(f'[Scheduler] 시작 ({mode_str}, OS: {self.system})')
        msg = f'스케줄러 시작 - {mode_str}'
        send_telegram_msg(msg)  # 텔레그램 발송 추가
        self.log_scheduler_event(msg)

        
        while True:
            now = datetime.now().strftime('%H:%M')
            self.load_config()  # config 실시간 반영
            
            for time_key, strategy_names in self.config.items():
                if now == time_key and time_key not in self.executed:
                    # strategy_names가 리스트가 아니면 리스트로 변환
                    if isinstance(strategy_names, str):
                        strategy_names = [strategy_names]
                    
                    strategies_str = ', '.join(strategy_names)
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
            
            # 자정이 지나면 executed 초기화 (다음 날 같은 시간에 다시 실행 가능)
            if now == "00:00":
                self.executed.clear()
                print(f'[Scheduler] 새로운 날 시작 - 실행 기록 초기화')
                self.log_scheduler_event('새로운 날 시작 - 실행 기록 초기화')
            
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