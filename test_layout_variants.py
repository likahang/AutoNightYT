#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from generate_photoshop_script import generate_jsx_script
from parse_thumbnail_txt import (
    LAYOUT_BIG_TITLE,
    LAYOUT_IMAGE_TITLE,
    infer_mmdd_from_path,
    parse_file,
    prepare_file_data,
)


TEST_DIR = Path(__file__).parent / "測試用文字檔"
TEST_DIR_2 = Path(__file__).parent / "測試用文字檔2"


def color_scheme():
    return {
        "id": "B03",
        "line1": {
            "base": "ffffff", "stroke": "133aa8", "special1": "fefd29",
            "special2": "aef2ff", "shadow": "002567", "explosion": "133aa8",
        },
        "line2": {
            "base": "168316", "stroke": "ffffff", "special1": "d61e1e",
            "special2": "9e00b1", "shadow": "e3e3e3", "explosion": "",
        },
    }


class LayoutParsingTests(unittest.TestCase):
    def test_infer_mmdd_from_folder_path_ignores_1800_time_folder(self):
        self.assertEqual(
            "0813",
            infer_mmdd_from_path(r"\\10.227.58.117\新聞txt\0813\1800", "9999"),
        )
        self.assertEqual(
            "0813",
            infer_mmdd_from_path(r"\\10.227.63.105\public\__CG-IN\08月\0813\1800\YT縮圖", "9999"),
        )
        self.assertEqual(
            "9999",
            infer_mmdd_from_path(r"\\10.227.58.117\新聞txt\1800", "9999"),
        )

    def test_item_18_is_labeled_layout(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 18 福建艦 殺美航母.txt")
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual('震撼"300里"', result["left_text"])
        self.assertEqual("福建艦圖", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_parenthesized_left_text_uses_next_image_instruction(self):
        result = parse_file(TEST_DIR_2 / "1800 晚報YT縮圖 9 美艦噩耗.txt")
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("挑釁中國", result["left_text"])
        self.assertEqual("定格 美驅逐艦+澳洲偵察機", result["image_instruction"])
        self.assertNotIn("左邊字:挑釁中國", result["effect_words"])
        self.assertNotIn("定格 美驅逐艦+澳洲偵察機", result["effect_words"])

    def test_left_vertical_marker_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "alias.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n(測試圖片)\n挑釁中國(左邊直字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("挑釁中國", result["left_text"])
        self.assertEqual("測試圖片", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_item_19_is_big_title_layout(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 19 通報全球 日失敗了.txt")
        self.assertEqual(LAYOUT_BIG_TITLE, result["layout_type"])
        self.assertEqual("", result["left_text"])
        self.assertEqual("", result["image_instruction"])

    def test_left_marker_without_parenthesized_previous_line_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n不是括號圖片\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("圖片指示" in message for message in result["validation_errors"]))

    def test_unclosed_title_quote_is_invalid(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 9 日開炸 嗆摧毀靖國神社.txt")
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("未閉合的引號" in message for message in result["validation_errors"]))

    def test_month_archive_image_matching_prefers_issue_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "08月" / "0813" / "1800" / "YT縮圖"
            image_dir.mkdir(parents=True)
            expected = image_dir / "18.福建艦.jpg"
            expected.write_bytes(b"test")
            (image_dir / "17.其他.jpg").write_bytes(b"test")
            result = prepare_file_data(
                TEST_DIR / "1800 晚報YT縮圖 18 福建艦 殺美航母.txt",
                "0813",
                temp_dir,
            )
        self.assertTrue(result["is_valid"])
        self.assertEqual(str(expected), result["image_path"])

    def test_plus_image_instruction_matches_two_images_in_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "0815" / "1800" / "YT縮圖"
            image_dir.mkdir(parents=True)
            left = image_dir / "15.高市人頭.jpg"
            right = image_dir / "15.戴旭日旗.jpg"
            left.write_bytes(b"left")
            right.write_bytes(b"right")
            result = prepare_file_data(
                TEST_DIR_2 / "1800 晚報YT縮圖 15 日拜鬼不悔改.txt",
                "0815",
                temp_dir,
            )
        self.assertTrue(result["is_valid"])
        self.assertEqual([str(left), str(right)], result["image_paths"])
        self.assertEqual(str(left), result["image_path"])


class LayoutJsxTests(unittest.TestCase):
    def setUp(self):
        self.label_result = parse_file(TEST_DIR / "1800 晚報YT縮圖 18 福建艦 殺美航母.txt")
        self.label_result["image_path"] = r"C:\images\18.福建艦.jpg"

    def test_labeled_layout_contains_full_workflow(self):
        script = generate_jsx_script(
            self.label_result,
            color_scheme(),
            "晚報YT縮圖(標圖版).psd",
            "output",
            "00a322",
            source_date="0813",
        )
        self.assertIn("標圖版專用流程", script)
        self.assertIn('verticalTextLayer.textItem.contents = "震撼  里"', script)
        self.assertIn('numberLayer0.textItem.contents = "300"', script)
        self.assertIn("setLabeledKerning(verticalTextLayer, 110", script)
        self.assertIn("titleLayer2.resize(1280", script)
        self.assertIn("userMaskFeather", script)
        self.assertIn("18.福建艦", script)

    def test_labeled_layout_two_images_uses_gradient_join(self):
        result = parse_file(TEST_DIR_2 / "1800 晚報YT縮圖 15 日拜鬼不悔改.txt")
        result["image_paths"] = [r"C:\images\高市人頭.jpg", r"C:\images\戴旭日旗.jpg"]
        result["image_path"] = result["image_paths"][0]
        script = generate_jsx_script(
            result,
            color_scheme(),
            "晚報YT縮圖(標圖版).psd",
            "output",
            "00a322",
            source_date="0815",
        )
        self.assertIn('"C:/images/高市人頭.jpg", "C:/images/戴旭日旗.jpg"', script)
        self.assertIn("applyLeftFadeGradientMask(leftImageLayer)", script)
        self.assertIn("leftImageBounds.right - 215", script)
        self.assertIn("rightImageLayer.move(leftImageLayer, ElementPlacement.PLACEAFTER)", script)

    def test_single_digit_stays_in_main_layer_as_fullwidth(self):
        result = dict(self.label_result)
        result["left_text"] = '震撼"3里"'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn('verticalTextLayer.textItem.contents = "震撼３里"', script)
        self.assertNotIn("numberLayer0.textItem.contents", script)

    def test_two_digit_uses_kerning_90(self):
        result = dict(self.label_result)
        result["left_text"] = '震撼"30里"'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn("setLabeledKerning(verticalTextLayer, 90", script)

    def test_big_title_layout_keeps_original_resize(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 19 通報全球 日失敗了.txt")
        script = generate_jsx_script(
            result, color_scheme(), "晚報YT縮圖.psd", "output", source_date="0813"
        )
        self.assertNotIn("標圖版專用流程", script)
        self.assertIn("titleLayer2.resize(1560", script)


if __name__ == "__main__":
    unittest.main()
