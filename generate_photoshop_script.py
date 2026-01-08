#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成Photoshop腳本來修改PSD檔案
"""

import os
import sys
import csv
import argparse
import re
import random
from datetime import datetime
from parse_thumbnail_txt import parse_file, get_today_mmdd

# --- UTF-8 for Windows ---
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def load_color_schemes(csv_path):
    """從CSV檔案載入配色方案"""
    schemes = {}
    try:
        with open(csv_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader) # 跳過標頭
            
            key_map = ['base', 'stroke', 'special1', 'special2', 'shadow', 'explosion']

            rows = list(reader)
            i = 0
            while i < len(rows):
                row1 = rows[i]
                if len(row1) > 1 and row1[0]:
                    color_id = row1[0].upper()
                    if i + 1 < len(rows):
                        row2 = rows[i+1]
                        
                        colors1 = {key_map[j]: val.strip().lstrip('#') for j, val in enumerate(row1[2:])}
                        colors2 = {key_map[j]: val.strip().lstrip('#') for j, val in enumerate(row2[2:])}

                        schemes[color_id] = {"line1": colors1, "line2": colors2}
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
    except FileNotFoundError:
        print(f"錯誤: 找不到顏色設定檔: {csv_path}")
        return None
    except Exception as e:
        print(f"讀取CSV時發生錯誤: {e}")
        return None
        
    return schemes

def generate_jsx_script(result_data, color_scheme, psd_path, output_path):
    """生成Photoshop JSX腳本"""
    
    mmdd = get_today_mmdd()
    
    def sanitize_filename(filename):
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '_', filename)
        filename = filename.strip('. ')
        filename = re.sub(r'__+', '_', filename)
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    new_filename = sanitize_filename(f"{mmdd}_{result_data['slag']}.psd")
    
    def escape_js_string(s):
        s = str(s)
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n').replace('\r', '\\r')
        return s
    
    title1_raw = result_data['title_line1']
    title2_raw = result_data['title_line2']
    
    # 檢查第一行大標的引號是否成對
    quote_count_1 = title1_raw.count('"')
    if quote_count_1 % 2 != 0:
        print(f"\n⚠️  警告: 第一行大標發現未閉合的引號，請檢查確認")
        print(f"   標題內容: {title1_raw}")
        print(f"   引號數量: {quote_count_1} (應為偶數)")
        input("\n請按 Enter 繼續，或按 Ctrl+C 取消...")
    
    # 檢查第二行大標的引號是否成對
    quote_count_2 = title2_raw.count('"')
    if quote_count_2 % 2 != 0:
        print(f"\n⚠️  警告: 第二行大標發現未閉合的引號，請檢查確認")
        print(f"   標題內容: {title2_raw}")
        print(f"   引號數量: {quote_count_2} (應為偶數)")
        input("\n請按 Enter 繼續，或按 Ctrl+C 取消...")
    
    # 提取第一行大標的引號內文字
    quoted_matches_1 = re.findall(r'"(.*?)"', title1_raw)
    special_text_1 = escape_js_string(quoted_matches_1[0]) if len(quoted_matches_1) > 0 else ""
    special_text_2 = escape_js_string(quoted_matches_1[1]) if len(quoted_matches_1) > 1 else ""
    
    # 提取第二行大標的引號內文字
    quoted_matches_2 = re.findall(r'"(.*?)"', title2_raw)
    special_text_3 = escape_js_string(quoted_matches_2[0]) if len(quoted_matches_2) > 0 else ""
    special_text_4 = escape_js_string(quoted_matches_2[1]) if len(quoted_matches_2) > 1 else ""

    title1 = escape_js_string(title1_raw)
    title2 = escape_js_string(title2_raw)
    anchor_name = escape_js_string(result_data['anchor'])
    
    line1_colors = color_scheme["line1"]
    line2_colors = color_scheme["line2"]

    psd_path_escaped = os.path.abspath(psd_path).replace(os.sep, '/')
    output_path_escaped = os.path.abspath(output_path).replace(os.sep, '/')
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Define static parts of the script as regular strings
    jsx_header = f"""
