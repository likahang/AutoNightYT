#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from format_robustness_audit import (
    Mutation,
    audit_corpus,
    mutate_extra_blank_lines,
    mutate_left_marker_alias,
    mutate_left_marker_without_parentheses,
)


SAMPLE = """1800 晚報YT縮圖 1 測試

林嘉源
辣晚報精華
(定 林嘉源 不要笑)

(大底黑色)
(測試圖片)
震撼(左邊字)

第一行大標
第二行大標
"""


class FormatRobustnessAuditTests(unittest.TestCase):
    def test_mutations_are_deterministic_and_do_not_edit_source(self):
        parsed = {"left_text": "震撼", "image_instruction": "測試圖片"}
        original = SAMPLE
        self.assertEqual(
            mutate_left_marker_alias(original, parsed),
            original.replace("左邊字", "左邊直字", 1),
        )
        self.assertIn("震撼 左邊字", mutate_left_marker_without_parentheses(original, parsed))
        self.assertEqual(original, SAMPLE)

    def test_audit_separates_invalid_baseline_and_reports_failures(self):
        mutations = (
            Mutation("blank_lines", "加入空行", mutate_extra_blank_lines),
            Mutation(
                "marker_without_parentheses",
                "標記移除括號",
                mutate_left_marker_without_parentheses,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            corpus = root / "corpus"
            output = root / "output"
            corpus.mkdir()
            (corpus / "valid.txt").write_text(SAMPLE, encoding="utf-8")
            (corpus / "invalid.txt").write_text(
                SAMPLE.replace("震撼(左邊字)", "(左邊字)"), encoding="utf-8"
            )

            report = audit_corpus(corpus, output, mutations, sample_limit_per_mutation=1)

            self.assertEqual(report["summary"]["corpus_files"], 2)
            self.assertEqual(report["summary"]["trusted_baselines"], 1)
            self.assertEqual(report["summary"]["baseline_issue_files"], 1)
            self.assertEqual(report["summary"]["generated_cases"], 2)
            self.assertEqual(report["summary"]["passed_cases"], 2)
            self.assertEqual(report["summary"]["failed_cases"], 0)
            self.assertTrue((output / "report.json").is_file())
            self.assertTrue((output / "report.md").is_file())


if __name__ == "__main__":
    unittest.main()
