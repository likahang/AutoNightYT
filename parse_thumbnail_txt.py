#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晚報YT縮圖文字檔解析程式
從網路路徑讀取文字檔並提取所需資訊
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path

# 設定Windows終端機編碼為UTF-8
if sys.platform == 'win32':
    try:
        # 設定終端機編碼為UTF-8
        os.system('chcp 65001 > nul 2>&1')
        # 設定標準輸出的編碼
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 主播名字列表
ANCHOR_NAMES = ["林嘉源", "鄭亦真", "張雅婷", "洪淑芬", "麥玉潔", "何橞瑢"]

# 需要排除的效果字關鍵字
EXCLUDED_EFFECT_KEYWORDS = ["大底黑色", "何橞瑢", "漫畫驚訝調暗暗"]


def get_today_mmdd():
    """取得今天的日期，格式為MMDD（月月日日）"""
    today = datetime.now()
    return today.strftime("%m%d")


def find_target_file(base_path):
    """在指定路徑下找到檔名包含'1800 晚報YT縮圖'的txt檔案"""
    target_pattern = "1800 晚報YT縮圖"
    
    try:
        # 列出目錄中的所有檔案
        files = os.listdir(base_path)
        
        # 找到符合條件的檔案
        for file in files:
            if target_pattern in file and file.endswith('.txt'):
                return os.path.join(base_path, file)
        
        return None
    except Exception as e:
        print(f"讀取目錄時發生錯誤: {e}")
        return None


def parse_file(file_path):
    """解析文字檔並提取所需資訊"""
    result = {
        "slag": "",
        "anchor": "",
        "title_line1": "",
        "title_line2": "",
        "color_words": [],
        "effect_words": []
    }
    
    lines = []
    # 嘗試多種編碼讀取
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n\r') for line in f.readlines()]
    except UnicodeDecodeError:
        try:
            print(f"UTF-8 解碼失敗，嘗試 CP950: {os.path.basename(file_path)}")
            with open(file_path, 'r', encoding='cp950') as f:
                lines = [line.rstrip('\n\r') for line in f.readlines()]
        except Exception as e:
            print(f"CP950 解碼也失敗: {e}")
            lines = []
    except Exception as e:
        print(f"讀取檔案錯誤: {e}")
        return None

    try:
        # 1. 第一行定義為Slag，如果第一行為空則使用檔名
        if lines and lines[0].strip():
            result["slag"] = lines[0].strip()
        else:
            # 使用檔名作為備援（移除副檔名）
            filename = os.path.basename(file_path)
            # 如果檔名包含空格，通常 Slag 也是用空格分隔，我們直接使用檔名即可
            result["slag"] = os.path.splitext(filename)[0]
        
        # 2. 找出主播名字
        for line in lines:
            for anchor in ANCHOR_NAMES:
                if anchor in line:
                    result["anchor"] = anchor
                    break
            if result["anchor"]:
                break
        
        # 3. 找出最後二行大標文字
        non_empty_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            # 跳過前面的元数据行和空行
            if stripped and not any(anchor in line for anchor in ANCHOR_NAMES) and i > 0:
                # 檢查是否是大標行
                if re.search(r'[a-zA-Z0-9\u4e00-\u9fff""]', stripped):
                    non_empty_lines.append(stripped)
        
        if len(non_empty_lines) >= 2:
            title1 = non_empty_lines[-2]
            title2 = non_empty_lines[-1]
        elif len(non_empty_lines) == 1:
            title1 = non_empty_lines[-1]
            title2 = ""
        else:
            title1 = ""
            title2 = ""
        
        result["title_line1"] = re.sub(r'\([^)]*\)', '', title1).strip()
        result["title_line2"] = re.sub(r'\([^)]*\)', '', title2).strip()
        
        # 4. 找出變色字
        full_text = '\n'.join(lines)
        color_word_pattern = r'"([^"]+)"'
        color_matches = re.findall(color_word_pattern, full_text)
        result["color_words"] = list(set(color_matches)) 
        
        # 5. 找出效果字
        effect_pattern = r'\(([^)]+)\)'
        effect_matches = re.findall(effect_pattern, full_text)
        
        for effect in effect_matches:
            should_exclude = False
            for keyword in EXCLUDED_EFFECT_KEYWORDS:
                if keyword in effect:
                    should_exclude = True
                    break
            
            if not should_exclude:
                result["effect_words"].append(effect.strip())
        
        result["effect_words"] = list(set(result["effect_words"]))
        
        return result
    
    except Exception as e:
        print(f"解析內容時發生錯誤: {e}")
        return None


def main():
    """主程式"""
    # 取得今天的日期
    mmdd = get_today_mmdd()
    print(f"今天的日期（MMDD格式）: {mmdd}")
    
    # 構建完整路徑
    base_path = f"\\\\10.227.58.117\\新聞txt\\{mmdd}\\1819"
    print(f"讀取路徑: {base_path}")
    
    # 檢查路徑是否存在
    if not os.path.exists(base_path):
        print(f"錯誤: 路徑不存在 - {base_path}")
        print("請確認:")
        print("1. 網路路徑是否可訪問")
        print("2. 日期是否正確")
        print("3. 目錄結構是否正確")
        return
    
    # 找到目標檔案
    target_file = find_target_file(base_path)
    
    if not target_file:
        print(f"錯誤: 在 {base_path} 中找不到包含'1800 晚報YT縮圖'的txt檔案")
        return
    
    print(f"找到目標檔案: {target_file}")
    
    # 解析檔案
    result = parse_file(target_file)
    
    if not result:
        print("解析失敗")
        return
    
    # 輸出結果到終端機
    print("\n" + "="*50)
    print("解析結果:")
    print("="*50)
    print(f"Slag: {result['slag']}")
    print(f"主播名字: {result['anchor']}")
    print(f"第一行大標: {result['title_line1']}")
    print(f"第二行大標: {result['title_line2']}")
    print(f"變色字: {result['color_words']}")
    print(f"效果字: {result['effect_words']}")
    print("="*50)
    
    # 同時將結果保存到檔案
    output_file = f"解析結果_{mmdd}.txt"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*50 + "\n")
            f.write("晚報YT縮圖解析結果\n")
            f.write("="*50 + "\n")
            f.write(f"日期: {mmdd}\n")
            f.write(f"來源檔案: {target_file}\n")
            f.write("-"*50 + "\n")
            f.write(f"Slag: {result['slag']}\n")
            f.write(f"主播名字: {result['anchor']}\n")
            f.write(f"第一行大標: {result['title_line1']}\n")
            f.write(f"第二行大標: {result['title_line2']}\n")
            f.write(f"變色字: {', '.join(result['color_words'])}\n")
            f.write(f"效果字: {', '.join(result['effect_words'])}\n")
            f.write("="*50 + "\n")
        print(f"\n結果已保存到檔案: {output_file}")
    except Exception as e:
        print(f"\n警告: 無法保存結果到檔案: {e}")
    
    # 也可以返回結果供其他程式使用
    return result


if __name__ == "__main__":
    main()

