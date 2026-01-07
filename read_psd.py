#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讀取PSD檔案並顯示圖層資訊
"""

import os
import sys

# 設定Windows終端機編碼為UTF-8
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul 2>&1')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

try:
    from psd_tools import PSDImage
    print("正在讀取PSD檔案...")
    print("="*60)
    
    psd_file = "晚報YT縮圖.psd"
    
    if not os.path.exists(psd_file):
        print(f"錯誤: 找不到檔案 {psd_file}")
        sys.exit(1)
    
    # 讀取PSD檔案
    psd = PSDImage.open(psd_file)
    
    print(f"檔案名稱: {psd_file}")
    print(f"寬度: {psd.width}")
    print(f"高度: {psd.height}")
    print(f"顏色模式: {psd.color_mode}")
    print(f"圖層數量: {len(list(psd))}")
    print("="*60)
    print("\n圖層列表:")
    print("="*60)
    
    def print_layers(layer, indent=0):
        """遞迴打印圖層"""
        prefix = "  " * indent
        layer_name = layer.name if hasattr(layer, 'name') else "未知"
        layer_type = type(layer).__name__
        
        print(f"{prefix}[{layer_type}] {layer_name}")
        
        # 如果有可見性屬性
        if hasattr(layer, 'visible'):
            print(f"{prefix}  可見: {layer.visible}")
        
        # 如果有不透明度
        if hasattr(layer, 'opacity'):
            print(f"{prefix}  不透明度: {layer.opacity}")
        
        # 如果有混合模式
        if hasattr(layer, 'blend_mode'):
            print(f"{prefix}  混合模式: {layer.blend_mode}")
        
        # 如果有子圖層
        if hasattr(layer, '__iter__'):
            for sublayer in layer:
                print_layers(sublayer, indent + 1)
    
    # 打印所有圖層
    for layer in psd:
        print_layers(layer)
    
    print("="*60)
    print(f"\n總共找到 {len(list(psd))} 個頂層圖層")
    
except ImportError:
    print("錯誤: 需要安裝 psd-tools 套件")
    print("請執行: pip install psd-tools")
    sys.exit(1)
except Exception as e:
    print(f"讀取PSD檔案時發生錯誤: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

