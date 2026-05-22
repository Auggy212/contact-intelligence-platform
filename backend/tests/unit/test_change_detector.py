"""Unit tests for OOXML change detection — no DB, no network."""

import pytest
from lxml import etree

from app.parsers.change_detector import (
    extract_tracked_deletions,
    extract_tracked_insertions,
    has_any_change,
    is_strikethrough,
)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _el(tag: str, **attrs) -> etree._Element:
    return etree.Element(f"{{{_W}}}{tag}", {f"{{{_W}}}{k}": v for k, v in attrs.items()})


def test_is_strikethrough_detects_strike():
    run = _el("r")
    rpr = etree.SubElement(run, f"{{{_W}}}rPr")
    etree.SubElement(rpr, f"{{{_W}}}strike")
    assert is_strikethrough(run) is True


def test_is_strikethrough_val_zero_means_no_strike():
    run = _el("r")
    rpr = etree.SubElement(run, f"{{{_W}}}rPr")
    strike = etree.SubElement(rpr, f"{{{_W}}}strike")
    strike.set(f"{{{_W}}}val", "0")
    assert is_strikethrough(run) is False


def test_is_strikethrough_no_rpr():
    run = _el("r")
    assert is_strikethrough(run) is False


def test_extract_tracked_insertions():
    body = _el("body")
    para = etree.SubElement(body, f"{{{_W}}}p")
    ins = etree.SubElement(para, f"{{{_W}}}ins")
    ins.set(f"{{{_W}}}author", "Alice")
    ins.set(f"{{{_W}}}date", "2026-01-01")
    run = etree.SubElement(ins, f"{{{_W}}}r")
    t = etree.SubElement(run, f"{{{_W}}}t")
    t.text = "Inserted text"

    results = extract_tracked_insertions(body)
    assert len(results) == 1
    assert results[0]["author"] == "Alice"
    assert results[0]["text"] == "Inserted text"


def test_extract_tracked_deletions():
    body = _el("body")
    para = etree.SubElement(body, f"{{{_W}}}p")
    del_elem = etree.SubElement(para, f"{{{_W}}}del")
    del_elem.set(f"{{{_W}}}author", "Bob")
    run = etree.SubElement(del_elem, f"{{{_W}}}r")
    dt = etree.SubElement(run, f"{{{_W}}}delText")
    dt.text = "Deleted text"

    results = extract_tracked_deletions(body)
    assert len(results) == 1
    assert results[0]["author"] == "Bob"
    assert results[0]["text"] == "Deleted text"


def test_has_any_change_flags_all_types():
    para = _el("p")
    # Add insertion
    ins = etree.SubElement(para, f"{{{_W}}}ins")
    r1 = etree.SubElement(ins, f"{{{_W}}}r")
    t1 = etree.SubElement(r1, f"{{{_W}}}t")
    t1.text = "inserted"
    # Add strikethrough run
    r2 = etree.SubElement(para, f"{{{_W}}}r")
    rpr = etree.SubElement(r2, f"{{{_W}}}rPr")
    etree.SubElement(rpr, f"{{{_W}}}strike")

    flags = has_any_change(para)
    assert flags["insertion"] is True
    assert flags["strikethrough"] is True
    assert flags["deletion"] is False
