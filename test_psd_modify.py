#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試PSD修改功能"""

import os
import sys

if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul 2>&1')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from psd_tools import PSDImage

psd = PSDImage.open("晚報YT縮圖.psd")

# 找到標題圖層
for layer in psd:
    if hasattr(layer, 'name') and layer.name == "標":
        print(f"找到「標」群組")
        for sublayer in layer:
            if hasattr(sublayer, 'text') and "大標" in sublayer.name:
                print(f"\n圖層: {sublayer.name}")
                print(f"類型: {type(sublayer)}")
                print(f"文字內容: {sublayer.text}")
                print(f"可用屬性: {dir(sublayer)}")
                
                # 檢查engine_data
                if hasattr(sublayer, 'engine_data'):
                    print(f"\nengine_data類型: {type(sublayer.engine_data)}")
                    if sublayer.engine_data:
                        print(f"engine_data內容: {sublayer.engine_data}")
                
                # 檢查是否有其他可修改的屬性
                print(f"\n嘗試修改...")
                try:
                    # 嘗試各種方法
                    if hasattr(sublayer, '_data'):
                        print(f"_data存在: {sublayer._data}")
                except Exception as e:
                    print(f"錯誤: {e}")

