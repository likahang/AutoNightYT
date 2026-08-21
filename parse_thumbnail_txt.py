#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晚報YT縮圖文字檔解析程式
從網路路徑讀取文字檔並提取所需資訊
"""

import os
import sys
import re
from difflib import SequenceMatcher
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
# 這些括號內容是版面／效果控制指示，不是圖片名稱。
# 圖片指示不要求含有「圖」字，因此只排除已知的控制格式。
NON_IMAGE_INSTRUCTION_KEYWORDS = ["超大字", *EXCLUDED_EFFECT_KEYWORDS]

LAYOUT_BIG_TITLE = "大標版"
LAYOUT_IMAGE_TITLE = "標圖版"
DEFAULT_IMAGE_ROOT = r"\\10.227.63.105\public\__CG-IN"
DEFAULT_TEXT_ROOT = r"\\10.227.58.117\新聞txt"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
LEFT_MARKER_PATTERN = r"左邊(?:直)?字"


def _is_parenthesized_line(value):
    """整行必須只包含一組半形括號，才視為圖片指示。"""
    return bool(re.fullmatch(r"\([^()]+\)", value.strip()))


def _is_non_image_instruction(value):
    """判斷括號內容是否為效果字或版面控制指示。"""
    text = str(value or "").strip()
    if not text:
        return True

    if any(keyword in text for keyword in NON_IMAGE_INSTRUCTION_KEYWORDS):
        return True

    # 「定 鄭亦真 不要笑」是定位／控制指示；「定格 美驅逐艦」仍可作為圖片指示。
    if re.match(r"^定\s+", text):
        return True

    return False


def _extract_explicit_image_instruction(value):
    """從含「定圖」的指示行取出可能的圖片名稱。"""
    text = str(value or "").strip()
    match = re.search(r"定圖\s*[:：]?\s*(.+)$", text)
    return [part for part in re.split(r"\s+", match.group(1).strip()) if part] if match else []


def _parse_left_marker(line):
    """解析左邊字標記，支援文字在標記外或括號內兩種格式。"""
    stripped = line.strip()

    embedded_match = re.fullmatch(
        rf"\(\s*({LEFT_MARKER_PATTERN})\s*[:：]\s*(.*?)\s*\)",
        stripped,
    )
    if embedded_match:
        return {
            "label": embedded_match.group(1),
            "left_text": embedded_match.group(2).strip(),
            "embedded": True,
        }

    marker_match = re.search(rf"\(\s*({LEFT_MARKER_PATTERN})\s*\)", line)
    if marker_match:
        left_text = re.sub(rf"\(\s*{LEFT_MARKER_PATTERN}\s*\)", "", line).strip()
        return {
            "label": marker_match.group(1),
            "left_text": left_text,
            "embedded": False,
        }

    return None


def _is_left_marker_effect(value):
    """避免左邊字標記被誤加入效果字。"""
    return bool(re.fullmatch(rf"\s*{LEFT_MARKER_PATTERN}(?:\s*[:：].*)?\s*", value.strip()))


def _find_nearby_image_instruction(lines, marker_index, prefer_after=False):
    """找左邊字附近的圖片指示；舊格式在上一行，新括號格式常在下一行。"""
    directions = (1, -1) if prefer_after else (-1, 1)

    for direction in directions:
        index = marker_index + direction
        while 0 <= index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                index += direction
                continue

            # 有些文字檔會在圖片指示括號前加上 +，例如 +(定圖 用今天 妤史努比)。
            image_candidate = re.sub(r"^\+\s*", "", candidate)
            if _is_parenthesized_line(image_candidate) and not _parse_left_marker(image_candidate):
                content = image_candidate[1:-1].strip()
                explicit_images = _extract_explicit_image_instruction(content)
                if explicit_images:
                    return " ".join(explicit_images), explicit_images
                if not _is_non_image_instruction(content):
                    return content, []
            break

    return "", []


def _normalize_image_text(value):
    """建立圖片指示與檔名配對用的寬鬆文字鍵。"""
    value = str(value)
    suffix = Path(value).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        value = str(Path(value).with_suffix(""))
    value = re.sub(r"^\s*\d+\s*[.．、_\-]*\s*", "", value)
    value = value.lower()
    value = value.replace("縮圖", "").replace("圖片", "").replace("照片", "").replace("圖", "")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)


def get_image_directory_candidates(mmdd, image_root=DEFAULT_IMAGE_ROOT):
    """回傳當日／月份歸檔目錄，兼容圖片資料夾大小寫寫法。"""
    mmdd = str(mmdd or "").strip()
    if not re.fullmatch(r"\d{4}", mmdd):
        return []

    month_folder = f"{mmdd[:2]}月"
    candidates = []
    # 不同日期／NAS 可能使用不同的圖片資料夾名稱。
    for archive_parts in ((mmdd,), (month_folder, mmdd)):
        for folder_name in ("晚報yt縮圖", "YT縮圖"):
            candidates.append(os.path.join(image_root, *archive_parts, "1800", folder_name))
    return candidates


def _image_instruction_parts(instruction):
    """圖片指示可用 + / ＋ 拆成多張圖，順序即左右順序。"""
    parts = [part.strip() for part in re.split(r"\s*[+＋]\s*", instruction or "") if part.strip()]
    return parts or [str(instruction or "").strip()]


def _collect_image_candidates(result, mmdd, image_root=DEFAULT_IMAGE_ROOT):
    directories = get_image_directory_candidates(mmdd, image_root)
    if not directories:
        return [], [], f"日期格式錯誤：{mmdd!r}（應為 MMDD）"

    issue_match = re.search(r"晚報YT縮圖\s*(\d+)", result.get("slag", ""))
    issue_number = int(issue_match.group(1)) if issue_match else None
    candidates = []
    existing_directories = []

    for directory_index, directory in enumerate(directories):
        if not os.path.isdir(directory):
            continue
        existing_directories.append(directory)
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue

        for entry in entries:
            if not entry.is_file() or Path(entry.name).suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            stem = Path(entry.name).stem
            prefix_match = re.match(r"^\s*(\d+)(?=\D|$)", stem)
            prefix_number = int(prefix_match.group(1)) if prefix_match else None
            number_match = issue_number is not None and prefix_number == issue_number
            candidate_key = _normalize_image_text(stem)
            # 同分時優先當日根目錄，再依檔名排序，確保結果固定。
            candidates.append({
                "number_match": number_match,
                "directory_rank": -directory_index,
                "name": entry.name.lower(),
                "path": entry.path,
                "key": candidate_key,
            })

    return candidates, directories, None


def _score_image_candidate(candidate, instruction):
    instruction_key = _normalize_image_text(instruction)
    candidate_key = candidate["key"]
    similarity = SequenceMatcher(None, instruction_key, candidate_key).ratio() if instruction_key and candidate_key else 0
    contains_match = bool(
        instruction_key
        and candidate_key
        and (instruction_key in candidate_key or candidate_key in instruction_key)
    )

    score = 0
    if candidate["number_match"]:
        score += 1000
    if instruction_key and candidate_key == instruction_key:
        score += 300
    elif contains_match:
        score += 180
    score += int(similarity * 100)
    return score, contains_match or similarity >= 0.6


def _pick_image_candidate(candidates, instruction, used_paths=None, strict_text=False):
    used_paths = set(used_paths or [])
    scored = []
    for candidate in candidates:
        if os.path.abspath(candidate["path"]) in used_paths:
            continue
        score, text_match = _score_image_candidate(candidate, instruction)
        if strict_text and not text_match:
            continue
        scored.append((
            score,
            candidate["number_match"],
            candidate["directory_rank"],
            candidate["name"],
            candidate["path"],
        ))

    if not scored:
        return None

    numbered_candidates = [item for item in scored if item[1]]
    pool = numbered_candidates or [item for item in scored if item[0] >= 60]
    if not pool:
        return None

    best = sorted(pool, key=lambda item: (-item[0], -item[2], item[3]))[0]
    return os.path.abspath(best[4])


def resolve_image_paths(result, mmdd, image_root=DEFAULT_IMAGE_ROOT):
    """依圖片指示配對圖片；多圖缺項時警告並保留其餘已找到圖片。"""
    if not result or result.get("layout_type") != LAYOUT_IMAGE_TITLE:
        return [], None

    instruction = result.get("image_instruction", "").strip()
    if not instruction:
        return [], "缺少圖片指示"

    candidates, directories, directory_error = _collect_image_candidates(result, mmdd, image_root)
    if directory_error:
        return [], directory_error

    if not candidates:
        searched = "、".join(directories)
        return [], f"找不到圖片資料夾或圖片檔；已搜尋：{searched}"

    alternatives = [
        str(part).strip()
        for part in result.get("image_instruction_candidates", [])
        if str(part).strip()
    ]
    if alternatives:
        # 「定圖」後以空格分隔的是候選名稱；找到任一張即可繼續。
        for alternative in alternatives:
            image_path = _pick_image_candidate(candidates, alternative, strict_text=False)
            if image_path:
                return [image_path], None
        searched = "、".join(directories)
        return [], f"圖片指示「{'、'.join(alternatives)}」找不到可配對圖片；已搜尋：{searched}"

    parts = _image_instruction_parts(instruction)
    image_paths = []
    used_paths = set()
    used_instruction_keys = set()
    missing_parts = []
    strict_text = len(parts) > 1

    for part in parts:
        part_key = _normalize_image_text(part)
        # 相同圖片指示可重複匯入，例如「破裂線」在多人中間出現兩次。
        paths_to_exclude = None if part_key in used_instruction_keys else used_paths
        image_path = _pick_image_candidate(candidates, part, paths_to_exclude, strict_text)
        if not image_path:
            if part not in missing_parts:
                missing_parts.append(part)
            used_instruction_keys.add(part_key)
            continue
        image_paths.append(image_path)
        used_paths.add(os.path.abspath(image_path))
        used_instruction_keys.add(part_key)

    result["image_warnings"] = [
        f"圖片指示「{part}」找不到可配對圖片，已略過該張圖"
        for part in missing_parts
    ]
    if not image_paths:
        searched = "、".join(directories)
        return [], f"所有圖片指示都找不到可配對圖片；已搜尋：{searched}"

    return image_paths, None


def resolve_image_path(result, mmdd, image_root=DEFAULT_IMAGE_ROOT):
    """相容舊呼叫：回傳第一張配對圖片。"""
    image_paths, image_error = resolve_image_paths(result, mmdd, image_root)
    return (image_paths[0] if image_paths else None), image_error


def prepare_file_data(file_path, mmdd, image_root=DEFAULT_IMAGE_ROOT):
    """解析並驗證版型；標圖版同時完成圖片配對。"""
    result = parse_file(file_path)
    if not result:
        return None

    errors = list(result.get("validation_errors", []))
    if result.get("layout_type") == LAYOUT_IMAGE_TITLE and not errors:
        image_paths, image_error = resolve_image_paths(result, mmdd, image_root)
        if image_error:
            errors.append(image_error)
        else:
            result["image_paths"] = image_paths
            result["image_path"] = image_paths[0] if image_paths else ""

    result["validation_errors"] = errors
    result["is_valid"] = not errors
    return result


def get_today_mmdd():
    """取得今天的日期，格式為MMDD（月月日日）"""
    today = datetime.now()
    return today.strftime("%m%d")


def get_text_directory_candidates(mmdd, text_root=DEFAULT_TEXT_ROOT):
    """回傳指定日期的晚報文字資料夾候選路徑。"""
    if not is_valid_mmdd(mmdd):
        return []

    date_root = os.path.join(text_root, str(mmdd).strip())
    return [
        os.path.join(date_root, "1800"),
        os.path.join(date_root, "1819"),
        date_root,
    ]


def is_valid_mmdd(value):
    """檢查字串是否為合理的 MMDD；避免把 1800 之類的時段誤判為日期。"""
    value = str(value or "").strip()
    if not re.fullmatch(r"\d{4}", value):
        return False

    month = int(value[:2])
    day = int(value[2:])
    return 1 <= month <= 12 and 1 <= day <= 31


def infer_mmdd_from_path(folder_path, fallback=None):
    """從資料夾路徑推斷 MMDD，找不到時回傳 fallback 或今天。"""
    path_text = str(folder_path or "")
    fallback = fallback or get_today_mmdd()

    # 只看路徑段落，避免 IP、檔名或其他數字干擾。
    parts = [part for part in re.split(r"[\\/]+", path_text) if part]
    for part in reversed(parts):
        if is_valid_mmdd(part):
            return part

    return fallback


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
        "effect_words": [],
        "layout_type": LAYOUT_BIG_TITLE,
        "left_text": "",
        "image_instruction": "",
        "image_instruction_candidates": [],
        "image_path": "",
        "image_paths": [],
        "image_warnings": [],
        "validation_errors": [],
        "is_valid": True,
    }
    
    lines = []
    # 嘗試多種編碼讀取
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
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

        # 2.1 判定版型並解析標圖版欄位。
        # 舊格式：圖片指示在左邊字上一個非空括號行。
        # 新格式：(左邊字:文字) / (左邊直字:文字) 優先取下一個非空括號行為圖片指示。
        left_markers = [
            (i, marker_info)
            for i, line in enumerate(lines)
            for marker_info in [_parse_left_marker(line)]
            if marker_info
        ]
        if left_markers:
            result["layout_type"] = LAYOUT_IMAGE_TITLE
            if len(left_markers) > 1:
                result["validation_errors"].append("找到多個左邊字標記")

            marker_index, marker_info = left_markers[0]
            left_text = marker_info["left_text"]
            if not left_text:
                result["validation_errors"].append("左邊字標記沒有文字內容")
            result["left_text"] = left_text

            image_instruction, image_instruction_candidates = _find_nearby_image_instruction(
                lines,
                marker_index,
                prefer_after=marker_info["embedded"],
            )
            if not image_instruction:
                result["validation_errors"].append(
                    "找到左邊字標記，但附近找不到完整括號包住的圖片指示"
                )
            else:
                result["image_instruction"] = image_instruction
                result["image_instruction_candidates"] = image_instruction_candidates
        
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

        for title_label, title_text in (
            ("第一行大標", result["title_line1"]),
            ("第二行大標", result["title_line2"]),
        ):
            quote_count = title_text.count('"')
            if quote_count % 2 != 0:
                result["validation_errors"].append(
                    f"{title_label}發現未閉合的引號：{title_text}"
                )
        
        # 4. 找出變色字
        full_text = '\n'.join(lines)
        color_word_pattern = r'"([^"]+)"'
        color_matches = re.findall(color_word_pattern, full_text)
        result["color_words"] = list(set(color_matches)) 
        
        # 5. 找出效果字
        effect_pattern = r'\(([^)]+)\)'
        effect_matches = re.findall(effect_pattern, full_text)
        
        for effect in effect_matches:
            stripped_effect = effect.strip()
            if (
                _is_left_marker_effect(stripped_effect)
                or stripped_effect == result.get("image_instruction")
                or _extract_explicit_image_instruction(stripped_effect)
            ):
                continue
            should_exclude = False
            for keyword in EXCLUDED_EFFECT_KEYWORDS:
                if keyword in effect:
                    should_exclude = True
                    break
            
            if not should_exclude:
                result["effect_words"].append(effect.strip())
        
        result["effect_words"] = list(set(result["effect_words"]))
        result["is_valid"] = not result["validation_errors"]
        
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

