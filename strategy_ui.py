import streamlit as st
import json
import os
import subprocess
import time
import re
from datetime import datetime, timedelta
from strategy_definitions import STRATEGY_NAME_TO_CODE
from config import LOG_FILE_PATH, ACCOUNT_OWNER_NAME
from telegram_bot import send_telegram_msg

st.set_page_config(layout="wide")

CONFIG_FILE = 'strategy_config.json'
AUTO_CONFIG_FILE = 'auto_strategy_config.json'
STRATEGY_OPTIONS = list(STRATEGY_NAME_TO_CODE.keys())
SCHEDULER_LOG_DIR = 'logs'

os.makedirs(SCHEDULER_LOG_DIR, exist_ok=True)


def load_strategy_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_strategy_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_auto_strategy_config():
    if os.path.exists(AUTO_CONFIG_FILE):
        with open(AUTO_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'auto_mode_enabled': False, 'auto_groups': []}


def save_auto_strategy_config(config: dict):
    with open(AUTO_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def is_valid_hhmm(value: str) -> bool:
    try:
        parts = (value or '').split(':')
        if len(parts) != 2:
            return False
        hh = int(parts[0])
        mm = int(parts[1])
        return 0 <= hh <= 23 and 0 <= mm <= 59
    except Exception:
        return False


def parse_progress_from_log(log_content):
    progress_info = {
        'current_task': '',
        'current': 0,
        'total': 0,
        'percentage': 0,
        'last_update': None
    }
    progress_pattern = r'=+ ([^[]+) 진행 중\.\.\. \[(\d+)/(\d+)\] =+'
    lines = log_content.split('\n')
    for line in reversed(lines):
        match = re.search(progress_pattern, line)
        if match:
            task_name = match.group(1).strip()
            current = int(match.group(2))
            total = int(match.group(3))
            percentage = (current / total) * 100 if total > 0 else 0
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
    try:
        log_files = [f for f in os.listdir(LOG_FILE_PATH)
                     if f.endswith('.log') and os.path.isfile(os.path.join(LOG_FILE_PATH, f))]
        if log_files:
            latest_file = max(log_files, key=lambda x: os.path.getmtime(os.path.join(LOG_FILE_PATH, x)))
            latest_path = os.path.join(LOG_FILE_PATH, latest_file)
            file_size = os.path.getsize(latest_path)
            if file_size > 0:
                with open(latest_path, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(max(0, file_size - 10000))
                    return f.read()
    except Exception as e:
        st.error(f"로그 파일 읽기 오류: {e}")
    return ""


def display_progress_monitor():
    st.subheader("📊 실시간 진행률 모니터링")
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    auto_refresh = st.checkbox("자동 새로고침 (5초 간격)", value=False, key="progress_refresh")

    if st.button("🔄 새로고침", key="manual_refresh"):
        st.rerun()

    log_content = read_latest_log()
    progress_info = parse_progress_from_log(log_content)

    with progress_placeholder.container():
        if progress_info['total'] > 0:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**현재 작업:** {progress_info['current_task']}")
                st.progress(progress_info['percentage'] / 100)
                st.write(
                    f"진행률: {progress_info['current']}/{progress_info['total']} ({progress_info['percentage']:.1f}%)")
            with col2:
                st.metric("완료", progress_info['current'])
            with col3:
                st.metric("전체", progress_info['total'])
            if progress_info['last_update']:
                st.caption(f"마지막 업데이트: {progress_info['last_update']}")
        else:
            st.info("진행률 정보를 찾을 수 없습니다.")

    with status_placeholder.container():
        st.subheader("📝 최근 로그 (마지막 15줄)")
        recent_logs = log_content.split('\n')[-15:] if log_content else []
        st.text_area("", value='\n'.join(recent_logs), height=200, key="recent_logs")

    if auto_refresh:
        time.sleep(5)
        st.rerun()


def main():
    st.title("📈 주식 매매 전략 관리 프로그램")
    st.markdown(f"**👤 계좌 주인: `{ACCOUNT_OWNER_NAME}`**")
    config = load_strategy_config()
    auto_config = load_auto_strategy_config()

    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 전략 설정", "⚡ 수동 실행", "🤖 오토모드 설정", "📊 진행률 모니터링"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("⏰ 시간대별 매매 전략 스케줄 설정")
            with st.form('add_strategy'):
                new_time = st.text_input('시간대 (예: 08:00)', '')
                selected_strategy = st.selectbox('추가할 전략 선택', STRATEGY_OPTIONS)
                if st.form_submit_button('전략 추가') and new_time:
                    if new_time not in config: config[new_time] = []
                    config[new_time].append(selected_strategy)
                    save_strategy_config(config)
                    st.rerun()

            st.markdown("---")
            st.markdown("### 📋 현재 등록된 매매 전략")
            if not config:
                st.info("등록된 전략이 없습니다.")
            else:
                for time_key in sorted(config.keys()):
                    t_col1, t_col2 = st.columns([3, 1])
                    t_col1.markdown(f"#### 🕒 {time_key}")
                    with t_col2:
                        with st.popover("시간 수정"):
                            edit_time = st.text_input("새 시간", value=time_key, key=f"edit_{time_key}")
                            if st.button("변경", key=f"btn_edit_{time_key}"):
                                data = config.pop(time_key)
                                if edit_time in config:
                                    config[edit_time].extend(data)
                                else:
                                    config[edit_time] = data
                                save_strategy_config(config)
                                st.rerun()

                    for i, strategy in enumerate(config[time_key]):
                        s_col1, s_col2 = st.columns([4, 1])
                        s_col1.markdown(f"&nbsp;&nbsp;{i + 1}. {strategy}")
                        if s_col2.button('삭제', key=f"del_{time_key}_{i}"):
                            config[time_key].pop(i)
                            if not config[time_key]: del config[time_key]
                            save_strategy_config(config)
                            st.rerun()
                    st.write("")

        with col2:
            st.subheader("📋 전략 시간대 일괄 복사")
            st.caption("기존 데이터를 삭제하고 덮어씁니다.")
            src_start = st.text_input("원본 시작", "09:00")
            src_end = st.text_input("원본 종료", "10:00")
            target_until = st.text_input("복사 완료 시점", "14:00")
            interval = st.number_input("간격(분)", min_value=1, value=60)

            if st.button("🚀 일괄 복사 실행 (Overwrite)"):
                try:
                    fmt = "%H:%M"
                    s_dt, e_dt, u_dt = datetime.strptime(src_start, fmt), datetime.strptime(src_end,
                                                                                            fmt), datetime.strptime(
                        target_until, fmt)
                    source_data = {k: v for k, v in config.items() if src_start <= k <= src_end}

                    if not source_data:
                        st.warning("원본 범위에 전략이 없습니다.")
                    else:
                        # 대상 범위 기존 데이터 삭제
                        t_start_str = (e_dt + timedelta(minutes=1)).strftime(fmt)
                        for k in [t for t in config.keys() if t_start_str <= t <= target_until]:
                            del config[k]

                        # 반복 복사
                        base_dt = datetime.strptime(min(source_data.keys()), fmt)
                        curr_dt = base_dt + timedelta(minutes=interval)
                        while curr_dt <= u_dt:
                            for orig_str, strats in source_data.items():
                                diff = datetime.strptime(orig_str, fmt) - base_dt
                                new_dt = curr_dt + diff
                                if new_dt <= u_dt:
                                    config[new_dt.strftime(fmt)] = list(strats)
                            curr_dt += timedelta(minutes=interval)

                        save_strategy_config(config)
                        st.success("복사 완료!")
                        st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

    with tab2:
        st.subheader("⚡ 매매 전략 수동 실행")
        selected_manual = st.selectbox("실행 전략", STRATEGY_OPTIONS, key='manual_exec')
        mode = st.radio("방식", ["터미널에서 실행", "백그라운드 실행"], horizontal=True)

        if st.button("전략 실행"):
            if mode == "터미널에서 실행":
                import platform
                sys_p = platform.system()
                if sys_p == "Windows":
                    os.system(f'start "실행: {selected_manual}" cmd /k "python main.py --name {selected_manual} & pause"')
                elif sys_p == "Darwin":
                    subprocess.run(["osascript", "-e",
                                    f'tell application "Terminal" to do script "cd {os.getcwd()} && python main.py --name {selected_manual}"'])
                st.success(f"🚀 {selected_manual} 실행됨!")
            else:
                subprocess.Popen(["python", "main.py", "--name", selected_manual])
                st.success("✅ 백그라운드 시작!")

    with tab3:
        st.subheader("🤖 오토모드 설정")

        # 전역 on/off
        auto_enabled = st.toggle(
            "오토모드 활성화",
            value=bool(auto_config.get('auto_mode_enabled', False)),
            key='auto_mode_enabled_toggle',
        )

        # 저장 버튼(전역 on/off 반영용)
        if st.button("오토모드 설정 저장", key="save_auto_mode_toggle"):
            auto_config['auto_mode_enabled'] = auto_enabled
            save_auto_strategy_config(auto_config)
            st.success("오토모드 on/off 저장됨")
            st.rerun()

        st.markdown("---")
        st.subheader("🧩 전략 묶음(순차 실행) 추가/수정")

        with st.form("add_auto_group_form", clear_on_submit=True):
            group_name = st.text_input("그룹 이름", "")
            colA, colB, colC = st.columns(3)
            with colA:
                start_hhmm = st.text_input("start (HH:MM)", "09:00")
            with colB:
                end_hhmm = st.text_input("end (HH:MM)", "10:00")
            with colC:
                retry_interval_sec = st.number_input("재시도 간격(초)", min_value=1, value=10, step=1)

            strategies = st.multiselect(
                "전략 묶음(약 5개, 순차 실행)",
                STRATEGY_OPTIONS,
                default=[],
            )

            submitted = st.form_submit_button("그룹 저장")
            if submitted:
                if not group_name.strip():
                    st.error("그룹 이름이 필요합니다.")
                elif not is_valid_hhmm(start_hhmm) or not is_valid_hhmm(end_hhmm):
                    st.error("start/end 형식은 HH:MM 이어야 합니다.")
                elif not strategies:
                    st.error("전략 묶음은 최소 1개 이상 선택해야 합니다.")
                else:
                    auto_config['auto_mode_enabled'] = auto_enabled
                    new_group = {
                        'group_name': group_name.strip(),
                        'start': start_hhmm,
                        'end': end_hhmm,
                        'strategies': strategies,
                        'retry_interval_sec': int(retry_interval_sec),
                    }

                    groups = auto_config.get('auto_groups') or []
                    replaced = False
                    for i, g in enumerate(groups):
                        if g.get('group_name') == new_group['group_name']:
                            groups[i] = new_group
                            replaced = True
                            break
                    if not replaced:
                        groups.append(new_group)
                    auto_config['auto_groups'] = groups

                    save_auto_strategy_config(auto_config)
                    st.success("오토모드 그룹 저장됨")
                    st.rerun()

        st.markdown("### 📋 현재 등록된 오토모드 그룹")
        groups = auto_config.get('auto_groups') or []
        if not groups:
            st.info("등록된 오토모드 그룹이 없습니다.")
        else:
            for i, g in enumerate(groups):
                g_name = g.get('group_name') or f'group_{i}'
                st.markdown(f"#### {g_name} ({g.get('start')} ~ {g.get('end')})")
                st.caption(f"전략수: {len(g.get('strategies') or [])}")
                for idx, s in enumerate(g.get('strategies')):
                    st.markdown(f"&nbsp;&nbsp;{idx + 1}. {s}")

                with st.expander("수정/삭제", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_start = st.text_input("start (HH:MM)", value=g.get('start') or '', key=f'auto_start_{i}')
                        new_end = st.text_input("end (HH:MM)", value=g.get('end') or '', key=f'auto_end_{i}')
                        new_retry = st.number_input(
                            "재시도 간격(초)",
                            min_value=1,
                            value=int(g.get('retry_interval_sec') or 10),
                            step=1,
                            key=f'auto_retry_{i}'
                        )
                    with col2:
                        new_strats = st.multiselect(
                            "전략 묶음",
                            STRATEGY_OPTIONS,
                            default=g.get('strategies') or [],
                            key=f'auto_strats_{i}'
                        )

                    if st.button("수정 저장", key=f'auto_save_{i}'):
                        if not new_strats:
                            st.error("전략 묶음은 최소 1개 이상 선택해야 합니다.")
                        elif not is_valid_hhmm(new_start) or not is_valid_hhmm(new_end):
                            st.error("start/end 형식은 HH:MM 이어야 합니다.")
                        else:
                            auto_config['auto_mode_enabled'] = auto_enabled
                            g_updated = dict(g)
                            g_updated['start'] = new_start
                            g_updated['end'] = new_end
                            g_updated['strategies'] = new_strats
                            g_updated['retry_interval_sec'] = int(new_retry)
                            groups[i] = g_updated
                            auto_config['auto_groups'] = groups
                            save_auto_strategy_config(auto_config)
                            st.success("그룹 수정 저장됨")
                            st.rerun()

                    if st.button("삭제", key=f'auto_del_{i}'):
                        auto_config['auto_mode_enabled'] = auto_enabled
                        groups.pop(i)
                        auto_config['auto_groups'] = groups
                        save_auto_strategy_config(auto_config)
                        st.success("그룹 삭제됨")
                        st.rerun()

    with tab4:
        display_progress_monitor()


if __name__ == '__main__':
    main()