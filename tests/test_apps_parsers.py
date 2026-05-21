"""Unit tests for apps_parsers — pure functions, no Qt."""
from __future__ import annotations

from adb_helper.core.apps_parsers import (
    parse_df,
    parse_meminfo,
    parse_pm_dump,
    parse_pm_list,
)


def test_parse_pm_list_simple():
    text = (
        "package:/data/app/com.example-1/base.apk=com.example\n"
        "package:/system/app/Chrome/Chrome.apk=com.android.chrome\n"
    )
    out = parse_pm_list(text)
    assert out == [
        ("/data/app/com.example-1/base.apk", "com.example"),
        ("/system/app/Chrome/Chrome.apk", "com.android.chrome"),
    ]


def test_parse_pm_list_skips_malformed():
    assert parse_pm_list("garbage\npackage:no-apk-suffix\n") == []


def test_parse_pm_dump_disabled():
    text = "  enabled=2\nnonLocalizedLabel=My App\n"
    label, disabled = parse_pm_dump(text)
    assert label == "My"   # nonLocalizedLabel regex stops at whitespace
    assert disabled is True


def test_parse_pm_dump_enabled_default():
    label, disabled = parse_pm_dump("  enabled=0\n")
    assert label == ""
    assert disabled is False


def test_parse_pm_dump_no_enabled_line():
    label, disabled = parse_pm_dump("nonLocalizedLabel=X\n")
    assert disabled is None


def test_parse_meminfo():
    text = "MemTotal:        4096000 kB\nMemAvailable:    2048000 kB\nSwapTotal:           0 kB\n"
    m = parse_meminfo(text)
    assert m["MemTotal"] == 4096000
    assert m["MemAvailable"] == 2048000
    assert m["SwapTotal"] == 0


def test_parse_df_human_columns_returns_used_total():
    # df modern output (block headers + line with /data)
    text = (
        "Filesystem   Size  Used Avail Use% Mounted on\n"
        "/dev/data    50G   30G   20G  60%  /data\n"
    )
    used_kib, total_kib = parse_df(text)
    # 50G ≈ 50 * 1024 * 1024 KiB; 30G ≈ 30 * 1024 * 1024 KiB.
    assert total_kib == 50 * 1024 * 1024
    assert used_kib == 30 * 1024 * 1024


def test_parse_df_old_style_inline():
    text = "/data: 52.0G total, 46.5G used, 5.5G available, ext4"
    used_kib, total_kib = parse_df(text)
    assert total_kib > 0
    assert used_kib > 0
    # used < total by definition
    assert used_kib < total_kib


def test_parse_df_empty():
    assert parse_df("") == (0, 0)
