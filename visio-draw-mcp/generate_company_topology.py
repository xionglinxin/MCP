"""生成公司网络拓扑图"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import OUTPUT_DIR, STENCIL_DIR
from visio_driver import (
    VIS_FIXED_FORMAT_PDF,
    VIS_OPEN_HIDDEN,
    VIS_OPEN_RO,
    _add_connector,
    _add_textbox,
    _find_master_by_keyword,
    _set_cell,
    _visio_session,
)

STENCIL_NAME = "企业网络产品 安全(VSS,蓝).vss"
OUTPUT_STEM = "company_network_topology"


def add_zone(page, x1, y1, x2, y2, title: str, fill: str = "RGB(240,248,252)",
              line: str = "RGB(47,166,216)"):
    shape = page.DrawRectangle(x1, y1, x2, y2)
    shape.Text = ""
    _set_cell(shape, "FillForegnd", fill)
    _set_cell(shape, "FillPattern", "1")
    _set_cell(shape, "LineColor", line)
    _set_cell(shape, "LineWeight", "1.4 pt")
    _add_textbox(page, x1 + 0.1, y2 - 0.38, x2 - 0.1, y2 - 0.06, title, size=12, color="RGB(0,80,120)")


def add_device(page, master, x, y, label: str, label_y_off: float = -0.65, label_h: float = 0.45):
    shape = page.Drop(master, x, y)
    shape.Text = ""
    try:
        _set_cell(shape, "Char.Size", "9 pt")
    except Exception:
        pass
    _add_textbox(page, x - 1.05, y + label_y_off, x + 1.05, y + label_y_off + label_h, label, size=9)
    return shape


def add_cable(page, x1, y1, x2, y2, color: str = "RGB(40,40,40)", weight: str = "1.2 pt"):
    line = page.DrawLine(x1, y1, x2, y2)
    _set_cell(line, "LineColor", color)
    _set_cell(line, "LineWeight", weight)


def generate():
    OUTPUT_DIR.mkdir(exist_ok=True)

    vsdx = OUTPUT_DIR / f"{OUTPUT_STEM}.vsdx"
    png = OUTPUT_DIR / f"{OUTPUT_STEM}.png"
    pdf = OUTPUT_DIR / f"{OUTPUT_STEM}.pdf"
    for p in (vsdx, png, pdf):
        if p.exists():
            p.unlink()

    with _visio_session() as visio:
        stencil_doc = visio.Documents.OpenEx(
            str(STENCIL_DIR / STENCIL_NAME), VIS_OPEN_RO | VIS_OPEN_HIDDEN
        )
        try:
            doc = visio.Documents.Add("")
            try:
                page = visio.ActivePage
                page.Name = "公司网络拓扑图"
                page.PageSheet.CellsU("PageWidth").FormulaU = "14 in"
                page.PageSheet.CellsU("PageHeight").FormulaU = "8.5 in"

                # ── 查找 Master ──
                internet = _find_master_by_keyword(stencil_doc, "Internet")
                fw = _find_master_by_keyword(stencil_doc, "防火墙")
                router = _find_master_by_keyword(stencil_doc, "通用路由器")
                core_sw = _find_master_by_keyword(stencil_doc, "核心交换机")
                acc_sw = _find_master_by_keyword(stencil_doc, "接入交换机")
                gen_sw = _find_master_by_keyword(stencil_doc, "通用交换机")
                server = _find_master_by_keyword(stencil_doc, "通用服务器")
                web_srv = _find_master_by_keyword(stencil_doc, "Web服务器")
                db = _find_master_by_keyword(stencil_doc, "数据库")
                pc = _find_master_by_keyword(stencil_doc, "PC")
                nb = _find_master_by_keyword(stencil_doc, "笔记本")
                lb = _find_master_by_keyword(stencil_doc, "负载均衡器")
                ips = _find_master_by_keyword(stencil_doc, "Anti-DDoS")
                disk = _find_master_by_keyword(stencil_doc, "Disk Array")

                # ── 标题 ──
                _add_textbox(page, 2.5, 8.05, 11.5, 8.40,
                             "某科技公司网络拓扑图（等保2.0三级参考）", size=22)
                _add_textbox(page, 3.0, 7.70, 11.0, 7.95,
                             "安全域划分：互联网接入区 | DMZ区 | 核心交换区 | 内部办公区 | 服务器区 | 运维管理区",
                             size=9, color="RGB(70,70,70)")

                # ═══════════════════════════════════════════════
                # 区域 1: 互联网接入区 (左上)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.35, 5.80, 3.10, 7.55, "互联网接入区", "RGB(255,245,238)", "RGB(220,130,80)")

                cloud = add_device(page, internet, 0.80, 7.00, "Internet\n电信/联通", -0.85, 0.55)
                r1 = add_device(page, router, 2.20, 7.00, "出口路由器\nAR-01\nGE0/0/0", -0.85, 0.55)

                # Firewall HA pair
                fw1 = add_device(page, fw, 0.90, 6.10, "主防火墙\nNGFW-Active\nHA-Link", -0.85, 0.55)
                fw2 = add_device(page, fw, 2.20, 6.10, "备防火墙\nNGFW-Standby", -0.85, 0.55)

                add_cable(page, 1.05, 6.75, 1.50, 6.75)
                add_cable(page, 1.70, 6.75, 2.00, 6.75)
                add_cable(page, 0.90, 6.40, 2.20, 6.40, "RGB(220,130,80)", "0.8 pt")
                _add_textbox(page, 1.30, 6.25, 2.00, 6.42, "HA心跳线", size=7, color="RGB(180,100,50)")

                # ═══════════════════════════════════════════════
                # 区域 2: DMZ 区 (左中)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.35, 3.25, 3.10, 5.45, "DMZ 区", "RGB(245,255,245)", "RGB(80,180,100)")

                ips_dev = add_device(page, ips, 1.75, 5.05, "入侵防御\nIPS", -0.60, 0.40)

                web1 = add_device(page, web_srv, 0.80, 4.00, "Web服务器\nNginx\n10.1.1.10", -0.70, 0.55)
                web2 = add_device(page, web_srv, 2.20, 4.00, "Web服务器\nNginx\n10.1.1.11", -0.70, 0.55)

                lb_dev = add_device(page, lb, 1.50, 3.50, "负载均衡\nSLB", -0.60, 0.40)

                add_cable(page, 0.80, 4.40, 1.50, 4.75)
                add_cable(page, 2.20, 4.40, 1.50, 4.75)
                add_cable(page, 0.80, 3.90, 1.50, 3.80)
                add_cable(page, 2.20, 3.90, 1.50, 3.80)

                # ═══════════════════════════════════════════════
                # 区域 3: 核心交换区 (中)
                # ═══════════════════════════════════════════════
                add_zone(page, 3.80, 4.30, 6.70, 7.55, "核心交换区", "RGB(240,248,255)", "RGB(47,140,216)")

                core1 = add_device(page, core_sw, 4.80, 6.90, "核心交换机-01\nCore-SW1\nVLAN Trunk", -0.90, 0.55)
                core2 = add_device(page, core_sw, 5.90, 6.90, "核心交换机-02\nCore-SW2\nVLAN Trunk", -0.90, 0.55)

                add_cable(page, 5.10, 6.65, 5.60, 6.65, "RGB(200,100,50)", "1.6 pt")
                _add_textbox(page, 5.10, 6.50, 5.60, 6.68, "堆叠", size=8, color="RGB(200,100,50)")

                # Connection: FW → IPS → Core
                add_cable(page, 1.53, 5.35, 1.53, 5.55)
                add_cable(page, 1.53, 5.55, 4.80, 6.40)
                add_cable(page, 2.60, 5.55, 5.90, 6.40)
                _add_textbox(page, 3.40, 5.60, 4.40, 5.78, "Trunk (LACP)", size=8, color="RGB(70,70,70)")

                # ═══════════════════════════════════════════════
                # 区域 4: 服务器区 (右下)
                # ═══════════════════════════════════════════════
                add_zone(page, 7.40, 4.30, 10.90, 7.55, "内部服务器区", "RGB(248,245,255)", "RGB(140,100,200)")

                srv1 = add_device(page, server, 8.10, 6.90, "应用服务器\nApp-SVR\n10.2.0.10", -0.90, 0.55)
                srv2 = add_device(page, server, 9.60, 6.90, "文件服务器\nFile-SVR\n10.2.0.11", -0.90, 0.55)
                db1 = add_device(page, db, 8.10, 5.50, "主数据库\nDB-Master\n10.2.0.20", -0.85, 0.55)
                db2 = add_device(page, db, 9.60, 5.50, "备数据库\nDB-Slave\n10.2.0.21", -0.85, 0.55)
                disk_dev = add_device(page, disk, 8.80, 4.50, "SAN存储\nDisk Array", -0.70, 0.45)

                # Server connections
                add_cable(page, 6.25, 6.40, 8.10, 6.45)
                add_cable(page, 6.25, 6.20, 9.60, 6.45)
                add_cable(page, 8.10, 6.50, 8.10, 5.90)
                add_cable(page, 9.60, 6.50, 9.60, 5.90)
                add_cable(page, 8.60, 5.20, 8.60, 4.80)
                add_cable(page, 9.30, 5.20, 9.30, 4.80)

                # Server internal
                add_cable(page, 8.10, 5.20, 9.60, 5.20, "RGB(140,100,200)", "0.8 pt")
                _add_textbox(page, 8.50, 5.05, 9.20, 5.22, "主从同步", size=7, color="RGB(120,80,180)")

                # ═══════════════════════════════════════════════
                # 区域 5: 内部办公区 (左下)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.35, 0.35, 6.70, 2.90, "内部办公区", "RGB(252,250,245)", "RGB(180,160,100)")

                acc1 = add_device(page, acc_sw, 1.50, 2.20, "接入交换机\nACC-SW1\nVLAN 10", -0.80, 0.55)
                acc2 = add_device(page, acc_sw, 4.50, 2.20, "接入交换机\nACC-SW2\nVLAN 20", -0.80, 0.55)

                pc1 = add_device(page, pc, 0.65, 0.95, "PC-01\n财务部\n192.168.1.10", -0.65, 0.55)
                pc2 = add_device(page, pc, 2.20, 0.95, "PC-02\n人事部\n192.168.1.11", -0.65, 0.55)
                nb1 = add_device(page, nb, 3.85, 0.95, "NB-01\n研发部\n192.168.2.10", -0.65, 0.55)
                nb2 = add_device(page, nb, 5.30, 0.95, "NB-02\n市场部\n192.168.2.11", -0.65, 0.55)

                add_cable(page, 0.65, 1.30, 1.50, 1.70)
                add_cable(page, 2.20, 1.30, 1.50, 1.70)
                add_cable(page, 3.85, 1.30, 4.50, 1.70)
                add_cable(page, 5.30, 1.30, 4.50, 1.70)

                # Core → Access
                add_cable(page, 4.80, 6.40, 1.50, 2.70)
                add_cable(page, 5.90, 6.40, 4.50, 2.70)
                _add_textbox(page, 3.20, 4.10, 4.30, 4.28, "光纤上联 (10GE)", size=8, color="RGB(70,70,70)")

                # ═══════════════════════════════════════════════
                # 区域 6: 运维管理区 (右)
                # ═══════════════════════════════════════════════
                add_zone(page, 7.40, 0.35, 10.90, 3.90, "运维管理区", "RGB(255,248,240)", "RGB(200,150,80)")

                mgmt_sw = add_device(page, gen_sw, 8.20, 3.20, "管理交换机\nMGMT-SW", -0.75, 0.50)

                mgmt1 = add_device(page, pc, 7.70, 2.00, "网管终端\nSolarWinds", -0.65, 0.50)
                mgmt2 = add_device(page, pc, 9.40, 2.00, "日志审计\nSIEM", -0.65, 0.50)
                mgmt3 = add_device(page, pc, 8.50, 0.90, "堡垒机\nBastion", -0.60, 0.42)

                add_cable(page, 7.70, 2.40, 8.20, 2.80)
                add_cable(page, 9.40, 2.40, 8.20, 2.80)
                add_cable(page, 8.50, 1.40, 8.20, 2.80)
                add_cable(page, 8.20, 2.80, 6.65, 6.40)

                # ═══════════════════════════════════════════════
                # 连接汇总标注
                # ═══════════════════════════════════════════════
                _add_textbox(page, 11.40, 7.00, 13.60, 7.55,
                             "图例说明", size=11, color="RGB(0,60,100)")
                legend_items = [
                    ("━━ 主链路 (10GE)", "RGB(40,40,40)"),
                    ("--- HA心跳线", "RGB(200,100,50)"),
                    ("··· 主从同步", "RGB(140,100,200)"),
                    ("Internet 外网", "RGB(100,100,100)"),
                    ("DMZ 对外服务区", "RGB(80,180,100)"),
                    ("Core 核心交换区", "RGB(47,140,216)"),
                    ("Server 服务器区", "RGB(140,100,200)"),
                    ("Office 办公区", "RGB(180,160,100)"),
                    ("MGMT 管理区", "RGB(200,150,80)"),
                ]
                for i, (txt, clr) in enumerate(legend_items):
                    _add_textbox(page, 11.40, 6.70 - i * 0.28, 13.60, 6.92 - i * 0.28,
                                 txt, size=8, color=clr)

                doc.SaveAs(str(vsdx))
                page.Export(str(png))
                doc.ExportAsFixedFormat(VIS_FIXED_FORMAT_PDF, str(pdf), 1, 0)

                for path in (vsdx, png, pdf):
                    if not path.exists() or path.stat().st_size == 0:
                        raise RuntimeError(f"Missing output: {path}")

                return {"ok": True, "vsdx": str(vsdx), "png": str(png), "pdf": str(pdf)}
            finally:
                doc.Close()
        finally:
            stencil_doc.Close()


if __name__ == "__main__":
    result = generate()
    print(result)
