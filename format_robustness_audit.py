#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建立文字格式變形案例，量測現有解析器的耐受度。

這是獨立稽核工具，不會接入縮圖生成流程，也不會修改來源文字檔。
原始檔若已被解析器標記為無效，會列入基準問題清單而不計入通過率。
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from parse_thumbnail_txt import parse_file


DEFAULT_CORPUS = Path(__file__).resolve().parent / "過去文字檔"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "format_audit_output"
CORE_FIELDS = (
    "layout_type",
    "anchor",
    "image_instruction",
    "left_text",
    "title_line1",
    "title_line2",
)
LEFT_LABEL_PATTERN = r"左邊(?:直)?字"


@dataclass(frozen=True)
class Mutation:
    """一種不改變文字語意、只改變編輯格式的變形。"""

    name: str
    description: str
    transform: Callable[[str, dict], str | None]


def read_text(path: Path) -> str:
    """依正式解析器相同順序讀取 UTF-8／CP950。"""
    for encoding in ("utf-8-sig", "cp950"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _join_lines(source: str, lines: list[str]) -> str:
    result = "\n".join(lines)
    if source.endswith(("\n", "\r")):
        result += "\n"
    return result


def _replace_once(source: str, pattern: str, replacement: str) -> str | None:
    result, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    return result if count else None


def mutate_all_parentheses_fullwidth(source: str, _parsed: dict) -> str | None:
    if "(" not in source and ")" not in source:
        return None
    return source.replace("(", "（").replace(")", "）")


def mutate_left_marker_fullwidth(source: str, _parsed: dict) -> str | None:
    pattern = rf"\(\s*({LEFT_LABEL_PATTERN})(\s*[:：][^)]*)?\s*\)"

    def replace(match: re.Match) -> str:
        suffix = match.group(2) or ""
        return f"（{match.group(1)}{suffix}）"

    result, count = re.subn(pattern, replace, source, count=1)
    return result if count else None


def mutate_left_marker_without_parentheses(source: str, _parsed: dict) -> str | None:
    embedded = re.compile(
        rf"^(?P<indent>\s*)\(\s*(?P<label>{LEFT_LABEL_PATTERN})\s*[:：]\s*"
        rf"(?P<text>[^()]*)\)"
    )
    lines = source.splitlines()
    for index, line in enumerate(lines):
        match = embedded.match(line)
        if match:
            lines[index] = (
                f"{match.group('indent')}{match.group('label')}：{match.group('text').strip()}"
                f"{line[match.end():]}"
            )
            return _join_lines(source, lines)

    inline = rf"\(\s*({LEFT_LABEL_PATTERN})\s*\)"
    result, count = re.subn(inline, r" \1", source, count=1)
    return result if count else None


def mutate_left_marker_separate_line(source: str, _parsed: dict) -> str | None:
    pattern = re.compile(
        rf"^(?P<indent>\s*)(?P<text>.+?)\s*\(\s*(?P<label>{LEFT_LABEL_PATTERN})\s*\)\s*$"
    )
    lines = source.splitlines()
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match and match.group("text").strip():
            lines[index : index + 1] = [
                f"{match.group('indent')}{match.group('text').rstrip()}",
                f"{match.group('indent')}({match.group('label')})",
            ]
            return _join_lines(source, lines)
    return None


def mutate_left_marker_embedded(source: str, _parsed: dict) -> str | None:
    pattern = re.compile(
        rf"^(?P<indent>\s*)(?P<text>.+?)\s*\(\s*(?P<label>{LEFT_LABEL_PATTERN})\s*\)\s*$"
    )
    lines = source.splitlines()
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match and match.group("text").strip():
            lines[index] = (
                f"{match.group('indent')}({match.group('label')}："
                f"{match.group('text').strip()})"
            )
            return _join_lines(source, lines)
    return None


def mutate_left_marker_alias(source: str, _parsed: dict) -> str | None:
    if "左邊直字" in source:
        return source.replace("左邊直字", "左邊字", 1)
    if "左邊字" in source:
        return source.replace("左邊字", "左邊直字", 1)
    return None


def mutate_left_marker_extra_spaces(source: str, _parsed: dict) -> str | None:
    pattern = rf"\(\s*({LEFT_LABEL_PATTERN})\s*\)"
    return _replace_once(source, pattern, r"(  \1  )")


def _image_line_index(source: str, parsed: dict) -> int | None:
    """依基準解析結果找到來源中的圖片指示行。"""
    expected = str(parsed.get("image_instruction") or "").strip()
    alternatives = {
        str(value).strip()
        for value in parsed.get("image_instruction_candidates", [])
        if str(value).strip()
    }
    if not expected:
        return None

    for index, line in enumerate(source.splitlines()):
        candidate = re.sub(r"^\s*\+\s*", "", line.strip())
        match = re.fullmatch(r"\(([^()]*)\)", candidate)
        if not match:
            continue
        content = match.group(1).strip()
        if content == expected:
            return index
        explicit = re.search(r"定圖\s*[:：]?\s*(.+)$", content)
        if explicit:
            parts = {part for part in re.split(r"\s+", explicit.group(1).strip()) if part}
            if alternatives and alternatives.issubset(parts):
                return index
    return None


def _mutate_image_wrapper(
    source: str, parsed: dict, wrapper: Callable[[str], str]
) -> str | None:
    lines = source.splitlines()
    index = _image_line_index(source, parsed)
    if index is None:
        return None
    match = re.fullmatch(r"(?P<indent>\s*)\+?\s*\((?P<content>[^()]*)\)\s*", lines[index])
    if not match:
        return None
    lines[index] = f"{match.group('indent')}{wrapper(match.group('content'))}"
    return _join_lines(source, lines)


def mutate_image_fullwidth_parentheses(source: str, parsed: dict) -> str | None:
    return _mutate_image_wrapper(source, parsed, lambda content: f"（{content}）")


def mutate_image_without_parentheses(source: str, parsed: dict) -> str | None:
    return _mutate_image_wrapper(source, parsed, lambda content: content)


def mutate_image_mixed_parentheses(source: str, parsed: dict) -> str | None:
    return _mutate_image_wrapper(source, parsed, lambda content: f"（{content})")


def mutate_image_leading_plus(source: str, parsed: dict) -> str | None:
    return _mutate_image_wrapper(source, parsed, lambda content: f"+({content})")


def mutate_extra_blank_lines(source: str, _parsed: dict) -> str | None:
    lines = source.splitlines()
    non_empty_count = sum(bool(line.strip()) for line in lines)
    if non_empty_count < 2:
        return None
    expanded: list[str] = []
    for line in lines:
        expanded.append(line)
        if line.strip():
            expanded.append("")
    return _join_lines(source, expanded)


MUTATIONS = (
    Mutation(
        "all_parentheses_fullwidth",
        "所有半形括號改成全形括號",
        mutate_all_parentheses_fullwidth,
    ),
    Mutation(
        "left_marker_fullwidth_parentheses",
        "只有左邊字標記改用全形括號",
        mutate_left_marker_fullwidth,
    ),
    Mutation(
        "left_marker_without_parentheses",
        "左邊字標記移除括號",
        mutate_left_marker_without_parentheses,
    ),
    Mutation(
        "left_marker_separate_line",
        "左邊字內容與標記拆成兩行",
        mutate_left_marker_separate_line,
    ),
    Mutation(
        "left_marker_embedded",
        "左邊字改成括號內冒號格式",
        mutate_left_marker_embedded,
    ),
    Mutation(
        "left_marker_alias",
        "左邊字與左邊直字互換",
        mutate_left_marker_alias,
    ),
    Mutation(
        "left_marker_extra_spaces",
        "左邊字標記內加入多餘空格",
        mutate_left_marker_extra_spaces,
    ),
    Mutation(
        "image_fullwidth_parentheses",
        "圖片指示改用全形括號",
        mutate_image_fullwidth_parentheses,
    ),
    Mutation(
        "image_without_parentheses",
        "圖片指示移除括號",
        mutate_image_without_parentheses,
    ),
    Mutation(
        "image_mixed_parentheses",
        "圖片指示混用全形與半形括號",
        mutate_image_mixed_parentheses,
    ),
    Mutation(
        "image_leading_plus",
        "圖片指示前加入加號",
        mutate_image_leading_plus,
    ),
    Mutation(
        "extra_blank_lines",
        "每個非空行後加入空行",
        mutate_extra_blank_lines,
    ),
)


def _core_values(parsed: dict | None) -> dict[str, object]:
    parsed = parsed or {}
    return {field: parsed.get(field, "") for field in CORE_FIELDS}


def compare_result(expected: dict, actual: dict | None) -> list[str]:
    """回傳不同欄位；新增驗證錯誤也視為失敗。"""
    if actual is None:
        return ["parse_failed"]
    different = [
        field
        for field in CORE_FIELDS
        if str(expected.get(field, "")).strip() != str(actual.get(field, "")).strip()
    ]
    if actual.get("validation_errors"):
        different.append("validation_errors")
    return different


def _safe_filename(value: str) -> str:
    value = re.sub(r"[<>:\"/\\|?*]+", "_", value)
    return value[:120].rstrip(" .") or "sample"


def _write_markdown(report: dict, path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# 文字格式耐受度報告",
        "",
        f"- 歷史文字檔：{summary['corpus_files']} 份",
        f"- 可作為基準：{summary['trusted_baselines']} 份",
        f"- 原本已有解析警告：{summary['baseline_issue_files']} 份",
        f"- 產生有效變形案例：{summary['generated_cases']} 份",
        f"- 通過：{summary['passed_cases']} 份",
        f"- 失敗：{summary['failed_cases']} 份",
        f"- 通過率：{summary['pass_rate_percent']}%",
        "",
        "## 各種格式變形",
        "",
        "| 變形 | 說明 | 案例 | 通過 | 失敗 | 通過率 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in report["mutations"]:
        lines.append(
            f"| `{item['name']}` | {item['description']} | {item['cases']} | "
            f"{item['passed']} | {item['failed']} | {item['pass_rate_percent']}% |"
        )

    lines.extend(["", "## 最常失敗的欄位", ""])
    if report["field_failures"]:
        for field, count in report["field_failures"].items():
            lines.append(f"- `{field}`：{count} 次")
    else:
        lines.append("- 無")

    lines.extend(["", "## 說明", ""])
    lines.append("原始檔本身已有解析警告者不計入通過率，請先由人工確認其正確欄位。")
    lines.append("變形案例只存在於測試輸出，不會修改歷史文字檔或正式生成流程。")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit_corpus(
    corpus: Path,
    output_dir: Path,
    mutations: tuple[Mutation, ...] = MUTATIONS,
    sample_limit_per_mutation: int = 3,
) -> dict:
    files = sorted(corpus.glob("*.txt"), key=lambda path: path.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_root = output_dir / "failure_samples"

    baseline_issues = []
    trusted: list[tuple[Path, str, dict]] = []
    for path in files:
        parsed = parse_file(str(path))
        if parsed is None or parsed.get("validation_errors"):
            baseline_issues.append(
                {
                    "file": path.name,
                    "errors": (parsed or {}).get("validation_errors", ["解析失敗"]),
                    "parsed": _core_values(parsed),
                }
            )
            continue
        trusted.append((path, read_text(path), parsed))

    mutation_stats = {
        mutation.name: {
            "name": mutation.name,
            "description": mutation.description,
            "cases": 0,
            "passed": 0,
            "failed": 0,
            "field_failures": Counter(),
        }
        for mutation in mutations
    }
    field_failures: Counter[str] = Counter()
    failure_details = []
    saved_samples: defaultdict[str, int] = defaultdict(int)

    with tempfile.TemporaryDirectory(prefix="thumbnail_format_audit_") as temp_name:
        temp_path = Path(temp_name) / "mutated.txt"
        for original_path, source, expected in trusted:
            for mutation in mutations:
                mutated = mutation.transform(source, expected)
                if mutated is None or mutated == source:
                    continue

                temp_path.write_text(mutated, encoding="utf-8")
                actual = parse_file(str(temp_path))
                differences = compare_result(expected, actual)
                stats = mutation_stats[mutation.name]
                stats["cases"] += 1

                if not differences:
                    stats["passed"] += 1
                    continue

                stats["failed"] += 1
                stats["field_failures"].update(differences)
                field_failures.update(differences)
                detail = {
                    "file": original_path.name,
                    "mutation": mutation.name,
                    "different_fields": differences,
                    "expected": _core_values(expected),
                    "actual": _core_values(actual),
                    "validation_errors": (actual or {}).get("validation_errors", ["解析失敗"]),
                }
                failure_details.append(detail)

                if saved_samples[mutation.name] < sample_limit_per_mutation:
                    sample_dir = sample_root / mutation.name
                    sample_dir.mkdir(parents=True, exist_ok=True)
                    sample_file = sample_dir / f"{_safe_filename(original_path.stem)}.txt"
                    sample_file.write_text(mutated, encoding="utf-8")
                    detail["sample_file"] = str(sample_file.resolve())
                    saved_samples[mutation.name] += 1

    mutations_report = []
    for mutation in mutations:
        stats = mutation_stats[mutation.name]
        cases = stats["cases"]
        stats["pass_rate_percent"] = round(stats["passed"] / cases * 100, 2) if cases else 0
        stats["field_failures"] = dict(stats["field_failures"].most_common())
        mutations_report.append(stats)

    generated_cases = sum(item["cases"] for item in mutations_report)
    passed_cases = sum(item["passed"] for item in mutations_report)
    failed_cases = generated_cases - passed_cases
    report = {
        "corpus": str(corpus.resolve()),
        "summary": {
            "corpus_files": len(files),
            "trusted_baselines": len(trusted),
            "baseline_issue_files": len(baseline_issues),
            "generated_cases": generated_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "pass_rate_percent": round(passed_cases / generated_cases * 100, 2)
            if generated_cases
            else 0,
        },
        "mutations": mutations_report,
        "field_failures": dict(field_failures.most_common()),
        "baseline_issues": baseline_issues,
        "failures": failure_details,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(report, output_dir / "report.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="稽核晚報文字檔格式耐受度")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-limit", type=int, default=3)
    args = parser.parse_args()

    if not args.corpus.is_dir():
        raise SystemExit(f"找不到歷史文字檔目錄：{args.corpus}")

    report = audit_corpus(
        args.corpus,
        args.output,
        sample_limit_per_mutation=max(0, args.sample_limit),
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"詳細報告：{(args.output / 'report.md').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
