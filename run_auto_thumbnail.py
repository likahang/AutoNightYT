#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動縮圖生成工具
"""

import os
import sys
import subprocess
import glob
import time
from datetime import datetime
from pathlib import Path

try:
    from tkinter import filedialog, Tk, simpledialog, Label, Entry, Button, Frame
except ImportError:
    print("❌ 無法載入 tkinter")
    input("按 Enter 鍵結束")
    sys.exit(1)


def main():
    print("=" * 50)
    print("  自動縮圖生成工具")
    print("=" * 50)
    print()

    # 1. 獲取日期
    print("[1/5] 獲取日期...")
    mmdd = datetime.now().strftime("%m%d")
    print(f"日期: {mmdd}")
    print()

    # 1.5 獲取製作者
    print("[1.5/5] 獲取製作者...")
    root_input = Tk()
    root_input.title("製作者")
    root_input.attributes('-topmost', True)
    
    # 創建自定義對話框
    frame = Frame(root_input, padx=20, pady=20)
    frame.pack()
    
    Label(frame, text="請輸入製作者名稱:", font=("Arial", 10)).pack(anchor="w", pady=(0, 10))
    
    entry_frame = Frame(frame)
    entry_frame.pack(anchor="w", fill="x")
    
    Label(entry_frame, text="_", font=("Arial", 10)).pack(side="left")
    entry = Entry(entry_frame, width=40, font=("Arial", 10))
    entry.pack(side="left", padx=(5, 0))
    entry.focus()
    
    creator = None
    
    def on_ok():
        nonlocal creator
        creator = entry.get()
        root_input.destroy()
    
    def on_cancel():
        root_input.destroy()
    
    button_frame = Frame(frame)
    button_frame.pack(pady=(10, 0))
    
    Button(button_frame, text="確認", command=on_ok, width=10).pack(side="left", padx=5)
    Button(button_frame, text="取消", command=on_cancel, width=10).pack(side="left", padx=5)
    
    root_input.mainloop()
    
    if creator is None or creator.strip() == "":
        print("已取消")
        input("按 Enter 鍵結束")
        sys.exit(1)
    
    print(f"✓ 製作者: {creator}")
    print()

    # 2. 選擇檔案
    print("[2/5] 開啟檔案選擇對話框...")
    root = Tk()
    root.withdraw()  # 隱藏 Tkinter 視窗
    root.attributes('-topmost', True)  # 置於最前

    default_path = f"\\\\10.227.58.117\\新聞txt\\{mmdd}\\1800"

    try:
        selected_files = filedialog.askopenfilenames(
            title="選擇縮圖文字檔案 (可選擇多個)",
            initialdir=default_path if os.path.exists(default_path) else os.path.expanduser("~"),
            filetypes=[("TXT files", "*.txt"), ("All files", "*.*")]
        )
    except Exception as e:
        print(f"❌ 檔案選擇對話框出錯: {e}")
        input("按 Enter 鍵結束")
        sys.exit(1)
    finally:
        root.destroy()

    if not selected_files:
        print("已取消選擇")
        input("按 Enter 鍵結束")
        sys.exit(1)

    print(f"選擇了 {len(selected_files)} 個檔案：")
    for i, f in enumerate(selected_files, 1):
        print(f"  {i}. {os.path.basename(f)}")
    print()

    # 3. 取得工作目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[3/5] 工作目錄: {script_dir}")
    print()

    # 3.5 計算 PSD 輸出目錄
    psd_output_dir = f"\\\\10.227.58.117\\新聞psd\\{mmdd}\\縮圖"
    try:
        # 確保目錄存在
        os.makedirs(psd_output_dir, exist_ok=True)
        print(f"✓ PSD 輸出目錄: {psd_output_dir}")
    except Exception as e:
        print(f"⚠ 無法建立 PSD 輸出目錄: {e}")
        print(f"  將使用本地目錄替代")
        psd_output_dir = "."
    print()

    # 4. 為每個檔案生成 Photoshop 腳本
    print("[4/5] 生成 Photoshop 腳本...")
    venv_python = os.path.join(script_dir, ".venv", "Scripts", "python.exe")

    if not os.path.exists(venv_python):
        print("❌ 找不到 Python 虛擬環境")
        input("按 Enter 鍵結束")
        sys.exit(1)

    # 為每個選中的檔案生成 JSX
    jsx_files_to_run = []
    
    for i, selected_file in enumerate(selected_files, 1):
        print(f"\n處理檔案 {i}/{len(selected_files)}: {os.path.basename(selected_file)}")
        
        try:
            result = subprocess.run(
                [
                    venv_python,
                    "generate_photoshop_script.py",
                    "--file", selected_file,
                    "--csv", "晚報變色.csv",
                    "--psd", "晚報YT縮圖.psd",
                    "--output-dir", psd_output_dir,
                    "--creator", creator
                ],
                cwd=script_dir,
                capture_output=False
            )

            if result.returncode != 0:
                print(f"❌ 檔案 {i} 的 Python 腳本執行失敗")
                continue
            
            # 找出剛生成的 JSX 檔案（在網路路徑中）
            jsx_files = sorted(
                glob.glob(os.path.join(psd_output_dir, "modify_thumbnail_*.jsx")),
                key=lambda x: os.path.getmtime(x),
                reverse=True
            )
            
            if jsx_files:
                latest_jsx = jsx_files[0]
                jsx_files_to_run.append(latest_jsx)
                print(f"✓ 生成 JSX: {os.path.basename(latest_jsx)}")
                
        except Exception as e:
            print(f"❌ 處理檔案 {i} 時出錯: {e}")
            continue
    
    print()
    
    if not jsx_files_to_run:
        print("❌ 沒有成功生成任何 JSX 檔案")
        input("按 Enter 鍵結束")
        sys.exit(1)
    
    print(f"✓ 共生成 {len(jsx_files_to_run)} 個 JSX 檔案")
    print()

    # 5. 在 Photoshop 中執行所有 JSX 腳本
    print("[5/5] 在 Photoshop 中執行腳本...")
    print()

    # 先嘗試禁用 Photoshop 的腳本安全警告
    print("配置 Photoshop 設置...")
    try:
        import winreg
        
        # Photoshop 2024 的登錄檔路徑
        reg_paths = [
            r"Software\Adobe\Photoshop\2024\Photoshop Settings",
            r"Software\Adobe\Photoshop\25.0\Photoshop Settings",
        ]
        
        for reg_path in reg_paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "DisableWarnBeforeExecutingUserAdobeScripts", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "Allow JavaScript Files To Read And Write Files And Access The Network", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                print("✓ Photoshop 安全設置已更新")
                break
            except:
                pass
    except Exception as e:
        print(f"⚠ 無法更新 Photoshop 登錄檔: {e}")
    
    # 配置 PSUserConfig.txt 以禁用腳本警告
    try:
        ps_settings_dir = os.path.expandvars(r"%APPDATA%\Adobe\Adobe Photoshop 2024\Adobe Photoshop 2024 Settings")
        ps_config_file = os.path.join(ps_settings_dir, "PSUserConfig.txt")
        
        # 確保目錄存在
        if not os.path.exists(ps_settings_dir):
            os.makedirs(ps_settings_dir, exist_ok=True)
        
        # 檢查並修改 PSUserConfig.txt
        config_updated = False
        if os.path.exists(ps_config_file):
            with open(ps_config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果沒有包含 WarnRunningScripts，就加入
            if "WarnRunningScripts" not in content:
                with open(ps_config_file, 'a', encoding='utf-8') as f:
                    f.write("\nWarnRunningScripts 0\n")
                config_updated = True
        else:
            # 創建新的 PSUserConfig.txt
            with open(ps_config_file, 'w', encoding='utf-8') as f:
                f.write("WarnRunningScripts 0\n")
            config_updated = True
        
        if config_updated:
            print("✓ PSUserConfig.txt 已配置")
    except Exception as e:
        print(f"⚠ 無法配置 PSUserConfig.txt: {e}")

    print()
    
    # 依序執行每個 JSX 檔案，等待每個完成後才執行下一個
    template_psd = os.path.join(script_dir, "晚報YT縮圖.psd")
    generated_psds = []
    
    for i, jsx_path in enumerate(jsx_files_to_run, 1):
        print("=" * 50)
        print(f"[{i}/{len(jsx_files_to_run)}] 執行: {os.path.basename(jsx_path)}")
        print("=" * 50)
        
        # 使用命令列方式啟動 Photoshop，避免安全警告
        photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe"
        jsx_path_abs = os.path.abspath(jsx_path)
        
        try:
            if os.path.exists(photoshop_exe):
                # 使用 -r 參數來直接執行 JSX，避免安全警告
                subprocess.Popen([photoshop_exe, "-r", jsx_path_abs])
            else:
                # 如果找不到 Photoshop，使用舊的方法
                os.startfile(jsx_path)
            print("✓ JSX 已發送至 Photoshop")
        except Exception as e:
            print(f"❌ 無法啟動: {e}")
            continue
        
        print()
        print("等待 PSD 檔案生成...")
        print()
        
        # 等待該 JSX 產生的 PSD 檔案（最多等待 600 秒 = 10 分鐘，給大檔案更多時間）
        max_wait = 600
        wait_start = time.time()
        psd_found = False
        
        # 記錄執行前已存在的檔案（在輸出目錄中）
        files_before = set(glob.glob(os.path.join(psd_output_dir, "*.psd"))) | set(glob.glob(os.path.join(psd_output_dir, "*.jpg")))
        
        while time.time() - wait_start < max_wait:
            time.sleep(2)
            elapsed = int(time.time() - wait_start)
            
            # 檢查是否生成了新的檔案（在輸出目錄中）
            all_files = glob.glob(os.path.join(psd_output_dir, "*.psd")) + glob.glob(os.path.join(psd_output_dir, "*.jpg"))
            
            for file_path in all_files:
                # 尋找新生成的檔案（不在之前的列表中，且還沒被記錄過）
                if file_path not in files_before and file_path not in generated_psds:
                    generated_psds.append(file_path)
                    print(f"✓ 檔案已生成: {os.path.basename(file_path)}")
                    # 如果生成的是 JPG，就認為完成
                    if file_path.lower().endswith('.jpg'):
                        psd_found = True
                        break
            
            if psd_found:
                break
            
            # 顯示進度
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"  已監控 {elapsed} 秒...", end='\r')
        
        print()
        
        if not psd_found:
            print(f"⚠ 檔案 {i} 在規定時間內未能生成 PSD")
        else:
            print(f"✓ 檔案 {i} 已完成，準備執行下一個...")
        
        print()
    
    print()
    print("=" * 50)
    print("✓ 所有檔案已處理完成！")
    print("=" * 50)
    print()
    
    # 刪除所有 JSX 檔案
    print("清理暫存檔案...")
    deleted_count = 0
    for jsx_path in jsx_files_to_run:
        try:
            if os.path.exists(jsx_path):
                os.remove(jsx_path)
                deleted_count += 1
        except Exception as e:
            print(f"⚠ 刪除 {os.path.basename(jsx_path)} 時出錯: {e}")
    
    print(f"✓ 已刪除 {deleted_count} 個 JSX 檔案")

    print()
    
    if len(generated_psds) >= len(jsx_files_to_run):
        print("=" * 50)
        print("✓ 完成！")
        print(f"已成功生成 {len(generated_psds)} 個 PSD 檔案：")
        for psd_path in sorted(generated_psds):
            print(f"  - {os.path.basename(psd_path)}")
        print("=" * 50)
        print()
        print("程式將自動關閉...")
        time.sleep(2)
        sys.exit(0)
    else:
        print("⚠ 未在規定時間內檢測到 PSD 檔案生成")
        print("可能的原因:")
        print("- Photoshop 未執行腳本")
        print("- 腳本執行失敗")
        print()
        input("按 Enter 鍵結束")


if __name__ == "__main__":
    main()
