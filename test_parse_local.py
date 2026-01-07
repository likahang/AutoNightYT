#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試程式 - 使用本地檔案測試解析邏輯
"""

import re
from parse_thumbnail_txt import parse_file

def test_parse_local_file():
    """測試解析本地檔案"""
    # 使用現有的文字檔測試
    test_file = "1800 晚報YT縮圖1 賴清德爆氣+蔡正元.txt"
    
    print(f"測試檔案: {test_file}")
    print("="*50)
    
    result = parse_file(test_file)
    
    if result:
        print("解析結果:")
        print(f"Slag: {result['slag']}")
        print(f"主播名字: {result['anchor']}")
        print(f"第一行大標: {result['title_line1']}")
        print(f"第二行大標: {result['title_line2']}")
        print(f"變色字: {result['color_words']}")
        print(f"效果字: {result['effect_words']}")
        print("="*50)
        
        # 驗證結果
        print("\n驗證:")
        assert result['slag'] == "1800 晚報YT縮圖1 賴清德爆氣+蔡正元 重一", "Slag不正確"
        assert result['anchor'] == "何橞瑢", "主播名字不正確"
        assert "賴爆氣" in result['title_line1'] or "反擊" in result['title_line1'], "第一行大標不正確"
        assert "蔡正元" in result['title_line2'] or "炸了" in result['title_line2'], "第二行大標不正確"
        assert "賴爆氣" in result['color_words'] or "反擊" in result['color_words'], "變色字不完整"
        assert "漫畫爆炸" in result['effect_words'], "效果字不完整"
        
        print("✓ 所有測試通過！")
    else:
        print("解析失敗")

if __name__ == "__main__":
    test_parse_local_file()

