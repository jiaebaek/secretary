import streamlit as st
import json
import os
import subprocess
import time
from strategy_definitions import STRATEGY_NAME_TO_CODE
from config import LOG_FILE_PATH

st.set_page_config(layout="wide")

CONFIG_FILE = 'strategy_config.json'
STRATEGY_OPTIONS = list(STRATEGY_NAME_TO_CODE.keys())
SCHEDULER_LOG_DIR = 'logs'  # 스케줄러 로그 디렉토리

os.makedirs(SCHEDULER_LOG_DIR, exist_ok=True)

def load_strategy_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_strategy_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def main():
    st.title("📈 주식 매매 전략 관리 프로그램 (with secretary)")
    config = load_strategy_config()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("⏰ 시간대별 매매 전략 스케줄 설정")

        with st.form('add_strategy'):
            new_time = st.text_input('시간대 (예: 08:00)', '')
            new_strategies = st.multiselect('추가할 전략 선택', STRATEGY_OPTIONS)
            submitted = st.form_submit_button('추가')

            if submitted and new_time and new_strategies:
                if new_time not in config:
                    config[new_time] = []
                config[new_time].extend([s for s in new_strategies if s not in config[new_time]])
                save_strategy_config(config)
                st.success(f'{new_time}에 전략 추가됨.')
                st.rerun()

        st.markdown("---")
        st.markdown("### 📋 현재 등록된 매매 전략")

        if not config:
            st.info("등록된 전략이 없습니다.")
        else:
            for time_key in sorted(config.keys()):
                st.markdown(f"**{time_key}**")
                for strategy in config[time_key]:
                    col_a, col_b = st.columns([4, 1])
                    col_a.markdown(f"- {strategy}")
                    if col_b.button('삭제', key=f"{time_key}_{strategy}"):
                        config[time_key].remove(strategy)
                        if not config[time_key]:
                            del config[time_key]
                        save_strategy_config(config)
                        st.success(f"{time_key}의 {strategy} 전략 삭제됨.")
                        st.rerun()

    with col2:
        st.subheader("⚡ 매매 전략 수동 실행")
        selected_strategy = st.selectbox("실행할 전략 선택", STRATEGY_OPTIONS, key='manual_exec')
        
        # 실행 모드 선택
        execution_mode = st.radio(
            "실행 방식 선택",
            ["백그라운드 실행", "터미널에서 실행"],
            horizontal=True
        )
        
        if st.button("전략 실행"):
            if execution_mode == "터미널에서 실행":
                # 터미널에서 실행
                import platform
                system = platform.system()
                
                try:
                    if system == "Windows":
                        # Windows에서 새 cmd 창 열기
                        cmd = f'start "전략 실행: {selected_strategy}" cmd /k "python main.py --name {selected_strategy} & pause"'
                        os.system(cmd)
                        st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                        st.info("터미널 창에서 실시간 로그를 확인하세요.")
                        
                    elif system == "Darwin":  # macOS
                        # macOS에서 터미널 열기
                        script = f'''
                        tell application "Terminal"
                            do script "cd {os.getcwd()} && python main.py --name {selected_strategy}"
                            activate
                        end tell
                        '''
                        subprocess.run(["osascript", "-e", script])
                        st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                        
                    elif system == "Linux":
                        # Linux에서 터미널 열기 (gnome-terminal, xterm 등)
                        try:
                            subprocess.Popen([
                                "gnome-terminal", "--", 
                                "bash", "-c", 
                                f"cd {os.getcwd()} && python main.py --name {selected_strategy}; read -p 'Press Enter to close...'"
                            ])
                            st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                        except FileNotFoundError:
                            # gnome-terminal이 없으면 xterm 시도
                            try:
                                subprocess.Popen([
                                    "xterm", "-e", 
                                    f"cd {os.getcwd()} && python main.py --name {selected_strategy}; read -p 'Press Enter to close...'"
                                ])
                                st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                            except FileNotFoundError:
                                st.error("터미널을 찾을 수 없습니다. 백그라운드 실행을 사용해주세요.")
                        
                except Exception as e:
                    st.error(f"터미널 실행 중 오류 발생: {str(e)}")
                    st.info("백그라운드 실행으로 전환합니다...")
                    execution_mode = "백그라운드 실행"
            
            if execution_mode == "백그라운드 실행":
                # 기존 백그라운드 실행 방식 (로그 파일 없이)
                with st.spinner(f"{selected_strategy} 실행 중..."):
                    result = subprocess.run(
                        ["python", "main.py", "--name", selected_strategy],
                        capture_output=True,
                        text=True
                    )
                st.success("전략 실행 완료!")
                st.text_area("실행 결과", result.stdout + result.stderr, height=300)

    st.markdown("---")
    st.subheader("📜 스케줄러 실행 로그 보기")
    st.info("💡 수동 실행 로그는 화면에서 바로 확인하세요. 여기서는 스케줄러 실행 로그만 표시됩니다.")

    log_files = sorted([f for f in os.listdir(SCHEDULER_LOG_DIR) if f.endswith(".log")], reverse=True)
    if not log_files:
        st.info("스케줄러 실행 로그가 없습니다.")
    else:
        selected_log = st.selectbox("로그 파일 선택", log_files)
        refresh = st.checkbox("자동 새로고침 (5초)", key="auto_refresh")

        def read_log(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.readlines()[-200:]

        log_path = os.path.join(SCHEDULER_LOG_DIR, selected_log)
        st.text_area("로그 내용", value="".join(read_log(log_path)), height=400)

        if refresh:
            time.sleep(5)
            st.rerun()
            
if __name__ == '__main__':
    main()