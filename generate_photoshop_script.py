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
import json
from datetime import datetime
from parse_thumbnail_txt import (
    DEFAULT_IMAGE_ROOT,
    LAYOUT_IMAGE_TITLE,
    get_today_mmdd,
    prepare_file_data,
)

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

def load_top_right_colors(csv_path):
    """從CSV檔案載入右上變色方案"""
    colors = {}
    try:
        with open(csv_path, mode='r', encoding='big5') as infile:
            reader = csv.reader(infile)
            next(reader)  # 跳過標頭
            
            for row in reader:
                if len(row) > 1 and row[0].strip():
                    group_id = row[0].strip().upper()  # A, B, C, D
                    color_values = [val.strip().lstrip('#') for val in row[1:4]]
                    colors[group_id] = color_values
    except FileNotFoundError:
        print(f"警告: 找不到右上變色檔: {csv_path}")
        return None
    except Exception as e:
        print(f"讀取右上變色CSV時發生錯誤: {e}")
        return None
    
    return colors

def load_effect_handling(csv_path):
    """從CSV檔案載入效果字處理對照表"""
    handling_map = {}
    if not os.path.exists(csv_path):
        return handling_map
        
    try:
        # 嘗試使用 cp950 (Big5) 讀取，因為通常是 Excel 產生的
        with open(csv_path, 'r', encoding='cp950') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            if not rows:
                return handling_map

            # 假設是「直向（Column-based）」格式：
            # 第一列 (Row 0) 是各欄位的「處理手法描述/名稱」
            # 第二列 (Row 1) 以後是該手法對應的「關鍵字」列表
            
            # 先確認有多少欄 (以第一列為準)
            header_row = rows[0]
            num_cols = len(header_row)
            
            for col_idx in range(num_cols):
                method = header_row[col_idx].strip()
                if not method: continue
                
                # 遍歷此欄位底下所有的列
                for row_idx in range(1, len(rows)):
                    row = rows[row_idx]
                    # 確保該列有足夠的欄位
                    if col_idx < len(row):
                        keyword = row[col_idx].strip()
                        if keyword:
                            handling_map[keyword] = method
                            
    except Exception as e:
        print(f"Warning: Loading effect handling CSV failed: {e}")
        
    return handling_map

def select_top_right_color(color_id, top_right_colors):
    """根據配色系統ID選擇右上變色
    
    規則:
    - O開頭 → 排除A組
    - P開頭 → 排除B組
    - B開頭 → 排除C組
    - G開頭 → 排除D組
    
    返回選定的顏色十六進制值
    """
    if not top_right_colors:
        return None
    
    # 根據色系ID首字母判斷排除的組別
    exclude_map = {
        'O': 'A',
        'P': 'B',
        'B': 'C',
        'G': 'D'
    }
    
    first_letter = color_id[0] if color_id else ''
    excluded_group = exclude_map.get(first_letter)
    
    # 可用的組別
    available_groups = [g for g in top_right_colors.keys() if g != excluded_group]
    
    if not available_groups:
        print(f"警告: 配色系統 {color_id} 沒有可用的右上變色組別")
        return None
    
    # 隨機選一個可用組別
    selected_group = random.choice(available_groups)
    # 從該組中隨機選一個顏色
    selected_color = random.choice(top_right_colors[selected_group])
    
    print(f"✓ 右上變色: {selected_group}組 - {selected_color}")
    return selected_color


def _js_string(value):
    """輸出可安全放入 JSX 的 Unicode 字串。"""
    return json.dumps(str(value), ensure_ascii=False)