#target photoshop
app.bringToFront();
// 晚報YT縮圖自動修改腳本
// 生成時間: {gen_time}
// 配色ID: {color_scheme.get('id', 'N/A')}
"""

    jsx_helpers = """
// --- Helper Functions ---
function hexToRgb(hex) {
    if (!hex || hex.length !== 6) return { r: 255, g: 255, b: 255 };
    var r = parseInt(hex.substring(0, 2), 16);
    var g = parseInt(hex.substring(2, 4), 16);
    var b = parseInt(hex.substring(4, 6), 16);
    return { r: r, g: g, b: b };
}

function setTextColor(layer, hexColor) {
    var rgb = hexToRgb(hexColor);
    var solidColor = new SolidColor();
    solidColor.rgb.red = rgb.r;
    solidColor.rgb.green = rgb.g;
    solidColor.rgb.blue = rgb.b;
    layer.textItem.color = solidColor;
}

function colorQuotedText(textLayer, textToColor, hexColor) {
    if (!textLayer || !textToColor || textToColor.length === 0 || !hexColor) return;
    
    try {
        // 設置活動圖層
        app.activeDocument.activeLayer = textLayer;
        
        // 獲取文字內容
        var content = textLayer.textItem.contents;
        var startIndex = content.indexOf(textToColor);
        if (startIndex === -1) return;
        
        var rgb = hexToRgb(hexColor);
        
        // 使用參考腳本的方法
        var originalRulerUnits = app.preferences.rulerUnits;
        app.preferences.rulerUnits = Units.PIXELS;
        
        var ref = new ActionReference();
        ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var layerDesc = executeActionGet(ref);
        var textDesc = layerDesc.getObjectValue(stringIDToTypeID('textKey'));
        var theText = textDesc.getString(stringIDToTypeID('textKey'));
        
        var rangeList = textDesc.getList(stringIDToTypeID('textStyleRange'));
        
        var idTxtt = charIDToTypeID("Txtt");
        var idFrom = charIDToTypeID("From");
        var idT = charIDToTypeID("T   ");
        var idTxtS = charIDToTypeID("TxtS");
        var idTxLr = charIDToTypeID("TxLr");
        var idTxt = charIDToTypeID("Txt ");
        var idsetd = charIDToTypeID("setd");
        
        // 構建樣式映射表 (Index -> rangeIndex)
        var styleIndexMap = [];
        
        for (var o = 0; o < rangeList.count; o++) {
            var rangeObj = rangeList.getObjectValue(o);
            var rFrom = rangeObj.getInteger(idFrom);
            var rTo = rangeObj.getInteger(idT);
            
            for (var k = rFrom; k < rTo; k++) {
                styleIndexMap[k] = o;
            }
        }
        
        var desc6 = new ActionDescriptor();
        var idnull = charIDToTypeID("null");
        var ref1 = new ActionReference();
        ref1.putEnumerated(idTxLr, charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        desc6.putReference(idnull, ref1);
        
        var desc7 = new ActionDescriptor();
        desc7.putString(idTxt, theText);
        var list2 = new ActionList();
        
        var targetStart = startIndex;
        var targetEnd = startIndex + textToColor.length;
        
        for (var m = 0; m < theText.length; m++) {
            var desc14 = new ActionDescriptor();
            desc14.putInteger(idFrom, m);
            desc14.putInteger(idT, m + 1);
            
            // 每次都重新讀取樣式，避免引用問題
            var rangeIdx = styleIndexMap[m] !== undefined ? styleIndexMap[m] : 0;
            var currentStyle = rangeList.getObjectValue(rangeIdx).getObjectValue(stringIDToTypeID('textStyle'));
            
            if (m >= targetStart && m < targetEnd) {
                // 變色的字符
                var desc21 = new ActionDescriptor();
                desc21.putDouble(charIDToTypeID("Rd  "), rgb.r);
                desc21.putDouble(charIDToTypeID("Grn "), rgb.g);
                desc21.putDouble(charIDToTypeID("Bl  "), rgb.b);
                currentStyle.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), desc21);
            }
            
            desc14.putObject(idTxtS, idTxtS, currentStyle);
            list2.putObject(charIDToTypeID("Txtt"), desc14);
        }
        
        desc7.putList(idTxtt, list2);
        desc6.putObject(idT, idTxLr, desc7);
        executeAction(idsetd, desc6, DialogModes.NO);
        
        app.preferences.rulerUnits = originalRulerUnits;
        
    } catch (e) {
        // 如果失敗則略過
    }
}

