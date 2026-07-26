"""Generate the Huawei firewall configuration case topology with Visio.

This script is intentionally case-specific: it creates the topology used by the
course "防火墙配置案例" and exports VSDX/PNG/PDF artifacts for the report.
"""

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
STENCIL_NAME = "企业网络产品 安全(VSS,蓝).vss"
STENCIL_SOURCE = HUAWEI_DIR / STENCIL_NAME
STENCIL_PATH = STENCIL_DIR / STENCIL_NAME
OUTPUT_STEM = "huawei_firewall_case_28"

TRUST_IP = "1.1.1.28/24"
OM_IP = "2.2.2.1/24"
UNTRUST_IP = "3.3.3.28/24"


def ensure_stencil() -> None:
    STENCIL_DIR.mkdir(exist_ok=True)
    if not STENCIL_PATH.exists():
        if not STENCIL_SOURCE.exists():
            raise FileNotFoundError(f"Missing Huawei stencil: {STENCIL_SOURCE}")
        shutil.copy2(STENCIL_SOURCE, STENCIL_PATH)


def add_device(page, master, x: float, y: float, label: str):
    shape = page.Drop(master, x, y)
    shape.Text = ""
    try:
        _set_cell(shape, "Char.Size", "9 pt")
    except Exception:
        pass
    _add_textbox(page, x - 0.72, y - 0.66, x + 0.72, y - 0.10, label, size=9)
    return shape


def add_zone(page, x1, y1, x2, y2, title: str, fill: str = "RGB(240,248,252)") -> None:
    shape = page.DrawRectangle(x1, y1, x2, y2)
    shape.Text = ""
    _set_cell(shape, "FillForegnd", fill)
    _set_cell(shape, "FillPattern", "1")
    _set_cell(shape, "LineColor", "RGB(47,166,216)")
    _set_cell(shape, "LineWeight", "1.6 pt")
    _add_textbox(page, x1 + 0.12, y2 - 0.42, x2 - 0.10, y2 - 0.06, title, size=13, color="RGB(0,90,130)")


def add_label(page, x, y, text: str, size: int = 10, color: str = "RGB(0,0,0)") -> None:
    _add_textbox(page, x - 0.85, y - 0.26, x + 0.85, y + 0.26, text, size=size, color=color)


def add_title(page, text: str) -> None:
    shape = page.DrawRectangle(2.0, 7.75, 9.0, 8.25)
    shape.Text = text
    _set_cell(shape, "FillPattern", "0")
    _set_cell(shape, "LinePattern", "0")
    _set_cell(shape, "Char.Size", "22 pt")
    _set_cell(shape, "Char.Style", "1")


def add_side_note(page) -> None:
    note = page.DrawRectangle(7.1, 5.55, 10.45, 7.15)
    note.Text = (
        "任务要求\n"
        "1. 根据规划配置防火墙接口IP地址\n"
        "2. 允许GE1/0/1响应Ping服务\n"
        "3. 创建OM安全区域，priority 95\n"
        "4. 允许OM区域ICMP访问untrust区域"
    )
    _set_cell(note, "FillForegnd", "RGB(255,250,235)")
    _set_cell(note, "LineColor", "RGB(230,160,40)")
    _set_cell(note, "LineWeight", "1.2 pt")
    _set_cell(note, "Char.Size", "10 pt")


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
                page.Name = "防火墙配置案例"
                page.PageSheet.CellsU("PageWidth").FormulaU = "11 in"
                page.PageSheet.CellsU("PageHeight").FormulaU = "8.5 in"

                cloud = _find_master_by_keyword(stencil_doc, "Internet")
                firewall = _find_master_by_keyword(stencil_doc, "防火墙")
                pc = _find_master_by_keyword(stencil_doc, "PC")
                router = _find_master_by_keyword(stencil_doc, "通用路由器")
                server = _find_master_by_keyword(stencil_doc, "通用服务器")

                add_title(page, "华为防火墙配置案例拓扑（学号后两位：28）")

                add_zone(page, 0.75, 2.80, 3.20, 4.25, "trust", "RGB(244,252,255)")
                add_zone(page, 3.80, 5.15, 7.20, 7.10, "新建安全区域 OM\npriority 95", "RGB(244,252,255)")
                add_zone(page, 7.85, 2.80, 10.20, 4.25, "untrust", "RGB(244,252,255)")

                trust_pc = add_device(page, pc, 2.15, 3.50, "PC-trust\n1.1.1.2/24")
                fw = add_device(page, firewall, 5.55, 3.50, "FW")
                om_server = add_device(page, server, 5.55, 6.15, "OM Server\n2.2.2.2/24")
                untrust_router = add_device(page, router, 8.70, 3.55, "AR-untrust")
                untrust_cloud = add_device(page, cloud, 9.60, 3.55, "Internet")

                # Connections
                from visio_driver import _add_connector
                _add_connector(page, trust_pc, fw)
                _add_connector(page, fw, om_server)
                _add_connector(page, fw, untrust_router)
                _add_connector(page, untrust_router, untrust_cloud)

                add_label(page, 4.05, 3.12, f"GE1/0/1\n{TRUST_IP}", size=10)
                add_label(page, 5.95, 4.55, f"GE1/0/2\n{OM_IP}", size=10)
                add_label(page, 6.95, 3.12, f"GE1/0/3\n{UNTRUST_IP}", size=10)
                add_label(page, 5.55, 2.35, "service-manage ping permit\ntrust -> local", size=9, color="RGB(20,90,150)")
                add_label(page, 7.10, 4.55, "security-policy R1\nOM -> untrust: ICMP permit", size=9, color="RGB(20,120,70)")
                add_side_note(page)

                doc.SaveAs(str(vsdx_path))
                page.Export(str(png_path))
                doc.ExportAsFixedFormat(VIS_FIXED_FORMAT_PDF, str(pdf_path), 1, 0)

                for path in (vsdx_path, png_path, pdf_path):
                    if not path.exists() or path.stat().st_size == 0:
                        raise RuntimeError(f"Missing generated output: {path}")

                return {
                    "ok": True,
                    "vsdx": str(vsdx_path),
                    "png": str(png_path),
                    "pdf": str(pdf_path),
                }
            finally:
                doc.Close()
        finally:
            stencil_doc.Close()


if __name__ == "__main__":
    result = generate()
    print(result)
