Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' 使用完整的激活命令并运行程序（隐藏窗口）
cmd = "cmd /c call ""H:\\anaconda3\\Scripts\\activate.bat"" cp310side6 && " & _
      """H:\\anaconda3\\envs\\cp310side6\\pythonw.exe"" """ & strPath & "\html-style-extractor.py"""

WshShell.Run cmd, 0, True