function findLayer(name, parent) {
    for (var i = 0; i < parent.layers.length; i++) {
        var layer = parent.layers[i];
        if (layer.name === name) return layer;
        if (layer.typename === 'LayerSet') {
            var found = findLayer(name, layer);
            if (found) return found;
        }
    }
    return null;
}

function applyLayerEffects(layer, strokeHex, shadowHex) {
    app.activeDocument.activeLayer = layer;
    var s2t = stringIDToTypeID;

    var strokeRgb = hexToRgb(strokeHex);
    var shadowRgb = hexToRgb(shadowHex);

    var descriptor = new ActionDescriptor();
    var reference = new ActionReference();
    reference.putProperty(s2t('property'), s2t('layerEffects'));
    reference.putEnumerated(s2t('layer'), s2t('ordinal'), s2t('targetEnum'));
    descriptor.putReference(s2t('null'), reference);
    
    var effectsDesc = new ActionDescriptor();
    
    // Stroke
    var strokeDesc = new ActionDescriptor();
    strokeDesc.putBoolean(s2t('enabled'), true);
    strokeDesc.putUnitDouble(s2t('size'), s2t('pixelsUnit'), 15);
    strokeDesc.putEnumerated(s2t('style'), s2t('frameStyle'), s2t('outsetFrame'));
    var strokeColorDesc = new ActionDescriptor();
    strokeColorDesc.putDouble(s2t('red'), strokeRgb.r);
    strokeColorDesc.putDouble(s2t('grain'), strokeRgb.g);
    strokeColorDesc.putDouble(s2t('blue'), strokeRgb.b);
    strokeDesc.putObject(s2t('color'), s2t('RGBColor'), strokeColorDesc);
    effectsDesc.putObject(s2t('frameFX'), s2t('frameFX'), strokeDesc);
    
    // Drop Shadow
    var shadowDesc = new ActionDescriptor();
    shadowDesc.putBoolean(s2t('enabled'), true);
    shadowDesc.putEnumerated(s2t('mode'), s2t('blendMode'), s2t('normal'));
    shadowDesc.putUnitDouble(s2t('opacity'), s2t('percentUnit'), 100);
    shadowDesc.putUnitDouble(s2t('localLightingAngle'), s2t('angleUnit'), 120);
    shadowDesc.putUnitDouble(s2t('distance'), s2t('pixelsUnit'), 10);
    shadowDesc.putUnitDouble(s2t('chokeMatte'), s2t('pixelsUnit'), 100);
    shadowDesc.putUnitDouble(s2t('blur'), s2t('pixelsUnit'), 18);
    var shadowColorDesc = new ActionDescriptor();
    shadowColorDesc.putDouble(s2t('red'), shadowRgb.r);
    shadowColorDesc.putDouble(s2t('grain'), shadowRgb.g);
    shadowColorDesc.putDouble(s2t('blue'), shadowRgb.b);
    shadowDesc.putObject(s2t('color'), s2t('RGBColor'), shadowColorDesc);
    effectsDesc.putObject(s2t('dropShadow'), s2t('dropShadow'), shadowDesc);
    
    descriptor.putObject(s2t('to'), s2t('layerEffects'), effectsDesc);
    executeAction(s2t('set'), descriptor, DialogModes.NO);
}

