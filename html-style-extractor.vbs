Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' ��ȡ�ű�����Ŀ¼
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' ʹ�������ļ���������г������ش��ڣ�
cmd = "cmd /c call ""H:\\anaconda3\\Scripts\\activate.bat"" cp310side6 && " & _
      """H:\\anaconda3\\envs\\cp310side6\\pythonw.exe"" """ & strPath & "\html-style-extractor.py"""

WshShell.Run cmd, 0, True
