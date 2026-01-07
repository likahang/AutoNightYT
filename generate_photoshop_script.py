#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成Photoshop腳本來修改PSD檔案
"""

import os
import sys
import random
from datetime import datetime
from parse_thumbnail_txt import parse_file, get_today_mmdd

# 設定Windows終端機編碼為UTF-8
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul 2>&1')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


def generate_jsx_script(result_data, psd_path, output_path):
    """生成Photoshop JSX腳本"""
    
    mmdd = get_today_mmdd()
    
    # 清理檔案名稱，移除Windows不允許的字元
    def sanitize_filename(filename):
        # Windows不允許的字元: < > : " / \ | ? *
        # 也移除控制字元
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # 移除開頭和結尾的點和空格
        filename = filename.strip('. ')
        # 移除連續的底線
        while '__' in filename:
            filename = filename.replace('__', '_')
        # 限制長度（Windows路徑限制，PSD檔案名稱建議不超過255字元）
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    new_filename = sanitize_filename(f"{mmdd}_{result_data['slag']}.psd")
    
    # 轉義JavaScript字串中的特殊字元
    def escape_js_string(s):
        s = str(s)
        s = s.replace('\\', '\\\\')  # 先處理反斜線
        s = s.replace('"', '\\"')     # 處理雙引號
        s = s.replace('\n', '\\n')    # 處理換行
        s = s.replace('\r', '\\r')    # 處理回車
        return s
    
    title1 = escape_js_string(result_data['title_line1'])
    title2 = escape_js_string(result_data['title_line2'])
    anchor_name = escape_js_string(result_data['anchor'])
    
    # 生成隨機顏色（RGB）
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    
    # 準備路徑（轉換為正斜線）
    psd_path_escaped = os.path.abspath(psd_path).replace(os.sep, '/')
    output_path_escaped = os.path.abspath(output_path).replace(os.sep, '/')
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 構建JSX腳本（使用字串連接避免f-string大括號問題）
    script_lines = [
        "#target photoshop",
        "",
        "// 晚報YT縮圖自動修改腳本",
        f"// 生成時間: {gen_time}",
        "",
        "// 將 Hex 轉換為 RGB 的輔助函式",
        "function hexToRgb(hex) {",
        "    var r = parseInt(hex.substring(0, 2), 16);",
        "    var g = parseInt(hex.substring(2, 4), 16);",
        "    var b = parseInt(hex.substring(4, 6), 16);",
        "    return { r: r, g: g, b: b };",
        "}",
        "",
        "// 設定形狀圖層顏色的函式",
        "function setShapeColor(r, g, b) {",
        "    function s2t(s) { return app.stringIDToTypeID(s); }",
        "",
        "    var descriptor = new ActionDescriptor();",
        "    var descriptor2 = new ActionDescriptor();",
        "    var descriptor3 = new ActionDescriptor();",
        "    var reference = new ActionReference();",
        "",
        "    reference.putEnumerated(s2t(\"contentLayer\"), s2t(\"ordinal\"), s2t(\"targetEnum\"));",
        "    descriptor.putReference(s2t(\"null\"), reference);",
        "",
        "    // 這裡使用 Photoshop 內部的 ID：red, grain, blue",
        "    descriptor3.putDouble(s2t(\"red\"), r);",
        "    descriptor3.putDouble(s2t(\"grain\"), g);",
        "    descriptor3.putDouble(s2t(\"blue\"), b);",
        "    ",
        "    descriptor2.putObject(s2t(\"color\"), s2t(\"RGBColor\"), descriptor3);",
        "    descriptor.putObject(s2t(\"to\"), s2t(\"solidColorLayer\"), descriptor2);",
        "",
        "    executeAction(s2t(\"set\"), descriptor, DialogModes.NO);",
        "}",
        "",
        "// 打開PSD檔案",
        f'var psdFile = new File("{psd_path_escaped}");',
        "if (!psdFile.exists) {",
        '    alert("錯誤: 找不到PSD檔案: " + psdFile.fsName);',
        "    exit();",
        "}",
        "app.open(psdFile);",
        "",
        "// 1. 重命名檔案",
        f'var newName = "{new_filename}";',
        "app.activeDocument.name = newName;",
        "",
        "// 2. 修改大標文字",
        "// 找到「標」群組",
        "var titleGroup = null;",
        "for (var i = 0; i < app.activeDocument.layers.length; i++) {",
        '    if (app.activeDocument.layers[i].name == "標") {',
        "        titleGroup = app.activeDocument.layers[i];",
        "        break;",
        "    }",
        "}",
        "",
        'if (titleGroup && titleGroup.typename == "LayerSet") {',
        "    // 找到兩個大標圖層",
        "    var titleLayers = [];",
        "    for (var i = 0; i < titleGroup.layers.length; i++) {",
        '        if (titleGroup.layers[i].name.indexOf("大標") != -1) {',
        "            titleLayers.push(titleGroup.layers[i]);",
        "        }",
        "    }",
        "    ",
        "    if (titleLayers.length >= 2) {",
        "        // 第一行大標替換第二個圖層，第二行大標替換第一個圖層",
        "        try {",
        f'            titleLayers[1].textItem.contents = "{title1}";',
        f'            titleLayers[0].textItem.contents = "{title2}";',
        "            ",
            "            // 使用變形方式改變圖層寬度",
            "            // 第一行大標 - 設定寬度為 1600",
            "            app.activeDocument.activeLayer = titleLayers[1];",
            "            var bounds1 = titleLayers[1].bounds;",
            "            var currentWidth1 = bounds1[2] - bounds1[0];",
            "            var currentHeight1 = bounds1[3] - bounds1[1];",
            "            var scaleX1 = 1600 / currentWidth1;",
            "            ",
            "            // 使用 resize 方法 - 從左側縮放",
            "            titleLayers[1].resize(scaleX1 * 100, 100, AnchorPosition.MIDDLELEFT);",
            "            ",
            "            // 第二行大標 - 設定寬度為 1620",
            "            app.activeDocument.activeLayer = titleLayers[0];",
            "            var bounds2 = titleLayers[0].bounds;",
            "            var currentWidth2 = bounds2[2] - bounds2[0];",
            "            var currentHeight2 = bounds2[3] - bounds2[1];",
            "            var scaleX2 = 1620 / currentWidth2;",
            "            ",
            "            // 使用 resize 方法 - 從左側縮放",
            "            titleLayers[0].resize(scaleX2 * 100, 100, AnchorPosition.MIDDLELEFT);",
        "        } catch (e) {",
        '            alert("修改大標文字時發生錯誤: " + e);',
        "        }",
        "        ",
        "        // 為兩個大標圖層添加Outside Stroke 15px 和 Drop Shadow",
        "        for (var i = 0; i < titleLayers.length; i++) {",
        "            try {",
        "                var layer = titleLayers[i];",
        "                app.activeDocument.activeLayer = layer;",
        "                ",
        "                // 添加描邊和陰影效果 - 使用參考腳本的方法",
        "                var s2t = stringIDToTypeID;",
        "                ",
        "                var descriptor = new ActionDescriptor();",
        "                var reference = new ActionReference();",
        "                reference.putProperty(s2t('property'), s2t('layerEffects'));",
        "                reference.putEnumerated(s2t('layer'), s2t('ordinal'), s2t('targetEnum'));",
        "                descriptor.putReference(s2t('null'), reference);",
        "                ",
        "                var effectsDesc = new ActionDescriptor();",
        "                ",
        "                // --- 1. 15px 外部描邊 ---",
        "                var strokeDesc = new ActionDescriptor();",
        "                strokeDesc.putBoolean(s2t('enabled'), true);",
        "                strokeDesc.putUnitDouble(s2t('size'), s2t('pixelsUnit'), 15);",
        "                strokeDesc.putEnumerated(s2t('style'), s2t('frameStyle'), s2t('outsetFrame')); // 外部",
        "                ",
        "                var strokeColor = new ActionDescriptor();",
        "                strokeColor.putDouble(s2t('red'), 0);",
        "                strokeColor.putDouble(s2t('grain'), 0);",
        "                strokeColor.putDouble(s2t('blue'), 0);",
        "                strokeDesc.putObject(s2t('color'), s2t('RGBColor'), strokeColor);",
        "                effectsDesc.putObject(s2t('frameFX'), s2t('frameFX'), strokeDesc);",
        "                ",
        "                // --- 2. 硬邊陰影 ---",
        "                var shadowDesc = new ActionDescriptor();",
        "                shadowDesc.putBoolean(s2t('enabled'), true);",
        "                shadowDesc.putEnumerated(s2t('mode'), s2t('blendMode'), s2t('normal')); // 混合模式: 正常",
        "                shadowDesc.putUnitDouble(s2t('opacity'), s2t('percentUnit'), 100);",
        "                shadowDesc.putUnitDouble(s2t('localLightingAngle'), s2t('angleUnit'), 120); // 角度 120",
        "                shadowDesc.putUnitDouble(s2t('distance'), s2t('pixelsUnit'), 10); // 距離 10px",
        "                shadowDesc.putUnitDouble(s2t('chokeMatte'), s2t('pixelsUnit'), 100); // 展開 (Spread) 100%",
        "                shadowDesc.putUnitDouble(s2t('blur'), s2t('pixelsUnit'), 18); // 尺寸 (Size) 18px",
        "                ",
        "                var shadowColor = new ActionDescriptor();",
        "                shadowColor.putDouble(s2t('red'), 0);",
        "                shadowColor.putDouble(s2t('grain'), 0);",
        "                shadowColor.putDouble(s2t('blue'), 0);",
        "                shadowDesc.putObject(s2t('color'), s2t('RGBColor'), shadowColor);",
        "                effectsDesc.putObject(s2t('dropShadow'), s2t('dropShadow'), shadowDesc);",
        "                ",
        "                // --- 執行套用 ---",
        "                descriptor.putObject(s2t('to'), s2t('layerEffects'), effectsDesc);",
        "                executeAction(s2t('set'), descriptor, DialogModes.NO);",
        "            } catch (e) {",
        "                alert('為大標圖層添加描邊和陰影時發生錯誤: ' + e);",
        "            }",
        "        }",
        "    } else {",
        '        alert("警告: 只找到 " + titleLayers.length + " 個大標圖層，需要2個");',
        "    }",
        '} else if (!titleGroup) {',
        '    alert("警告: 找不到「標」圖層群組");',
        "}",
        "",
        "// 3. 設定主播圖層可見性",
        "var anchorGroup = null;",
        "for (var i = 0; i < app.activeDocument.layers.length; i++) {",
        '    if (app.activeDocument.layers[i].name == "主播") {',
        "        anchorGroup = app.activeDocument.layers[i];",
        "        break;",
        "    }",
        "}",
        "",
        'if (anchorGroup && anchorGroup.typename == "LayerSet") {',
        "    // 主播名字對應",
        "    var anchorMapping = {",
        '        "林嘉源": "林嘉源",',
        '        "鄭亦真": "鄭亦真 ",',
        '        "張雅婷": "張雅婷",',
        '        "洪淑芬": "洪淑芬",',
        '        "麥玉潔": "麥玉潔",',
        '        "何橞瑢": "何橞瑢"',
        "    };",
        "    ",
        f'    var targetName = anchorMapping["{anchor_name}"] || "{anchor_name}";',
        "    var layersToDelete = [];",
        "    var foundTarget = false;",
        "    ",
        "    for (var i = 0; i < anchorGroup.layers.length; i++) {",
        "        var layer = anchorGroup.layers[i];",
        "        var layerName = layer.name;",
        "        // 移除尾隨空格",
        '        while (layerName.length > 0 && layerName.charAt(layerName.length - 1) == " ") {',
        "            layerName = layerName.substring(0, layerName.length - 1);",
        "        }",
        "        ",
        "        if (layerName == targetName) {",
        "            layer.visible = true;",
        "            foundTarget = true;",
        "        } else {",
        "            layersToDelete.push(layer);",
        "        }",
        "    }",
        "    ",
        "    if (!foundTarget) {",
        '        alert("警告: 找不到主播圖層「" + targetName + "」");',
        "    }",
        "    ",
        "    // 刪除其他主播圖層（從後往前刪除，避免索引問題）",
        "    for (var i = layersToDelete.length - 1; i >= 0; i--) {",
        "        try {",
        "            layersToDelete[i].remove();",
        "        } catch (e) {",
        '            alert("刪除圖層時發生錯誤: " + e);',
        "        }",
        "    }",
        '} else if (!anchorGroup) {',
        '    alert("警告: 找不到「主播」圖層群組");',
        "}",
        "",
        "// 4. 修改精華版_顏色可變群組",
        "var colorGroup = null;",
        "for (var i = 0; i < app.activeDocument.layers.length; i++) {",
        '    if (app.activeDocument.layers[i].name == "精華版_顏色可變") {',
        "        colorGroup = app.activeDocument.layers[i];",
        "        break;",
        "    }",
        "}",
        "",
        f'if (colorGroup && colorGroup.typename == "LayerSet") {{',
        "    // 4.1 第一個圖層（索引0）替換成主播名字",
        "    if (colorGroup.layers.length >= 1) {",
        "        var nameLayer = colorGroup.layers[0]; // 第一個圖層（索引0）",
        "        try {",
        "            if (nameLayer.kind == LayerKind.TEXT) {",
        f'                nameLayer.textItem.contents = "{anchor_name}";',
        "            }",
        "        } catch (e) {",
        '            alert("修改第一個圖層文字時發生錯誤: " + e);',
        "        }",
        "    }",
        "    ",
        "    // 4.2 第4個圖層（索引3）隨機變色",
        "    if (colorGroup.layers.length >= 4) {",
        "        var targetLayer = colorGroup.layers[3]; // 第4個圖層（索引3）",
        "        ",
        "        // 定義顏色清單 (Hex 格式)",
        "        var colorList = [",
        '            "f05910", "fe4701", "dc1000", "a700fe", ',
        '            "7800ff", "342292", "0031e5", "181aab", ',
        '            "1f2966", "00a322", "008f5a", "007e0b"',
        "        ];",
        "        ",
        "        // 隨機選取一個顏色",
        "        var randomHex = colorList[Math.floor(Math.random() * colorList.length)];",
        "        var rgb = hexToRgb(randomHex);",
        "        ",
        "        // 選擇圖層",
        "        app.activeDocument.activeLayer = targetLayer;",
        "        ",
        "        try {",
        "            setShapeColor(rgb.r, rgb.g, rgb.b);",
        "        } catch (e) {",
        '            alert("變更失敗。請確保選取的是「形狀圖層」或「純色填充層」。\\n錯誤: " + e);',
        "        }",
        "    } else {",
        '        alert("警告: 「精華版_顏色可變」群組只有 " + colorGroup.layers.length + " 個圖層，需要至少4個");',
        "    }",
        '} else if (!colorGroup) {',
        '    alert("警告: 找不到「精華版_顏色可變」圖層群組");',
        "}",
        "",
        "// 保存檔案",
        f'var saveFile = new File("{output_path_escaped}/" + newName);',
        "// 確保目錄存在",
        "if (!saveFile.parent.exists) {",
        "    saveFile.parent.create();",
        "}",
        "",
        "var psdOptions = new PhotoshopSaveOptions();",
        "psdOptions.embedColorProfile = true;",
        "psdOptions.alphaChannels = true;",
        "psdOptions.layers = true;",
        "",
        "try {",
        "    app.activeDocument.saveAs(saveFile, psdOptions);",
        '    alert("處理完成！\\n檔案已保存為: " + newName);',
        "} catch (e) {",
        '    alert("保存檔案時發生錯誤: " + e + "\\n檔案路徑: " + saveFile.fsName);',
        "}",
    ]
    
    return "\n".join(script_lines)


def main():
    """主程式"""
    test_file = "1800 晚報YT縮圖2 賴清德認台灣要最壞打算.txt"
    
    print("="*60)
    print("生成Photoshop腳本")
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
    
    # 生成JSX腳本
    psd_path = "晚報YT縮圖.psd"
    if not os.path.exists(psd_path):
        print(f"\n錯誤: 找不到PSD檔案: {psd_path}")
        return
    
    mmdd = get_today_mmdd()
    script_content = generate_jsx_script(result, psd_path, ".")
    
    # 保存腳本
    script_file = f"modify_thumbnail_{mmdd}.jsx"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n✓ Photoshop腳本已生成: {script_file}")
    print(f"\n使用方式:")
    print(f"  1. 打開Photoshop")
    print(f"  2. 選擇 檔案 > 腳本 > 瀏覽...")
    print(f"  3. 選擇 {script_file}")
    print(f"  4. 腳本會自動執行所有修改")


if __name__ == "__main__":
    main()
