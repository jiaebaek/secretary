Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""C:\Users\deser\Project\secretary"" && python scheduler.py --terminal", 0