def build_labeled_layout_logic(result_data):
    """建立標圖版專用的左邊字、圖片與尺寸限制 JSX。"""
    left_text = re.sub(r'["“”]', '', result_data.get('left_text', '')).strip()
    original_image_path = result_data.get('image_path', '')
    raw_image_paths = result_data.get('image_paths') or ([original_image_path] if original_image_path else [])
    image_paths = [str(path).replace('\\', '/') for path in raw_image_paths if path]
    image_layer_names = [os.path.splitext(os.path.basename(path))[0] for path in raw_image_paths if path]
    number_matches = list(re.finditer(r'\d+(?:\.\d+)?', left_text))
    all_single_digits = bool(number_matches) and all(
        re.fullmatch(r'\d', match.group(0)) for match in number_matches
    )

    number_specs = []
    if all_single_digits:
        main_left_text = left_text.translate(str.maketrans('0123456789', '０１２３４５６７８９'))
    elif number_matches:
        pieces = []
        cursor = 0
        output_length = 0
        for match in number_matches:
            before = left_text[cursor:match.start()]
            pieces.append(before)
            output_length += len(before)
            gap_start = output_length
            pieces.append('  ')
            output_length += 2
            token = match.group(0)
            number_specs.append({
                'text': token,
                'gap_start': gap_start,
                'prefix': ''.join(pieces)[:-2],
                'kerning': 90 if token.isdigit() and len(token) == 2 else 110,
            })
            cursor = match.end()
        pieces.append(left_text[cursor:])
        main_left_text = ''.join(pieces)
    else:
        main_left_text = left_text

    kerning_calls = []
    number_create_blocks = []
    number_finalize_blocks = []
    for index, spec in enumerate(number_specs):
        # 兩個替代空格分別位於 gap_start 與 gap_start + 1，kerning 設在兩者之間。
        kerning_calls.append(
            f"    setLabeledKerning(verticalTextLayer, {spec['kerning']}, "
            f"{spec['gap_start'] + 1}, {spec['gap_start'] + 2});"
        )
        prefix_expression = _js_string(spec['prefix'])
        number_expression = _js_string(spec['text'])
        number_create_blocks.append(f"""
    var prefixProbe{index} = verticalTextLayer.duplicate();
    prefixProbe{index}.textItem.contents = {prefix_expression};
    var prefixBounds{index} = labeledLayerBounds(prefixProbe{index});
    prefixProbe{index}.remove();

    var numberLayer{index} = verticalTextLayer.duplicate();
    numberLayer{index}.name = "直標數字" + ({index} === 0 ? "" : "_{index + 1}");
    numberLayer{index}.textItem.contents = {number_expression};
    numberLayer{index}.textItem.direction = Direction.HORIZONTAL;
    var numberBounds{index} = labeledLayerBoundsNoEffects(numberLayer{index});
    if (numberBounds{index}.width > 0) {{
        numberLayer{index}.resize(250 / numberBounds{index}.width * 100, 100, AnchorPosition.MIDDLECENTER);
    }}
    numberBounds{index} = labeledLayerBounds(numberLayer{index});
    var numberTargetCenterX{index} = (mainVerticalBounds.left + mainVerticalBounds.right) / 2;
    var numberTargetTop{index} = prefixBounds{index}.bottom - 38;
    numberLayer{index}.translate(
        numberTargetCenterX{index} - ((numberBounds{index}.left + numberBounds{index}.right) / 2),
        numberTargetTop{index} - numberBounds{index}.top
    );
""")
        number_finalize_blocks.append(f"""
    var finalNumberBounds{index} = labeledLayerBoundsNoEffects(numberLayer{index});
    if (finalNumberBounds{index}.width > 0 && Math.abs(finalNumberBounds{index}.width - 250) > 0.1) {{
        numberLayer{index}.resize(250 / finalNumberBounds{index}.width * 100, 100, AnchorPosition.MIDDLECENTER);
    }}
    mainVerticalBounds = labeledLayerBounds(verticalTextLayer);
    finalNumberBounds{index} = labeledLayerBounds(numberLayer{index});
    numberLayer{index}.translate(
        ((mainVerticalBounds.left + mainVerticalBounds.right) / 2) -
        ((finalNumberBounds{index}.left + finalNumberBounds{index}.right) / 2),
        0
    );
""")

    return f"""
    // --- 標圖版專用流程 ---
    function labeledPx(value) {{
        return value.as("px");
    }}

    function labeledLayerBounds(layer) {{
        var b = layer.bounds;
        return {{
            left: labeledPx(b[0]), top: labeledPx(b[1]),
            right: labeledPx(b[2]), bottom: labeledPx(b[3]),
            width: labeledPx(b[2]) - labeledPx(b[0]),
            height: labeledPx(b[3]) - labeledPx(b[1])
        }};
    }}

    function labeledLayerBoundsNoEffects(layer) {{
        var b = layer.boundsNoEffects;
        return {{
            left: labeledPx(b[0]), top: labeledPx(b[1]),
            right: labeledPx(b[2]), bottom: labeledPx(b[3]),
            width: labeledPx(b[2]) - labeledPx(b[0]),
            height: labeledPx(b[3]) - labeledPx(b[1])
        }};
    }}

    function fitLabeledTitleMaxWidth(layer, maxWidth) {{
        if (!layer) return;
        var b = labeledLayerBounds(layer);
        if (b.width > maxWidth) {{
            layer.resize(maxWidth / b.width * 100, 100, AnchorPosition.MIDDLELEFT);
        }}
    }}

    function setLabeledKerning(layer, value, fromIndex, toIndex) {{
        doc.activeLayer = layer;
        var layerRef = new ActionReference();
        layerRef.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var layerDesc = executeActionGet(layerRef);
        var textDesc = layerDesc.getObjectValue(stringIDToTypeID("textKey"));
        var kerningRangeID = stringIDToTypeID("kerningRange");
        var kerningList = new ActionList();
        if (textDesc.hasKey(kerningRangeID)) {{
            var oldList = textDesc.getList(kerningRangeID);
            for (var kr = 0; kr < oldList.count; kr++) {{
                kerningList.putObject(kerningRangeID, oldList.getObjectValue(kr));
            }}
        }}
        var kernDesc = new ActionDescriptor();
        kernDesc.putInteger(stringIDToTypeID("from"), fromIndex);
        kernDesc.putInteger(stringIDToTypeID("to"), toIndex);
        kernDesc.putInteger(stringIDToTypeID("kerning"), value);
        kerningList.putObject(kerningRangeID, kernDesc);
        textDesc.putList(kerningRangeID, kerningList);
        var setDesc = new ActionDescriptor();
        var targetRef = new ActionReference();
        targetRef.putEnumerated(charIDToTypeID("TxLr"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        setDesc.putReference(charIDToTypeID("null"), targetRef);
        setDesc.putObject(charIDToTypeID("T   "), charIDToTypeID("TxLr"), textDesc);
        executeAction(charIDToTypeID("setd"), setDesc, DialogModes.NO);
    }}

    // 大標沿用舊流程後，再確保標圖版最終上限。
    if (typeof titleLayer1 !== "undefined") fitLabeledTitleMaxWidth(titleLayer1, 1400);
    if (typeof titleLayer2 !== "undefined") fitLabeledTitleMaxWidth(titleLayer2, 1280);

    // 左邊字完全忽略引號變色；一位數全部轉全形，其餘數字另建橫向圖層。
    var verticalGroup = findLayer("直標", doc);
    if (!verticalGroup || !verticalGroup.artLayers) throw new Error("找不到群組『直標』");
    var verticalTextLayer = verticalGroup.artLayers.getByName("直標直標");
    verticalTextLayer.textItem.contents = {_js_string(main_left_text)};
{chr(10).join(kerning_calls)}
    var mainVerticalBounds = labeledLayerBounds(verticalTextLayer);
{''.join(number_create_blocks)}
    var verticalGroupBounds = labeledLayerBounds(verticalGroup);
    if (verticalGroupBounds.height > 1000) {{
        var verticalScale = 1000 / verticalGroupBounds.height * 100;
        verticalGroup.resize(verticalScale, verticalScale, AnchorPosition.TOPLEFT);
    }}
{''.join(number_finalize_blocks)}

    // 圖片以嵌入式智慧型物件匯入；單圖沿用柔邊遮罩，雙圖用左右拼接與左圖漸層遮罩。
    var labeledImagePaths = {json.dumps(image_paths, ensure_ascii=False)};
    var labeledImageNames = {json.dumps(image_layer_names, ensure_ascii=False)};
    var imageGroup = findLayer("圖片", doc);
    if (!imageGroup || !imageGroup.artLayers) throw new Error("找不到群組『圖片』");

    function placeLabeledSmartObject(pathText, layerName) {{
        var sourceFile = new File(pathText);
        if (!sourceFile.exists) throw new Error("找不到標圖版圖片：" + sourceFile.fsName);
        var placeDescriptor = new ActionDescriptor();
        placeDescriptor.putPath(charIDToTypeID("null"), sourceFile);
        placeDescriptor.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
        executeAction(charIDToTypeID("Plc "), placeDescriptor, DialogModes.NO);
        var layer = doc.activeLayer;
        layer.name = layerName;
        layer.move(imageGroup, ElementPlacement.INSIDE);
        return layer;
    }}

    function fitLayerToWidth(layer, targetWidth) {{
        var bounds = labeledLayerBounds(layer);
        if (bounds.width > 0) {{
            layer.resize(targetWidth / bounds.width * 100, targetWidth / bounds.width * 100, AnchorPosition.MIDDLECENTER);
        }}
    }}

    function centerLayerAt(layer, centerX, centerY) {{
        var bounds = labeledLayerBounds(layer);
        layer.translate(
            centerX - ((bounds.left + bounds.right) / 2),
            centerY - ((bounds.top + bounds.bottom) / 2)
        );
    }}

    function applyContractFeatherMask(layer) {{
        doc.activeLayer = layer;
        var selectDescriptor = new ActionDescriptor();
        var selectionReference = new ActionReference();
        selectionReference.putProperty(charIDToTypeID("Chnl"), charIDToTypeID("fsel"));
        selectDescriptor.putReference(charIDToTypeID("null"), selectionReference);
        var transparencyReference = new ActionReference();
        transparencyReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Trsp"));
        selectDescriptor.putReference(charIDToTypeID("T   "), transparencyReference);
        executeAction(charIDToTypeID("setd"), selectDescriptor, DialogModes.NO);
        doc.selection.contract(20);

        var maskDescriptor = new ActionDescriptor();
        maskDescriptor.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
        var maskReference = new ActionReference();
        maskReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
        maskDescriptor.putReference(charIDToTypeID("At  "), maskReference);
        maskDescriptor.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), charIDToTypeID("RvlS"));
        executeAction(charIDToTypeID("Mk  "), maskDescriptor, DialogModes.NO);

        var featherDescriptor = new ActionDescriptor();
        var featherLayerReference = new ActionReference();
        featherLayerReference.putEnumerated(stringIDToTypeID("layer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        featherDescriptor.putReference(charIDToTypeID("null"), featherLayerReference);
        var featherLayerDescriptor = new ActionDescriptor();
        featherLayerDescriptor.putUnitDouble(stringIDToTypeID("userMaskFeather"), charIDToTypeID("#Pxl"), 20);
        featherDescriptor.putObject(charIDToTypeID("T   "), stringIDToTypeID("layer"), featherLayerDescriptor);
        executeAction(charIDToTypeID("setd"), featherDescriptor, DialogModes.NO);
        doc.selection.deselect();
    }}

    function addRevealAllMask(layer) {{
        doc.activeLayer = layer;
        var maskDescriptor = new ActionDescriptor();
        maskDescriptor.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
        var maskReference = new ActionReference();
        maskReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
        maskDescriptor.putReference(charIDToTypeID("At  "), maskReference);
        maskDescriptor.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), charIDToTypeID("RvlA"));
        executeAction(charIDToTypeID("Mk  "), maskDescriptor, DialogModes.NO);
    }}

    function selectLayerMask() {{
        var maskReference = new ActionReference();
        maskReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
        var maskDescriptor = new ActionDescriptor();
        maskDescriptor.putReference(charIDToTypeID("null"), maskReference);
        maskDescriptor.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), maskDescriptor, DialogModes.NO);
    }}

    function gradientColorStop(red, green, blue, location) {{
        var stop = new ActionDescriptor();
        var color = new ActionDescriptor();
        color.putDouble(charIDToTypeID("Rd  "), red);
        color.putDouble(charIDToTypeID("Grn "), green);
        color.putDouble(charIDToTypeID("Bl  "), blue);
        stop.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), color);
        stop.putEnumerated(charIDToTypeID("Type"), charIDToTypeID("Clry"), charIDToTypeID("UsrS"));
        stop.putInteger(charIDToTypeID("Lctn"), location);
        stop.putInteger(charIDToTypeID("Mdpn"), 50);
        return stop;
    }}

    function opacityStop(opacity, location) {{
        var stop = new ActionDescriptor();
        stop.putUnitDouble(charIDToTypeID("Opct"), charIDToTypeID("#Prc"), opacity);
        stop.putInteger(charIDToTypeID("Lctn"), location);
        stop.putInteger(charIDToTypeID("Mdpn"), 50);
        return stop;
    }}

    function applyLeftFadeGradientMask(layer) {{
        addRevealAllMask(layer);
        selectLayerMask();
        var bounds = labeledLayerBounds(layer);
        var midY = (bounds.top + bounds.bottom) / 2;

        var gradientDescriptor = new ActionDescriptor();
        var fromPoint = new ActionDescriptor();
        fromPoint.putUnitDouble(charIDToTypeID("Hrzn"), charIDToTypeID("#Pxl"), bounds.left);
        fromPoint.putUnitDouble(charIDToTypeID("Vrtc"), charIDToTypeID("#Pxl"), midY);
        gradientDescriptor.putObject(charIDToTypeID("From"), charIDToTypeID("Pnt "), fromPoint);

        var toPoint = new ActionDescriptor();
        toPoint.putUnitDouble(charIDToTypeID("Hrzn"), charIDToTypeID("#Pxl"), bounds.right);
        toPoint.putUnitDouble(charIDToTypeID("Vrtc"), charIDToTypeID("#Pxl"), midY);
        gradientDescriptor.putObject(charIDToTypeID("T   "), charIDToTypeID("Pnt "), toPoint);
        gradientDescriptor.putEnumerated(charIDToTypeID("Type"), charIDToTypeID("GrdT"), charIDToTypeID("Lnr "));
        gradientDescriptor.putBoolean(charIDToTypeID("Dthr"), true);

        var gradient = new ActionDescriptor();
        gradient.putString(charIDToTypeID("Nm  "), "Left 80 White To Right 20 Black");
        gradient.putEnumerated(charIDToTypeID("GrdF"), charIDToTypeID("GrdF"), charIDToTypeID("CstS"));
        gradient.putDouble(charIDToTypeID("Intr"), 4096);

        var colorStops = new ActionList();
        colorStops.putObject(charIDToTypeID("Clrt"), gradientColorStop(255, 255, 255, 0));
        colorStops.putObject(charIDToTypeID("Clrt"), gradientColorStop(255, 255, 255, 3277));
        colorStops.putObject(charIDToTypeID("Clrt"), gradientColorStop(0, 0, 0, 4096));
        gradient.putList(charIDToTypeID("Clrs"), colorStops);

        var opacityStops = new ActionList();
        opacityStops.putObject(charIDToTypeID("TrnS"), opacityStop(100, 0));
        opacityStops.putObject(charIDToTypeID("TrnS"), opacityStop(100, 4096));
        gradient.putList(charIDToTypeID("Trns"), opacityStops);
        gradientDescriptor.putObject(charIDToTypeID("Grad"), charIDToTypeID("Grdn"), gradient);
        executeAction(charIDToTypeID("Grdn"), gradientDescriptor, DialogModes.NO);
    }}

    if (labeledImagePaths.length === 0) {{
        throw new Error("標圖版沒有配對圖片");
    }} else if (labeledImagePaths.length === 1) {{
        var imageLayer = placeLabeledSmartObject(labeledImagePaths[0], labeledImageNames[0]);
        fitLayerToWidth(imageLayer, 1400);
        centerLayerAt(imageLayer, 960, 260);
        applyContractFeatherMask(imageLayer);
    }} else {{
        var leftImageLayer = placeLabeledSmartObject(labeledImagePaths[0], labeledImageNames[0]);
        fitLayerToWidth(leftImageLayer, 1400);
        centerLayerAt(leftImageLayer, 960, 260);
        applyLeftFadeGradientMask(leftImageLayer);

        var rightImageLayer = placeLabeledSmartObject(labeledImagePaths[1], labeledImageNames[1]);
        fitLayerToWidth(rightImageLayer, 1400);
        centerLayerAt(rightImageLayer, 960, 260);
        var leftImageBounds = labeledLayerBounds(leftImageLayer);
        var rightImageBounds = labeledLayerBounds(rightImageLayer);
        rightImageLayer.translate(
            (leftImageBounds.right - 215) - rightImageBounds.left,
            ((leftImageBounds.top + leftImageBounds.bottom) / 2) -
            ((rightImageBounds.top + rightImageBounds.bottom) / 2)
        );
        rightImageLayer.move(leftImageLayer, ElementPlacement.PLACEAFTER);
    }}
    // --- 標圖版專用流程結束 ---
"""

