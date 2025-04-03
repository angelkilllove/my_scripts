Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' 使用批处理文件运行Python脚本（显示窗口和输出）
batFile = strPath & "\update_cursor_token_main_runner.bat"
WshShell.Run "cmd /c """ & batFile & """", 1, False
