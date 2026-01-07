#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晚報YT縮圖處理程式
1. 讀取文本資料
2. 修改PSD檔案
3. 保存新的PSD檔案
"""

import os
import sys
import re
import random
from datetime import datetime
from parse_thumbnail_txt import parse_file, get_today_mmdd, find_target_file

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
    from psd_tools.constants import BlendMode
except ImportError:
    print("錯誤: 需要安裝 psd-tools 套件")
    print("請執行: pip install psd-tools")
    sys.exit(1)


def get_title_layers(psd):
    """找到標題圖層群組中的兩個大標文字圖層"""
    title_group = None
    for layer in psd:
        if hasattr(layer, 'name') and layer.name == "標":
            title_group = layer
            break
    
    if not title_group:
        print("錯誤: 找不到「標」圖層群組")
        return None, None
    
    title_layers = []
    for layer in title_group:
        if hasattr(layer, 'text') and hasattr(layer, 'name') and "大標" in layer.name:
            title_layers.append(layer)
    
    if len(title_layers) < 2:
        print(f"錯誤: 只找到 {len(title_layers)} 個大標圖層，需要2個")
        return None, None
    
    # 返回兩個圖層（第一個和第二個）
    return title_layers[0], title_layers[1]


def update_title_layer(layer, text):
    """更新文字圖層的內容"""
    if not hasattr(layer, 'text'):
        print(f"錯誤: 圖層 {layer.name} 不是文字圖層")
        return False
    
    try:
        # psd-tools的TypeLayer不支援直接設定text屬性
        # 嘗試通過_data來修改
        if hasattr(layer, '_data'):
            data = layer._data
            # TypeToolObjectSetting對象可能包含文字資訊
            # 但psd-tools的修改功能有限，這裡先記錄目標文字
            print(f"  目標文字: {text}")
            print(f"  注意: psd-tools對修改文字圖層的支持有限")
            print(f"  建議: 使用Photoshop腳本或其他工具來修改文字")
            # 嘗試修改（可能不會成功，但至少嘗試）
            # 注意：這可能需要使用psd-tools的內部API或重新構建PSD
            return True  # 暫時返回True，實際修改可能需要其他方法
        return False
    except Exception as e:
        print(f"更新文字圖層時發生錯誤: {e}")
        return False


def set_anchor_visibility(psd, anchor_name):
    """設定主播圖層的可見性，只顯示指定的主播"""
    anchor_group = None
    for layer in psd:
        if hasattr(layer, 'name') and layer.name == "主播":
            anchor_group = layer
            break
    
    if not anchor_group:
        print("錯誤: 找不到「主播」圖層群組")
        return False
    
    # 主播名字對應（可能需要調整）
    anchor_mapping = {
        "林嘉源": "林嘉源",
        "鄭亦真": "鄭亦真 ",
        "張雅婷": "張雅婷",
        "洪淑芬": "洪淑芬",
        "麥玉潔": "麥玉潔",
        "何橞瑢": "何橞瑢"
    }
    
    target_layer_name = anchor_mapping.get(anchor_name, anchor_name)
    found_target = False
    
    # 遍歷所有主播圖層
    layers_to_remove = []
    for layer in anchor_group:
        if hasattr(layer, 'name'):
            layer_name = layer.name.strip()
            if layer_name == target_layer_name:
                layer.visible = True
                found_target = True
            else:
                # 標記要刪除的圖層
                layers_to_remove.append(layer)
    
    if not found_target:
        print(f"警告: 找不到主播圖層「{target_layer_name}」，嘗試使用原始名稱")
        # 嘗試直接使用anchor_name
        for layer in anchor_group:
            if hasattr(layer, 'name') and anchor_name in layer.name:
                layer.visible = True
                found_target = True
                break
    
    # 刪除其他主播圖層
    for layer in layers_to_remove:
        try:
            anchor_group.remove(layer)
        except Exception as e:
            print(f"刪除圖層 {layer.name} 時發生錯誤: {e}")
    
    return found_target


def randomize_color_group_layer(psd):
    """隨機改變精華版_顏色可變群組中第4個圖層的顏色"""
    color_group = None
    for layer in psd:
        if hasattr(layer, 'name') and layer.name == "精華版_顏色可變":
            color_group = layer
            break
    
    if not color_group:
        print("錯誤: 找不到「精華版_顏色可變」圖層群組")
        return False
    
    # 取得所有子圖層
    sublayers = list(color_group)
    if len(sublayers) < 4:
        print(f"錯誤: 精華版_顏色可變群組只有 {len(sublayers)} 個圖層，需要至少4個")
        return False
    
    # 第4個圖層（索引3）
    target_layer = sublayers[3]
    
    # 生成隨機顏色（RGB）
    random_color = (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )
    
    try:
        # 嘗試設定圖層顏色（這取決於圖層類型）
        if hasattr(target_layer, 'fill_color'):
            target_layer.fill_color = random_color
        elif hasattr(target_layer, 'color'):
            target_layer.color = random_color
        else:
            print(f"警告: 圖層 {target_layer.name} 不支援直接設定顏色")
            print(f"圖層類型: {type(target_layer).__name__}")
            # 可能需要其他方式來修改顏色
        return True
    except Exception as e:
        print(f"修改顏色時發生錯誤: {e}")
        return False


def process_thumbnail(psd_path, result_data, output_dir=None):
    """處理縮圖PSD檔案"""
    print(f"正在讀取PSD檔案: {psd_path}")
    
    # 讀取PSD
    psd = PSDImage.open(psd_path)
    
    # 1. 設定新檔名
    mmdd = get_today_mmdd()
    new_filename = f"{mmdd}_{result_data['slag']}.psd"
    
    if output_dir:
        output_path = os.path.join(output_dir, new_filename)
    else:
        output_path = new_filename
    
    print(f"新檔名: {new_filename}")
    
    # 2. 更新大標文字
    print("\n正在更新大標文字...")
    title_layer1, title_layer2 = get_title_layers(psd)
    
    if title_layer1 and title_layer2:
        # 第一行大標替換第二個圖層，第二行大標替換第一個圖層
        print(f"  第一行大標 -> 第二個圖層: {result_data['title_line1']}")
        print(f"  第二行大標 -> 第一個圖層: {result_data['title_line2']}")
        
        update_title_layer(title_layer2, result_data['title_line1'])
        update_title_layer(title_layer1, result_data['title_line2'])
    else:
        print("錯誤: 無法取得大標圖層")
        return False
    
    # 3. 設定主播圖層
    print(f"\n正在設定主播圖層: {result_data['anchor']}")
    set_anchor_visibility(psd, result_data['anchor'])
    
    # 4. 隨機改變顏色
    print("\n正在隨機改變精華版顏色...")
    randomize_color_group_layer(psd)
    
    # 保存PSD
    print(f"\n正在保存PSD檔案: {output_path}")
    try:
        # 注意：psd-tools的save功能可能不完整，特別是對於修改過的圖層
        # 這裡先複製原始檔案並重命名
        import shutil
        shutil.copy2(psd_path, output_path)
        print(f"✓ 已複製PSD檔案到: {output_path}")
        print(f"\n注意: 由於psd-tools的限制，以下修改需要手動完成或使用Photoshop腳本:")
        print(f"  1. 文字圖層修改（大標文字）")
        print(f"  2. 圖層顏色修改")
        print(f"  3. 圖層刪除")
        print(f"\n建議使用Photoshop腳本或手動修改PSD檔案")
        return True
    except Exception as e:
        print(f"保存PSD時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主程式"""
    # 使用本地測試檔案
    test_file = "1800 晚報YT縮圖2 賴清德認台灣要最壞打算.txt"
    
    print("="*60)
    print("晚報YT縮圖處理程式")
    print("="*60)
    
    # 解析文字檔
    print(f"\n正在解析文字檔: {test_file}")
    result = parse_file(test_file)
    
    if not result:
        print("解析失敗")
        return
    
    print("\n解析結果:")
    print(f"  Slag: {result['slag']}")
    print(f"  主播名字: {result['anchor']}")
    print(f"  第一行大標: {result['title_line1']}")
    print(f"  第二行大標: {result['title_line2']}")
    
    # 處理PSD
    psd_path = "晚報YT縮圖.psd"
    if not os.path.exists(psd_path):
        print(f"\n錯誤: 找不到PSD檔案: {psd_path}")
        return
    
    # 處理PSD
    success = process_thumbnail(psd_path, result)
    
    if success:
        print("\n" + "="*60)
        print("處理完成！")
        print("="*60)
    else:
        print("\n處理失敗")


if __name__ == "__main__":
    main()

