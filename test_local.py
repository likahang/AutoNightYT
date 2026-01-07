#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試本地檔案解析"""

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

from parse_thumbnail_txt import parse_file

# 自動找到所有符合條件的測試檔案
current_dir = os.getcwd()
target_pattern = "1800 晚報YT縮圖"

# 找出所有包含"1800 晚報YT縮圖"的txt檔案
test_files = []
for file in os.listdir(current_dir):
    if target_pattern in file and file.endswith('.txt'):
        test_files.append(file)

# 按檔名排序
test_files.sort()

print(f"找到 {len(test_files)} 個測試檔案\n")

# 測試所有檔案
for i, filename in enumerate(test_files, 1):
    print(f"測試檔案 {i}/{len(test_files)}: {filename}")
    print("="*60)
    result = parse_file(filename)
    if result:
        print(f"Slag: {result['slag']}")
        print(f"主播名字: {result['anchor']}")
        print(f"第一行大標: {result['title_line1']}")
        print(f"第二行大標: {result['title_line2']}")
        print(f"變色字: {result['color_words']}")
        print(f"效果字: {result['effect_words']}")
    else:
        print("解析失敗")
    print("\n")

print(f"測試完成！共測試 {len(test_files)} 個檔案")