def generate_jsx_script(result_data, color_scheme, psd_path, output_path, top_right_color=None, creator="", effect_map=None, source_date=None):
    """生成Photoshop JSX腳本"""
    
    mmdd = source_date or get_today_mmdd()
    
    def sanitize_filename(filename):
        # 替換 Windows 非法字元 (保留 %, 因為我們會透過 JSX 處理它的路徑編碼問題)
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '_', filename)
        filename = filename.strip('. ')
        filename = re.sub(r'__+', '_', filename)
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    # 強制檢測製作者：如果 creator 為空，嘗試從現有 PSD 檔案中尋找
    import glob
    if (not creator or not creator.strip()) and os.path.exists(output_path):
        # 構造搜尋樣式: MMDD_Slag_*.psd
        # 先計算不含製作者的基本部分
        base_slug = f"{mmdd}_{result_data['slag']}"
        # 為了安全起見，我們只 sanitize Slag 部分
        sanitized_slag = sanitize_filename(result_data['slag'])
        # 這裡有個微妙之處：sanitize_filename 可能會把 "_" 也做為連接符
        # 我們假設 sanitize_filename(f"{mmdd}_{slag}_xxx.psd") 
        # 等同於 f"{mmdd}_{sanitize_filename(slag)}_xxx.psd" 
        # 但 sanitize_filename 會把特殊字元變 "_"
        
        # 讓我們使用更寬鬆的glob: output_path/mmdd_slag_*.psd
        # 考慮到 slag 可能含有特殊字符，我們先用 sanitize 過的版本來搜尋
        search_pattern = os.path.join(output_path, f"{mmdd}_{sanitized_slag}_*.psd")
        
        # Windows 路徑可能需要轉義 glob
        found_files = glob.glob(search_pattern)
        
        # 過濾掉不符合格式的檔案 (例如 0130_Title.psd 沒有後綴)
        candidates = []
        base_prefix = f"{mmdd}_{sanitized_slag}_"
        for f_path in found_files:
            f_name = os.path.basename(f_path)
            # 檢查是否確實以 prefix 開頭並且以 .psd 結尾
            if f_name.startswith(base_prefix) and f_name.lower().endswith('.psd'):
                # 提取中間的部分
                suffix_part = f_name[len(base_prefix):-4] # 去掉 .psd
                if suffix_part:
                    candidates.append((f_path, suffix_part))
        
        if candidates:
            # 如果有多個，取修改時間最新的
            candidates.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
            detected_creator = candidates[0][1]
            print(f"✓ 自動偵測到現有製作者: {detected_creator}")
            creator = detected_creator

    # 添加製作者到檔名
    creator_suffix = ""
    has_creator = "false"
    if creator and creator.strip() != "":
        creator_suffix = f"_{creator.strip()}"
        has_creator = "true"
    
    new_filename = sanitize_filename(f"{mmdd}_{result_data['slag']}{creator_suffix}.psd")
    
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
    
    # 檢查第二行大標的引號是否成對
    quote_count_2 = title2_raw.count('"')
    if quote_count_2 % 2 != 0:
        print(f"\n⚠️  警告: 第二行大標發現未閉合的引號，請檢查確認")
        print(f"   標題內容: {title2_raw}")
        print(f"   引號數量: {quote_count_2} (應為偶數)")
    
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
    
    # 網絡路徑處理：\\IP\share -> //IP/share (ExtendScript UNC 路徑)
    if output_path.startswith('\\\\'):
        # \\10.227.58.117\新聞psd\0129\縮圖 -> //10.227.58.117/新聞psd/0129/縮圖
        output_path_escaped = '//' + output_path[2:].replace('\\', '/')
    else:
        output_path_escaped = output_path.replace('\\', '/')
    
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

