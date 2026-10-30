#!/usr/bin/env python3
"""Create a grouped Industrial AI weekly report draft from a sources CSV.

The script validates the CSV schema, row count, categories, and source dates,
then emits a Markdown scaffold with grouped items and a reference list. Final
prose, DOCX rendering, and headlines should still be created by the agent
following SKILL.md. This scaffold is internal: source metadata and Chinese
reference indexes must be edited into publishable prose and English-only
references without publication dates before delivery.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path


CATEGORIES = [
    "制造业企业巨头动态",
    "工业AI新技术/新产品",
    "工业AI资本与初创动态",
    "前沿科研与学术",
    "代表性中小企业新闻",
]

SECTION_LABELS = {
    "制造业企业巨头动态": "【一、请改写为行业趋势判断：本期巨头与产能新闻共同说明什么变化】",
    "工业AI新技术/新产品": "【二、请改写为行业趋势判断：本期技术产品正在进入哪些现场入口】",
    "工业AI资本与初创动态": "【三、请改写为行业趋势判断：本期资本正在重新定价哪些工业AI能力】",
    "前沿科研与学术": "【四、请改写为行业趋势判断：本期科研正在补齐哪些落地短板】",
    "代表性中小企业新闻": "【五、请改写为行业趋势判断：本期中小企业落地显示哪些基础盘变化】",
}

REQUIRED_COLUMNS = ["title", "published_at", "event_date", "content", "link", "category"]
MIN_ROWS = 25
MAX_ROWS = 30


def parse_date(value: str, field_name: str, row_no: int) -> dt.date:
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise SystemExit(f"Row {row_no}: {field_name} must be YYYY-MM-DD or YYYYMMDD, got {value!r}")


def read_sources(path: Path, start: dt.date, end: dt.date) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            raise SystemExit(
                "CSV header must be exactly: " + ",".join(REQUIRED_COLUMNS)
            )
        rows = [{key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS} for row in reader]

    if not MIN_ROWS <= len(rows) <= MAX_ROWS:
        raise SystemExit(f"CSV must contain {MIN_ROWS}-{MAX_ROWS} rows, got {len(rows)}")

    for index, row in enumerate(rows, start=2):
        missing = [key for key in REQUIRED_COLUMNS if not row[key]]
        if missing:
            raise SystemExit(f"Row {index}: missing required fields: {', '.join(missing)}")
        published_at = parse_date(row["published_at"], "published_at", index)
        event_date = parse_date(row["event_date"], "event_date", index)
        if not start <= published_at <= end:
            raise SystemExit(f"Row {index}: published_at {published_at} is outside {start}..{end}")
        if not start <= event_date <= end:
            raise SystemExit(f"Row {index}: event_date {event_date} is outside {start}..{end}")

    bad_categories = sorted({row["category"] for row in rows if row["category"] not in CATEGORIES})
    if bad_categories:
        raise SystemExit("Unknown category values: " + ", ".join(bad_categories))

    category_counts = {category: 0 for category in CATEGORIES}
    for row in rows:
        category_counts[row["category"]] += 1
    sparse_categories = [category for category, count in category_counts.items() if count < 5]
    if sparse_categories:
        details = ", ".join(f"{category}={category_counts[category]}" for category in sparse_categories)
        raise SystemExit("Each category must contain at least 5 rows: " + details)

    return rows


def default_range(today: dt.date) -> tuple[dt.date, dt.date]:
    start = today - dt.timedelta(days=today.weekday() + 7)
    end = today - dt.timedelta(days=today.weekday() + 1)
    return start, end


def build_markdown(rows: list[dict[str, str]], start: dt.date, end: dt.date) -> str:
    references: list[str] = []
    lines: list[str] = [
        "# 请根据本周最强商业新闻点改写标题，正文标题不得出现“工业AI周报”",
        "",
        "【核心观察】",
        "",
        f"本期覆盖周期：{start:%Y%m%d} - {end:%Y%m%d}。请在正式成稿时用本周最强新闻点改写核心观察，避免写成泛泛趋势摘要。新闻小标题须改写为进展标签，呈现主体、动作和新状态，不要照搬CSV标题。",
        "",
    ]

    for category in CATEGORIES:
        section_rows = [row for row in rows if row["category"] == category]
        if not section_rows:
            continue

        lines.extend(["", SECTION_LABELS[category], ""])
        for row in section_rows:
            ref_no = len(references) + 1
            lines.extend([row["title"], "", f"{row['content']} [{ref_no}]", ""])
            references.append(f"[{ref_no}] {row['title']} - {row['link']}")

    lines.extend(["", "【References】", "", *references, ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    if args.start and args.end:
        start = parse_date(args.start, "--start", 0)
        end = parse_date(args.end, "--end", 0)
    else:
        start, end = default_range(dt.date.today())
    if start > end:
        raise SystemExit("--start must be before or equal to --end")

    rows = read_sources(args.csv_file, start, end)
    markdown = build_markdown(rows, start, end)

    out_path = args.out or Path(f"industrial_ai_weekly_report_{start:%Y%m%d}_{end:%Y%m%d}.md")
    out_path.write_text(markdown, encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