function removeQuotes(textLayer) {
    if (!textLayer) return;
    try {
        var content = textLayer.textItem.contents;
        var newContent = content.replace(/"/g, '');
        textLayer.textItem.contents = newContent;
    } catch (e) {
        // 如果失敗則略過
    }
}

function setLastCharBaselineShift(textLayer, shiftValue) {
    if (!textLayer) return;
    try {
        app.activeDocument.activeLayer = textLayer;
        
        var content = textLayer.textItem.contents;
        if (content.length === 0) return;
        
        var lastCharIndex = content.length - 1;
        
        // 讀取現有的 textKey
        var ref = new ActionReference();
        ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var layerDesc = executeActionGet(ref);
        var textKey = layerDesc.getObjectValue(stringIDToTypeID("textKey"));
        var theText = textKey.getString(stringIDToTypeID("textKey"));
        var rangeList = textKey.getList(stringIDToTypeID("textStyleRange"));
        
        // 構建新的 textStyleRange 列表
        var newRangeList = new ActionList();
        
        for (var i = 0; i < rangeList.count; i++) {
            var range = rangeList.getObjectValue(i);
            var from = range.getInteger(stringIDToTypeID("from"));
            var to = range.getInteger(stringIDToTypeID("to"));
            var oldStyle = range.getObjectValue(stringIDToTypeID("textStyle"));
            
            // 檢查最後一個字符是否在這個 range 中
            if (lastCharIndex >= from && lastCharIndex < to) {
                if (from < lastCharIndex) {
                    // 前面部分保持原樣
                    var frontRange = new ActionDescriptor();
                    frontRange.putInteger(stringIDToTypeID("from"), from);
                    frontRange.putInteger(stringIDToTypeID("to"), lastCharIndex);
                    frontRange.putObject(stringIDToTypeID("textStyle"), stringIDToTypeID("textStyle"), oldStyle);
                    newRangeList.putObject(stringIDToTypeID("textStyleRange"), frontRange);
                }
                
                // 最後一個字符：複製樣式並設定基線位移
                var lastRange = new ActionDescriptor();
                lastRange.putInteger(stringIDToTypeID("from"), lastCharIndex);
                lastRange.putInteger(stringIDToTypeID("to"), to);
                
                // 複製所有屬性
                var newStyle = new ActionDescriptor();
                for (var k = 0; k < oldStyle.count; k++) {
                    var key = oldStyle.getKey(k);
                    var keyStr = typeIDToStringID(key);
                    // 跳過 baselineShift 和 impliedBaselineShift，我們會重新設定
                    if (keyStr === "baselineShift" || keyStr === "impliedBaselineShift") continue;
                    var type = oldStyle.getType(key);
                    switch (type) {
                        case DescValueType.BOOLEANTYPE: newStyle.putBoolean(key, oldStyle.getBoolean(key)); break;
                        case DescValueType.INTEGERTYPE: newStyle.putInteger(key, oldStyle.getInteger(key)); break;
                        case DescValueType.DOUBLETYPE: newStyle.putDouble(key, oldStyle.getDouble(key)); break;
                        case DescValueType.STRINGTYPE: newStyle.putString(key, oldStyle.getString(key)); break;
                        case DescValueType.OBJECTTYPE: newStyle.putObject(key, oldStyle.getObjectType(key), oldStyle.getObjectValue(key)); break;
                        case DescValueType.ENUMERATEDTYPE: newStyle.putEnumerated(key, oldStyle.getEnumerationType(key), oldStyle.getEnumerationValue(key)); break;
                        case DescValueType.UNITDOUBLE: newStyle.putUnitDouble(key, oldStyle.getUnitDoubleType(key), oldStyle.getUnitDoubleValue(key)); break;
                        case DescValueType.LISTTYPE: newStyle.putList(key, oldStyle.getList(key)); break;
                    }
                }
                
                // 設定基線位移 (使用 pixelsUnit)
                newStyle.putUnitDouble(stringIDToTypeID("baselineShift"), stringIDToTypeID("pixelsUnit"), shiftValue);
                newStyle.putUnitDouble(stringIDToTypeID("impliedBaselineShift"), stringIDToTypeID("pixelsUnit"), shiftValue);
                
                lastRange.putObject(stringIDToTypeID("textStyle"), stringIDToTypeID("textStyle"), newStyle);
                newRangeList.putObject(stringIDToTypeID("textStyleRange"), lastRange);
            } else {
                // 其他 range 保持原樣
                newRangeList.putObject(stringIDToTypeID("textStyleRange"), range);
            }
        }
        
        // 構建新的 textKey，複製所有其他屬性
        var newTextKey = new ActionDescriptor();
        for (var j = 0; j < textKey.count; j++) {
            var tk = textKey.getKey(j);
            if (tk == stringIDToTypeID("textStyleRange")) {
                newTextKey.putList(stringIDToTypeID("textStyleRange"), newRangeList);
            } else {
                var ttype = textKey.getType(tk);
                switch (ttype) {
                    case DescValueType.BOOLEANTYPE: newTextKey.putBoolean(tk, textKey.getBoolean(tk)); break;
                    case DescValueType.INTEGERTYPE: newTextKey.putInteger(tk, textKey.getInteger(tk)); break;
                    case DescValueType.DOUBLETYPE: newTextKey.putDouble(tk, textKey.getDouble(tk)); break;
                    case DescValueType.STRINGTYPE: newTextKey.putString(tk, textKey.getString(tk)); break;
                    case DescValueType.OBJECTTYPE: newTextKey.putObject(tk, textKey.getObjectType(tk), textKey.getObjectValue(tk)); break;
                    case DescValueType.ENUMERATEDTYPE: newTextKey.putEnumerated(tk, textKey.getEnumerationType(tk), textKey.getEnumerationValue(tk)); break;
                    case DescValueType.UNITDOUBLE: newTextKey.putUnitDouble(tk, textKey.getUnitDoubleType(tk), textKey.getUnitDoubleValue(tk)); break;
                    case DescValueType.LISTTYPE: newTextKey.putList(tk, textKey.getList(tk)); break;
                }
            }
        }
        
        // 套用修改
        var desc = new ActionDescriptor();
        var ref2 = new ActionReference();
        ref2.putEnumerated(stringIDToTypeID("textLayer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        desc.putReference(stringIDToTypeID("null"), ref2);
        desc.putObject(stringIDToTypeID("to"), stringIDToTypeID("textLayer"), newTextKey);
        executeAction(stringIDToTypeID("set"), desc, DialogModes.NO);
        
    } catch (e) {
        alert("基線位移設定失敗: " + e);
    }
}

// 讓 Rectangle 2 變色方式與精華版_顏色可變/Rectangle 1 一致
function setShapeColor(layer, hexColor) {
    if (!layer) return;
    var rgb = hexToRgb(hexColor);
    try {
        app.activeDocument.activeLayer = layer;
        var s2t = stringIDToTypeID;
        var descriptor = new ActionDescriptor();
        var reference = new ActionReference();
        reference.putEnumerated(s2t("contentLayer"), s2t("ordinal"), s2t("targetEnum"));
        descriptor.putReference(s2t("null"), reference);
        var fillDesc = new ActionDescriptor();
        var colorDesc = new ActionDescriptor();
        colorDesc.putDouble(s2t("red"), rgb.r);
        colorDesc.putDouble(s2t("grain"), rgb.g);
        colorDesc.putDouble(s2t("blue"), rgb.b);
        fillDesc.putObject(s2t("color"), s2t("RGBColor"), colorDesc);
        descriptor.putObject(s2t("to"), s2t("solidColorLayer"), fillDesc);
        executeAction(s2t("set"), descriptor, DialogModes.NO);
    } catch (e) {
        // fallback: 若失敗則略過
    }
}
"""

    # Use a standard string template to avoid f-string brace syntax errors
    jsx_main_template = """
// --- Main Script ---
try {
    // 0. 確保Photoshop視窗最大化以避免顯示空間問題
    try {
        app.bringToFront();
        // 嘗試最大化應用程式視窗
        var bounds = app.activeDocument ? app.activeDocument.window.bounds : null;
    } catch (e) {
        // 忽略視窗操作錯誤
    }
    
    // 1. 開啟PSD檔案
    var psdFile = new File("PSD_PATH_PLACEHOLDER");
    if (!psdFile.exists) throw "找不到PSD檔案: " + psdFile.fsName;
    
    // 使用最簡單的方式開啟，讓Photoshop自己處理
    app.open(psdFile);
    var doc = app.activeDocument;
    
    // 2. 確保視窗適當顯示
    try {
        if (doc.window) {
            // 設置檢視為適合視窗
            doc.window.zoom = ZoomType.FITINWINDOW;
        }
    } catch (e) {
        // 忽略檢視設置錯誤
    }

    // 3. Rename
    var newName = "NEW_FILENAME_PLACEHOLDER";
    doc.name = newName;

    // 4. Update Titles
    var titleGroup = findLayer("標", doc);
    if (titleGroup) {
        var titleLayer1 = titleGroup.layers[1];
        var titleLayer2 = titleGroup.layers[0];

        titleLayer1.textItem.contents = "TITLE1_PLACEHOLDER";
        titleLayer2.textItem.contents = "TITLE2_PLACEHOLDER";
        
        // Remove quotes first to avoid overwriting color formatting
        removeQuotes(titleLayer1);
        removeQuotes(titleLayer2);

        setTextColor(titleLayer1, "LINE1_BASE_COLOR");
        setTextColor(titleLayer2, "LINE2_BASE_COLOR");
        
        applyLayerEffects(titleLayer1, "LINE1_STROKE_COLOR", "LINE1_SHADOW_COLOR");
        applyLayerEffects(titleLayer2, "LINE2_STROKE_COLOR", "LINE2_SHADOW_COLOR");
        
        // Special Quoted Text Coloring - 第一行大標 (now without quotes)
        colorQuotedText(titleLayer1, "SPECIAL_TEXT_1", "LINE1_SPECIAL1_COLOR");
        colorQuotedText(titleLayer1, "SPECIAL_TEXT_2", "LINE1_SPECIAL2_COLOR");
        
        // Special Quoted Text Coloring - 第二行大標 (now without quotes)
        colorQuotedText(titleLayer2, "SPECIAL_TEXT_3", "LINE2_SPECIAL1_COLOR");
        colorQuotedText(titleLayer2, "SPECIAL_TEXT_4", "LINE2_SPECIAL2_COLOR");
        
        titleLayer1.resize(1380 / (titleLayer1.bounds[2] - titleLayer1.bounds[0]) * 100, 100, AnchorPosition.MIDDLELEFT);
        titleLayer2.resize(1560 / (titleLayer2.bounds[2] - titleLayer2.bounds[0]) * 100, 100, AnchorPosition.MIDDLELEFT);
        
        // 設定第一行大標最後一個字的基線位移 (-17.88px) - 在 resize 之後執行
        setLastCharBaselineShift(titleLayer1, -17.88);
    } else {
        alert("警告: 找不到 '標' 圖層群組");
    }

    // 4.1 Update anchor name in 精華版_顏色可變
    var colorGroup = findLayer("精華版_顏色可變", doc);
    if (colorGroup && colorGroup.layers.length > 0) {
        var anchorTextLayer = colorGroup.layers[0];
        if (anchorTextLayer.kind && anchorTextLayer.kind.toString() === 'LayerKind.TEXT') {
            anchorTextLayer.textItem.contents = "ANCHOR_NAME_PLACEHOLDER";
        }
    }

    // 5. Update Anchor
    var anchorGroup = findLayer("主播", doc);
    if (anchorGroup) {
        var anchorMap = {'林嘉源': '林嘉源', '鄭亦真': '鄭亦真 ', '張雅婷': '張雅婷', '洪淑芬': '洪淑芬', '麥玉潔': '麥玉潔', '何橞瑢': '何橞瑢' };
        var targetName = anchorMap["ANCHOR_NAME_PLACEHOLDER"] || "ANCHOR_NAME_PLACEHOLDER";
        
        // Delete other anchor layers and keep only the target one
        var layersToDelete = [];
        for (var i = 0; i < anchorGroup.layers.length; i++) {
            var layer = anchorGroup.layers[i];
            var layerName = layer.name.replace(/\\s+$/, '');
            if (layerName !== targetName) {
                layersToDelete.push(layer);
            } else {
                layer.visible = true; // Make sure the target layer is visible
            }
        }
        
        // Delete the collected layers
        for (var j = 0; j < layersToDelete.length; j++) {
            layersToDelete[j].remove();
        }
    } else {
        alert("警告: 找不到 '主播' 圖層群組");
    }

    // 6. Update "Rectangle 2" color (精確尋找效果群組下的 ShapeLayer)
    var effectGroup = findLayer("效果", doc);
    if (effectGroup && effectGroup.layers) {
        var rect2 = null;
        for (var i = 0; i < effectGroup.layers.length; i++) {
            var lyr = effectGroup.layers[i];
            if (lyr.name === "Rectangle 2" && lyr.kind && lyr.kind.toString() === 'LayerKind.SOLIDFILL') {
                rect2 = lyr;
                break;
            }
        }
        if (rect2) {
            setShapeColor(rect2, "EXPLOSION_COLOR");
        } else {
            alert("警告: '效果' 群組下找不到 ShapeLayer 'Rectangle 2'");
        }
    } else {
        alert("警告: 找不到 '效果' 群組");
    }

    // 7. Save File and Close
    var saveFile = new File("OUTPUT_PATH_PLACEHOLDER/" + newName);
    if (!saveFile.parent.exists) saveFile.parent.create();
    var psdOptions = new PhotoshopSaveOptions();
    psdOptions.embedColorProfile = true;
    psdOptions.alphaChannels = true;
    psdOptions.layers = true;
    doc.saveAs(saveFile, psdOptions);
    doc.close(SaveOptions.DONOTSAVECHANGES);

    alert("處理完成！\\n檔案已保存為: " + newName + "\\n位置: " + saveFile.fsName);

} catch (e) {
    alert("腳本執行時發生錯誤: " + e + "\\n\\n請確保Photoshop有足夠記憶體，並且PSD檔案沒有損壞。");
}
"""

    # Perform replacements manually
    replacements = {
        "PSD_PATH_PLACEHOLDER": psd_path_escaped,
        "NEW_FILENAME_PLACEHOLDER": new_filename,
        "TITLE1_PLACEHOLDER": title1,
        "TITLE2_PLACEHOLDER": title2,
        "LINE1_BASE_COLOR": line1_colors['base'],
        "LINE2_BASE_COLOR": line2_colors['base'],
        "LINE1_STROKE_COLOR": line1_colors['stroke'],
        "LINE1_SHADOW_COLOR": line1_colors['shadow'],
        "LINE2_STROKE_COLOR": line2_colors['stroke'],
        "LINE2_SHADOW_COLOR": line2_colors['shadow'],
        "SPECIAL_TEXT_1": special_text_1,
        "LINE1_SPECIAL1_COLOR": line1_colors['special1'],
        "SPECIAL_TEXT_2": special_text_2,
        "LINE1_SPECIAL2_COLOR": line1_colors['special2'],
        "SPECIAL_TEXT_3": special_text_3,
        "LINE2_SPECIAL1_COLOR": line2_colors['special1'],
        "SPECIAL_TEXT_4": special_text_4,
        "LINE2_SPECIAL2_COLOR": line2_colors['special2'],
        "ANCHOR_NAME_PLACEHOLDER": anchor_name,
        "EXPLOSION_COLOR": line1_colors['explosion'],
        "OUTPUT_PATH_PLACEHOLDER": output_path_escaped
    }
    
    jsx_main = jsx_main_template
    for key, value in replacements.items():
        jsx_main = jsx_main.replace(key, str(value))

    return (jsx_header + jsx_helpers + jsx_main).strip()


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description="為晚報YT縮圖生成Photoshop腳本。 সন")
    parser.add_argument("--file", required=True, help="包含縮圖資訊的文字檔路徑。")
    parser.add_argument("--color-id", help="要使用的顏色方案編號 (例如 B01, R02)。如果省略，將隨機選取一個。 সন")
    parser.add_argument("--psd", default="晚報YT縮圖.psd", help="Photoshop範本檔案的路徑。 সন")
    parser.add_argument("--csv", default="晚報變色.csv", help="顏色配置CSV檔案的路徑。 সন")
    parser.add_argument("--output-dir", default=".", help="生成的JSX和PSD檔案的輸出目錄。 সন")

    args = parser.parse_args()

    print("="*60)
    print("生成Photoshop腳本")
    print("="*60)

    print(f"\n正在載入顏色配置: {args.csv}")
    color_schemes = load_color_schemes(args.csv)
    if not color_schemes:
        return

    color_id = args.color_id
    if color_id:
        color_id = color_id.upper()
        print(f"✓ 使用指定的顏色ID: {color_id}")
    else:
        available_ids = list(color_schemes.keys())
        if not available_ids:
            print("錯誤: 顏色設定檔中沒有可用的顏色ID。 সন")
            return
        color_id = random.choice(available_ids)
        print(f"✓ 未指定顏色ID，隨機選取: {color_id}")

    selected_scheme = color_schemes.get(color_id)
    if not selected_scheme:
        print(f"錯誤: 在 {args.csv} 中找不到顏色ID '{color_id}'。 সন")
        print(f"可用ID: {', '.join(color_schemes.keys())}")
        return
    
    print(f"\n正在解析文字檔: {args.file}")
    if not os.path.exists(args.file):
        print(f"錯誤: 找不到輸入的文字檔: {args.file}")
        return
    result = parse_file(args.file)
    if not result:
        print("解析失敗")
        return
    
    print("\n解析結果:")
    print(f"  Slag: {result['slag']}")
    print(f"  主播名字: {result['anchor']}")
    print(f"  第一行大標: {result['title_line1']}")
    print(f"  第二行大標: {result['title_line2']}")
    
    if not os.path.exists(args.psd):
        print(f"\n錯誤: 找不到PSD檔案: {args.psd}")
        return
    
    selected_scheme['id'] = color_id
    
    script_content = generate_jsx_script(result, selected_scheme, args.psd, args.output_dir)
    
    mmdd = get_today_mmdd()
    script_file = os.path.join(args.output_dir, f"modify_thumbnail_{mmdd}_{color_id.upper()}.jsx")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n✓ Photoshop腳本已生成: {script_file}")
    print(f"\n使用方式:")
    print(f"  1. 確保 '{args.psd}' 檔案存在於指定位置。 সন")
    print(f"  2. 雙擊 {os.path.abspath(script_file)} 直接執行。 সন")
    print(f"  或")
    print(f"  2. 在Photoshop中選擇 檔案 > 腳本 > 瀏覽... সন")
    print(f"  3. 選擇 {os.path.abspath(script_file)}")
    print(f"\n腳本會自動:")
    print(f"  - 啟動/切換到Photoshop")
    print(f"  - 開啟PSD檔案")
    print(f"  - 執行所有修改")
    print(f"  - 另存新檔並關閉原檔案")
    print(f"\n注意: 如果遇到顯示空間不足的錯誤，請確保螢幕解析度足夠或將Photoshop視窗最大化。")


if __name__ == "__main__":
    main()
