import streamlit as st
import sqlite3
import pandas as pd
import os
from config import DB_PATH  # 기존 config.py에서 DB 경로 로드

# 페이지 설정
st.set_page_config(page_title="주식비서 원격 관리 시스템", layout="wide")

def get_connection():
    """DB 연결 생성"""
    return sqlite3.connect(DB_PATH)

def load_data(table_name):
    """테이블 데이터 로드"""
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def save_data(df, table_name):
    """수정된 데이터를 DB에 저장"""
    conn = get_connection()
    try:
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        st.success(f"'{table_name}' 테이블이 성공적으로 업데이트되었습니다.")
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 보안 세션 (간이 로그인) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 관리자 인증")
    password = st.text_input("접속 암호를 입력하세요", type="password")
    if st.button("로그인"):
        if password == "1234": # 여기에 실제 사용할 암호를 입력하세요
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("암호가 틀렸습니다.")
    st.stop()

# --- 메인 대시보드 ---
st.title("📈 주식비서 설정 관리자 (Remote)")
st.info(f"현재 연결된 DB: {DB_PATH}")

# 메뉴 구성
tabs = st.tabs([
    "기본설정(secretary_setup)", 
    "매도설정", 
    "신용매수/매도설정", 
    "물타기/수익률 구간"
])

# 1. 기본 설정 (secretary_setup)
with tabs[0]:
    st.subheader("⚙️ 시스템 핵심 변수 수정")
    df_setup = load_data("secretary_setup")
    # value 컬럼을 문자열로 형변환하여 편집 가능하게 처리
    df_setup['value'] = df_setup['value'].astype(str)
    disabled_cols_sell = [c for c in ["id", "key"] if c in df_setup.columns]
    edited_setup = st.data_editor(
        df_setup, 
        column_config={
            "value": st.column_config.TextColumn(
                "설정값 (Value)",
                help="숫자나 문자를 입력하세요.",
                required=True
            ),
            # ID 컬럼 등이 있다면 수정을 못 하게 막을 수도 있습니다.
            # "id": st.column_config.Column(disabled=True) 
        },
        num_rows="dynamic", 
        disabled=disabled_cols_sell,
        key="setup_editor"
    )
    if st.button("기본설정 저장"):
        save_data(edited_setup, "secretary_setup")

# 2. 매도 설정
with tabs[1]:
    st.subheader("💰 단계별 익절/매도 설정")
    df_sell = load_data("매도설정")
    disabled_cols_sell = [c for c in ["id", "key"] if c in df_sell.columns]
    edited_sell = st.data_editor(
        df_sell,
        num_rows="dynamic",
        disabled=disabled_cols_sell,
        key="sell_editor",
    )
    if st.button("매도설정 저장"):
        save_data(edited_sell, "매도설정")

# 3. 신용 매수/매도 설정
with tabs[2]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💳 신용 매수 설정")
        df_c_buy = load_data("신용매수설정")
        disabled_cols_c_buy = [c for c in ["id", "key"] if c in df_c_buy.columns]
        edited_c_buy = st.data_editor(
            df_c_buy,
            num_rows="dynamic",
            disabled=disabled_cols_c_buy,
            key="cbuy_editor",
        )
        if st.button("신용매수 저장"):
            save_data(edited_c_buy, "신용매수설정")
    
    with col2:
        st.subheader("📊 신용 매도 설정")
        df_c_sell = load_data("신용매도설정")
        disabled_cols_c_sell = [c for c in ["id", "key"] if c in df_c_sell.columns]
        edited_c_sell = st.data_editor(
            df_c_sell,
            num_rows="dynamic",
            disabled=disabled_cols_c_sell,
            key="csell_editor",
        )
        if st.button("신용매도 저장"):
            save_data(edited_c_sell, "신용매도설정")

# 4. 물타기 및 기타 구간 설정
with tabs[3]:
    st.subheader("📉 종목 하락/상승률 대응 구간")
    c1, c2 = st.columns(2)
    with c1:
        df_down = load_data("secretary_stockdownrate")
        disabled_cols_down = [c for c in ["id", "key"] if c in df_down.columns]
        edited_down = st.data_editor(
            df_down,
            num_rows="dynamic",
            disabled=disabled_cols_down,
            key="down_editor",
        )
        if st.button("하락률 구간 저장"):
            save_data(edited_down, "secretary_stockdownrate")
    with c2:
        df_up = load_data("secretary_stockuprate")
        disabled_cols_up = [c for c in ["id", "key"] if c in df_up.columns]
        edited_up = st.data_editor(
            df_up,
            num_rows="dynamic",
            disabled=disabled_cols_up,
            key="up_editor",
        )
        if st.button("상승률 구간 저장"):
            save_data(edited_up, "secretary_stockuprate")

st.divider()
st.caption("주의: 이곳에서 수정된 내용은 실시간으로 DB에 반영되며, 다음번 'Trading Strategy' 실행 시 적용됩니다.")