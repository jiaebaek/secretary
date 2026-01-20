import streamlit as st
import json
import os
import subprocess
import time
import re
from strategy_definitions import STRATEGY_NAME_TO_CODE
from config import LOG_FILE_PATH, ACCOUNT_OWNER_NAME


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


def parse_progress_from_log(log_content):
    """로그에서 진행률 정보를 파싱"""
    progress_info = {
        'current_task': '',
        'current': 0,
        'total': 0,
        'percentage': 0,
        'last_update': None
    }

    # 진행률 패턴 매칭 (예: "현금주식 매도 진행 중... [21/690]")
    progress_pattern = r'=+ ([^[]+) 진행 중\.\.\. \[(\d+)/(\d+)\] =+'

    lines = log_content.split('\n')
    for line in reversed(lines):  # 최신 로그부터 검색
        match = re.search(progress_pattern, line)
        if match:
            task_name = match.group(1).strip()
            current = int(match.group(2))
            total = int(match.group(3))
            percentage = (current / total) * 100 if total > 0 else 0

            # 시간 정보 추출 (로그 라인에서)
            time_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
            time_match = re.search(time_pattern, line)
            last_update = time_match.group() if time_match else None

            progress_info = {
                'current_task': task_name,
                'current': current,
                'total': total,
                'percentage': percentage,
                'last_update': last_update
            }
            break

    return progress_info


