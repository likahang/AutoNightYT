@echo off
chcp 65001
echo 正在開始打包 exe...
echo 請確保已安裝 pyinstaller (pip install pyinstaller)

pyinstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --windowed ^
 --name "晚報YT縮圖生成器" ^
 --icon "icon.ico" ^
 --add-data "icon.png;." ^
 --add-data "cg-indigo-loader.svg;." ^
 --add-data "晚報YT縮圖.psd;." ^
 --add-data "晚報YT縮圖(標圖版).psd;." ^
 --add-data "晚報變色.csv;." ^
 --add-data "右上變色.csv;." ^
 --add-data "效果字處理.csv;." ^
 --add-data "參考.jsx;." ^
 --noupx ^
 gui_main.py

echo.
if %errorlevel% neq 0 (
    echo ❌ 打包失敗！請檢查錯誤訊息。
    exit /b %errorlevel%
)

echo.
echo ✅ 打包完成！
echo 執行檔位於 dist\晚報YT縮圖生成器.exe
echo.
