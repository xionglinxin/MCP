"""生成 Web 服务安全综合防御拓扑图 - 大作业"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import OUTPUT_DIR, STENCIL_DIR
from drawing import _contained_path, _resolve_stencil_path
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
OUTPUT_STEM = "web_service_security_defense"


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

    vsdx = _contained_path(OUTPUT_DIR, OUTPUT_DIR / f"{OUTPUT_STEM}.vsdx")
    png = _contained_path(OUTPUT_DIR, OUTPUT_DIR / f"{OUTPUT_STEM}.png")
    pdf = _contained_path(OUTPUT_DIR, OUTPUT_DIR / f"{OUTPUT_STEM}.pdf")
    for p in (vsdx, png, pdf):
        if p.exists():
            p.unlink()

    with _visio_session() as visio:
        stencil_doc = visio.Documents.OpenEx(
            str(_resolve_stencil_path(STENCIL_NAME)), VIS_OPEN_RO | VIS_OPEN_HIDDEN
        )
        try:
            doc = visio.Documents.Add("")
            try:
                page = visio.ActivePage
                page.Name = "Web服务安全综合防御"
                page.PageSheet.CellsU("PageWidth").FormulaU = "16 in"
                page.PageSheet.CellsU("PageHeight").FormulaU = "10 in"

                # ── 查找 Master ──
                internet = _find_master_by_keyword(stencil_doc, "Internet")
                fw = _find_master_by_keyword(stencil_doc, "防火墙")
                router = _find_master_by_keyword(stencil_doc, "通用路由器")
                core_sw = _find_master_by_keyword(stencil_doc, "核心交换机")
                spine_sw = _find_master_by_keyword(stencil_doc, "核心交换机")  # Spine
                leaf_sw = _find_master_by_keyword(stencil_doc, "接入交换机")  # Leaf
                server = _find_master_by_keyword(stencil_doc, "通用服务器")
                web_srv = _find_master_by_keyword(stencil_doc, "Web服务器")
                db = _find_master_by_keyword(stencil_doc, "数据库")
                waf = _find_master_by_keyword(stencil_doc, "防火墙")  # 用防火墙图标代替 WAF
                ips = _find_master_by_keyword(stencil_doc, "Anti-DDoS")  # 用 Anti-DDoS 图标
                ids = _find_master_by_keyword(stencil_doc, "Anti-DDoS")  # 用 Anti-DDoS 图标
                vpn = _find_master_by_keyword(stencil_doc, "VPN")
                lb = _find_master_by_keyword(stencil_doc, "负载均衡器")

                # ── 标题 ──
                _add_textbox(page, 3.0, 9.55, 13.0, 9.90,
                             "Web服务安全的综合防御拓扑图", size=24)
                _add_textbox(page, 3.5, 9.15, 12.5, 9.45,
                             "架构：Spine-Leaf大二层 | 双核心双出口 | 纵深防御 | 支持IPv4/IPv6",
                             size=10, color="RGB(70,70,70)")

                # ═══════════════════════════════════════════════
                # 区域 1: Internet 接入区 (顶部)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.5, 8.0, 4.5, 8.95, "Internet 接入区", "RGB(255,245,238)", "RGB(220,130,80)")

                cloud1 = add_device(page, internet, 1.2, 8.45, "Internet\n电信出口", -0.70, 0.45)
                cloud2 = add_device(page, internet, 3.8, 8.45, "Internet\n联通出口", -0.70, 0.45)

                # ═══════════════════════════════════════════════
                # 区域 2: 边界防火墙区 (出口双防火墙)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.5, 6.5, 4.5, 7.75, "边界安全区", "RGB(255,240,240)", "RGB(200,80,80)")

                fw1 = add_device(page, fw, 1.2, 7.10, "NGFW-01\n主出口\nNAT/ACL", -0.75, 0.55)
                fw2 = add_device(page, fw, 3.8, 7.10, "NGFW-02\n备出口\nNAT/ACL", -0.75, 0.55)

                add_cable(page, 1.2, 8.0, 1.2, 7.50)
                add_cable(page, 3.8, 8.0, 3.8, 7.50)
                add_cable(page, 1.6, 7.10, 3.4, 7.10, "RGB(200,80,80)", "0.8 pt")
                _add_textbox(page, 2.1, 6.95, 2.9, 7.12, "VRRP", size=7, color="RGB(180,60,60)")

                # ═══════════════════════════════════════════════
                # 区域 3: 安全设备区 (WAF + IPS + VPN + 审计)
                # ═══════════════════════════════════════════════
                add_zone(page, 5.2, 6.5, 10.5, 8.95, "安全防护层", "RGB(245,255,245)", "RGB(80,180,100)")

                waf_dev = add_device(page, waf, 6.0, 8.40, "WAF\nWeb应用防火墙", -0.70, 0.45)
                ips_dev = add_device(page, ips, 7.5, 8.40, "IPS\n入侵防御", -0.70, 0.45)
                ids_dev = add_device(page, ids, 9.0, 8.40, "IDS\n入侵检测", -0.70, 0.45)

                vpn_dev = add_device(page, vpn, 6.0, 7.10, "VPN Gateway\nSSL/IPSec", -0.70, 0.45)
                audit = add_device(page, server, 7.5, 7.10, "数据审计\n数据库审计", -0.70, 0.45)
                siem = add_device(page, server, 9.0, 7.10, "SIEM\n安全管理中心", -0.70, 0.45)

                # 连接防火墙到安全设备
                add_cable(page, 1.2, 6.70, 6.0, 7.95)
                add_cable(page, 3.8, 6.70, 9.0, 7.95)

                # ═══════════════════════════════════════════════
                # 区域 4: 核心交换区 - Spine 层 (双核心)
                # ═══════════════════════════════════════════════
                add_zone(page, 5.2, 4.8, 10.5, 6.25, "Spine层 (核心)", "RGB(240,248,255)", "RGB(47,140,216)")

                spine1 = add_device(page, spine_sw, 6.5, 5.50, "Spine-01\n核心交换机\nVLAN Trunk", -0.85, 0.55)
                spine2 = add_device(page, spine_sw, 8.8, 5.50, "Spine-02\n核心交换机\nVLAN Trunk", -0.85, 0.55)

                add_cable(page, 6.9, 5.30, 8.4, 5.30, "RGB(200,100,50)", "1.6 pt")
                _add_textbox(page, 7.2, 5.15, 8.1, 5.33, "Eth-Trunk", size=8, color="RGB(200,100,50)")

                # 安全设备连接到 Spine
                add_cable(page, 6.0, 6.70, 6.5, 5.95)
                add_cable(page, 7.5, 6.70, 7.0, 5.95)
                add_cable(page, 9.0, 6.70, 8.8, 5.95)

                # ═══════════════════════════════════════════════
                # 区域 5: Leaf 层 (接入交换机)
                # ═══════════════════════════════════════════════
                add_zone(page, 5.2, 2.8, 10.5, 4.55, "Leaf层 (接入)", "RGB(245,250,255)", "RGB(100,150,220)")

                leaf1 = add_device(page, leaf_sw, 6.0, 3.80, "Leaf-01\nVLAN 100", -0.75, 0.50)
                leaf2 = add_device(page, leaf_sw, 7.5, 3.80, "Leaf-02\nVLAN 200", -0.75, 0.50)
                leaf3 = add_device(page, leaf_sw, 9.0, 3.80, "Leaf-03\nVLAN 300", -0.75, 0.50)

                # Spine to Leaf 全连接
                add_cable(page, 6.5, 5.10, 6.0, 4.25)
                add_cable(page, 6.5, 5.10, 7.5, 4.25)
                add_cable(page, 8.8, 5.10, 7.5, 4.25)
                add_cable(page, 8.8, 5.10, 9.0, 4.25)

                # ═══════════════════════════════════════════════
                # 区域 6: Web 服务器集群区 (云平台)
                # ═══════════════════════════════════════════════
                add_zone(page, 0.5, 0.5, 4.5, 5.3, "Web服务器集群 (云平台)", "RGB(248,245,255)", "RGB(140,100,200)")

                lb_dev = add_device(page, lb, 2.5, 4.80, "负载均衡器\nNginx/LVS", -0.65, 0.45)

                web1 = add_device(page, web_srv, 1.0, 3.70, "Web-01\nApache/HTTPS\n10.1.1.10", -0.80, 0.60)
                web2 = add_device(page, web_srv, 2.5, 3.70, "Web-02\nApache/HTTPS\n10.1.1.11", -0.80, 0.60)
                web3 = add_device(page, web_srv, 4.0, 3.70, "Web-03\nApache/HTTPS\n10.1.1.12", -0.80, 0.60)

                # Web 到 LB
                add_cable(page, 1.0, 4.10, 2.3, 4.50)
                add_cable(page, 2.5, 4.10, 2.5, 4.50)
                add_cable(page, 4.0, 4.10, 2.7, 4.50)

                # LB 到 Leaf
                add_cable(page, 3.0, 4.80, 6.0, 4.10)

                _add_textbox(page, 1.0, 2.90, 4.0, 3.20,
                             "配置：open-ssl, iptables\n流量控制, 连接数限制\n非法输入检测与过滤",
                             size=8, color="RGB(100,60,150)")

                # ═══════════════════════════════════════════════
                # 区域 7: 数据库服务器区
                # ═══════════════════════════════════════════════
                add_zone(page, 11.2, 4.8, 15.5, 8.95, "数据服务区", "RGB(255,248,240)", "RGB(200,150,80)")

                db1 = add_device(page, db, 12.0, 8.25, "MySQL-Master\n主数据库\n10.2.0.10", -0.85, 0.55)
                db2 = add_device(page, db, 13.5, 8.25, "MySQL-Slave\n从数据库\n10.2.0.11", -0.85, 0.55)

                dns_srv = add_device(page, server, 12.0, 7.00, "DNS Server\nIPv4/IPv6", -0.70, 0.45)
                ftp_srv = add_device(page, server, 13.5, 7.00, "FTP Server\nVSFTPD", -0.70, 0.45)

                ssh_srv = add_device(page, server, 12.0, 5.70, "SSH Server\n堡垒机\n禁root/空口令", -0.80, 0.55)
                backup = add_device(page, server, 13.5, 5.70, "Backup Server\n备份服务器", -0.75, 0.50)

                # 数据库主从同步
                add_cable(page, 12.5, 8.25, 13.0, 8.25, "RGB(200,150,80)", "0.8 pt")
                _add_textbox(page, 12.5, 8.10, 13.0, 8.27, "主从同步", size=7, color="RGB(180,130,60)")

                # Spine 到数据服务区
                add_cable(page, 8.8, 5.50, 12.0, 7.50)
                add_cable(page, 8.8, 5.50, 13.5, 7.50)

                # ═══════════════════════════════════════════════
                # 区域 8: 内部管理区
                # ═══════════════════════════════════════════════
                add_zone(page, 11.2, 0.5, 15.5, 4.55, "运维管理区", "RGB(252,250,245)", "RGB(180,160,100)")

                mgmt_sw = add_device(page, leaf_sw, 13.3, 4.00, "管理交换机", -0.65, 0.40)

                admin1 = add_device(page, server, 12.0, 2.80, "网管终端\nSNMP", -0.65, 0.45)
                admin2 = add_device(page, server, 13.5, 2.80, "日志服务器\nSyslog", -0.65, 0.45)
                admin3 = add_device(page, server, 12.0, 1.50, "监控平台\nZabbix", -0.65, 0.45)
                admin4 = add_device(page, server, 13.5, 1.50, "配置中心\nAnsible", -0.65, 0.45)

                add_cable(page, 12.0, 3.20, 13.3, 3.70)
                add_cable(page, 13.5, 3.20, 13.3, 3.70)
                add_cable(page, 12.0, 1.90, 13.3, 3.70)
                add_cable(page, 13.5, 1.90, 13.3, 3.70)

                # 管理区连接到 Spine
                add_cable(page, 13.3, 4.30, 10.5, 5.30)

                # ═══════════════════════════════════════════════
                # 图例说明
                # ═══════════════════════════════════════════════
                legend_box = page.DrawRectangle(0.5, 0.5, 4.5, 2.6)
                legend_box.Text = ""
                _set_cell(legend_box, "FillForegnd", "RGB(255,255,255)")
                _set_cell(legend_box, "FillPattern", "1")
                _set_cell(legend_box, "LineColor", "RGB(100,100,100)")
                _set_cell(legend_box, "LineWeight", "1 pt")

                _add_textbox(page, 0.6, 2.35, 4.4, 2.55, "安全技术说明", size=11, color="RGB(0,60,100)")

                legend_items = [
                    "✓ Spine-Leaf 大二层架构 (VXLAN/EVPN)",
                    "✓ 双核心交换机 Eth-Trunk 链路聚合",
                    "✓ 双出口防火墙 VRRP 热备份",
                    "✓ WAF/IPS/IDS 多层安全防护",
                    "✓ Apache: open-ssl, HTTPS, QUIC",
                    "✓ iptables: 开放 80/443/21/22/53",
                    "✓ MySQL: 访问控制、审计日志",
                    "✓ SSH: 禁止 root、拒绝空口令",
                    "✓ 防火墙: NAT、ACL、策略路由",
                    "✓ 全网支持 IPv4/IPv6 双栈",
                ]
                y_start = 2.15
                for i, txt in enumerate(legend_items):
                    _add_textbox(page, 0.7, y_start - i * 0.16, 4.3, y_start + 0.14 - i * 0.16,
                                 txt, size=8, color="RGB(50,50,50)")

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
