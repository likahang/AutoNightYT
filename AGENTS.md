# 專案長期規則

## 專案定位

本專案是 Windows 上的晚報 YouTube 縮圖批次生成器：讀取新聞文字檔，解析版型與文字指示，產生 Photoshop JSX，並由 Photoshop 套用 PSD 模板後輸出 PSD/JPG。

## 技術架構

- Python 3：文字解析、GUI、工作執行緒、JSX 產生器。
- GUI：PyQt5，入口為 `gui_main.py`；背景工作流程在 `worker.py`。
- Photoshop：必須使用 JSX 與既有 PSD 模板，不以其他繪圖引擎取代 Photoshop。
- 文字解析：`parse_thumbnail_txt.py`；JSX 產生：`generate_photoshop_script.py`。
- CLI 流程：`run_auto_thumbnail.py`。
- 模板：`晚報YT縮圖.psd`（大標版）及 `晚報YT縮圖(標圖版).psd`（標圖版）。
- CSV 設定檔使用既有 Big5/CP950 讀取方式；文字檔優先 UTF-8，失敗再嘗試 CP950。

## 必須遵守的限制

- 未經使用者明確要求，不要更換 PSD 模板、圖層名稱、Photoshop JSX 流程或輸出格式。
- 不要用 Windows GUI 操作取代可重現的本地測試；Photoshop 實機測試需使用者明確要求。
- 不要把 PSD、網路共享檔案、聊天紀錄、暫存 log 或測試輸出加入 Git。
- 修改前先保留既有未提交變更；不可使用 `git reset --hard` 或未經確認的刪除操作。
- 標圖版左邊字必須忽略引號變色；`(左邊字)`、`(左邊直字)` 及帶冒號格式都要維持相容。
- 數字規則：一位數轉全形留在主層；多位數另建橫向數字層，W=250；兩位數 kerning=90，其他目前規則為 110。
- 標圖版 `直標` 群組最終高度不可超過 1000px；大標1 W 上限 1400px，大標2 W 上限 1280px。
- 標圖版圖片必須以智慧型物件匯入；資料夾名稱需兼容 `晚報yt縮圖` 與 `YT縮圖`，並支援當日及月份歸檔路徑。

## Coding conventions

- Python 以清楚的小函數處理解析與 JSX 片段生成；維持既有函式命名與繁體中文註解風格。
- JSX 字串插值必須正確處理 Windows/UNC 路徑與 Unicode；不可直接拼接未轉義的使用者文字。
- 新增規則要有對應的單元測試或至少更新既有測試斷言。
- 使用 `apply_patch` 修改檔案；完成後執行語法檢查與測試。

## Build / test

```powershell
python -m unittest test_layout_variants.py
python -m py_compile parse_thumbnail_txt.py generate_photoshop_script.py gui_main.py worker.py
開啟本地測試.bat
```

正式打包使用 `build_exe.bat`（需在 Windows、已安裝 PyInstaller 的環境執行）。

## 固定的技術選擇

- Photoshop JSX + PSD 模板是既定產線，不改成 ImageMagick、PIL 或其他渲染方式。
- 標圖版圖片使用 Photoshop Embedded Smart Object，避免縮放後模糊。
- GUI 以 PyQt5 維持現有流程；網路來源與輸出仍依使用者選定日期切換。
