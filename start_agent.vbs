Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\AI AGENT FOR JOBS\AI AGENT"
WshShell.Run """D:\AI AGENT FOR JOBS\AI AGENT\.venv\Scripts\pythonw.exe"" orchestrator.py", 0, False
Set WshShell = Nothing