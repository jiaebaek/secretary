Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""D:\\PycharmProjects\\secretary_v2_rest"" && python scheduler.py --terminal", 0
WshShell.Run "cmd /c cd /d ""D:\\PycharmProjects\\secretary_v2_rest"" && python auto_scheduler.py --poll 1", 1
