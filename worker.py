#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
後台工作線程 - 執行實際的文件生成
"""

import os
import subprocess
import sys
import time
import glob
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from generate_photoshop_script import run_generation_logic
from parse_thumbnail_txt import prepare_file_data


class GenerationWorker(QThread):
    """文件生成工作線程"""
    
    # 信號定義
    progress = pyqtSignal(int, int, str)  # (當前索引, 總數, 檔案名稱)
    log = pyqtSignal(str)  # (日誌信息)
    completed = pyqtSignal(int, int, int)  # (成功數, 失敗數, 總數)
    error = pyqtSignal(str)  # (錯誤信息)
    warning = pyqtSignal(str)  # 可略過的單檔警告
    file_completed = pyqtSignal(str, str)  # (filename, jpg_path) - 檔案完成並生成 JPG
    file_failed = pyqtSignal(str)  # (filename) - 檔案生成失敗
    
    def __init__(self, checked_files, date, creator, folder_path):
        super().__init__()
        self.checked_files = checked_files
        self.date = date
        self.creator = creator
        self.folder_path = folder_path
        self.is_running = True
        self.is_paused = False
    
    def pause(self):
        """暫停線程"""
        self.is_paused = True
    
    def resume(self):
        """恢復線程"""
        self.is_paused = False
    
    def stop(self):
        """停止線程"""
        self.is_running = False
        self.is_paused = False # 確保如果暫停中也能退出
    
    def clean_jsx_output_folder(self):
        """清理 JSX 輸出資料夾"""
        try:
            desktop_dir = Path.home() / "Desktop"
            jsx_output_dir = desktop_dir / "晚報YT腳本"
            
            if jsx_output_dir.exists():
                count = 0
                # 只刪除 .jsx 和 .log 檔案，避免誤刪
                for file_path in list(jsx_output_dir.glob("*.jsx")) + list(jsx_output_dir.glob("*.log")):
                    try:
                        file_path.unlink()
                        count += 1
                    except:
                        pass
                if count > 0:
                    self.log.emit(f"🧹 已清理舊的腳本檔案: {count} 個")
        except Exception as e:
            self.log.emit(f"⚠️ 清理腳本資料夾失敗: {e}")

    def run(self):
        """執行文件生成"""
        try:
            # 啟動時先清理舊檔案
            self.clean_jsx_output_folder()
            
            total_count = len(self.checked_files)
            success_count = 0
            failed_count = 0
            
            self.log.emit(f"[第 1 階段] 生成 JSX 腳本...")
            
            # 第 1 階段：生成所有 JSX 腳本並記錄對應關係
            jsx_map = {}  # {filename: jsx_path}
            
            for index, filename in enumerate(self.checked_files):
                if not self.is_running:
                    break
                
                try:
                    file_path = os.path.join(self.folder_path, filename)
                    if not os.path.exists(file_path):
                        self.log.emit(f"❌ [{index+1}/{total_count}] 文件不存在: {filename}")
                        failed_count += 1
                        continue

                    # 先判定版型並驗證標圖版的圖片指示／圖片路徑。
                    parsed = prepare_file_data(file_path, self.date)
                    if not parsed:
                        warning_message = f"{filename}\n解析失敗，已略過該檔。"
                        self.log.emit(f"⚠️ {warning_message.replace(chr(10), ' ')}")
                        self.warning.emit(warning_message)
                        failed_count += 1
                        self.file_failed.emit(filename)
                        continue
                    if parsed.get("validation_errors"):
                        details = "\n".join(f"• {item}" for item in parsed["validation_errors"])
                        warning_message = f"{filename}\n{details}\n\n已略過該檔。"
                        self.log.emit(f"⚠️ {filename}：{'；'.join(parsed['validation_errors'])}（已略過）")
                        self.warning.emit(warning_message)
                        failed_count += 1
                        self.file_failed.emit(filename)
                        continue

                    self.log.emit(f"  版型判定: {parsed['layout_type']}")
                    
                    # 第一階段不更新進度條，僅記錄日誌
                    # self.progress.emit(index + 1, filename)
                    self.log.emit(f"⏳ [{index+1}/{total_count}] 生成 JSX: {filename}")
                    
                    # 生成 JSX 腳本並獲取路徑
                    jsx_path = self.generate_jsx_with_path(file_path)
                    
                    if jsx_path:
                        self.log.emit(f"✓ [{index+1}/{total_count}] JSX 已生成: {filename}")
                        jsx_map[filename] = jsx_path
                        success_count += 1
                    else:
                        self.log.emit(f"❌ [{index+1}/{total_count}] JSX 生成失敗: {filename}")
                        failed_count += 1
                        self.file_failed.emit(filename)  # 發送失敗信號
                        
                except Exception as e:
                    self.log.emit(f"❌ [{index+1}/{total_count}] 錯誤: {str(e)}")
                    failed_count += 1
                    self.file_failed.emit(filename)  # 發送失敗信號
            
            if not jsx_map:
                self.log.emit("❌ 未能生成任何 JSX 文件")
                self.completed.emit(0, total_count, total_count)
                return
            
            # 第 2 階段：逐個執行 Photoshop
            self.log.emit(f"\n[第 2 階段] 執行 Photoshop 生成文件... ({len(jsx_map)} 個)")
            self.setup_photoshop_security()
            
            psd_output_dir = f"\\\\10.227.58.117\\新聞psd\\{self.date}\\縮圖"
            success_count = 0
            
            for idx, (filename, jsx_path) in enumerate(jsx_map.items(), 1):
                if not self.is_running:
                    break
                
                # 處理暫停邏輯
                while self.is_paused:
                    if not self.is_running:
                        break
                    time.sleep(0.5) # 每 0.5 秒檢查一次
                
                if not self.is_running:
                    break
                
                self.log.emit(f"⏳ [{idx}/{len(jsx_map)}] 執行 Photoshop: {filename}")
                
                result = self.run_photoshop_jsx(jsx_path, filename, psd_output_dir)
                
                # 發送進度信號 (當前, 總數, 檔案名)
                # 只有在執行完成後才更新進度條，確保使用者看到縮圖後進度條才前進
                # 當前進度 = 第一階段失敗數 + 當前處理序號
                current_progress = failed_count + idx
                self.progress.emit(current_progress, total_count, filename)
                
                if result:
                    self.log.emit(f"✓ [{idx}/{len(jsx_map)}] 完成: {filename}")
                    success_count += 1
                else:
                    self.log.emit(f"❌ [{idx}/{len(jsx_map)}] 失敗: {filename}")
            
            # 發送完成信號
            final_failed = total_count - success_count
            self.log.emit(f"\n✓ 批次處理完成 - 成功: {success_count}, 失敗: {final_failed}")
            self.log.emit("✓ Photoshop 保持開啟，可繼續使用或手動關閉")
            
            self.completed.emit(success_count, final_failed, total_count)
            
        except Exception as e:
            self.error.emit(f"致命錯誤: {str(e)}")
    
    def generate_jsx_with_path(self, file_path):
        """生成 JSX 腳本並返回其路徑"""
        try:
            desktop_dir = Path.home() / "Desktop"
            jsx_output_dir = desktop_dir / "晚報YT腳本"
            
            # 記錄執行前的 JSX 文件
            jsx_before = set(glob.glob(os.path.join(jsx_output_dir, "*.jsx")))
            
            # 生成 JSX
            result = self.generate_jsx(file_path)
            
            if result != 0:
                self.log.emit(f"⚠️ JSX 生成進程返回非零碼: {result}")
                return None
            
            # 找出新生成的 JSX 文件
            time.sleep(0.5)
            jsx_after = set(glob.glob(os.path.join(jsx_output_dir, "*.jsx")))
            new_jsx = jsx_after - jsx_before
            
            if new_jsx:
                return list(new_jsx)[0]
            
            # 如果沒有檢測到新文件，查看是否有最新修改的 JSX 文件
            all_jsx_files = glob.glob(os.path.join(jsx_output_dir, "*.jsx"))
            if all_jsx_files:
                latest_jsx = max(all_jsx_files, key=lambda f: os.path.getmtime(f))
                # 檢查最新文件的修改時間是否在最近 5 秒內
                if time.time() - os.path.getmtime(latest_jsx) < 5:
                    self.log.emit(f"✓ 使用最新生成的 JSX: {os.path.basename(latest_jsx)}")
                    return latest_jsx
            
            self.log.emit(f"⚠️ 未能檢測到新生成的 JSX 文件")
            return None
            
        except Exception as e:
            self.log.emit(f"獲取 JSX 路徑錯誤: {str(e)}")
            import traceback
            self.log.emit(f"詳細信息: {traceback.format_exc()}")
            return None
    
    def generate_jsx(self, file_path):
        """生成 JSX 腳本"""
        try:
            script_dir = Path(__file__).parent
            
            desktop_dir = Path.home() / "Desktop"
            jsx_output_dir = desktop_dir / "晚報YT腳本"
            jsx_output_dir.mkdir(exist_ok=True)
            
            psd_output_dir = f"\\\\10.227.58.117\\新聞psd\\{self.date}\\縮圖"
            
            # 處理資源路徑 (支援打包後環境)
            if hasattr(sys, '_MEIPASS'):
                 base_path = Path(sys._MEIPASS)
            else:
                 base_path = script_dir

            csv_file = base_path / "晚報變色.csv"
            psd_file = base_path / "晚報YT縮圖.psd"
            labeled_psd_file = base_path / "晚報YT縮圖(標圖版).psd"
            
            self.log.emit(f"⚙️ 執行生成邏輯: {os.path.basename(file_path)}")
            
            # 調用 Python 函數直接執行，不需要 subprocess
            result_code = run_generation_logic(
                str(file_path),
                None, # color_id (隨機)
                str(psd_file),
                str(csv_file),
                str(jsx_output_dir),
                psd_output_dir,
                self.creator,
                self.date,
                str(labeled_psd_file),
            )
            
            if result_code != 0:
                self.log.emit(f"⚠️ JSX 生成返回錯誤代碼: {result_code}")
            else:
                self.log.emit(f"✓ JSX 生成成功")
            
            return result_code
            
        except Exception as e:
            self.log.emit(f"JSX 生成錯誤: {str(e)}")
            import traceback
            self.log.emit(f"詳細信息: {traceback.format_exc()}")
            return 1
    
    def setup_photoshop_security(self):
        """配置 Photoshop 安全設置"""
        try:
            import winreg
            reg_paths = [
                r"Software\Adobe\Photoshop\2024\Photoshop Settings",
                r"Software\Adobe\Photoshop\25.0\Photoshop Settings",
            ]
            
            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
                    winreg.SetValueEx(key, "DisableWarnBeforeExecutingUserAdobeScripts", 0, winreg.REG_DWORD, 1)
                    winreg.CloseKey(key)
                    self.log.emit("✓ Photoshop 安全設置已配置")
                    break
                except:
                    pass
        except:
            pass
    
    def run_photoshop_jsx(self, jsx_path, filename, psd_output_dir):
        """執行 Photoshop JSX 文件並返回生成的 JPG 路徑"""
        try:
            photoshop_exe = r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe"
            jsx_path_abs = os.path.abspath(jsx_path)
            
            if not os.path.exists(photoshop_exe):
                self.log.emit("⚠ Photoshop 執行檔未找到")
                return None
            
            # 確保輸出文件夾存在
            if not os.path.exists(psd_output_dir):
                try:
                    os.makedirs(psd_output_dir, exist_ok=True)
                except Exception as e:
                    self.log.emit(f"  ⚠️ 無法創建文件夾: {str(e)}")
                    return None
            
            # JPG 輸出文件夾
            jpg_output_dir = os.path.join(psd_output_dir, "JPG")
            if not os.path.exists(jpg_output_dir):
                try:
                    os.makedirs(jpg_output_dir, exist_ok=True)
                except:
                    pass

            # 記錄開始前有哪些 JPG 檔案 (在 JPG 子目錄中)
            files_before = {}
            if os.path.exists(jpg_output_dir):
                for file_path in glob.glob(os.path.join(jpg_output_dir, "*.jpg")):
                    if os.path.isfile(file_path):
                        files_before[file_path] = os.path.getmtime(file_path)
            
            self.log.emit(f"  啟動執行: {os.path.basename(jsx_path)}")
            self.log.emit(f"  JSX 路徑: {jsx_path_abs}")
            self.log.emit(f"  輸出目錄 (PSD): {psd_output_dir}")
            self.log.emit(f"  輸出目錄 (JPG): {jpg_output_dir}")
            
            # 直接使用 -r 參數執行 JSX（這是穩定的方式）
            try:
                subprocess.Popen([photoshop_exe, "-r", jsx_path_abs])
                self.log.emit(f"  ✓ JSX 已發送至 Photoshop")
            except Exception as e:
                self.log.emit(f"  ❌ 無法啟動 Photoshop: {e}")
                return None
            
            # 等待檔案生成
            self.log.emit(f"  等待 PSD/JPG 檔案生成中... (最多 600 秒)")
            
            max_wait = 600
            wait_start = time.time()
            
            while time.time() - wait_start < max_wait:
                time.sleep(1)  # 每秒檢查一次
                
                elapsed = int(time.time() - wait_start)
                
                # 檢查是否有新的 JPG 檔案
                current_files = {}
                if os.path.exists(jpg_output_dir):
                    for file_path in glob.glob(os.path.join(jpg_output_dir, "*.jpg")):
                        if os.path.isfile(file_path):
                            current_files[file_path] = os.path.getmtime(file_path)
                
                # 找到新生成的 JPG (全新文件 或 修改時間更新的文件)
                new_files = []
                for f, mtime in current_files.items():
                    if f not in files_before:
                        new_files.append(f)
                    elif mtime > files_before[f]:
                        new_files.append(f)
                
                if new_files:
                    # 選擇最新的 JPG 檔案
                    newest_jpg = max(new_files, key=lambda f: current_files[f])
                    
                    # 等待一段時間確保檔案完全寫入並釋放鎖定
                    # (特別是透過網路路徑時，檔案系統可能有延遲)
                    time.sleep(2)
                    
                    self.log.emit(f"  ✓ 生成文件: {os.path.basename(newest_jpg)}")
                    
                    # 發送信號通知 GUI 更新縮圖
                    self.file_completed.emit(filename, newest_jpg)
                    
                    return newest_jpg
                
                # 每 10 秒打印一次進度
                if elapsed % 10 == 0:
                    self.log.emit(f"  等待中... ({elapsed} 秒)")
            
            # 超時
            self.log.emit(f"  ⏳ 等待超時 (600 秒) - 可能 Photoshop 還在處理")
            return None
            
        except Exception as e:
            self.log.emit(f"執行 JSX 錯誤: {str(e)}")
            import traceback
            self.log.emit(f"  詳細信息: {traceback.format_exc()}")
            return None
    
    def run_generation(self, file_path):
        """執行單個文件的生成流程（舊方法，保留以相容性）"""
        return self.generate_jsx(file_path)
    
    def stop(self):
        """停止工作線程"""
        self.is_running = False
        self.wait()
