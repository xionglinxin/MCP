"""Generate the redundant gateway MSTP/VRRP topology with Huawei Visio icons."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from config import OUTPUT_DIR, STENCIL_DIR
from visio_driver import (
    VIS_FIXED_FORMAT_PDF,
    VIS_OPEN_HIDDEN,
    VIS_OPEN_RO,
    _add_textbox,
    _find_master_by_keyword,
    _set_cell,
    _visio_session,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR.parent
HUAWEI_DIR = WORKSPACE / "华为官方网络拓扑图标库（2019年10月）"
STENCIL_NAME = "企业网络产品 交换机&无线(VSS,蓝).vss"
STENCIL_SOURCE = HUAWEI_DIR / STENCIL_NAME
STENCIL_PATH = STENCIL_DIR / STENCIL_NAME
OUTPUT_STEM = "redundant_gateway_mstp_vrrp"


def ensure_stencil() -> None:
    STENCIL_DIR.mkdir(exist_ok=True)
    if not STENCIL_PATH.exists():
        if not STENCIL_SOURCE.exists():
            raise FileNotFoundError(f"Missing Huawei stencil: {STENCIL_SOURCE}")
        shutil.copy2(STENCIL_SOURCE, STENCIL_PATH)


def add_box(page, x1, y1, x2, y2, text: str, fill: str, line: str = "RGB(47,166,216)") -> None:
    shape = page.DrawRectangle(x1, y1, x2, y2)
    shape.Text = text
    _set_cell(shape, "FillForegnd", fill)
    _set_cell(shape, "FillPattern", "1")
    _set_cell(shape, "LineColor", line)
    _set_cell(shape, "LineWeight", "1.2 pt")
    _set_cell(shape, "Char.Size", "10 pt")
    _set_cell(shape, "Char.Color", "RGB(0,70,105)")


def add_title(page) -> None:
    _add_textbox(page, 1.1, 7.85, 9.9, 8.30, "冗余网关配置拓扑（MSTP 单域多实例 + VRRP）", size=21)
    _add_textbox(page, 1.7, 7.48, 9.3, 7.78,
                 "VLAN2 -> MSTI 1，VLAN3 -> MSTI 2；VRRP Master 与 MSTP 根桥方向一致",
                 size=10, color="RGB(70,70,70)")


def add_device(page, master, x: float, y: float, label: str, label_y_offset: float = -0.70):
    shape = page.Drop(master, x, y)
    shape.Text = ""
    try:
        _set_cell(shape, "Char.Size", "9 pt")
    except Exception:
        pass
    _add_textbox(page, x - 1.10, y + label_y_offset, x + 1.10, y + label_y_offset + 0.45, label, size=9)
    return shape


def add_line(page, x1, y1, x2, y2, color: str = "RGB(40,40,40)", weight: str = "1.2 pt") -> None:
    line = page.DrawLine(x1, y1, x2, y2)
    _set_cell(line, "LineColor", color)
    _set_cell(line, "LineWeight", weight)


def generate() -> dict:
    ensure_stencil()
    OUTPUT_DIR.mkdir(exist_ok=True)

    vsdx_path = OUTPUT_DIR / f"{OUTPUT_STEM}.vsdx"
    png_path = OUTPUT_DIR / f"{OUTPUT_STEM}.png"
    pdf_path = OUTPUT_DIR / f"{OUTPUT_STEM}.pdf"
    for path in (vsdx_path, png_path, pdf_path):
        if path.exists():
            path.unlink()

    with _visio_session() as visio:
        stencil_doc = visio.Documents.OpenEx(str(STENCIL_PATH), VIS_OPEN_RO | VIS_OPEN_HIDDEN)
        try:
            doc = visio.Documents.Add("")
            try:
                page = visio.ActivePage
                page.Name = "冗余网关配置"
                page.PageSheet.CellsU("PageWidth").FormulaU = "11 in"
                page.PageSheet.CellsU("PageHeight").FormulaU = "8.5 in"

                core_sw = _find_master_by_keyword(stencil_doc, "核心交换机")
                access_sw = _find_master_by_keyword(stencil_doc, "接入交换机")
                pc = _find_master_by_keyword(stencil_doc, "PC")

                add_title(page)
                add_box(page, 0.70, 1.45, 10.30, 7.15, "MST Region 1", "RGB(245,252,255)", "RGB(70,170,215)")

                sw1 = add_device(page, core_sw, 3.10, 6.10, "SW1\nMSTI1 Root Primary\nVLAN2 VRRP Master", -0.95)
                sw2 = add_device(page, core_sw, 7.90, 6.10, "SW2\nMSTI2 Root Primary\nVLAN3 VRRP Master", -0.95)
                sw3 = add_device(page, access_sw, 3.10, 2.70, "SW3\nAccess VLAN2", -0.85)
                sw4 = add_device(page, access_sw, 7.90, 2.70, "SW4\nAccess VLAN3", -0.85)
                pc1 = add_device(page, pc, 1.65, 2.20, "PC1\n192.168.1.1/24\nGW 192.168.1.254", -0.70)
                pc2 = add_device(page, pc, 9.35, 2.20, "PC2\n192.168.2.1/24\nGW 192.168.2.254", -0.70)

                # Redundant trunks
                add_line(page, 3.10, 5.75, 3.10, 3.05)
                add_line(page, 7.90, 5.75, 7.90, 3.05)
                add_line(page, 3.35, 5.85, 7.65, 3.05)
                add_line(page, 7.65, 5.85, 3.35, 3.05)
                add_line(page, 2.15, 2.20, 2.80, 2.55, "RGB(80,80,80)", "1 pt")
                add_line(page, 8.20, 2.55, 8.85, 2.20, "RGB(80,80,80)", "1 pt")

                add_box(page, 3.75, 4.05, 7.25, 5.20,
                        "实例映射\ninstance 1 vlan 2\ninstance 2 vlan 3",
                        "RGB(255,250,232)", "RGB(230,165,55)")
                _add_textbox(page, 3.30, 4.30, 4.85, 4.75, "Trunk\nVLAN 2,3", size=8, color="RGB(70,70,70)")
                _add_textbox(page, 6.15, 4.30, 7.70, 4.75, "Trunk\nVLAN 2,3", size=8, color="RGB(70,70,70)")
                _add_textbox(page, 0.95, 5.20, 3.00, 6.30,
                             "VLAN2 网关\nVIP 192.168.1.254\nSW1: 192.168.1.252 Master\nSW2: 192.168.1.253 Backup",
                             size=8, color="RGB(20,90,150)")
                _add_textbox(page, 8.00, 5.20, 10.15, 6.30,
                             "VLAN3 网关\nVIP 192.168.2.254\nSW2: 192.168.2.253 Master\nSW1: 192.168.2.252 Backup",
                             size=8, color="RGB(20,90,150)")
                _add_textbox(page, 1.25, 1.52, 9.75, 1.95,
                             "目标：二层 MSTP 消除环路并按 VLAN 分担链路；三层 VRRP 提供网关冗余，主网关失效时由备网关接管。",
                             size=9, color="RGB(20,110,70)")

                doc.SaveAs(str(vsdx_path))
                page.Export(str(png_path))
                doc.ExportAsFixedFormat(VIS_FIXED_FORMAT_PDF, str(pdf_path), 1, 0)

                for path in (vsdx_path, png_path, pdf_path):
                    if not path.exists() or path.stat().st_size == 0:
                        raise RuntimeError(f"Missing generated output: {path}")

                return {"ok": True, "vsdx": str(vsdx_path), "png": str(png_path), "pdf": str(pdf_path)}
            finally:
                doc.Close()
        finally:
            stencil_doc.Close()


if __name__ == "__main__":
    print(generate())
