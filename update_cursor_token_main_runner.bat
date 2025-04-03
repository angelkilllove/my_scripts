@echo off
call "H:\anaconda3\Scripts\activate.bat" base
echo 正在使用环境: base
echo 运行Python脚本: update_cursor_token_main.py
echo.
"H:\anaconda3\python.exe" "H:/PyQt5Project/常用脚本/update_cursor_token_main.py"
echo.
echo 脚本执行完毕，按任意键退出...
pause > nul
