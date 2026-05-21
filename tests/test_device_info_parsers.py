"""Unit tests for device_info_parsers."""
from __future__ import annotations

from adb_helper.core.device_info_parsers import (
    NA,
    khz_to_mhz,
    kib_to_human,
    parse_battery,
    parse_cpuinfo,
    parse_display,
    parse_getprop,
    parse_ip_addr,
    parse_ip_link,
    parse_mac_file,
    parse_meminfo,
    parse_surfaceflinger,
)


def test_kib_to_human():
    assert kib_to_human(0) == "0 KB"
    assert kib_to_human(2048) == "2 MB"
    assert kib_to_human(2 * 1024 * 1024) == "2.0 GB"


def test_khz_to_mhz_valid():
    assert khz_to_mhz("2000000") == "2000 MHz"


def test_khz_to_mhz_invalid_returns_na():
    assert khz_to_mhz("") == NA
    assert khz_to_mhz("abc") == NA


def test_parse_getprop():
    text = "[ro.product.model]: [SM-A346E]\n[ro.product.brand]: [samsung]\n"
    out = parse_getprop(text)
    assert out["ro.product.model"] == "SM-A346E"
    assert out["ro.product.brand"] == "samsung"


def test_parse_meminfo_subset():
    text = "MemTotal:  4096 kB\nfoo: bar\n"
    assert parse_meminfo(text)["MemTotal"] == 4096


def test_parse_battery_keys_normalised():
    text = "  level: 78\n  status: 2\n  Max charging current: 1500\n"
    out = parse_battery(text)
    assert out["level"] == "78"
    assert out["status"] == "2"
    assert "max_charging_current" in out


def test_parse_cpuinfo_cores_and_hardware():
    text = (
        "processor : 0\nmodel name : Cortex-A55\n"
        "processor : 1\nmodel name : Cortex-A55\n"
        "Hardware  : Mediatek\n"
    )
    cpu = parse_cpuinfo(text)
    assert cpu["cores"] == "2"
    assert cpu["hardware"] == "Mediatek"


def test_parse_display_real():
    out = parse_display("real 1080 x 2400 refreshRate=120.0")
    assert out["resolution"] == "1080 x 2400"
    assert out["refresh_rate"] == "120 Hz"


def test_parse_surfaceflinger_gles():
    text = "GLES: Vendor, Renderer, OpenGL ES 3.2 v1.r45"
    out = parse_surfaceflinger(text)
    assert out["vendor"] == "Vendor"
    assert out["renderer"] == "Renderer"
    assert out["version"].startswith("OpenGL ES 3.2")


def test_parse_ip_addr():
    assert parse_ip_addr("    inet 192.168.1.10/24 brd ...") == "192.168.1.10"
    assert parse_ip_addr("nope") == ""


def test_parse_ip_link():
    text = "2: wlan0:\n    link/ether aa:bb:cc:dd:ee:ff brd ff:ff:ff:ff:ff:ff"
    assert parse_ip_link(text) == "aa:bb:cc:dd:ee:ff"


def test_parse_mac_file_only_valid():
    assert parse_mac_file("aa:bb:cc:dd:ee:ff\n") == "aa:bb:cc:dd:ee:ff"
    assert parse_mac_file("not a mac") == ""