def read_latest_log():
    """최신 로그 파일 읽기 (성능 최적화)"""
    try:
        log_files = [f for f in os.listdir(LOG_FILE_PATH)
                     if f.endswith('.log') and os.path.isfile(os.path.join(LOG_FILE_PATH, f))]
        if log_files:
            # 최신 파일 찾기 (수정 시간 기준)
            latest_file = max(log_files,
                              key=lambda x: os.path.getmtime(os.path.join(LOG_FILE_PATH, x)))
            latest_path = os.path.join(LOG_FILE_PATH, latest_file)

            file_size = os.path.getsize(latest_path)
            if file_size > 0:
                with open(latest_path, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(max(0, file_size - 10000))
                    return f.read()
    except Exception as e:
        st.error(f"로그 파일 읽기 오류: {e}")
    return ""


def is_process_running():
    """trading 프로세스가 실행 중인지 확인"""
    import platform
    import psutil

    try:
        # psutil을 사용해서 프로세스 확인 (터미널 창이 안 뜸)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('main.py' in str(arg) for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        # psutil이 없는 경우 기존 방식 사용하되 터미널 창 숨기기
        system = platform.system()
        try:
            if system == "Windows":
                # Windows에서 터미널 창 숨기기
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo
                )
                return 'main.py' in result.stdout
            else:
                # Linux/macOS
                result = subprocess.run(
                    ['pgrep', '-f', 'main.py'],
                    capture_output=True,
                    text=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return len(result.stdout.strip()) > 0
        except:
            return False


def display_progress_monitor():
    """진행률 모니터링 표시"""
    st.subheader("📊 실시간 진행률 모니터링")

    # 실시간 업데이트를 위한 플레이스홀더
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    # 자동 새로고침 옵션
    auto_refresh = st.checkbox("자동 새로고침 (5초 간격)", value=False, key="progress_refresh")

    # 수동 새로고침 버튼
    if st.button("🔄 새로고침", key="manual_refresh"):
        st.rerun()

    # 로그에서 진행률 정보 파싱
    log_content = read_latest_log()
    progress_info = parse_progress_from_log(log_content)

    with progress_placeholder.container():
        if progress_info['total'] > 0:
            # 진행률 표시
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**현재 작업:** {progress_info['current_task']}")
                progress_bar = st.progress(progress_info['percentage'] / 100)
                st.write(
                    f"진행률: {progress_info['current']}/{progress_info['total']} ({progress_info['percentage']:.1f}%)")

            with col2:
                st.metric("완료", progress_info['current'])

            with col3:
                st.metric("전체", progress_info['total'])

            if progress_info['last_update']:
                st.caption(f"마지막 업데이트: {progress_info['last_update']}")
        else:
            st.info("진행률 정보를 찾을 수 없습니다. 전략이 실행 중이거나 초기화 단계일 수 있습니다.")

    # 최근 로그 표시
    with status_placeholder.container():
        st.subheader("📝 최근 로그 (마지막 15줄)")
        recent_logs = log_content.split('\n')[-15:] if log_content else []
        log_text = '\n'.join(recent_logs)
        st.text_area("", value=log_text, height=200, key="recent_logs")

    # 자동 새로고침 (사용자가 체크한 경우에만)
    if auto_refresh:
        time.sleep(5)
        st.rerun()


def main():
    st.title("📈 주식 매매 전략 관리 프로그램 (with secretary)")
    st.markdown(f"**👤 계좌 주인: `{ACCOUNT_OWNER_NAME}`**")
    config = load_strategy_config()

    # 탭으로 구성 변경
    tab1, tab2, tab3 = st.tabs(["⚙️ 전략 설정", "⚡ 수동 실행", "📊 진행률 모니터링"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("⏰ 시간대별 매매 전략 스케줄 설정")

            # 1. 중복 추가를 위해 st.selectbox 방식으로 변경
            with st.form('add_strategy'):
                new_time = st.text_input('시간대 (예: 08:00)', '')
                selected_strategy = st.selectbox('추가할 전략 선택', STRATEGY_OPTIONS)
                submitted = st.form_submit_button('전략 추가')

                if submitted and new_time:
                    if new_time not in config:
                        config[new_time] = []

                    # 중복 체크 없이 리스트에 추가
                    config[new_time].append(selected_strategy)
                    save_strategy_config(config)
                    st.success(f'{new_time}에 {selected_strategy} 전략이 추가되었습니다.')
                    st.rerun()

            st.markdown("---")
            st.markdown("### 📋 현재 등록된 매매 전략")

            if not config:
                st.info("등록된 전략이 없습니다.")
            else:
                for time_key in sorted(config.keys()):
                    st.markdown(f"**{time_key}**")
                    # 2. 인덱스(i)를 사용하여 중복된 이름의 전략도 고유하게 식별
                    for i, strategy in enumerate(config[time_key]):
                        col_a, col_b = st.columns([4, 1])
                        col_a.markdown(f"{i + 1}. {strategy}")

                        # 3. 삭제 버튼의 key에 인덱스를 포함하여 충돌 방지
                        if col_b.button('삭제', key=f"{time_key}_{strategy}_{i}"):
                            config[time_key].pop(i)  # 인덱스로 삭제
                            if not config[time_key]:
                                del config[time_key]
                            save_strategy_config(config)
                            st.success(f"{time_key}의 {strategy} 전략이 삭제되었습니다.")
                            st.rerun()

    with tab2:
        st.subheader("⚡ 매매 전략 수동 실행")

        selected_strategy = st.selectbox("실행할 전략 선택", STRATEGY_OPTIONS, key='manual_exec')

        # 실행 모드 선택
        execution_mode = st.radio(
            "실행 방식 선택",
            ["터미널에서 실행", "백그라운드 실행"],
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
                        st.info("터미널 창에서 실시간 로그를 확인하거나 '진행률 모니터링' 탭을 이용하세요.")

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
                        st.info("'진행률 모니터링' 탭에서 실시간 진행상황을 확인하세요.")

                    elif system == "Linux":
                        # Linux에서 터미널 열기 (gnome-terminal, xterm 등)
                        try:
                            subprocess.Popen([
                                "gnome-terminal", "--",
                                "bash", "-c",
                                f"cd {os.getcwd()} && python main.py --name {selected_strategy}; read -p 'Press Enter to close...'"
                            ])
                            st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                            st.info("'진행률 모니터링' 탭에서 실시간 진행상황을 확인하세요.")
                        except FileNotFoundError:
                            # gnome-terminal이 없으면 xterm 시도
                            try:
                                subprocess.Popen([
                                    "xterm", "-e",
                                    f"cd {os.getcwd()} && python main.py --name {selected_strategy}; read -p 'Press Enter to close...'"
                                ])
                                st.success(f"🚀 {selected_strategy} 전략이 새 터미널에서 실행됩니다!")
                                st.info("'진행률 모니터링' 탭에서 실시간 진행상황을 확인하세요.")
                            except FileNotFoundError:
                                st.error("터미널을 찾을 수 없습니다. 백그라운드 실행을 사용해주세요.")

                except Exception as e:
                    st.error(f"터미널 실행 중 오류 발생: {str(e)}")
                    st.info("백그라운드 실행으로 전환합니다...")
                    execution_mode = "백그라운드 실행"

            if execution_mode == "백그라운드 실행":
                # 백그라운드에서 실행하고 진행률 모니터링으로 안내
                with st.spinner(f"{selected_strategy} 백그라운드에서 시작 중..."):
                    process = subprocess.Popen(
                        ["python", "main.py", "--name", selected_strategy],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    time.sleep(2)  # 프로세스 시작 대기

                st.success("✅ 전략이 백그라운드에서 시작되었습니다!")
                st.info("📊 '진행률 모니터링' 탭에서 실시간 진행상황을 확인하세요.")

    with tab3:
        display_progress_monitor()


if __name__ == '__main__':
    main()