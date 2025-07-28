@echo off
cd /d "C:\Users\deser\Project\secretary"

:: Streamlit 실행
start "Streamlit" cmd /k "python -m streamlit run strategy_ui.py"

:: 5초 대기 (Streamlit이 완전히 시작될 때까지)
timeout /t 5