function processRotateEffect(textLayer, textToChange, newSize, angle) {
    if (!textLayer || !textToChange) return;
    
    try {
        app.activeDocument.activeLayer = textLayer;
        var content = textLayer.textItem.contents;
        var startIndex = content.indexOf(textToChange);
        if (startIndex === -1) return;
        
        // 1. Duplicate Layer
        var rotLayer = textLayer.duplicate();
        rotLayer.name = textLayer.name + "_Rot_" + textToChange;
        
        // 2. Update Original Layer first (Replace char with Space safely)
        // Using ActionDescriptor to avoid resetting style ranges (colors, effects)
        var ref = new ActionReference();
        ref.putEnumerated(stringIDToTypeID("layer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        var layerDesc = executeActionGet(ref);
        var textKeyDesc = layerDesc.getObjectValue(stringIDToTypeID('textKey'));
        var currentText = textKeyDesc.getString(stringIDToTypeID('textKey'));
        
        // Ensure we preserve the length so style ranges don't break
        var replacementSpaces = "";
        for(var k=0; k<textToChange.length; k++) {
            replacementSpaces += " ";
        }
        
        // Construct new text
        var newText = currentText.substring(0, startIndex) + replacementSpaces + currentText.substring(startIndex + textToChange.length);
        
        // Update the string in the TextKey descriptor
        textKeyDesc.putString(stringIDToTypeID('textKey'), newText);
        
        // Write back the updated TextKey
        var setDesc = new ActionDescriptor();
        var setRef = new ActionReference();
        setRef.putEnumerated(stringIDToTypeID("textLayer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        setDesc.putReference(stringIDToTypeID("null"), setRef);
        setDesc.putObject(stringIDToTypeID("to"), stringIDToTypeID("textLayer"), textKeyDesc);
        
        executeAction(stringIDToTypeID("set"), setDesc, DialogModes.NO);
        
        // Get original layer bounds AFTER modification (this is the text without the target char)
        var origBounds = textLayer.bounds;
        var origLeft = origBounds[0];  // Left edge X position
        var origCenterY = (origBounds[1] + origBounds[3]) / 2;
        
        // Calculate the X position based on character widths
        var xOffset = 0;
        var chineseCharWidth = 163.18; // 中文字寬度
        var symbolWidth = 120.90;      // 符號寬度
        
        for (var i = 0; i < startIndex; i++) {
            var ch = content.charAt(i);
            // 判斷是否為中文字符 (CJK Unified Ideographs)
            if (ch.match(/[\u4e00-\u9fff]/)) {
                xOffset += chineseCharWidth;
            } else {
                // 其他字符視為符號
                xOffset += symbolWidth;
            }
        }
        
        // Target X position is original left + calculated offset
        var targetX = origLeft + xOffset;
        
        // 3. Setup Rotated Layer (Keep only target char)
        app.activeDocument.activeLayer = rotLayer;
        rotLayer.textItem.contents = textToChange;
        
        // Set Size
        rotLayer.textItem.size = new UnitValue(newSize, "px");
        
        // Rotate
        rotLayer.rotate(angle, AnchorPosition.MIDDLECENTER);
        
        // 4. Move to position: Place at the calculated position based on character index
        var rotBoundsAfter = rotLayer.bounds;
        var rotLeftAfter = rotBoundsAfter[0];
        var rotCenterYAfter = (rotBoundsAfter[1] + rotBoundsAfter[3]) / 2;
        
        // Target position: calculated X based on character widths
        var targetY = origCenterY;
        
        // Calculate how much to move
        var deltaX = targetX - rotLeftAfter;
        var deltaY = targetY - rotCenterYAfter;
        
        // Translate the layer
        rotLayer.translate(deltaX, deltaY);
        
    } catch (e) {
        alert("Rotate Effect Error: " + e);
    }
}

function changeFontSizePart(textLayer, textToChange, newSize) {
    if (!textLayer || !textToChange || textToChange.length === 0 || !newSize) return;
    
    try {
        app.activeDocument.activeLayer = textLayer;
        var content = textLayer.textItem.contents;
        var startIndex = content.indexOf(textToChange);
        if (startIndex === -1) return;
        var endIndex = startIndex + textToChange.length;

        // 1. Get current text styles to find Color and Font
        var ref = new ActionReference();
        ref.putEnumerated(stringIDToTypeID("layer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        var layerDesc = executeActionGet(ref);
        var textKey = layerDesc.getObjectValue(stringIDToTypeID('textKey'));
        var rangeList = textKey.getList(stringIDToTypeID('textStyleRange'));
        
        var currentColorDesc = null;
        var currentFontName = null;
        var useFauxItalic = false;
        var useFauxBold = false;
        
        // Find the range that covers the start of our text
        for (var i = 0; i < rangeList.count; i++) {
            var rangeObj = rangeList.getObjectValue(i);
            var from = rangeObj.getInteger(stringIDToTypeID("from"));
            var to = rangeObj.getInteger(stringIDToTypeID("to"));
            
            if (startIndex >= from && startIndex < to) {
                var styleObj = rangeObj.getObjectValue(stringIDToTypeID("textStyle"));
                if (styleObj.hasKey(stringIDToTypeID("color"))) {
                    currentColorDesc = styleObj.getObjectValue(stringIDToTypeID("color"));
                }
                if (styleObj.hasKey(stringIDToTypeID("fontPostScriptName"))) {
                    currentFontName = styleObj.getString(stringIDToTypeID("fontPostScriptName"));
                }
                if (styleObj.hasKey(stringIDToTypeID("syntheticItalic"))) {
                    useFauxItalic = styleObj.getBoolean(stringIDToTypeID("syntheticItalic"));
                }
                if (styleObj.hasKey(stringIDToTypeID("syntheticBold"))) {
                    useFauxBold = styleObj.getBoolean(stringIDToTypeID("syntheticBold"));
                }
                break;
            }
        }

        // 2. Construct the Update Action
        var idsetd = stringIDToTypeID("set");
        var desc = new ActionDescriptor();
        var refTgt = new ActionReference();
        refTgt.putEnumerated(stringIDToTypeID("textLayer"), stringIDToTypeID("ordinal"), stringIDToTypeID("targetEnum"));
        desc.putReference(stringIDToTypeID("null"), refTgt);
        
        var textDesc = new ActionDescriptor();
        var textRangeList = new ActionList();
        
        var rangeDesc = new ActionDescriptor();
        rangeDesc.putInteger(stringIDToTypeID("from"), startIndex);
        rangeDesc.putInteger(stringIDToTypeID("to"), endIndex);
        
        var styleDesc = new ActionDescriptor();
        
        // Use pointsUnit matching the user's working sample script
        styleDesc.putUnitDouble(stringIDToTypeID("size"), stringIDToTypeID("pointsUnit"), newSize);
        
        // Restore Color
        if (currentColorDesc) {
            styleDesc.putObject(stringIDToTypeID("color"), stringIDToTypeID("RGBColor"), currentColorDesc);
        }
        
        // Restore Font (Important anchor for style updates)
        if (currentFontName) {
            styleDesc.putString(stringIDToTypeID("fontPostScriptName"), currentFontName);
        }
        
        // Restore Faux Styles
        if (useFauxItalic) {
            styleDesc.putBoolean(stringIDToTypeID("syntheticItalic"), true);
        }
        if (useFauxBold) {
            styleDesc.putBoolean(stringIDToTypeID("syntheticBold"), true);
        }
        
        rangeDesc.putObject(stringIDToTypeID("textStyle"), stringIDToTypeID("textStyle"), styleDesc);
        textRangeList.putObject(stringIDToTypeID("textStyleRange"), rangeDesc);
        
        textDesc.putList(stringIDToTypeID("textStyleRange"), textRangeList);
        desc.putObject(stringIDToTypeID("to"), stringIDToTypeID("textLayer"), textDesc);
        
        executeAction(idsetd, desc, DialogModes.NO);
        
    } catch (e) {
        alert("Error in changeFontSizePart: " + e);
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
    // 禁用所有對話框
    app.displayDialogs = DialogModes.NO;
    
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
        
        // Resize title layers first
        TITLE_RESIZE_LOGIC_PLACEHOLDER
        
        // EFFECT_WORDS_LOGIC_PLACEHOLDER
        
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
        var anchorMap = {'林嘉源': '林嘉源', '鄭亦真': '鄭亦真', '張雅婷': '張雅婷', '洪淑芬': '洪淑芬', '麥玉潔': '麥玉潔', '何橞瑢': '何橞瑢' };
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

    // 6.1 Update "Rectangle 1" color in 精華版_顏色可變
    var colorGroup2 = findLayer("精華版_顏色可變", doc);
    if (colorGroup2 && colorGroup2.layers.length > 3) {
        var rect1 = colorGroup2.layers[3];  // 第4個圖層（索引3）
        if (rect1 && rect1.kind && rect1.kind.toString() === 'LayerKind.SOLIDFILL') {
            setShapeColor(rect1, "TOP_RIGHT_COLOR");
        }
    }

    LAYOUT_SPECIFIC_LOGIC_PLACEHOLDER

    // 7. Save File and Close
    // 使用 Folder 對象來處理 UNC 路徑，避免中文字符編碼問題
    var outputFolder = new Folder("OUTPUT_PATH_PLACEHOLDER");
    var fallbackFolder = null;
    
    if (!outputFolder.exists) {
        // 嘗試創建輸出文件夾
        var parentFolder = new Folder(outputFolder.parent);
        if (!parentFolder.exists) {
            try {
                parentFolder.create();
            } catch(e) {
                // 父文件夾創建失敗，記錄錯誤
                var logFile = new File(Folder.desktop + "/error_create_parent.txt");
                logFile.open("w");
                logFile.write("無法創建父文件夾: " + outputFolder.parent + "\\n錯誤: " + e.toString());
                logFile.close();
            }
        }
        try {
            outputFolder.create();
        } catch(e) {
            // 輸出文件夾創建失敗，使用本地桌面作為備用
            fallbackFolder = Folder.desktop;
            var logFile = new File(Folder.desktop + "/error_create_output.txt");
            logFile.open("w");
            logFile.write("無法創建輸出文件夾: " + outputFolder.toString() + "\\n錯誤: " + e.toString() + "\\n使用備用文件夾: " + fallbackFolder);
            logFile.close();
        }
    }
    
    var actualFolder = outputFolder.exists ? outputFolder : fallbackFolder;
    if (!actualFolder) {
        actualFolder = Folder.desktop;
    }
    
    // 處理檔名中的 % 符號 (替換為 %25 以避免被解析為轉義字符)
    var safeNameForPath = newName.replace(/%/g, "%25");
    var saveFile = new File(actualFolder.toString() + "/" + safeNameForPath);
    
    var psdOptions = new PhotoshopSaveOptions();
    psdOptions.embedColorProfile = true;
    psdOptions.alphaChannels = true;
    psdOptions.layers = true;
    
    // 禁用所有對話框 (強制覆蓋)
    app.displayDialogs = DialogModes.NO;
    
    try {
        doc.saveAs(saveFile, psdOptions, true); // true = asCopy (but here we want to overwrite)
        // 實際上 EXTENSION SCRIPT 的 saveAs 若檔案存在會直接覆蓋，但在某些版本可能會跳出詢問
        // 正確的寫法是不要指定 asCopy，但要確保 displayDialogs = NO
    } catch(e) {
        // 如果第一次存檔失敗，嘗試先刪除舊檔案
        try {
            if (saveFile.exists) {
                saveFile.remove();
                doc.saveAs(saveFile, psdOptions, true);
            } else {
                throw e;
            }
        } catch(e2) {
            alert("保存 PSD 檔案失敗: " + saveFile + " 錯誤: " + e2.toString());
        }
    }
    
    // 8. Save for Web as JPG (去除製作者後綴)
    // 創建 JPG 子資料夾
    var jpgFolder = new Folder(actualFolder.toString() + "/JPG");
    if (!jpgFolder.exists) {
        jpgFolder.create();
    }

    var jpgName = newName.replace(/\\.psd$/i, '.jpg');
    
    // 只有在有製作者後綴時，才嘗試移除最後一段 (避免變成 0130.jpg)
    // HAS_CREATOR_PLACEHOLDER
    var hasCreator = HAS_CREATOR_PLACEHOLDER;
    
    if (hasCreator) {
        // 移除製作者名稱後綴 (e.g., "_桁" from filename)
        jpgName = jpgName.replace(/_[^_]+\\.jpg$/, '.jpg');
    }
    
    // 同樣需要處理 jpg 檔名中的 %
    var safeJpgNameForPath = jpgName.replace(/%/g, "%25");
    var jpgFile = new File(jpgFolder.toString() + "/" + safeJpgNameForPath);
    
    var sfwOptions = new ExportOptionsSaveForWeb();
    sfwOptions.format = SaveDocumentType.JPEG;
    sfwOptions.includeProfile = false;
    sfwOptions.interlaced = false;
    sfwOptions.optimized = true;
    sfwOptions.quality = 60;
    
    // 清理記憶體並執行垃圾回收
    try {
        app.purge();
    } catch(e) {}
    
    try {
        doc.exportDocument(jpgFile, ExportType.SAVEFORWEB, sfwOptions);
    } catch(e) {
        alert("導出 JPG 檔案失敗: " + jpgFile + " 錯誤: " + e.toString());
    }
    doc.close(SaveOptions.DONOTSAVECHANGES);

} catch (e) {
    // 寫入錯誤標記文件到本地桌面目錄（而不是網絡路徑）
    var desktopFolder = Folder.desktop;
    var scriptFolder = new Folder(desktopFolder.toString() + "/晚報YT腳本");
    if (!scriptFolder.exists) {
        scriptFolder.create();
    }
    
    var errorFileName = "error_" + new Date().getTime() + ".txt";
    var errorFile = new File(scriptFolder.toString() + "/" + errorFileName);
    var errorContent = "腳本執行失敗: " + e.toString() + "\\n\\n";
    errorContent += "請確保 PSD 檔案有效，Photoshop 有足夠記憶體。\\n";
    errorContent += "輸出路徑: OUTPUT_PATH_PLACEHOLDER\\n";
    errorContent += "新檔名: NEW_FILENAME_PLACEHOLDER";
    
    try {
        errorFile.open("w");
        errorFile.write(errorContent);
        errorFile.close();
    } catch(fileErr) {
        // 即使本地寫入失敗也不要彈出對話框
    }
    
    // 嘗試關閉文檔
    try {
        if (doc != null && doc.isDirty) {
            doc.close(SaveOptions.DONOTSAVECHANGES);
        }
    } catch(closeErr) {}
}
"""

    # Generate Effect Words Logic
    effect_words_logic = ""
    if effect_map and result_data.get('effect_words'):
        for ef_word in result_data['effect_words']:
             parts = ef_word.strip().split()
             if len(parts) >= 2:
                  target_text = parts[0]
                  keyword = parts[1]
                  
                  if keyword in effect_map:
                       action = effect_map[keyword]
                       
                       # Check for Rotate action
                       if "旋轉" in action:
                           # Parse logic: "把字改成300 px, 旋轉"
                           # Extract size
                           size_match = re.search(r'(\d+)', action)
                           size_val = size_match.group(1) if size_match else "300"
                           
                           # Extract angle? Default 15 if not specified? 
                           # If action is just "把字改成300 px, 旋轉", use 15.
                           angle_val = 15
                           angle_match = re.search(r'旋轉.*?(\d+)', action)
                           if angle_match:
                               angle_val = angle_match.group(1)
                           
                           t_esc = escape_js_string(target_text)
                           effect_words_logic += f'    // Effect: {keyword} -> {action} (Rotate)\n'
                           effect_words_logic += f'    processRotateEffect(titleLayer1, "{t_esc}", {size_val}, {angle_val});\n'
                           effect_words_logic += f'    processRotateEffect(titleLayer2, "{t_esc}", {size_val}, {angle_val});\n'
                           
                       else:
                           match = re.search(r'(\d+)', action)
                           if match:
                               size_val = match.group(1)
                               t_esc = escape_js_string(target_text)
                               effect_words_logic += f'    // Effect: {keyword} -> {action}\n'
                               effect_words_logic += f'    changeFontSizePart(titleLayer1, "{t_esc}", {size_val});\n'
                               effect_words_logic += f'    changeFontSizePart(titleLayer2, "{t_esc}", {size_val});\n'

    is_labeled_layout = result_data.get('layout_type') == LAYOUT_IMAGE_TITLE
    if is_labeled_layout:
        # 沿用原本大標1的1380px；大標2在標圖版改為1280px。
        title_resize_logic = (
            'titleLayer1.resize(1380 / (titleLayer1.bounds[2] - titleLayer1.bounds[0]) * 100, '
            '100, AnchorPosition.MIDDLELEFT);\n'
            '        titleLayer2.resize(1280 / (titleLayer2.bounds[2] - titleLayer2.bounds[0]) * 100, '
            '100, AnchorPosition.MIDDLELEFT);'
        )
        layout_specific_logic = build_labeled_layout_logic(result_data)
    else:
        title_resize_logic = (
            'titleLayer1.resize(1380 / (titleLayer1.bounds[2] - titleLayer1.bounds[0]) * 100, '
            '100, AnchorPosition.MIDDLELEFT);\n'
            '        titleLayer2.resize(1560 / (titleLayer2.bounds[2] - titleLayer2.bounds[0]) * 100, '
            '100, AnchorPosition.MIDDLELEFT);'
        )
        layout_specific_logic = ''

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
        "EFFECT_WORDS_LOGIC_PLACEHOLDER": effect_words_logic,
        "TITLE_RESIZE_LOGIC_PLACEHOLDER": title_resize_logic,
        "LAYOUT_SPECIFIC_LOGIC_PLACEHOLDER": layout_specific_logic,
        "LINE2_SPECIAL1_COLOR": line2_colors['special1'],
        "SPECIAL_TEXT_4": special_text_4,
        "LINE2_SPECIAL2_COLOR": line2_colors['special2'],
        "ANCHOR_NAME_PLACEHOLDER": anchor_name,
        "EXPLOSION_COLOR": line1_colors['explosion'],
        "TOP_RIGHT_COLOR": top_right_color if top_right_color else "ffffff",
        "OUTPUT_PATH_PLACEHOLDER": output_path_escaped,
        "HAS_CREATOR_PLACEHOLDER": has_creator
    }
    
    jsx_main = jsx_main_template
    for key, value in replacements.items():
        jsx_main = jsx_main.replace(key, str(value))

    return (jsx_header + jsx_helpers + jsx_main).strip()


def run_generation_logic(
    file_path,
    color_id,
    psd_path,
    csv_path,
    jsx_output_dir,
    psd_output_dir,
    creator,
    source_date=None,
    labeled_psd_path=None,
    image_root=DEFAULT_IMAGE_ROOT,
):
    """執生成邏輯，方便外部調用"""
    
    # 確保路徑是絕對路徑
    file_path = os.path.abspath(file_path)
    psd_path = os.path.abspath(psd_path)
    if labeled_psd_path:
        labeled_psd_path = os.path.abspath(labeled_psd_path)
    csv_path = os.path.abspath(csv_path)
    jsx_output_dir = os.path.abspath(jsx_output_dir)
    # psd_output_dir 可以是網絡路徑，不一定要轉為本地絕對路徑
    
    print("="*60)
    print("生成Photoshop腳本")
    print("="*60)

    print(f"\n正在載入顏色配置: {csv_path}")
    color_schemes = load_color_schemes(csv_path)
    if not color_schemes:
        return 1

    if color_id:
        color_id = color_id.upper()
        print(f"✓ 使用指定的顏色ID: {color_id}")
    else:
        available_ids = list(color_schemes.keys())
        if not available_ids:
            print("錯誤: 顏色設定檔中沒有可用的顏色ID。")
            return 1
        color_id = random.choice(available_ids)
        print(f"✓ 未指定顏色ID，隨機選取: {color_id}")

    selected_scheme = color_schemes.get(color_id)
    if not selected_scheme:
        print(f"錯誤: 在 {csv_path} 中找不到顏色ID '{color_id}'。")
        print(f"可用ID: {', '.join(color_schemes.keys())}")
        return 1
    
    effective_date = source_date or get_today_mmdd()

    print(f"\n正在解析文字檔: {file_path}")
    if not os.path.exists(file_path):
        print(f"錯誤: 找不到輸入的文字檔: {file_path}")
        return 1
    result = prepare_file_data(file_path, effective_date, image_root)
    if not result:
        print("解析失敗")
        return 1

    if result.get('validation_errors'):
        print("\n⚠ 此檔案略過：")
        for validation_error in result['validation_errors']:
            print(f"  - {validation_error}")
        return 2

    if result.get('layout_type') == LAYOUT_IMAGE_TITLE:
        if not labeled_psd_path:
            labeled_psd_path = os.path.join(os.path.dirname(psd_path), '晚報YT縮圖(標圖版).psd')
        psd_path = labeled_psd_path
    
    print("\n解析結果:")
    print(f"  Slag: {result['slag']}")
    print(f"  版型: {result['layout_type']}")
    print(f"  主播名字: {result['anchor']}")
    print(f"  第一行大標: {result['title_line1']}")
    print(f"  第二行大標: {result['title_line2']}")
    if result.get('layout_type') == LAYOUT_IMAGE_TITLE:
        print(f"  左邊字: {result['left_text']}")
        print(f"  圖片指示: {result['image_instruction']}")
        print(f"  配對圖片: {result['image_path']}")
    
    if result.get('effect_words'):
        print(f"  效果字: {', '.join(result['effect_words'])}")
    else:
        print(f"  效果字: (無)")
    
    # 驗證標題內容
    title1_stripped = result['title_line1'].strip() if result['title_line1'] else ""
    title2_stripped = result['title_line2'].strip() if result['title_line2'] else ""
    
    if not title1_stripped or not title2_stripped:
        error_msg = f"標題內容不完整\n"
        error_msg += f"- 第一行大標: '{result['title_line1']}' (空值)\n"
        error_msg += f"- 第二行大標: '{result['title_line2']}' (空值)\n"
        error_msg += f"請檢查文字檔內容是否正確"
        
        print(f"\n❌ 錯誤: {error_msg}")
        
        # 寫入錯誤日誌到 JSX 輸出目錄
        try:
            if not os.path.exists(jsx_output_dir):
                os.makedirs(jsx_output_dir, exist_ok=True)
                
            error_log_file = os.path.join(jsx_output_dir, f"error_{os.path.basename(file_path)}.log")
            with open(error_log_file, 'w', encoding='utf-8') as f:
                f.write(error_msg)
            print(f"⚠ 錯誤日誌已保存: {error_log_file}")
        except Exception as e:
            print(f"⚠ 無法保存錯誤日誌: {e}")
        
        return 1
    
    if not os.path.exists(psd_path):
        print(f"\n錯誤: 找不到PSD檔案: {psd_path}")
        return 1
    
    selected_scheme['id'] = color_id
    
    # 載入右上變色方案
    print(f"\n正在載入右上變色配置...")
    top_right_csv = os.path.join(os.path.dirname(csv_path), '右上變色.csv')
    # 如果找不到，嘗試在同目錄找
    if not os.path.exists(top_right_csv):
         top_right_csv = '右上變色.csv'
         
    top_right_colors = load_top_right_colors(top_right_csv)
    top_right_selected = None
    if top_right_colors:
        top_right_selected = select_top_right_color(color_id, top_right_colors)
    
    # 載入效果字處理方案
    print(f"\n正在載入效果字配置...")
    effect_csv = os.path.join(os.path.dirname(csv_path), '效果字處理.csv')
    if not os.path.exists(effect_csv):
         effect_csv = '效果字處理.csv'
    
    if os.path.exists(effect_csv):
        effect_map = load_effect_handling(effect_csv)
        print(f"✓ 已載入效果字: {len(effect_map)} 筆規則")
    else:
        effect_map = {}
        print(f"⚠ 找不到效果字配置檔: {effect_csv} (略過)")

    # 使用 PSD 輸出目錄作為 JSX 中 Photoshop 的輸出位置
    script_content = generate_jsx_script(
        result,
        selected_scheme,
        psd_path,
        psd_output_dir,
        top_right_selected,
        creator,
        effect_map,
        effective_date,
    )
    
    mmdd = effective_date
    
    import hashlib
    slug_hash = hashlib.md5(result['slag'].encode()).hexdigest()[:6].upper()
    
    if not os.path.exists(jsx_output_dir):
        os.makedirs(jsx_output_dir, exist_ok=True)

    script_file = os.path.join(jsx_output_dir, f"modify_thumbnail_{mmdd}_{color_id.upper()}_{slug_hash}.jsx")
    
    try:
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
    except Exception as e:
        print(f"無法寫入 JSX 文件: {e}")
        return 1
    
    print(f"\n✓ Photoshop腳本已生成: {script_file}")
    
    return 0


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description="為晚報YT縮圖生成Photoshop腳本。")
    parser.add_argument("--file", required=True, help="包含縮圖資訊的文字檔路徑。")
    parser.add_argument("--color-id", help="要使用的顏色方案編號 (例如 B01, R02)。如果省略，將隨機選取一個。")
    parser.add_argument("--psd", default="晚報YT縮圖.psd", help="Photoshop範本檔案的路徑。")
    parser.add_argument("--labeled-psd", default="晚報YT縮圖(標圖版).psd", help="標圖版 Photoshop 範本檔案。")
    parser.add_argument("--date", help="來源日期（MMDD）；未指定時使用今天。")
    parser.add_argument("--image-root", default=DEFAULT_IMAGE_ROOT, help="標圖版圖片根目錄。")
    parser.add_argument("--csv", default="晚報變色.csv", help="顏色配置CSV檔案的路徑。")
    parser.add_argument("--jsx-output-dir", default=".", help="生成的JSX檔案輸出目錄。")
    parser.add_argument("--psd-output-dir", default=".", help="生成的PSD檔案輸出目錄。")
    parser.add_argument("--creator", default="", help="製作者名稱，將附加在PSD檔案名後。")

    args = parser.parse_args()

    sys.exit(run_generation_logic(
        args.file,
        args.color_id,
        args.psd,
        args.csv,
        args.jsx_output_dir,
        args.psd_output_dir,
        args.creator,
        args.date,
        args.labeled_psd,
        args.image_root,
    ))


if __name__ == "__main__":
    main()
