Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' ��ȡ�ű�����Ŀ¼
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' ʹ���������ļ�����Python�ű�����ʾ���ں������
batFile = strPath & "\update_cursor_token_main_runner.bat"
WshShell.Run "cmd /c """ & batFile & """", 1, False
