#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動縮圖生成系統 - GUI 主程序
Modern Dark Mode with Neon Accent Colors
"""

import sys
import os
import json
import math
import random
import xml.etree.ElementTree as ET
from worker import GenerationWorker
import re
from datetime import datetime
from pathlib import Path
from functools import partial
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QCheckBox, QSpinBox, QComboBox,
    QScrollArea, QFrame, QProgressBar, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QGridLayout, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QElapsedTimer, QRectF, QByteArray
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QCursor, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QSize
import subprocess
import glob
from parse_thumbnail_txt import (
    ANCHOR_NAMES,
    get_text_directory_candidates,
    infer_mmdd_from_path,
    is_valid_mmdd,
    parse_file,
    prepare_file_data,
)
from generate_photoshop_script import (
    get_color_scheme_source_description,
    load_color_schemes,
    load_top_right_colors,
)


UNRECORDED_CONFIG = "未記錄"


def format_generation_stats(pending, completed, failed):
    return f"待生成: {pending} ｜ 已完成: {completed} ｜ 失敗: {failed}"


def resolve_visual_config(override=None, resolved=None, persisted=None):
    """依自訂、已完成生成、歷史紀錄的順序取得縮圖實際設定。"""
    sources = (override or {}, resolved or {}, persisted or {})
    visual = {}
    for key in ("color_id", "top_right_color"):
        for source in sources:
            value = str(source.get(key, "") or "").strip()
            if value:
                visual[key] = value
                break
    return visual

# ===== 配色方案 =====
class DarkTheme:
    # 主色調
    BG_PRIMARY = "#1e1e2e"      # 深炭灰色背景
    BG_SECONDARY = "#2a2a3e"    # 稍淺的背景
    BG_TERTIARY = "#32323f"     # 更淺的背景
    
    # 強調色（霓虹色系）
    ACCENT_PINK = "#FF006E"     # 霓虹粉
    ACCENT_CYAN = "#00D9FF"     # 霓虹青
    ACCENT_PURPLE = "#B537F2"   # 亮紫
    ACCENT_GREEN = "#00FF41"    # 霓虹綠（成功）
    ACCENT_RED = "#FF0055"      # 霓虹紅（錯誤）
    ACCENT_ORANGE = "#FFB000"   # 霓虹橙（警告）
    
    # 文本顏色
    TEXT_PRIMARY = "#E0E0E0"    # 主文本
    TEXT_SECONDARY = "#A0A0A0"  # 次要文本
    TEXT_HINT = "#707070"       # 提示文本
    
    # 邊框
    BORDER = "#4a4a5e"          # 邊框顏色

# ===== 樣式表 =====
STYLESHEET = f"""
QMainWindow {{
    background-color: {DarkTheme.BG_PRIMARY};
    color: {DarkTheme.TEXT_PRIMARY};
}}

QWidget {{
    background-color: {DarkTheme.BG_PRIMARY};
    color: {DarkTheme.TEXT_PRIMARY};
}}

QLabel {{
    color: {DarkTheme.TEXT_PRIMARY};
}}

