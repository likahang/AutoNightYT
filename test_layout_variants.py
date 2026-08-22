#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from generate_photoshop_script import (
    generate_jsx_script,
    validate_color_scheme_csv_text,
)
from gui_main import (
    format_generation_stats,
    get_display_effect_words,
    get_scheme_explosion_color,
    resolve_visual_config,
)
from parse_thumbnail_txt import (
    LAYOUT_BIG_TITLE,
    LAYOUT_IMAGE_TITLE,
    apply_text_result_overrides,
    get_text_directory_candidates,
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
    def test_google_color_sheet_csv_matches_existing_schema(self):
        csv_text = (Path(__file__).parent / "晚報變色.csv").read_text(encoding="utf-8-sig")
        self.assertTrue(validate_color_scheme_csv_text(csv_text))
        self.assertFalse(validate_color_scheme_csv_text("編號,錯誤欄位\nB01,第一行"))

    def test_generation_stats_text(self):
        self.assertEqual(
            "待生成: 3 ｜ 已完成: 2 ｜ 失敗: 1",
            format_generation_stats(3, 2, 1),
        )

    def test_color_scheme_swatch_uses_explosion_color(self):
        self.assertEqual("133aa8", get_scheme_explosion_color(color_scheme()))
        self.assertEqual("", get_scheme_explosion_color({"line1": {"explosion": "錯誤"}}))

    def test_anchor_position_instruction_is_hidden_from_effect_display(self):
        self.assertEqual(
            ["超大字"],
            get_display_effect_words(["定 主播 不要笑", "定  鄭亦真  不要笑", "超大字"]),
        )

    def test_thumbnail_visual_config_does_not_invent_unrecorded_colors(self):
        self.assertEqual({}, resolve_visual_config())

    def test_thumbnail_visual_config_uses_actual_or_explicit_override(self):
        persisted = {"color_id": "G01", "top_right_color": "112233"}
        resolved = {"color_id": "B02", "top_right_color": "445566"}
        self.assertEqual(resolved, resolve_visual_config(None, resolved, persisted))
        self.assertEqual(
            {"color_id": "P03", "top_right_color": "778899"},
            resolve_visual_config(
                {"color_id": "P03", "top_right_color": "778899"},
                resolved,
                persisted,
            ),
        )

    def test_text_directory_candidates_follow_date(self):
        root = r"\\server\新聞txt"
        self.assertEqual(
            [
                r"\\server\新聞txt\0819\1800",
                r"\\server\新聞txt\0819\1819",
                r"\\server\新聞txt\0819",
            ],
            get_text_directory_candidates("0819", root),
        )
        self.assertEqual([], get_text_directory_candidates("1800", root))

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
        self.assertEqual("美驅逐艦+澳洲偵察機", result["image_instruction"])
        self.assertNotIn("左邊字:挑釁中國", result["effect_words"])
        self.assertNotIn("定格 美驅逐艦+澳洲偵察機", result["effect_words"])

    def test_image_notes_and_accidental_at_sign_are_ignored(self):
        examples = (
            ("(雅萬高鐵圖)(隔天上)", "雅萬高鐵圖"),
            ("(黃岩島圖)@", "黃岩島圖"),
        )
        for index, (image_line, expected) in enumerate(examples):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "image_note.txt"
                path.write_text(
                    "1800 晚報YT縮圖 1 測試\n林嘉源\n"
                    f"{image_line}\n震撼(左邊字)\n第一行\n第二行\n",
                    encoding="utf-8",
                )
                result = parse_file(path)
            self.assertEqual(expected, result["image_instruction"])
            self.assertNotIn("隔天上", result["effect_words"])
            self.assertEqual([], result["validation_errors"])

    def test_ding_and_dingge_are_removed_from_image_instruction(self):
        examples = (
            ("(定 普丁登島 圖)", "普丁登島 圖"),
            ("(定格 美驅逐艦)", "美驅逐艦"),
        )
        for index, (image_line, expected) in enumerate(examples):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "ding_image.txt"
                path.write_text(
                    "1800 晚報YT縮圖 1 測試\n何橞瑢\n"
                    f"日本氣瘋(左邊字)\n{image_line}\n第一行\n第二行\n",
                    encoding="utf-8",
                )
                result = parse_file(path)
            self.assertEqual(expected, result["image_instruction"])
            self.assertEqual([], result["validation_errors"])

    def test_multiple_parenthesized_images_keep_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "multiple_parenthesized_images.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n鄭亦真\n"
                "(定格 國際法庭院長赤根智子)+(高市早苗人頭)\n"
                "反擊逮捕令(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual("國際法庭院長赤根智子+高市早苗人頭", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_left_marker_before_text_uses_following_text_and_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "marker_before_text.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n何橞瑢\n(左邊直字)\n"
                "普丁開殺戒\n(定圖P1)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual("普丁開殺戒", result["left_text"])
        self.assertEqual("P1", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_missing_image_line_still_warns_and_skips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing_image.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n震撼北京(左邊字)\n"
                "第一行有引號\"完整\"\n第二行也完整\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual("", result["image_instruction"])
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("圖片指示" in message for message in result["validation_errors"]))

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

    def test_effect_instruction_is_not_image_instruction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "effect_before_marker.txt"
            path.write_text(
                "1800 晚報YT縮圖 3 測試\n林嘉源\n(超大字)\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("", result["image_instruction"])
        self.assertTrue(any("圖片指示" in message for message in result["validation_errors"]))

    def test_dingtu_marker_extracts_image_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dingtu.txt"
            path.write_text(
                "1800 晚報YT縮圖 3 測試\n林嘉源\n(定圖 妤史努比)\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("妤史努比", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_dingtu_space_separated_candidates_accept_any_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "08月" / "0813" / "1800" / "YT縮圖"
            image_dir.mkdir(parents=True)
            expected = image_dir / "3.妤史努比.jpg"
            expected.write_bytes(b"test")
            path = Path(temp_dir) / "dingtu_candidates.txt"
            path.write_text(
                "1800 晚報YT縮圖 3 測試\n林嘉源\n(定圖 用今天 妤史努比)\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = prepare_file_data(path, "0813", temp_dir)
        self.assertTrue(result["is_valid"])
        self.assertEqual([str(expected.resolve())], result["image_paths"])

    def test_dingtu_instruction_with_leading_plus(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "08月" / "0819" / "1800" / "YT縮圖"
            image_dir.mkdir(parents=True)
            expected = image_dir / "3.妤史努比.jpg"
            expected.write_bytes(b"test")
            path = Path(temp_dir) / "dingtu_plus.txt"
            path.write_text(
                "1800 晚報YT縮圖 3 測試\n鄭亦真\n(定 鄭亦真 不要笑)\n"
                "(大底黑色)\n(超大字+漫畫驚訝調暗暗+ 卡通大火調暗暗)\n"
                "(左邊字:高人套路)\n+(定圖 用今天 妤史努比)\n"
                "(\"扁南部權力\"綠色字)\n\"妤\"招招致命\n\"扁南部權力\"再起\n",
                encoding="utf-8",
            )
            result = prepare_file_data(path, "0819", temp_dir)
        self.assertTrue(result["is_valid"])
        self.assertEqual("妤史努比", result["image_instruction_candidates"][1])
        self.assertEqual([str(expected.resolve())], result["image_paths"])

    def test_item_19_is_big_title_layout(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 19 通報全球 日失敗了.txt")
        self.assertEqual(LAYOUT_BIG_TITLE, result["layout_type"])
        self.assertEqual("", result["left_text"])
        self.assertEqual("", result["image_instruction"])

    def test_image_instruction_without_parentheses_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unwrapped_image.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n不是括號圖片\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("不是括號圖片", result["image_instruction"])
        self.assertTrue(result["is_valid"])

    def test_fullwidth_and_mixed_parentheses_are_normalized(self):
        examples = (
            "（測試圖片）\n震撼（左邊字）",
            "（測試圖片)\n震撼(左邊字）",
        )
        for index, body in enumerate(examples):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "mixed_brackets.txt"
                path.write_text(
                    f"1800 晚報YT縮圖 1 測試\n林嘉源\n{body}\n第一行\n第二行\n",
                    encoding="utf-8",
                )
                result = parse_file(path)
            self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
            self.assertEqual("震撼", result["left_text"])
            self.assertEqual("測試圖片", result["image_instruction"])
            self.assertEqual([], result["validation_errors"])

    def test_left_marker_without_parentheses_is_supported(self):
        examples = (
            "震撼 左邊字",
            "左邊字：震撼",
            "左邊字震撼",
        )
        for index, marker_line in enumerate(examples):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "unwrapped_marker.txt"
                path.write_text(
                    "1800 晚報YT縮圖 1 測試\n林嘉源\n(測試圖片)\n"
                    f"{marker_line}\n第一行\n第二行\n",
                    encoding="utf-8",
                )
                result = parse_file(path)
            self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
            self.assertEqual("震撼", result["left_text"])
            self.assertEqual("測試圖片", result["image_instruction"])
            self.assertEqual([], result["validation_errors"])

    def test_left_text_and_marker_on_separate_lines_are_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "separate_marker.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n測試圖片\n震撼\n(左邊字)\n"
                "第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual(LAYOUT_IMAGE_TITLE, result["layout_type"])
        self.assertEqual("震撼", result["left_text"])
        self.assertEqual("測試圖片", result["image_instruction"])
        self.assertEqual([], result["validation_errors"])

    def test_control_instruction_without_parentheses_is_not_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "control_not_image.txt"
            path.write_text(
                "1800 晚報YT縮圖 1 測試\n林嘉源\n超大字\n測試(左邊字)\n第一行\n第二行\n",
                encoding="utf-8",
            )
            result = parse_file(path)
        self.assertEqual("", result["image_instruction"])
        self.assertTrue(any("圖片指示" in message for message in result["validation_errors"]))

    def test_embedded_left_marker_can_carry_image_on_same_line(self):
        examples = (
            "(左邊字：震撼)+(左圖+右圖)",
            "左邊字：震撼 +(左圖+右圖)",
            "震撼 左邊字+(左圖+右圖)",
        )
        for index, marker_line in enumerate(examples):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "same_line_image.txt"
                path.write_text(
                    "1800 晚報YT縮圖 1 測試\n林嘉源\n"
                    f"{marker_line}\n第一行\n第二行\n",
                    encoding="utf-8",
                )
                result = parse_file(path)
            self.assertEqual("震撼", result["left_text"])
            self.assertEqual("左圖+右圖", result["image_instruction"])
            self.assertEqual([], result["validation_errors"])

    def test_unclosed_title_quote_is_invalid(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 9 日開炸 嗆摧毀靖國神社.txt")
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("未閉合的引號" in message for message in result["validation_errors"]))

    def test_session_title_override_clears_quote_error_without_editing_source(self):
        source = (
            "1800 晚報YT縮圖 1 測試\n林嘉源\n(大底黑色)\n"
            "炸掉\"靖國神社\n第二行大標\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "quote_override.txt"
            path.write_text(source, encoding="utf-8")
            result = prepare_file_data(
                path,
                "0813",
                result_overrides={"title_line1": '炸掉"靖國神社"'},
            )
            unchanged_source = path.read_text(encoding="utf-8")

        self.assertTrue(result["is_valid"])
        self.assertEqual('炸掉"靖國神社"', result["title_line1"])
        self.assertFalse(any("未閉合的引號" in item for item in result["validation_errors"]))
        self.assertEqual(source, unchanged_source)

    def test_invalid_session_override_keeps_quote_error(self):
        result = {
            "title_line1": '炸掉"靖國神社',
            "title_line2": "第二行",
            "validation_errors": ["第一行大標發現未閉合的引號"],
        }
        apply_text_result_overrides(result, {"title_line1": '仍然"錯誤'})
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("未閉合的引號" in item for item in result["validation_errors"]))

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

    def test_multi_image_instruction_skips_missing_parts_and_keeps_found_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "08月" / "0821" / "1800" / "YT縮圖"
            image_dir.mkdir(parents=True)
            trump = image_dir / "18.川普.png"
            zelensky = image_dir / "18.澤倫.png"
            moj = image_dir / "18.穆傑塔巴.png"
            for image_path in (trump, zelensky, moj):
                image_path.write_bytes(b"test")

            text_path = Path(temp_dir) / "1800 晚報YT縮圖18 美伊跨國黑幕.txt"
            text_path.write_text(
                "1800 晚報YT縮圖18 美伊跨國黑幕\n鄭亦真\n"
                "+(川普+破裂線+澤倫+破裂線+穆傑塔巴)\n"
                "(左邊字:烏誤擊伊朗?)\n這下鬧大\n扯出美伊跨國黑幕\n",
                encoding="utf-8",
            )
            result = prepare_file_data(text_path, "0821", temp_dir)

        self.assertTrue(result["is_valid"])
        self.assertEqual([str(trump), str(zelensky), str(moj)], result["image_paths"])
        self.assertEqual(
            ["圖片指示「破裂線」找不到可配對圖片，已略過該張圖"],
            result["image_warnings"],
        )


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
        self.assertIn('verticalTextLayer, "里"', script)
        self.assertIn("numberTargetWidth / numberBounds0.width * 100", script)
        self.assertIn("numberTargetHeight0 / numberBounds0.height * 100", script)
        self.assertIn("measureLabeledGapHeight(verticalTextLayer, 110)", script)
        self.assertIn('gapProbe.textItem.contents = "田  田"', script)
        self.assertIn("gapBounds.height - compactBounds.height", script)
        self.assertIn("compactBounds.height) * 0.95", script)
        self.assertIn("finalNumberTargetWidth / finalNumberBounds0.width * 100", script)
        self.assertIn("finalNumberTargetHeight0 / finalNumberBounds0.height * 100", script)
        self.assertIn(
            "numberTargetCenterX0 = (mainVerticalBounds.left + mainVerticalBounds.right) / 2",
            script,
        )
        self.assertIn("finalNumberTargetCenterX0", script)
        self.assertIn(
            "var labeledTextLayersToRotate = [verticalTextLayer, numberLayer0]",
            script,
        )
        self.assertIn("rotateLabeledTextLayersTogether(labeledTextLayersToRotate, -4.08)", script)
        self.assertNotIn("250 / numberBounds0.width", script)
        self.assertIn("titleLayer2.resize(1340", script)
        self.assertIn("setLastCharBaselineShift(titleLayer1, -17.88)", script)
        self.assertIn("titleLayer1, 200, null", script)
        self.assertIn("titleLayer2, 200, null", script)
        self.assertNotIn("titleLayer1, 200, 80", script)
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

    def test_labeled_layout_three_images_places_all_as_smart_objects(self):
        result = dict(self.label_result)
        result["image_paths"] = [
            r"C:\images\川普.png",
            r"C:\images\澤倫.png",
            r"C:\images\穆傑塔巴.png",
        ]
        result["image_path"] = result["image_paths"][0]
        script = generate_jsx_script(
            result,
            color_scheme(),
            "晚報YT縮圖(標圖版).psd",
            "output",
            "00a322",
            source_date="0821",
        )
        self.assertIn('"C:/images/川普.png", "C:/images/澤倫.png", "C:/images/穆傑塔巴.png"', script)
        self.assertIn("labeledImagePaths.length === 2", script)
        self.assertIn("multiImageIndex = labeledImagePaths.length - 1", script)
        self.assertIn("var multiImageLayer = placeLabeledSmartObject(", script)
        self.assertIn("centerLayerAt(multiImageLayer, 960, 260)", script)

    def test_single_digit_stays_in_main_layer_as_fullwidth(self):
        result = dict(self.label_result)
        result["left_text"] = '震撼"3里"'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn('verticalTextLayer.textItem.contents = "震撼３里"', script)
        self.assertNotIn("numberLayer0.textItem.contents", script)

    def test_single_punctuation_stays_in_main_layer_as_fullwidth(self):
        result = dict(self.label_result)
        result["left_text"] = '震撼!里'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn('verticalTextLayer.textItem.contents = "震撼！里"', script)
        self.assertNotIn("numberLayer0.textItem.contents", script)

    def test_multi_character_number_and_punctuation_tokens_use_horizontal_layer(self):
        examples = ("!!", "3%", "3:1", "-3!")
        for token in examples:
            with self.subTest(token=token):
                result = dict(self.label_result)
                result["left_text"] = f'震撼{token}里'
                script = generate_jsx_script(
                    result, color_scheme(), "標圖版.psd", "output", source_date="0813"
                )
                self.assertIn('verticalTextLayer.textItem.contents = "震撼  里"', script)
                self.assertIn(f'numberLayer0.textItem.contents = "{token}"', script)
                self.assertIn("setLabeledKerning(verticalTextLayer, 110", script)

    def test_two_digit_uses_kerning_90(self):
        result = dict(self.label_result)
        result["left_text"] = '震撼"30里"'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn("setLabeledKerning(verticalTextLayer, 90", script)
        self.assertIn("measureLabeledGapHeight(verticalTextLayer, 90)", script)

    def test_multiple_number_layers_rotate_together_with_main_text(self):
        result = dict(self.label_result)
        result["left_text"] = '震12撼34里'
        script = generate_jsx_script(
            result, color_scheme(), "標圖版.psd", "output", source_date="0813"
        )
        self.assertIn(
            "var labeledTextLayersToRotate = [verticalTextLayer, numberLayer0, numberLayer1]",
            script,
        )
        self.assertIn("rotateLabeledTextLayersTogether(labeledTextLayersToRotate, -4.08)", script)

    def test_big_title_layout_uses_1500_width_and_minus_30_baseline_shift(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 19 通報全球 日失敗了.txt")
        result["title_line1"] = "「美真相曝光」"
        result["title_line2"] = "「日失敗了」"
        script = generate_jsx_script(
            result, color_scheme(), "晚報YT縮圖.psd", "output", source_date="0813"
        )
        self.assertNotIn("標圖版專用流程", script)
        self.assertIn("titleLayer1.resize(1500", script)
        self.assertIn("titleLayer2.resize(1560", script)
        self.assertIn("setLastCharBaselineShift(titleLayer1, -30)", script)
        self.assertIn("titleLayer1, 350, 80", script)
        self.assertIn("titleLayer2, 350, 80", script)
        self.assertIn(
            "setCornerBracketStyleAt(textLayer, characterIndex, 400, openingBaselineShift)", script
        )
        self.assertIn("setCornerBracketStyleAt(textLayer, characterIndex, 400, null)", script)
        self.assertIn('charIDToTypeID("From")', script)
        self.assertIn('charIDToTypeID("T   ")', script)
        self.assertIn('charIDToTypeID("Krng")', script)
        self.assertIn('titleLayer1.textItem.contents = "「美真相曝光」"', script)
        self.assertIn('titleLayer2.textItem.contents = "「日失敗了」"', script)
        self.assertIn(
            "kerningValues[rangePosition] = value",
            script,
        )
        self.assertIn("openingHasTextBefore = kerningCharacterIndex > 0", script)
        self.assertIn("if (openingHasTextBefore)", script)
        self.assertIn(
            "setTitleKerningAtRangePosition(textLayer, -300, kerningCharacterIndex - 1)", script
        )
        self.assertIn(
            "setTitleKerningAtRangePosition(textLayer, -300, kerningCharacterIndex + 1)", script
        )
        self.assertIn("var rangeEnd = textLength", script)
        self.assertIn("rangeStart = rangeEnd - 1", script)
        self.assertIn("必須從\n    // 後往前寫入", script)
        self.assertIn('leadingOpeningBracket = content.length > 0 && content.charAt(0) === "「"', script)
        self.assertIn("textLayer.translate(-140, 0)", script)
        self.assertIn('content.replace(/\\s+$/, "")', script)
        self.assertIn(
            'contentWithoutTrailingWhitespace.charAt(contentWithoutTrailingWhitespace.length - 1) === "」"',
            script,
        )
        self.assertIn("(titleWidth + 70) / titleWidth * 100", script)
        self.assertIn("AnchorPosition.MIDDLELEFT", script)
        self.assertNotIn("\\u200B", script)
        self.assertNotIn("getTitleTextHorizontalScale", script)
        self.assertNotIn("var minimumKerningPosition = -1", script)
        self.assertNotIn("setTitleInsertionKerning", script)
        self.assertIn("titleLayer1, 350, 80", script)
        self.assertIn("titleLayer2, 350, 80", script)

    def test_percent_sign_in_title_uses_seventy_percent_character_size(self):
        result = parse_file(TEST_DIR / "1800 晚報YT縮圖 19 通報全球 日失敗了.txt")
        result["title_line1"] = "支持70%"
        script = generate_jsx_script(
            result, color_scheme(), "晚報YT縮圖.psd", "output", source_date="0813"
        )
        self.assertIn('titleLayer1.textItem.contents = "支持70%"', script)
        self.assertIn("setTitlePercentSignsSize(textLayer, content, percentFontSize)", script)
        self.assertIn("cloneCornerBracketStyle(sourceStyle, fixedFontSize, null)", script)
        self.assertIn("if (percentCount === 0) return", script)
        self.assertIn("titleLayer1, 350, 80", script)

        labeled_result = dict(self.label_result)
        labeled_result["title_line1"] = "支持70%"
        labeled_script = generate_jsx_script(
            labeled_result,
            color_scheme(),
            "晚報YT縮圖(標圖版).psd",
            "output",
            source_date="0813",
        )
        self.assertIn("titleLayer1, 200, null", labeled_script)
        self.assertIn("titleLayer2, 200, null", labeled_script)
        self.assertNotIn("getTitleGlyphVisibleHeight", labeled_script)


if __name__ == "__main__":
    unittest.main()
