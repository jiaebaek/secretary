@echo off
cd /d "C:\Users\deser\Project\secretary"

:: Streamlit을 백그라운드에서 실행 (터미널 창 없음)
start /B pythonw -m streamlit run strategy_ui.py

:: 5초 대기
timeout /t 5 >nul