QLineEdit {{
    background-color: {DarkTheme.BG_SECONDARY};
    color: {DarkTheme.TEXT_PRIMARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 5px;
    padding: 5px;
    font-size: 11pt;
}}

QLineEdit:focus {{
    border: 2px solid {DarkTheme.ACCENT_CYAN};
}}

QPushButton {{
    background-color: {DarkTheme.ACCENT_PINK};
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 11pt;
}}

QPushButton:hover {{
    background-color: {DarkTheme.ACCENT_PURPLE};
}}

QPushButton:pressed {{
    background-color: {DarkTheme.ACCENT_RED};
}}

QPushButton:disabled {{
    background-color: {DarkTheme.BG_TERTIARY};
    color: {DarkTheme.TEXT_HINT};
}}

QListWidget {{
    background-color: {DarkTheme.BG_SECONDARY};
    color: {DarkTheme.TEXT_PRIMARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 5px;
}}

QListWidget::item:selected {{
    background-color: {DarkTheme.ACCENT_CYAN};
    color: {DarkTheme.BG_PRIMARY};
}}

QListWidget::item:hover {{
    background-color: {DarkTheme.ACCENT_PURPLE};
    color: white;
}}

QTextEdit {{
    background-color: {DarkTheme.BG_SECONDARY};
    color: {DarkTheme.TEXT_PRIMARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 5px;
    font-family: 'Courier New';
    font-size: 10pt;
}}

QFrame {{
    background-color: {DarkTheme.BG_SECONDARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 5px;
}}

QProgressBar {{
    background-color: {DarkTheme.BG_TERTIARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 5px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {DarkTheme.ACCENT_GREEN};
    border-radius: 3px;
}}

QCheckBox {{
    color: {DarkTheme.TEXT_PRIMARY};
}}

QCheckBox::indicator:unchecked {{
    background-color: {DarkTheme.BG_TERTIARY};
    border: 1px solid {DarkTheme.BORDER};
    border-radius: 3px;
}}

QCheckBox::indicator:checked {{
    background-color: {DarkTheme.ACCENT_CYAN};
    border: 1px solid {DarkTheme.ACCENT_CYAN};
    border-radius: 3px;
}}

QScrollBar:vertical {{
    background-color: {DarkTheme.BG_SECONDARY};
    width: 12px;
}}

QScrollBar::handle:vertical {{
    background-color: {DarkTheme.BORDER};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {DarkTheme.ACCENT_PINK};
}}

QMenuBar {{
    background-color: {DarkTheme.BG_SECONDARY};
    color: {DarkTheme.TEXT_PRIMARY};
    border-bottom: 1px solid {DarkTheme.BORDER};
}}

QMenuBar::item:selected {{
    background-color: {DarkTheme.ACCENT_PURPLE};
}}

QMenu {{
    background-color: {DarkTheme.BG_SECONDARY};
    color: {DarkTheme.TEXT_PRIMARY};
    border: 1px solid {DarkTheme.BORDER};
}}

QMenu::item:selected {{
    background-color: {DarkTheme.ACCENT_CYAN};
    color: {DarkTheme.BG_PRIMARY};
}}
"""


# ===== 自訂排序函數 =====
def extract_numbers_for_sort(filename):
    """從檔名提取所有數字用於排序"""
    # 從檔名中提取所有數字，轉換為整數列表用於排序
    numbers = re.findall(r'\d+', filename)
    # 返回包含數字的元組，便於比較
    # 例如: "1800晚報YT縮周2..." -> (1800, 2)
    return tuple(int(n) for n in numbers) if numbers else (0,)

def sanitize_filename_part(text):
    """單獨淨化檔名的一部分 (Slag)，模擬生成腳本的行為"""
    # 替換 Windows 非法字元
    invalid_chars = r'[<>:"/\\|?*]'
    text = re.sub(invalid_chars, '_', text)
    text = text.strip() # 去除前後空白
    text = re.sub(r'__+', '_', text) # 合併底線
    return text

def normalize_string_for_compare(text):
    """標準化字串用於比較 (移除所有空白、底線、橫線)"""
    return re.sub(r'[\s_\-]', '', text).lower()

class FileListWidget(QListWidget):
    """自訂文件列表小部件"""
    def __init__(self):
        super().__init__()
        self.setSelectionMode(self.SelectionMode.MultiSelection)
        self.item_checked = {}  # 記錄勾選狀態
        
    def add_file(self, filename):
        """添加文件到列表"""
        item = QListWidgetItem()
        item.setText(f"☐ {filename}")
        item.setData(Qt.ItemDataRole.UserRole, filename)
        self.addItem(item)
        self.item_checked[filename] = False
        
    def get_checked_files(self):
        """獲取所有勾選的文件"""
        checked = []
        for filename, is_checked in self.item_checked.items():
            if is_checked:
                checked.append(filename)
        return checked
    
    def toggle_all(self):
        """全選/全不選"""
        # 檢查是否已經全部被選中
        all_checked = all(self.item_checked.values())
        
        # 如果全部已選，則全不選；否則全選
        new_state = not all_checked
        
        for filename in self.item_checked:
            self.item_checked[filename] = new_state
        self.update_display()
    
    def refresh_list(self):
        """反向切換選擇 (保留方法名) 或 刷新列表"""
        pass # 由外部控制
    
    def update_display(self):
        """更新顯示"""
        for i in range(self.count()):
            item = self.item(i)
            filename = item.data(Qt.ItemDataRole.UserRole)
            is_checked = self.item_checked.get(filename, False)
            checkbox_symbol = "☑" if is_checked else "☐"
            item.setText(f"{checkbox_symbol} {filename}")
    
    def mousePressEvent(self, event):
        """滑鼠點擊時切換勾選狀態"""
        item = self.itemAt(event.pos())
        if item:
            filename = item.data(Qt.ItemDataRole.UserRole)
            self.item_checked[filename] = not self.item_checked[filename]
            self.update_display()
        super().mousePressEvent(event)


class CGLoadingOverlay(QWidget):
    """在縮圖上透明播放 CGLoading SVG 的描線動畫。"""

    DEFAULT_SVG_PATH = Path.home() / "Documents" / "CGLoading" / "cg-indigo-loader.svg"

    def __init__(self, parent=None, svg_path=None):
        super().__init__(parent)
        self.svg_path = Path(svg_path or self.DEFAULT_SVG_PATH)
        self.path_data = self._load_path_data()
        self.elapsed = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def _load_path_data(self):
        """從指定 SVG 讀取兩段 CG 路徑，避免複製另一份動畫資產。"""
        try:
            root = ET.parse(self.svg_path).getroot()
            paths = [
                element.attrib.get("d", "")
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == "path" and element.attrib.get("d")
            ]
            if len(paths) >= 4:
                return paths[0], paths[1], paths[2], paths[3]
        except (OSError, ET.ParseError):
            pass
        return None

    def start(self):
        """開始動畫；資產不存在時交由呼叫端顯示文字備援。"""
        if not self.path_data:
            return False
        self.elapsed.start()
        self.show()
        self.raise_()
        self.timer.start()
        self.update()
        return True

    def stop(self):
        self.timer.stop()
        self.hide()

    @staticmethod
    def _ease(progress):
        progress = max(0.0, min(1.0, progress))
        return 0.5 - math.cos(math.pi * progress) / 2

    @classmethod
    def _between(cls, phase, start, end, start_value, end_value):
        if phase <= start:
            return start_value
        if phase >= end:
            return end_value
        progress = cls._ease((phase - start) / (end - start))
        return start_value + (end_value - start_value) * progress

    def _render_svg(self, phase):
        track1, track2, anim1, anim2 = self.path_data

        if phase < 0.25:
            offset1 = self._between(phase, 0.0, 0.25, 1000, 0)
        elif phase < 0.50:
            offset1 = 0
        elif phase < 0.65:
            offset1 = self._between(phase, 0.50, 0.65, 0, 1000)
        else:
            offset1 = 1000

        if phase < 0.25:
            offset2 = 1000
            opacity2 = 1
        elif phase < 0.50:
            offset2 = self._between(phase, 0.25, 0.50, 1000, 0)
            opacity2 = 1
        elif phase < 0.75:
            offset2 = 0
            opacity2 = 1
        elif phase < 0.90:
            offset2 = self._between(phase, 0.75, 0.90, 0, -1000)
            opacity2 = 1
        else:
            offset2 = -1000
            opacity2 = max(0.0, 1.0 - (phase - 0.90) / 0.05)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="600 330 200 120">
<g fill="none" stroke="#6366f1" stroke-width="7" stroke-miterlimit="10" opacity="0.2">
<path d="{track1}"/><path d="{track2}"/>
</g>
<g fill="none" stroke="#6366f1" stroke-width="7" stroke-linecap="round" stroke-miterlimit="10" stroke-dasharray="1000">
<path d="{anim1}" stroke-dashoffset="{offset1:.2f}"/>
<path d="{anim2}" stroke-dashoffset="{offset2:.2f}" opacity="{opacity2:.3f}"/>
</g></svg>'''
        return QSvgRenderer(QByteArray(svg.encode("utf-8")))

    def paintEvent(self, event):
        if not self.path_data or not self.elapsed.isValid():
            return
        phase = (self.elapsed.elapsed() % 4000) / 4000.0
        renderer = self._render_svg(phase)
        if not renderer.isValid():
            return

        width = min(200.0, max(100.0, self.width() * 0.55))
        height = width * 0.60
        target = QRectF(
            (self.width() - width) / 2,
            (self.height() - height) / 2,
            width,
            height,
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, target)


class AspectRatioLabel(QLabel):
    """保持寬高比的標籤"""
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.original_pixmap = None
        self.loading_overlay = None
        self.loading_active = False
        self.loading_fallback_text = ""

    def setPixmap(self, p):
        self.original_pixmap = p
        self.update()

    def setText(self, text):
        self.original_pixmap = None
        super().setText(text)

    def setLoading(self, active, fallback_text=""):
        """重新生成時暫時隱藏縮圖，但保留原圖供失敗時恢復。"""
        self.loading_active = active
        self.loading_fallback_text = fallback_text if active else ""
        self.update()
    
    def hasHeightForWidth(self):
        """告訴 Layout 系統我們有基於寬度的高度計算"""
        return True

    def heightForWidth(self, width):
        """計算保持 16:9 的高度"""
        return int(width * 9 / 16)
        
    def paintEvent(self, event):
        if self.loading_active:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(DarkTheme.BG_TERTIARY))
            if self.loading_fallback_text:
                painter.setPen(QColor(DarkTheme.TEXT_SECONDARY))
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    self.loading_fallback_text,
                )
            return
        if self.original_pixmap and not self.original_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            # 使用我們計算好的尺寸 (Label 自身的尺寸已經由 Layout 根據 heightForWidth 設定好了)
            target_size = self.size()
            
            # 確保圖片以 "Crop to Fill" 方式繪製，或者乾脆縮放
            # 如果 Label 已經是 16:9，那麼 KeepAspectRatio 就會填滿
            scaled = self.original_pixmap.scaled(
                target_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 計算居中位置 (以防萬一有誤差)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.drawPixmap(x, y, scaled)
        else:
            super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.setGeometry(self.rect())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ThumbnailGridWidget(QWidget):
    """縮圖網格展示小部件（4 列排列）"""
    # 信號：重新處理請求
    reprocess_requested = pyqtSignal(str)  # (filename)
    thumbnail_selected = pyqtSignal(str)  # (filename)
    
    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.thumbnails = {}
        # JPG 監控機制: 儲存路徑與最後修改時間
        self.monitored_files = {} # {filename: {'path': jpg_path, 'mtime': timestamp}}
        self.init_ui()
        
        # 啟動定時器，每 2 秒檢查一次已顯示的 JPG 是否有更新
        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.timeout.connect(self.check_for_updates)
        self.monitoring_timer.start(2000)
    
    def check_for_updates(self):
        """檢查監控中的檔案是否有變更"""
        for filename, info in list(self.monitored_files.items()):
            jpg_path = info.get('path')
            last_mtime = info.get('mtime')
            
            if jpg_path and os.path.exists(jpg_path):
                try:
                    current_mtime = os.path.getmtime(jpg_path)
                    # 如果檔案修改時間變新了 (且不是 0)
                    if current_mtime > last_mtime and last_mtime > 0:
                        # 更新記錄
                        self.monitored_files[filename]['mtime'] = current_mtime
                        # 觸發 UI 更新
                        # 使用 retry_count=0 立即嘗試重新載入
                        self.update_thumbnail(filename, jpg_path)
                        # 如果 parent 存在，或許可以發出 log
                        if self.parent_window and hasattr(self.parent_window, "add_log"):
                            # 避免 log 刷屏，只在控制台印出或選擇性 log
                            # self.parent_window.add_log(f"🔄 偵測到外部更新: {filename}")
                            pass
                except:
                    pass

    def init_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        # 設定整體對齊方式為靠上，避免單行時被強制垂直拉伸
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # 強制 4 列等寬
        for i in range(4):
            layout.setColumnStretch(i, 1)
        self.setLayout(layout)
    
    def add_placeholder(self, name, index):
        """添加佔位符（4 列排列）"""
        # 外層框架
        frame = QFrame()
        # 強制每個卡片使用擴展策略 (垂直方向改為 Preferred 以配合 heightForWidth)
        from PyQt6.QtWidgets import QSizePolicy
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DarkTheme.BG_TERTIARY};
                border: 1px solid {DarkTheme.BORDER};
                border-radius: 5px;
                padding: 5px;
                min-width: 110px;
            }}
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(3)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        
        # 頂部：文件名和重新處理按鈕
        top_layout = QHBoxLayout()
        
        # 顯示文件名
        name_label = QLabel(name)
        # 加大字體並加粗
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        name_label.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        name_label.setWordWrap(True)
        # 移除高度限制，改用最小高度，讓它能完整顯示多行文字
        name_label.setMinimumHeight(40)
        
        # 重新處理按鈕
        reprocess_btn = QPushButton("↻")
        reprocess_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        reprocess_btn.setMaximumWidth(30)
        reprocess_btn.setMaximumHeight(30)
        reprocess_btn.setMinimumWidth(30)
        reprocess_btn.setMinimumHeight(30)
        reprocess_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkTheme.ACCENT_CYAN};
                color: {DarkTheme.BG_PRIMARY};
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {DarkTheme.ACCENT_PURPLE};
            }}
            QPushButton:pressed {{
                background-color: {DarkTheme.ACCENT_PINK};
            }}
        """)
        # 使用 functools.partial 來正確傳遞文件名，不接收信號的布爾參數
        reprocess_btn.clicked.connect(partial(self.on_reprocess_clicked, name))
        reprocess_btn.setEnabled(False)  # 初始禁用，直到縮圖生成完成
        
        # 將 label 設為 stretch=1，讓它佔據所有剩餘空間，確保寬度最大化
        top_layout.addWidget(name_label, 1)
        top_layout.addWidget(reprocess_btn)
        
        # 顯示狀態/圖像
        status_label = AspectRatioLabel("⏳ 等待生成")
        status_label.setFont(QFont("Arial", 8))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        status_label.setMinimumHeight(100)
        status_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        status_label.setToolTip("雙擊開啟對應 PSD")
        status_label.clicked.connect(partial(self.thumbnail_selected.emit, name))
        status_label.double_clicked.connect(partial(self.open_psd_for_thumbnail, name))
        # 設定 expanding 策略，讓圖片可以隨視窗放大
        from PyQt6.QtWidgets import QSizePolicy
        status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        loading_overlay = CGLoadingOverlay(status_label)
        status_label.loading_overlay = loading_overlay
        loading_overlay.setGeometry(status_label.rect())
        
        frame_layout.addLayout(top_layout)
        frame_layout.addWidget(status_label)
        
        # 計算行列位置（4 列）
        row = index // 4
        col = index % 4
        self.layout().addWidget(frame, row, col)
        # 移除 setRowStretch(row, 1)，因為這會強制拉伸行高
        
        self.thumbnails[name] = {
            "frame": frame, 
            "status_label": status_label,
            "loading_overlay": loading_overlay,
            "reprocess_btn": reprocess_btn,
            "status": "waiting",
            "jpg_path": None,
            "psd_path": None
        }
    
    def on_reprocess_clicked(self, filename, checked=False):
        """重新處理按鈕被點擊"""
        if self.parent_window:
            self.parent_window.on_reprocess_requested(filename)
        else:
            self.reprocess_requested.emit(filename)

    def show_reprocess_loading(self, name):
        """重新生成時隱藏縮圖，只顯示 CG loading 動畫。"""
        info = self.thumbnails.get(name)
        if not info:
            return
        overlay = info.get("loading_overlay")
        animation_started = bool(overlay and overlay.start())
        info["status_label"].setLoading(
            True,
            "" if animation_started else "⏳ 重新生成中...",
        )
        info["status"] = "processing"

    def stop_loading(self, name):
        info = self.thumbnails.get(name)
        if not info:
            return
        overlay = info.get("loading_overlay")
        if overlay:
            overlay.stop()
        info["status_label"].setLoading(False)

    def find_psd_for_jpg(self, jpg_path):
        """從縮圖 JPG 路徑推回對應的 PSD 路徑"""
        if not jpg_path:
            return None

        jpg = Path(jpg_path)
        output_dir = jpg.parent.parent if jpg.parent.name.lower() == "jpg" else jpg.parent
        stem = jpg.stem

        candidates = [
            output_dir / f"{stem}.psd",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        try:
            all_psds = list(output_dir.glob("*.psd"))
        except Exception:
            return None

        # 有製作者時，JPG 會移除最後的 _製作者，但 PSD 仍保留該後綴。
        suffix_matches = [psd for psd in all_psds if psd.stem.startswith(f"{stem}_")]
        if suffix_matches:
            newest = max(suffix_matches, key=lambda p: p.stat().st_mtime)
            return str(newest)

        # 最後用寬鬆比對，支援檔名中有空白、底線或橫線差異。
        target_norm = normalize_string_for_compare(stem)
        loose_matches = []
        for psd in all_psds:
            psd_norm = normalize_string_for_compare(psd.stem)
            if target_norm and target_norm in psd_norm:
                loose_matches.append(psd)

        if loose_matches:
            newest = max(loose_matches, key=lambda p: p.stat().st_mtime)
            return str(newest)

        return None

    def open_psd_for_thumbnail(self, name):
        """雙擊縮圖時開啟對應 PSD"""
        info = self.thumbnails.get(name)
        if not info:
            return

        jpg_path = info.get("jpg_path")
        psd_path = info.get("psd_path")

        if not psd_path or not os.path.exists(psd_path):
            psd_path = self.find_psd_for_jpg(jpg_path)
            info["psd_path"] = psd_path

        if psd_path and os.path.exists(psd_path):
            try:
                os.startfile(psd_path)
                if self.parent_window and hasattr(self.parent_window, "add_log"):
                    self.parent_window.add_log(f"🖼️ 已開啟 PSD: {os.path.basename(psd_path)}")
            except Exception as e:
                QMessageBox.warning(self, "錯誤", f"無法開啟 PSD:\n{psd_path}\n\n{e}")
        else:
            if self.parent_window and hasattr(self.parent_window, "add_log"):
                self.parent_window.add_log(f"⚠️ 找不到對應 PSD: {name}")
            QMessageBox.warning(self, "找不到 PSD", "找不到這張縮圖對應的 PSD 檔。")
    
    def update_thumbnail(self, name, jpg_path, retry_count=0):
        """更新縮圖顯示 JPG 圖像 (附帶重試機制)"""
        if name not in self.thumbnails:
            return
        
        # 加入監控列表
        if os.path.exists(jpg_path):
            try:
                mtime = os.path.getmtime(jpg_path)
                self.monitored_files[name] = {'path': jpg_path, 'mtime': mtime}
            except:
                pass

        try:
            status_label = self.thumbnails[name]["status_label"]
            reprocess_btn = self.thumbnails[name]["reprocess_btn"]
            
            # 強制清除舊圖快取
            # 我們不能直接 QPixmap(jpg_path) 因為 Qt 可能會快取
            # 開檔讀取二進制資料再載入通常可以繞過快取
            image_data = None
            with open(jpg_path, 'rb') as f:
                image_data = f.read()
            
            pixmap = QPixmap()
            if image_data:
                pixmap.loadFromData(image_data)
            
            if not pixmap.isNull():
                # 使用 AspectRatioLabel 自動縮放
                self.stop_loading(name)
                status_label.setPixmap(pixmap)
                status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.thumbnails[name]["status"] = "completed"
                self.thumbnails[name]["jpg_path"] = jpg_path
                self.thumbnails[name]["psd_path"] = self.find_psd_for_jpg(jpg_path)
                # 啟用重新處理按鈕
                reprocess_btn.setEnabled(True)
            else:
                # 如果載入失敗，且重試次數少於 3 次，則嘗試重試
                if retry_count < 3:
                     # 1秒後重試
                    QTimer.singleShot(1000, lambda: self.update_thumbnail(name, jpg_path, retry_count + 1))
                    if retry_count == 0:
                        status_label.setText("⏳ 載入中...")
                else:
                    self.stop_loading(name)
                    status_label.setText("❌ 圖像載入失敗")
                    # 即使顯示失敗，也啟用按鈕讓使用者可以重試
                    reprocess_btn.setEnabled(True)
                    
        except Exception as e:
            self.stop_loading(name)
            status_label.setText(f"❌ 錯誤")
            reprocess_btn.setEnabled(True)
    
    def mark_completed(self, name):
        """標記為已完成"""
        if name in self.thumbnails:
            self.thumbnails[name]["status"] = "completed"
    
    def mark_failed(self, name):
        """標記為失敗"""
        if name not in self.thumbnails:
            return
        
        try:
            status_label = self.thumbnails[name]["status_label"]
            self.stop_loading(name)
            status_label.setText("❌ 生成失敗")
            status_label.setStyleSheet(f"color: {DarkTheme.ACCENT_RED};")
            self.thumbnails[name]["status"] = "failed"
        except Exception as e:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("晚報YT縮圖 - 自動生成系統")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(STYLESHEET)
        
        # 載入設定
        self.settings_file = Path(os.path.expanduser("~")) / ".ytthumb_settings.json"
        self.load_settings()
        
        # 工作線程
        self.worker = None
        self.thumbnail_overrides = {}
        self.resolved_thumbnail_configs = {}
        self.pending_thumbnail_configs = {}
        self.active_reprocess_filename = None
        self.batch_generation_active = False
        self.batch_pending_files = set()
        self.batch_completed_files = set()
        self.batch_failed_files = set()
        self.selected_thumbnail_filename = None
        self.config_folder = None
        self.color_schemes = self.load_available_color_schemes()
        self.top_right_colors = self.load_available_top_right_colors()
        
        self.init_ui()
        self.add_log(f"🎨 配色來源: {get_color_scheme_source_description()}")

    def load_available_color_schemes(self):
        """載入右欄可選用的大標配色。"""
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        return load_color_schemes(str(base_path / "晚報變色.csv")) or {}

    def load_available_top_right_colors(self):
        """載入右欄可使用的右上變色色碼。"""
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        return load_top_right_colors(str(base_path / "右上變色.csv")) or {}
    
    def load_settings(self):
        """載入保存的設定"""
        self.settings = {}
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except:
                self.settings = {}
    
    def save_settings(self):
        """保存設定"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def init_ui(self):
        """初始化 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== 頂部操作區 =====
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        
        # 日期
        date_label = QLabel("📅 日期:")
        date_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.date_input = QLineEdit()
        self.date_input.setText(datetime.now().strftime("%m%d"))
        self.date_input.setMaximumWidth(100)
        self.date_input.returnPressed.connect(self.on_date_entered)
        
        # 製作者
        creator_label = QLabel("👤 製作者:")
        creator_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.creator_input = QLineEdit()
        self.creator_input.setPlaceholderText("輸入製作者名稱...")
        self.creator_input.setMinimumWidth(200)
        
        # 開始按鈕
        self.start_btn = QPushButton("▶ 開始生成")
        self.start_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.start_btn.setMinimumWidth(120)
        self.start_btn.clicked.connect(self.on_start_clicked)
        
        # 暫停按鈕
        self.pause_btn = QPushButton("⏸ 暫停")
        self.pause_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.pause_btn.setMinimumWidth(80)
        self.pause_btn.hide()  # 預設隱藏
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        
        # 進度顯示
        self.progress_label = QLabel("準備就緒")
        self.progress_label.setFont(QFont("Arial", 10))
        self.progress_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        
        top_layout.addWidget(date_label)
        top_layout.addWidget(self.date_input)
        top_layout.addSpacing(20)
        top_layout.addWidget(creator_label)
        top_layout.addWidget(self.creator_input)
        top_layout.addStretch()
        top_layout.addWidget(self.progress_label)
        top_layout.addWidget(self.start_btn)
        top_layout.addWidget(self.pause_btn)
        
        main_layout.addWidget(top_frame)
        
        # ===== 中間內容區（左右分割） =====
        content_layout = QHBoxLayout()
        
        # ===== 左側：文件列表 =====
        self.file_list_default_width = 300
        self.file_list_auto_max_width = 560
        left_frame = QFrame()
        left_frame.setMinimumWidth(self.file_list_default_width)
        left_frame.setMaximumWidth(self.file_list_default_width)
        self.left_frame = left_frame
        left_layout = QVBoxLayout(left_frame)
        
        left_title = QLabel("📁 文字檔案")
        left_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_title.setStyleSheet(f"color: {DarkTheme.ACCENT_CYAN};")
        
        browse_btn = QPushButton("🔍 瀏覽文件夾")
        browse_btn.clicked.connect(self.on_browse_folder)
        
        self.file_list = FileListWidget()
        self.file_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.file_list.itemDoubleClicked.connect(self.on_file_double_clicked)
        
        file_ops_layout = QHBoxLayout()
        all_btn = QPushButton("全選")
        all_btn.clicked.connect(self.file_list.toggle_all)
        
        # 將「反選」按鈕修改為「重整列表」按鈕
        refresh_btn = QPushButton("↻ 重整列表")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DarkTheme.BG_TERTIARY};
                color: {DarkTheme.TEXT_SECONDARY};
                border: 1px solid {DarkTheme.BORDER};
            }}
            QPushButton:hover {{
                color: {DarkTheme.TEXT_PRIMARY};
                border-color: {DarkTheme.ACCENT_CYAN};
            }}
        """)
        # 連結到瀏覽文件夾函數，這樣會重新讀取當前或預設路徑中的文件
        refresh_btn.clicked.connect(self.on_refresh_files)
        
        file_ops_layout.addWidget(all_btn)
        file_ops_layout.addWidget(refresh_btn)
        
        left_layout.addWidget(left_title)
        left_layout.addWidget(browse_btn)
        left_layout.addWidget(self.file_list)
        left_layout.addLayout(file_ops_layout)
        
        # ===== 右側：預覽區 =====
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        right_title = QLabel("🖼️  待生成縮圖")
        right_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_title.setStyleSheet(f"color: {DarkTheme.ACCENT_PINK};")
        
        self.stats_label = QLabel(format_generation_stats(0, 0, 0))
        self.stats_label.setFont(QFont("Arial", 10))
        self.stats_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")

        right_header_layout = QHBoxLayout()
        right_header_layout.setContentsMargins(0, 0, 0, 0)
        right_header_layout.addWidget(right_title)
        right_header_layout.addStretch()
        right_header_layout.addWidget(self.stats_label)
        
        self.scroll = QScrollArea()
        self.thumbnail_grid = ThumbnailGridWidget(parent_window=self)
        self.thumbnail_grid.reprocess_requested.connect(self.on_reprocess_requested)
        self.thumbnail_grid.thumbnail_selected.connect(self.on_thumbnail_selected)
        self.scroll.setWidget(self.thumbnail_grid)
        self.scroll.setWidgetResizable(True)
        
        right_layout.addLayout(right_header_layout)
        right_layout.addWidget(self.scroll)
        
        content_layout.addWidget(left_frame, 9)
        content_layout.addWidget(right_frame, 42)
        content_layout.addWidget(self.create_thumbnail_config_panel(), 9)
        main_layout.addLayout(content_layout)
        
        # ===== 進度條 =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # ===== 底部日誌區 =====
        log_title = QLabel("📋 工作日誌 (可摺疊)")
        log_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        log_title.setStyleSheet(f"color: {DarkTheme.ACCENT_ORANGE};")
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        log_ops_layout = QHBoxLayout()
        clear_log_btn = QPushButton("🗑️ 清空日誌")
        clear_log_btn.clicked.connect(self.on_clear_log)
        open_folder_btn = QPushButton("📂 打開文件夾")
        open_folder_btn.clicked.connect(self.on_open_folder)
        log_ops_layout.addWidget(clear_log_btn)
        log_ops_layout.addWidget(open_folder_btn)
        log_ops_layout.addStretch()
        
        main_layout.addWidget(log_title)
        main_layout.addWidget(self.log_text)
        main_layout.addLayout(log_ops_layout)
        
        self.add_log("✓ 系統已啟動")
        
        # 自動載入預設路徑中的文件
        self.auto_load_default_folder()

    def create_thumbnail_config_panel(self):
        """建立右側的單張縮圖設定面板。"""
        self.config_default_width = 300
        self.config_auto_max_width = 560
        panel = QFrame()
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(self.config_default_width)
        panel.setVisible(False)
        self.thumbnail_config_panel = panel
        outer = QVBoxLayout(panel)

        title = QLabel("🎛 縮圖設定")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {DarkTheme.ACCENT_PURPLE};")
        outer.addWidget(title)

        self.config_selected_label = QLabel("請點擊中間的縮圖")
        self.config_selected_label.setWordWrap(True)
        self.config_selected_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        outer.addWidget(self.config_selected_label)

        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.config_scroll = config_scroll
        self.config_form_widget = QWidget()
        form = QFormLayout(self.config_form_widget)
        self.config_form_layout = form
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(8)

        self.config_layout_value = QLineEdit()
        self.config_layout_value.setReadOnly(True)
        form.addRow("版型", self.config_layout_value)

        self.config_color_combo = QComboBox()
        self.config_color_combo.addItems(sorted(self.color_schemes.keys()))
        self.config_color_combo.currentTextChanged.connect(self.on_config_color_changed)
        form.addRow("配色", self.config_color_combo)

        self.config_anchor_combo = QComboBox()
        self.config_anchor_combo.addItems(ANCHOR_NAMES)
        form.addRow("主播", self.config_anchor_combo)

        self.config_top_right = QComboBox()
        self.config_top_right.setIconSize(QSize(20, 20))
        form.addRow("右上變色", self.config_top_right)

        self.config_left_text = QLineEdit()
        form.addRow("左邊字", self.config_left_text)
        self.config_left_text_label = form.labelForField(self.config_left_text)

        self.config_title1 = QLineEdit()
        form.addRow("大標第一行", self.config_title1)

        self.config_title2 = QLineEdit()
        form.addRow("大標第二行", self.config_title2)

        self.config_image_instruction = QLineEdit()
        self.config_image_instruction.setReadOnly(True)
        form.addRow("圖片指示", self.config_image_instruction)
        self.config_image_instruction_label = form.labelForField(self.config_image_instruction)

        self.config_image_preview = QLabel("尚無圖片")
        self.config_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.config_image_preview.setMinimumHeight(120)
        self.config_image_preview.setStyleSheet(
            f"background-color: {DarkTheme.BG_PRIMARY}; color: {DarkTheme.TEXT_HINT}; "
            f"border: 1px solid {DarkTheme.BORDER};"
        )
        form.addRow("實際圖片", self.config_image_preview)
        self.config_image_preview_label = form.labelForField(self.config_image_preview)

        self.config_color_words = QLineEdit()
        self.config_color_words.setReadOnly(True)
        form.addRow("引號變色字", self.config_color_words)

        self.config_effect_words = QLineEdit()
        self.config_effect_words.setReadOnly(True)
        form.addRow("效果字", self.config_effect_words)

        self.config_validation = QLineEdit()
        self.config_validation.setReadOnly(True)
        form.addRow("格式檢查", self.config_validation)

        self.config_file_content = QTextEdit()
        self.config_file_content.setReadOnly(True)
        self.config_file_content.setMinimumHeight(180)
        form.addRow("文字檔", self.config_file_content)

        config_scroll.setWidget(self.config_form_widget)
        outer.addWidget(config_scroll, 1)

        note = QLabel("修改只套用本次程式工作階段，不會改寫原始文字檔。")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {DarkTheme.TEXT_HINT};")
        outer.addWidget(note)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("套用設定")
        apply_btn.clicked.connect(self.apply_thumbnail_config)
        reset_btn = QPushButton("還原設定")
        reset_btn.clicked.connect(self.reset_thumbnail_config)
        buttons.addWidget(apply_btn)
        buttons.addWidget(reset_btn)
        outer.addLayout(buttons)

        self.config_form_widget.setEnabled(False)
        apply_btn.setEnabled(False)
        reset_btn.setEnabled(False)
        self.config_apply_btn = apply_btn
        self.config_reset_btn = reset_btn
        return panel

    def adjust_thumbnail_config_width(self):
        """依目前可見設定的需要加寬右欄，避免外層出現橫向捲動條。"""
        if not self.thumbnail_config_panel.isVisible():
            return

        self.config_form_layout.activate()
        self.config_form_widget.adjustSize()

        scroll_extra = self.config_scroll.frameWidth() * 2
        if self.config_scroll.verticalScrollBar().isVisible():
            scroll_extra += self.config_scroll.verticalScrollBar().sizeHint().width()

        panel_margins = self.thumbnail_config_panel.layout().contentsMargins()
        required_width = (
            self.config_form_widget.sizeHint().width()
            + scroll_extra
            + panel_margins.left()
            + panel_margins.right()
        )
        target_width = max(
            self.config_default_width,
            min(required_width, self.config_auto_max_width),
        )
        self.thumbnail_config_panel.setMinimumWidth(target_width)
        self.thumbnail_config_panel.setMaximumWidth(target_width)

    def reset_thumbnail_config_width(self):
        """右欄隱藏時恢復原本的固定寬度。"""
        self.thumbnail_config_panel.setMinimumWidth(220)
        self.thumbnail_config_panel.setMaximumWidth(self.config_default_width)

    def adjust_file_list_width(self):
        """只有檔名超出預設寬度時才自動加寬左欄。"""
        if self.file_list.count() == 0:
            self.reset_file_list_width()
            return

        longest_item_width = self.file_list.sizeHintForColumn(0)
        list_extra = (
            self.file_list.frameWidth() * 2
            + (
                self.file_list.verticalScrollBar().sizeHint().width()
                if self.file_list.verticalScrollBar().isVisible()
                else 0
            )
            + 4
        )
        margins = self.left_frame.layout().contentsMargins()
        required_width = longest_item_width + list_extra + margins.left() + margins.right()
        if required_width <= self.file_list_default_width + 16:
            target_width = self.file_list_default_width
        else:
            auto_max_width = max(self.file_list_auto_max_width, int(self.width() * 0.40))
            target_width = min(required_width, auto_max_width)
        self.left_frame.setMinimumWidth(target_width)
        self.left_frame.setMaximumWidth(target_width)

    def reset_file_list_width(self):
        """載入新列表前恢復左欄預設固定寬度。"""
        self.left_frame.setMinimumWidth(self.file_list_default_width)
        self.left_frame.setMaximumWidth(self.file_list_default_width)
    
    def auto_load_default_folder(self):
        """自動載入預設網路路徑中的文件"""
        # 獲取今天的日期（MMDD 格式）
        today = datetime.now().strftime("%m%d")
        
        # 構建預設路徑列表（優先順序）
        default_paths = get_text_directory_candidates(today)
        
        # 尋找存在的路徑並載入
        folder_loaded = False
        for folder_path in default_paths:
            if os.path.exists(folder_path):
                self.load_files_from_folder(folder_path)
                self.settings["last_folder"] = folder_path
                self.save_settings()
                self.add_log(f"✓ 已自動載入: {folder_path}")
                folder_loaded = True
                break
        
        if not folder_loaded:
            self.add_log(f"⚠️ 預設路徑不存在，請手動選擇文件夾")

    def on_date_entered(self):
        """日期欄按 Enter 後，切換至該日的晚報文字資料夾。"""
        mmdd = self.date_input.text().strip()
        if not is_valid_mmdd(mmdd):
            QMessageBox.warning(self, "日期格式錯誤", "請輸入 MMDD，例如 0820")
            return

        for folder_path in get_text_directory_candidates(mmdd):
            if os.path.isdir(folder_path):
                self.load_files_from_folder(folder_path)
                self.settings["last_folder"] = folder_path
                self.save_settings()
                self.add_log(f"📅 已切換至 {mmdd}: {folder_path}")
                return

        searched = "\n".join(get_text_directory_candidates(mmdd))
        self.add_log(f"⚠️ 找不到 {mmdd} 的文字資料夾")
        QMessageBox.warning(
            self,
            "找不到文字資料夾",
            f"找不到 {mmdd} 的文字資料夾，已搜尋：\n{searched}",
        )

    def on_refresh_files(self):
        """刷新當前文件夾的文件"""
        current_folder = self.settings.get("last_folder", "")
        if current_folder and os.path.exists(current_folder):
            self.load_files_from_folder(current_folder)
            self.add_log(f"🔄 已重新整理列表: {current_folder}")
        else:
            self.on_browse_folder()
    
    
    def add_log(self, message):
        """添加日誌"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自動滾動到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def set_config_row_visible(self, field, visible):
        """同步顯示或隱藏右欄表單的一整列。"""
        field.setVisible(visible)
        label = self.config_form_layout.labelForField(field)
        if label:
            label.setVisible(visible)

    def get_allowed_top_right_colors(self, color_id):
        """依配色組別回傳可選的右上變色色碼。"""
        exclude_map = {"O": "A", "P": "B", "B": "C", "G": "D"}
        excluded_group = exclude_map.get((color_id or "")[:1].upper())
        colors = []
        for group, values in self.top_right_colors.items():
            if group == excluded_group:
                continue
            for value in values:
                color = str(value).strip().lstrip("#").lower()
                if re.fullmatch(r"[0-9a-f]{6}", color) and color not in colors:
                    colors.append(color)
        return colors

    def populate_top_right_combo(self, color_id, selected_color=""):
        """以色塊圖示與色碼填入右上變色下拉選單。"""
        if color_id not in self.color_schemes:
            self.config_top_right.blockSignals(True)
            self.config_top_right.clear()
            self.config_top_right.addItem(UNRECORDED_CONFIG)
            self.config_top_right.setEnabled(False)
            self.config_top_right.blockSignals(False)
            return ""

        self.config_top_right.setEnabled(True)
        colors = self.get_allowed_top_right_colors(color_id)
        selected = str(selected_color or "").strip().lstrip("#").lower()
        if selected and selected not in colors and re.fullmatch(r"[0-9a-f]{6}", selected):
            colors.insert(0, selected)
        if not selected and colors:
            selected = random.choice(colors)

        self.config_top_right.blockSignals(True)
        self.config_top_right.clear()
        for color in colors:
            swatch = QPixmap(20, 20)
            swatch.fill(QColor(f"#{color}"))
            self.config_top_right.addItem(QIcon(swatch), color)
        selected_index = self.config_top_right.findText(selected)
        if selected_index >= 0:
            self.config_top_right.setCurrentIndex(selected_index)
        self.config_top_right.blockSignals(False)
        return self.config_top_right.currentText()

    def on_config_color_changed(self, color_id):
        """切換配色時同步更新可用的右上變色清單。"""
        if not hasattr(self, "config_top_right"):
            return
        current = self.config_top_right.currentText().strip().lower()
        allowed = self.get_allowed_top_right_colors(color_id)
        self.populate_top_right_combo(color_id, current if current in allowed else "")

    def set_config_color_selection(self, color_id):
        """顯示已記錄配色；沒有紀錄時明確顯示未記錄。"""
        self.config_color_combo.blockSignals(True)
        unknown_index = self.config_color_combo.findText(UNRECORDED_CONFIG)
        if color_id in self.color_schemes:
            if unknown_index >= 0:
                self.config_color_combo.removeItem(unknown_index)
            color_index = self.config_color_combo.findText(color_id)
            self.config_color_combo.setCurrentIndex(color_index)
        else:
            if unknown_index < 0:
                self.config_color_combo.insertItem(0, UNRECORDED_CONFIG)
                unknown_index = 0
            self.config_color_combo.setCurrentIndex(unknown_index)
        self.config_color_combo.blockSignals(False)

    def read_text_file_for_display(self, file_path):
        """讀取右欄要顯示的原始文字檔內容。"""
        for encoding in ("utf-8-sig", "cp950"):
            try:
                with open(file_path, "r", encoding=encoding) as infile:
                    return infile.read()
            except UnicodeDecodeError:
                continue
            except OSError:
                return ""
        return ""

    def thumbnail_config_storage_key(self, filename, source_file_path=""):
        """以來源文字檔完整路徑作為生成設定的穩定索引。"""
        if source_file_path:
            return os.path.normcase(os.path.normpath(os.path.abspath(source_file_path)))
        folder = self.settings.get("last_folder", "")
        if not folder or not filename:
            return ""
        return os.path.normcase(os.path.normpath(os.path.abspath(os.path.join(folder, filename))))

    def load_persisted_thumbnail_config(self, filename):
        """讀取與目前 JPG 相符的上次成功生成設定。"""
        records = self.settings.get("thumbnail_generation_configs", {})
        if not isinstance(records, dict):
            return {}
        record = records.get(self.thumbnail_config_storage_key(filename), {})
        if not isinstance(record, dict):
            return {}

        thumbnail_info = getattr(self, "thumbnail_grid", None)
        thumbnail_info = thumbnail_info.thumbnails.get(filename, {}) if thumbnail_info else {}
        current_jpg = thumbnail_info.get("jpg_path")
        saved_jpg = record.get("jpg_path")
        if current_jpg and saved_jpg:
            if os.path.normcase(os.path.normpath(current_jpg)) != os.path.normcase(os.path.normpath(saved_jpg)):
                return {}
            try:
                saved_mtime = float(record.get("jpg_mtime", 0))
                if saved_mtime and abs(os.path.getmtime(current_jpg) - saved_mtime) > 0.001:
                    return {}
            except (OSError, TypeError, ValueError):
                return {}
        return record

    def persist_thumbnail_config(self, filename, report, jpg_path):
        """保存成功生成時實際使用的配色，供重新啟動後讀回。"""
        storage_key = self.thumbnail_config_storage_key(
            filename, report.get("source_file_path", "")
        )
        color_id = str(report.get("color_id", "") or "").strip()
        top_right = str(report.get("top_right_color", "") or "").strip().lstrip("#").lower()
        if not storage_key or color_id not in self.color_schemes or not re.fullmatch(r"[0-9a-f]{6}", top_right):
            return

        records = self.settings.setdefault("thumbnail_generation_configs", {})
        if not isinstance(records, dict):
            records = {}
            self.settings["thumbnail_generation_configs"] = records
        try:
            jpg_mtime = os.path.getmtime(jpg_path)
        except OSError:
            jpg_mtime = 0
        records[storage_key] = {
            "color_id": color_id,
            "top_right_color": top_right,
            "jpg_path": os.path.normpath(jpg_path),
            "jpg_mtime": jpg_mtime,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.save_settings()

    def get_thumbnail_visual_config(self, filename, resolved):
        """取得自訂或實際生成設定；單純查看縮圖時不再隨機選色。"""
        visual = resolve_visual_config(
            self.thumbnail_overrides.get(filename),
            resolved,
            self.load_persisted_thumbnail_config(filename),
        )
        return visual.get("color_id", ""), visual.get("top_right_color", "")

    def update_config_image_preview(self, image_paths):
        """在右欄顯示實際配對圖片的小圖。"""
        paths = [str(path) for path in (image_paths or []) if path]
        if not paths:
            self.config_image_preview.clear()
            self.config_image_preview.setText("尚未配對圖片")
            self.config_image_preview.setToolTip("")
            return

        pixmap = QPixmap(paths[0])
        if pixmap.isNull():
            self.config_image_preview.clear()
            self.config_image_preview.setText("圖片無法預覽")
        else:
            self.config_image_preview.setPixmap(
                pixmap.scaled(
                    260, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.config_image_preview.setToolTip("\n".join(paths))

    def on_thumbnail_selected(self, filename):
        """載入被點擊縮圖的文字解析結果與生成設定。"""
        folder = self.settings.get("last_folder", "")
        file_path = os.path.join(folder, filename) if folder else ""
        if not file_path or not os.path.isfile(file_path):
            self.add_log(f"❌ 無法載入縮圖設定，找不到文字檔: {file_path or filename}")
            return

        parsed = prepare_file_data(file_path, self.date_input.text().strip())
        if not parsed:
            parsed = parse_file(file_path)
        if not parsed:
            self.add_log(f"❌ 無法解析縮圖設定: {filename}")
            return

        self.selected_thumbnail_filename = filename
        self.thumbnail_config_panel.setVisible(True)
        resolved = self.resolved_thumbnail_configs.get(filename, {})
        display_result = dict(parsed)
        if resolved.get("result"):
            display_result.update(resolved["result"])
        display_result.update(self.thumbnail_overrides.get(filename, {}))

        self.config_selected_label.setText(filename)
        self.config_layout_value.setText(display_result.get("layout_type", ""))
        self.config_anchor_combo.setCurrentText(display_result.get("anchor", ""))
        self.config_left_text.setText(display_result.get("left_text", ""))
        self.config_title1.setText(display_result.get("title_line1", ""))
        self.config_title2.setText(display_result.get("title_line2", ""))
        self.config_image_instruction.setText(display_result.get("image_instruction", ""))
        image_paths = display_result.get("image_paths", []) or []
        if not image_paths and display_result.get("image_path"):
            image_paths = [display_result["image_path"]]
        self.update_config_image_preview(image_paths)
        self.config_color_words.setText("、".join(display_result.get("color_words", []) or []))
        self.config_effect_words.setText("、".join(display_result.get("effect_words", []) or []))
        validation_errors = display_result.get("validation_errors", []) or []
        image_warnings = display_result.get("image_warnings", []) or []
        if validation_errors:
            self.config_validation.setText("；".join(validation_errors))
        elif image_warnings:
            self.config_validation.setText("警告：" + "；".join(image_warnings))
        else:
            self.config_validation.setText("正常")
        self.config_file_content.setPlainText(self.read_text_file_for_display(file_path))

        color_id, top_right = self.get_thumbnail_visual_config(filename, resolved)
        self.set_config_color_selection(color_id)
        self.populate_top_right_combo(color_id, top_right)

        has_left_text = bool(display_result.get("left_text", "").strip())
        self.set_config_row_visible(self.config_left_text, has_left_text)
        has_image = bool(image_paths)
        self.set_config_row_visible(self.config_image_preview, has_image)
        self.set_config_row_visible(
            self.config_image_instruction,
            bool(display_result.get("image_instruction", "").strip()),
        )

        self.config_form_widget.setEnabled(True)
        self.config_apply_btn.setEnabled(True)
        self.config_reset_btn.setEnabled(True)
        QTimer.singleShot(0, self.adjust_thumbnail_config_width)

    def apply_thumbnail_config(self):
        """保存單張縮圖覆寫設定，並立即重新生成目前縮圖。"""
        filename = self.selected_thumbnail_filename
        if not filename:
            return

        title1 = self.config_title1.text().strip()
        title2 = self.config_title2.text().strip()
        if not title1 or not title2:
            QMessageBox.warning(self, "設定不完整", "大標第一行與第二行都不能留空。")
            return
        if title1.count('"') % 2 or title2.count('"') % 2:
            QMessageBox.warning(self, "引號未閉合", "大標中的半形雙引號必須成對出現。")
            return

        top_right = self.config_top_right.currentText().strip().lstrip("#")
        color_text = self.config_color_combo.currentText().strip()
        if color_text not in self.color_schemes:
            QMessageBox.warning(self, "設定不完整", "請先選擇配色組別。")
            return
        if not re.fullmatch(r"[0-9a-fA-F]{6}", top_right):
            QMessageBox.warning(self, "設定不完整", "請先選擇右上變色。")
            return
        self.thumbnail_overrides[filename] = {
            "color_id": color_text,
            "top_right_color": top_right.lower(),
            "anchor": self.config_anchor_combo.currentText().strip(),
            "left_text": self.config_left_text.text().strip(),
            "title_line1": title1,
            "title_line2": title2,
        }
        self.add_log(f"🎛 已套用縮圖設定: {filename}")
        self.config_selected_label.setText(f"{filename}\n⏳ 已套用自訂設定，正在重新生成")
        self.on_reprocess_requested(filename)

    def reset_thumbnail_config(self):
        """移除單張縮圖覆寫，還原文字檔與目前實際生成設定。"""
        filename = self.selected_thumbnail_filename
        if not filename:
            return
        self.thumbnail_overrides.pop(filename, None)
        self.add_log(f"↩ 已還原設定: {filename}")
        self.on_thumbnail_selected(filename)

    def on_config_resolved(self, filename, report):
        """暫存 JSX 實際使用的設定，待 JPG 成功生成後再確認。"""
        self.pending_thumbnail_configs[filename] = dict(report or {})
    
    def on_browse_folder(self):
        """瀏覽文件夾"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇文字檔案夾",
            os.path.expanduser("~")
        )
        if folder:
            self.load_files_from_folder(folder)
            # 保存文件夾路徑到設定
            self.settings["last_folder"] = folder
            self.save_settings()
            self.add_log(f"✓ 已載入文件夾: {folder}")

    def on_file_double_clicked(self, item):
        """雙擊文字檔列表項目時，以 Windows 預設程式開啟檔案。"""
        filename = item.data(Qt.ItemDataRole.UserRole)
        current_folder = self.settings.get("last_folder", "")
        file_path = os.path.join(current_folder, filename) if current_folder and filename else ""

        if not file_path or not os.path.isfile(file_path):
            self.add_log(f"❌ 找不到文字檔: {file_path or filename}")
            QMessageBox.warning(self, "找不到文字檔", f"無法開啟：\n{file_path or filename}")
            return

        try:
            os.startfile(file_path)
            self.add_log(f"📄 已開啟文字檔: {filename}")
        except OSError as error:
            self.add_log(f"❌ 無法開啟文字檔: {file_path}（{error}）")
            QMessageBox.warning(self, "無法開啟文字檔", f"無法開啟：\n{file_path}\n\n{error}")
    
    def load_files_from_folder(self, folder_path):
        """從文件夾載入 .txt 檔案 (只顯示檔名含有「晚報YT縮圖」的，按數字排序)"""
        normalized_folder = os.path.normcase(os.path.abspath(folder_path))
        if self.config_folder != normalized_folder:
            self.config_folder = normalized_folder
            self.thumbnail_overrides.clear()
            self.resolved_thumbnail_configs.clear()
            self.pending_thumbnail_configs.clear()
            self.selected_thumbnail_filename = None
            if hasattr(self, "config_form_widget"):
                self.thumbnail_config_panel.setVisible(False)
                self.reset_thumbnail_config_width()
                self.config_form_widget.setEnabled(False)
                self.config_apply_btn.setEnabled(False)
                self.config_reset_btn.setEnabled(False)
                self.config_selected_label.setText("請點擊中間的縮圖")

        self.file_list.clear()
        self.file_list.item_checked = {}
        self.reset_file_list_width()
        
        # 獲取所有 .txt 檔案
        all_txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        
        # 過濾：只顯示檔名含有「晚報YT縮圖」的文件
        filtered_files = [f for f in all_txt_files if "晚報YT縮圖" in os.path.basename(f)]
        
        # 按檔名中的數字排序（自訂排序方式）
        filtered_files = sorted(filtered_files, key=lambda x: extract_numbers_for_sort(os.path.basename(x)))
        
        for file_path in filtered_files:
            filename = os.path.basename(file_path)
            self.file_list.add_file(filename)
        QTimer.singleShot(0, self.adjust_file_list_width)
        
        # === 新增功能：載入文件時自動預覽已完成的縮圖 ===
        # 初始化預覽縮圖網格
        self.thumbnail_grid = ThumbnailGridWidget(parent_window=self)
        self.thumbnail_grid.reprocess_requested.connect(self.on_reprocess_requested)
        self.thumbnail_grid.thumbnail_selected.connect(self.on_thumbnail_selected)
        
        # 1. 嘗試推斷輸出路徑
        # 嘗試從路徑中提取 MMDD，例如 .../0813/1800 或 .../08月/0813/1800。
        previous_date = self.date_input.text().strip()
        mmdd = infer_mmdd_from_path(folder_path)
        if previous_date != mmdd:
            self.date_input.setText(mmdd)
            self.add_log(f"📅 日期已切換為: {mmdd}")
        
        # 設定預期的 JPG 輸出目錄 (標準網位路徑)
        # 結構通常是: \\10.227.58.117\新聞psd\MMDD\縮圖\JPG
        base_output = r"\\10.227.58.117\新聞psd"
        jpg_output_dir = os.path.join(base_output, mmdd, "縮圖", "JPG")
        
        # 如果標準路徑不存在或無法訪問，才嘗試舊的相對路徑邏輯
        if not os.path.exists(jpg_output_dir):
            jpg_output_dir = os.path.join(folder_path, "縮圖")
            # 如果連相對路徑的縮圖資料夾也沒有，再試試看上一層的縮圖/JPG (針對本地測試結構)
            if not os.path.exists(jpg_output_dir):
                jpg_output_dir = os.path.join(folder_path, "縮圖", "JPG")

        self.add_log(f"🔍 預覽掃描目錄: {jpg_output_dir}")

        # 緩存目錄下所有 JPG 檔案，避免重複 IO
        existing_jpgs = {} # {normalized_name: full_filename}
        if os.path.exists(jpg_output_dir):
            try:
                # 只列出檔案名
                for f in os.listdir(jpg_output_dir):
                    if f.lower().endswith('.jpg'):
                         # 建立標準化映射
                         norm_name = normalize_string_for_compare(f)
                         existing_jpgs[norm_name] = f
            except:
                pass

        # 僅將已存在縮圖的文件加入網格
        grid_index = 0
        for file_path in filtered_files:
            filename = os.path.basename(file_path)
            filename_no_ext = os.path.splitext(filename)[0]
            
            jpg_path = None
            
            target_slugs = [] # 候選的比較字串 (標準化後)
            
            # 1. 加入檔名本身 (標準化)
            target_slugs.append(normalize_string_for_compare(filename_no_ext))
            
            # 2. 嘗試讀取 Slag (文字檔第一行)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                if first_line:
                    target_slugs.append(normalize_string_for_compare(first_line))
            except:
                pass
            
            # 3. 嘗試匹配
            # 預期生成的 JPG 檔名包含: MMDD + Slag/Filename
            # 所以如果 existing_jpgs 的某些 key 包含 (mmdd + target_slug)，就算匹配
            
            mmdd_norm = normalize_string_for_compare(mmdd)
            
            for slug in target_slugs:
                # 組合期望的關鍵特徵: mmdd + slug
                # 注意: 實際檔名可能是 mmdd_slug_creator.jpg，中間可能有其他字符
                # 所以我們檢查 key 是否包含 mmdd 和 slug
                
                # 簡單模式: 檢查是否有任何 jpg 的標準化名稱等於 mmdd + slug (或其他組合)
                # 由於這比較嚴格，我們改用包含測試
                
                for exist_norm, exist_f in existing_jpgs.items():
                    # 檢查是否以 mmdd 開頭，並且包含 slug
                    if exist_norm.startswith(mmdd_norm) and slug in exist_norm:
                        jpg_path = os.path.join(jpg_output_dir, exist_f)
                        break
                if jpg_path: break
            
            # 如果還沒找到，嘗試放寬條件: 只要包含 slug 且在目標資料夾內 (假設資料夾本身已經分日期了)
            if not jpg_path:
                 for slug in target_slugs:
                    for exist_norm, exist_f in existing_jpgs.items():
                        if slug in exist_norm:
                            jpg_path = os.path.join(jpg_output_dir, exist_f)
                            break
                    if jpg_path: break

            if jpg_path and os.path.exists(jpg_path):
                # 只有當縮圖存在時才添加到網格
                self.thumbnail_grid.add_placeholder(filename, grid_index)
                self.thumbnail_grid.update_thumbnail(filename, jpg_path)
                grid_index += 1
        
        # 設置為 ScrollArea 的內容
        self.scroll.setWidget(self.thumbnail_grid)
        # ============================================

        total_found = len(all_txt_files)
        filtered_count = len(filtered_files)
        self.add_log(f"✓ 找到 {filtered_count} 個晚報YT縮圖檔案 (總共 {total_found} 個 .txt 文件)")

    def update_generation_stats(self):
        """依本次批次工作狀態更新待生成／完成／失敗數量。"""
        self.stats_label.setText(
            format_generation_stats(
                len(self.batch_pending_files),
                len(self.batch_completed_files),
                len(self.batch_failed_files),
            )
        )

    def start_generation_stats(self, filenames):
        self.batch_generation_active = True
        self.batch_pending_files = set(filenames)
        self.batch_completed_files = set()
        self.batch_failed_files = set()
        self.update_generation_stats()

    def finish_generation_file(self, filename, succeeded):
        """單張批次工作完成時即時更新統計，重複信號不重複計數。"""
        if not self.batch_generation_active or filename not in self.batch_pending_files:
            return
        self.batch_pending_files.discard(filename)
        if succeeded:
            self.batch_completed_files.add(filename)
        else:
            self.batch_failed_files.add(filename)
        self.update_generation_stats()
    
    def on_start_clicked(self):
        """開始生成"""
        try:
            creator = self.creator_input.text().strip()
            if not creator:
                QMessageBox.warning(self, "警告", "請輸入製作者名稱")
                return
            
            checked_files = self.file_list.get_checked_files()
            if not checked_files:
                QMessageBox.warning(self, "警告", "請選擇至少一個文件")
                return
            
            # 保存設定
            self.settings["creator"] = creator
            self.save_settings()
            
            # 更新 UI 狀態
            self.start_btn.setEnabled(False)
            self.start_btn.setText("⏳ 處理中...")
            self.pause_btn.show()
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("⏸ 暫停")
            self.progress_label.setText(f"處理中... (0/{len(checked_files)})")
            
            self.add_log(f"▶ 開始生成 {len(checked_files)} 個縮圖")
            self.add_log(f"  製作者: {creator}")
            
            # 準備預覽縮圖網格 (如果不存在則建立，存在則重置選中項狀態)
            if not hasattr(self, 'thumbnail_grid') or self.thumbnail_grid is None:
                self.thumbnail_grid = ThumbnailGridWidget(parent_window=self)
                self.thumbnail_grid.reprocess_requested.connect(self.on_reprocess_requested)
                self.thumbnail_grid.thumbnail_selected.connect(self.on_thumbnail_selected)
                self.scroll.setWidget(self.thumbnail_grid)

            # 重置選中檔案的狀態
            for filename in checked_files:
                # 確保項目存在於網格中
                if filename not in self.thumbnail_grid.thumbnails:
                    current_count = len(self.thumbnail_grid.thumbnails)
                    self.thumbnail_grid.add_placeholder(filename, current_count)
                
                # 重置顯示狀態為等待中
                self.thumbnail_grid.thumbnails[filename]["status_label"].setText("⏳ 等待生成")
                self.thumbnail_grid.thumbnails[filename]["status_label"].setPixmap(QPixmap()) # 清空圖片
                self.thumbnail_grid.thumbnails[filename]["status"] = "waiting"
                self.thumbnail_grid.thumbnails[filename]["jpg_path"] = None
                self.thumbnail_grid.thumbnails[filename]["psd_path"] = None
                self.thumbnail_grid.thumbnails[filename]["reprocess_btn"].setEnabled(False)
            
            # 更新統計
            self.start_generation_stats(checked_files)
            self.progress_bar.setValue(0)
            
            # 創建並啟動工作線程
            date = self.date_input.text().strip()
            if not is_valid_mmdd(date):
                QMessageBox.warning(self, "警告", "日期格式錯誤，請輸入 MMDD，例如 0813")
                self.batch_generation_active = False
                self.batch_pending_files.clear()
                self.batch_completed_files.clear()
                self.batch_failed_files.clear()
                self.update_generation_stats()
                self.start_btn.setEnabled(True)
                self.start_btn.setText("▶ 開始生成")
                self.pause_btn.hide()
                return
            last_folder = self.settings.get("last_folder", os.getcwd())
            
            self.worker = GenerationWorker(
                checked_files, date, creator, last_folder, self.thumbnail_overrides
            )
            self.worker.progress.connect(self.on_progress_update)
            self.worker.log.connect(self.on_worker_log)
            self.worker.completed.connect(self.on_generation_complete)
            self.worker.error.connect(self.on_worker_error)
            self.worker.warning.connect(self.on_worker_warning)
            self.worker.file_completed.connect(self.on_file_completed)
            self.worker.file_failed.connect(self.on_file_failed)
            self.worker.config_resolved.connect(self.on_config_resolved)
            self.worker.start()
            
        except Exception as e:
            self.add_log(f"❌ 錯誤: {str(e)}")
            self.start_btn.setEnabled(True)
            self.start_btn.setText("▶ 開始生成")
            self.pause_btn.hide()
            import traceback
            print(traceback.format_exc())

    def on_pause_clicked(self):
        """暫停/繼續"""
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                self.worker.resume()
                self.pause_btn.setText("⏸ 暫停")
                self.start_btn.setText("⏳ 處理中...")
                self.add_log("▶ 繼續執行")
            else:
                self.worker.pause()
                self.pause_btn.setText("▶ 繼續")
                self.start_btn.setText("⏸ 已暫停")
                self.add_log("⏸ 已暫停 (將在當前任務完成後暫停)")
    
    def on_progress_update(self, index, total, filename):
        """更新進度條"""
        if total > 0:
            percent = int((index / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"處理中... ({index}/{total})")
    
    def on_worker_log(self, message):
        """工作線程日誌"""
        self.add_log(message)
    
    def on_worker_error(self, error_msg):
        """工作線程錯誤"""
        if self.batch_generation_active:
            self.batch_failed_files.update(self.batch_pending_files)
            self.batch_pending_files.clear()
            self.batch_generation_active = False
            self.update_generation_stats()
        self.add_log(f"❌ {error_msg}")
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶ 開始生成")
        self.pause_btn.hide()

    def on_reprocess_error(self, error_msg):
        """單張重新生成失敗時停止 loading，並保留原縮圖。"""
        active_filename = self.active_reprocess_filename
        if active_filename and active_filename in self.thumbnail_grid.thumbnails:
            self.thumbnail_grid.stop_loading(active_filename)
            self.thumbnail_grid.thumbnails[active_filename]["reprocess_btn"].setEnabled(True)
        self.active_reprocess_filename = None
        self.on_worker_error(error_msg)

    def on_worker_warning(self, warning_msg):
        """顯示可略過的單檔警告，批次工作繼續執行。"""
        QMessageBox.warning(self, "檔案已略過", warning_msg)

    
    def on_generation_complete(self, success_count, failed_count, total_count):
        """生成完成"""
        self.batch_generation_active = False
        self.batch_pending_files.clear()
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶ 開始生成")
        self.pause_btn.hide()
        self.pause_btn.setText("⏸ 暫停")
        self.progress_bar.setValue(100)
        self.progress_label.setText("已完成")
        
        # 更新統計
        self.stats_label.setText(format_generation_stats(0, success_count, failed_count))
        
        # 顯示結果於日誌 (取代彈出視窗)
        if failed_count == 0:
            msg = f"✓ 所有 {success_count} 個縮圖已成功生成！"
            color = DarkTheme.ACCENT_GREEN
        else:
            msg = f"⚠️ 部分完成 - 成功: {success_count} | 失敗: {failed_count} | 總計: {total_count}"
            color = DarkTheme.ACCENT_ORANGE
            
        # 使用 HTML 格式添加強調日誌
        timestamp = datetime.now().strftime("%H:%M:%S")
        # 多加兩行空行讓它更明顯
        self.log_text.append("")
        html_msg = f'<span style="color: {color}; font-weight: bold; font-size: 12pt;">[{timestamp}] {msg}</span>'
        self.log_text.append(html_msg)
        self.log_text.append("")
        
        # 自動滾動到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def on_file_completed(self, filename, jpg_path):
        """檔案生成完成，更新縮圖"""
        self.finish_generation_file(filename, True)
        self.thumbnail_grid.update_thumbnail(filename, jpg_path)
        report = self.pending_thumbnail_configs.pop(filename, None)
        if report:
            self.resolved_thumbnail_configs[filename] = report
            override = self.thumbnail_overrides.get(filename)
            if override is not None:
                override["color_id"] = report.get("color_id", override.get("color_id", ""))
                override["top_right_color"] = report.get(
                    "top_right_color", override.get("top_right_color", "")
                )
            self.persist_thumbnail_config(filename, report, jpg_path)
            if self.selected_thumbnail_filename == filename:
                self.on_thumbnail_selected(filename)
    
    def on_file_failed(self, filename):
        """檔案生成失敗，標記為失敗狀態"""
        self.finish_generation_file(filename, False)
        self.thumbnail_grid.mark_failed(filename)
    
    def on_reprocess_complete(self, success_count, failed_count, total_count):
        """重新處理完成"""
        active_filename = self.active_reprocess_filename
        if active_filename and active_filename in self.thumbnail_grid.thumbnails:
            self.thumbnail_grid.stop_loading(active_filename)
            self.thumbnail_grid.thumbnails[active_filename]["reprocess_btn"].setEnabled(True)
        self.active_reprocess_filename = None
        # 顯示結果於日誌
        if failed_count == 0:
            msg = f"✓ 縮圖重新生成成功！"
            color = DarkTheme.ACCENT_GREEN
        else:
            msg = f"⚠️ 重新生成失敗"
            color = DarkTheme.ACCENT_RED
            
        # 使用 HTML 格式添加強調日誌
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append("")
        html_msg = f'<span style="color: {color}; font-weight: bold; font-size: 12pt;">[{timestamp}] {msg}</span>'
        self.log_text.append(html_msg)
        self.log_text.append("")
        
        # 自動滾動到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def on_reprocess_requested(self, filename):
        """重新處理單個檔案的請求"""
        try:
            self.add_log(f"🔔 接收重新處理信號: {filename}")
            # 取得檔案的完整路徑
            last_folder = self.settings.get("last_folder", os.getcwd())
            file_path = os.path.join(last_folder, filename)
            
            # 如果找不到檔案，嘗試加上 .txt 副檔名（防呆機制）
            if not os.path.exists(file_path):
                if not filename.lower().endswith('.txt'):
                    test_path = os.path.join(last_folder, filename + ".txt")
                    if os.path.exists(test_path):
                        self.add_log(f"ℹ️ 自動修正檔名: {filename} -> {filename}.txt")
                        filename = filename + ".txt"
                        file_path = test_path
            
            if not os.path.exists(file_path):
                self.add_log(f"❌ 檔案不存在: {file_path}")
                return
            
            # 檢查縮圖是否存在
            # 注意: 如果我們修正了 filename (加上 .txt)，這裡的檢查也要對應調整
            # 但 grid 中的 key 通常是原始傳入的 filename
            # 如果 key 不匹配，我們可能無法更新 UI 狀態，但仍可執行生成
            target_key = filename
            if filename not in self.thumbnail_grid.thumbnails:
                # 嘗試找原始 key (去掉 .txt 的版本，或是加上 .txt 的版本)
                if filename.endswith(".txt") and filename[:-4] in self.thumbnail_grid.thumbnails:
                    target_key = filename[:-4]
                elif filename + ".txt" in self.thumbnail_grid.thumbnails:
                    target_key = filename + ".txt"
                else:
                    self.add_log(f"⚠️ 找不到對應的縮圖元件 (key: {filename})，將繼續執行但無法更新狀態")
                    target_key = None
            
            # 重置該檔案的縮圖狀態
            if target_key:
                self.thumbnail_grid.show_reprocess_loading(target_key)
                self.thumbnail_grid.thumbnails[target_key]["reprocess_btn"].setEnabled(False)
                self.active_reprocess_filename = target_key
            
            self.add_log(f"↻ 重新生成: {filename}")
            
            # 建立只包含這個檔案的 worker
            date = self.date_input.text().strip()
            if not is_valid_mmdd(date):
                QMessageBox.warning(self, "警告", "日期格式錯誤，請輸入 MMDD，例如 0813")
                return
            creator = self.creator_input.text().strip()
            
            self.reprocess_worker = GenerationWorker(
                [filename], date, creator, last_folder, self.thumbnail_overrides
            )
            self.reprocess_worker.progress.connect(self.on_progress_update)
            self.reprocess_worker.log.connect(self.on_worker_log)
            self.reprocess_worker.file_completed.connect(self.on_file_completed)
            self.reprocess_worker.file_failed.connect(self.on_file_failed)
            self.reprocess_worker.config_resolved.connect(self.on_config_resolved)
            self.reprocess_worker.error.connect(self.on_reprocess_error)
            self.reprocess_worker.warning.connect(self.on_worker_warning)
            # 連接完成信號
            self.reprocess_worker.completed.connect(self.on_reprocess_complete)
            self.reprocess_worker.start()
            
            self.add_log(f"✓ 重新處理 worker 已啟動")
        except Exception as e:
            import traceback
            traceback.print_exc()
            if self.active_reprocess_filename:
                self.thumbnail_grid.stop_loading(self.active_reprocess_filename)
                self.active_reprocess_filename = None
            self.add_log(f"❌ 重新處理出錯: {str(e)}")

    
    def on_clear_log(self):
        """清空日誌"""
        self.log_text.clear()
    
    def on_open_folder(self):
        """打開輸出文件夾"""
        date = self.date_input.text().strip()
        if is_valid_mmdd(date):
            output_folder = os.path.join(r"\\10.227.58.117\新聞psd", date, "縮圖")
        else:
            output_folder = r"\\10.227.58.117\新聞psd"
        try:
            os.startfile(output_folder)
        except:
            QMessageBox.warning(self, "錯誤", f"無法打開文件夾: {output_folder}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
