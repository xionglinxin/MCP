"""
测试脚本：生成企业网络规划拓扑图
策略：先探测 VSS 中的真实 Master 名称，再做模糊匹配
"""
import sys
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
STENCIL_DIR = BASE_DIR / "stencils"
OUTPUT_DIR = BASE_DIR / "outputs"
HUAWEI_DIR = BASE_DIR.parent / "华为官方网络拓扑图标库（2019年10月）"

STENCIL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Visio Draw MCP 测试：企业网络规划拓扑图")
print("=" * 60)

# ============================================================
# 步骤 1：复制图标库
# ============================================================
print("\n[步骤 1] 复制华为图标库到 stencils/ ...")
vss_files = list(HUAWEI_DIR.glob("*.vss"))
if not vss_files:
    print(f"  ✗ 在 {HUAWEI_DIR} 中未找到 .vss 文件")
    sys.exit(1)

for vss_file in vss_files:
    dest = STENCIL_DIR / vss_file.name
    if not dest.exists():
        shutil.copy2(vss_file, dest)
        print(f"  ✓ {vss_file.name}")
    else:
        print(f"  - {vss_file.name} (已存在)")

# ============================================================
# 步骤 2：列出图标库
# ============================================================
print("\n[步骤 2] 列出可用图标库 ...")
from visio_driver import list_stencils

r = list_stencils()
if not r["ok"]:
    print(f"  ✗ {r}")
    sys.exit(1)
print(f"  ✓ 共 {len(r['stencils'])} 个")

# ============================================================
# 步骤 3：探测真实 Master 名称
# ============================================================
# 使用安全设备图标库（包含防火墙/IPS/Server等）
STENCIL = "企业网络产品 安全(VSS,蓝).vss"
print(f"\n[步骤 3] 探测 Master 名称: {STENCIL} ...")

from visio_driver import list_masters

r = list_masters(STENCIL)
if not r["ok"]:
    print(f"  ✗ Visio COM 错误: {r.get('error')}")
    print("  → 请确认 Microsoft Visio 已安装")
    sys.exit(1)

all_masters = r["masters"]
print(f"  ✓ 共 {len(all_masters)} 个 Master:")
for m in all_masters:
    print(f"    '{m}'")

# ============================================================
# 步骤 4：模糊匹配 Master → 功能角色
# ============================================================
print("\n[步骤 4] 匹配 Master → 功能角色 ...")

# Strip 掉 Master 名中的 \r\n
stripped = [m.strip().lower() for m in all_masters]  # 仅用于匹配，保留原始名给 COM

# 关键词 → 角色（按优先级排列，越长越精确）
KEYWORD_MAP = [
    # (关键词, 角色, 权重加成)
    # --- cloud / internet ---
    ("internet", "cloud", 2),
    ("网络云", "cloud", 1),
    ("云平台", "cloud", 0),
    # --- firewall ---
    ("防火墙", "firewall", 1),
    ("虚拟防火墙", "firewall", 0),  # prefer non-virtual
    # --- ips / ids ---
    ("anti-ddos", "ips", 4),
    ("检测设备", "ips", 3),
    ("清洗", "ips", 2),
    ("apt攻击", "ips", 0),
    ("流量探针", "ips", 0),
    ("采集器", "ips", 0),
    # --- switch ---
    ("核心交换机", "switch", 2),
    ("通用交换机", "switch", 2),
    ("接入交换机", "switch", 1),
    ("交换机", "switch", 0),
    # --- router ---
    ("通用路由器", "router", 2),
    ("general-purpose router", "router", 2),
    ("路由", "router", 0),
    # --- server ---
    ("通用服务器", "server", 2),
    ("服务器", "server", 1),
    ("web服务器", "server", 1),
    # --- database ---
    ("数据库", "database", 4),
    ("disk array", "database", 0),
    ("存储阵列", "database", 0),
    # --- pc / terminal ---
    ("笔记本电脑", "pc", 2),
    ("个人网络用户", "pc", 1),
    ("pc", "pc", 2),
]

# 匹配：对每个角色选最佳（最高关键词长度 + 权重 + 最短短Master名）
role_best = {}  # role -> (score, original_master)
for i, master in enumerate(all_masters):
    lower = stripped[i]  # 用 stripped 名做关键词匹配
    for keyword, role, weight in KEYWORD_MAP:
        if keyword in lower:
            score = len(keyword) + weight * 3 - len(lower) * 0.01
            if role not in role_best or score > role_best[role][0]:
                role_best[role] = (score, master)  # ← 存原始名给 COM
            break  # 每个 master 只匹配第一个关键词

for role in ["cloud", "firewall", "ips", "switch", "router", "server", "database", "pc"]:
    if role in role_best:
        print(f"  ✓ {role:12s} → '{role_best[role][1]}'")
    else:
        print(f"  ✗ {role:12s} → 未匹配")

# 构建最终映射
role_masters = {r: role_best[r][1] for r in role_best}

# 报告缺失的角色
needed = ["cloud", "firewall", "ips", "switch", "server", "database", "pc"]
missing = [r for r in needed if r not in role_masters]
if missing:
    print(f"\n  ⚠ 未匹配到以下角色: {missing}")
    print(f"  可用 Master: {all_masters}")
    sys.exit(1)

# ============================================================
# 步骤 5：构造并验证拓扑图规格
# ============================================================
print("\n[步骤 5] 构造拓扑图规格 ...")

from schema import DiagramSpec, NodeSpec, EdgeSpec, LayoutSpec

def m(role):
    """获取角色对应的真实 Master 名称"""
    return role_masters[role]


def validate_diagram_spec_local(spec: DiagramSpec) -> dict:
    """本脚本只验证数据结构，不依赖 MCP Server 运行时。"""
    errors = []
    warnings = []

    node_ids = [node.id for node in spec.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("Duplicate node IDs detected")

    node_id_set = set(node_ids)
    connected_nodes = set()

    for edge in spec.edges:
        if edge.from_ not in node_id_set:
            errors.append(f"Edge references missing source node: {edge.from_}")
        if edge.to not in node_id_set:
            errors.append(f"Edge references missing target node: {edge.to}")
        connected_nodes.add(edge.from_)
        connected_nodes.add(edge.to)

    isolated_nodes = node_id_set - connected_nodes
    if isolated_nodes and spec.edges:
        warnings.append(f"Isolated nodes detected: {', '.join(sorted(isolated_nodes))}")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

spec = DiagramSpec(
    title="企业网络规划拓扑图（等保2.0参考）",
    stencil=STENCIL,
    layout=LayoutSpec(direction="LR"),
    nodes=[
        NodeSpec(id="internet",      label="Internet\n互联网",        master=m("cloud"),    x=0.9,  y=6.8),
        NodeSpec(id="firewall_main", label="主防火墙\nNGFW-HA",       master=m("firewall"), x=2.3,  y=7.35),
        NodeSpec(id="firewall_bak",  label="备防火墙\nNGFW-HA",       master=m("firewall"), x=2.3,  y=6.25),
        NodeSpec(id="ips",           label="入侵防御\nIPS",           master=m("ips"),      x=3.7,  y=6.8),
        NodeSpec(id="core_sw1",      label="核心交换机1\nCore-SW",    master=m("switch"),   x=5.1,  y=7.25),
        NodeSpec(id="core_sw2",      label="核心交换机2\nCore-SW",    master=m("switch"),   x=5.1,  y=6.1),
        NodeSpec(id="dmz_web",       label="Web服务器\nDMZ区",        master=m("server"),   x=6.8,  y=7.45),
        NodeSpec(id="dmz_mail",      label="邮件服务器\nDMZ区",        master=m("server"),   x=6.8,  y=6.55),
        NodeSpec(id="app_server",    label="应用服务器\n业务区",        master=m("server"),   x=7.8,  y=5.3),
        NodeSpec(id="db_main",       label="主数据库\n核心库",         master=m("database"), x=9.15, y=5.3),
        NodeSpec(id="db_backup",     label="备份数据库\n灾备",         master=m("database"), x=10.35,y=4.3),
        NodeSpec(id="admin_pc",      label="运维终端\n堡垒机",         master=m("pc"),       x=6.45, y=3.45),
        NodeSpec(id="log_server",    label="日志审计\nSIEM",          master=m("server"),   x=8.15, y=3.45),
    ],
    edges=[
        EdgeSpec(**{"from": "internet",      "to": "firewall_main", "label": "外部流量"}),
        EdgeSpec(**{"from": "internet",      "to": "firewall_bak",  "label": "备用链路"}),
        EdgeSpec(**{"from": "firewall_main", "to": "ips",           "label": "安全检查"}),
        EdgeSpec(**{"from": "firewall_bak",  "to": "ips",           "label": "安全检查"}),
        EdgeSpec(**{"from": "ips",           "to": "core_sw1",      "label": "转发"}),
        EdgeSpec(**{"from": "ips",           "to": "core_sw2",      "label": "冗余转发"}),
        EdgeSpec(**{"from": "core_sw1",      "to": "dmz_web",       "label": "HTTP/HTTPS"}),
        EdgeSpec(**{"from": "core_sw1",      "to": "dmz_mail",      "label": "SMTP/IMAP"}),
        EdgeSpec(**{"from": "core_sw1",      "to": "app_server",    "label": "应用流量"}),
        EdgeSpec(**{"from": "core_sw2",      "to": "app_server",    "label": "冗余链路"}),
        EdgeSpec(**{"from": "app_server",    "to": "db_main",       "label": "数据读写"}),
        EdgeSpec(**{"from": "db_main",       "to": "db_backup",     "label": "主从同步"}),
        EdgeSpec(**{"from": "core_sw1",      "to": "admin_pc",      "label": "管理通道"}),
        EdgeSpec(**{"from": "core_sw1",      "to": "log_server",    "label": "日志采集"}),
        EdgeSpec(**{"from": "firewall_main", "to": "log_server",    "label": "安全日志"}),
        EdgeSpec(**{"from": "ips",           "to": "log_server",    "label": "告警日志"}),
    ],
    output_name="enterprise_network_topology"
)

print(f"  节点: {len(spec.nodes)} 个")
print(f"  连接: {len(spec.edges)} 条")
print(f"  布局: {spec.layout.direction}")

# 验证
v = validate_diagram_spec_local(spec)
if not v["ok"]:
    print(f"  ✗ 验证失败: {v['errors']}")
    sys.exit(1)
print(f"  ✓ 验证通过")
if v.get("warnings"):
    for w in v["warnings"]:
        print(f"  ⚠ {w}")

# ============================================================
# 步骤 6：生成 Visio 图表
# ============================================================
print("\n[步骤 6] 生成 Visio 图表 ...")
from visio_driver import draw_diagram

r = draw_diagram(spec.model_dump(by_alias=True))
if not r["ok"]:
    print(f"  ✗ 失败: {r.get('error')}")
    sys.exit(1)

vsdx_path = r["file"]
print(f"  ✓ 图表已生成:")
print(f"    {vsdx_path}")

# ============================================================
# 步骤 7-8：导出
# ============================================================
from visio_driver import export_diagram

for fmt in ("png", "pdf"):
    print(f"\n[步骤 {'7' if fmt == 'png' else '8'}] 导出 {fmt.upper()} ...")
    r = export_diagram(vsdx_path, fmt)
    if r["ok"]:
        print(f"  ✓ {r['file']}")
    else:
        print(f"  ✗ {r.get('error')}")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print("✅ 测试全部完成！")
print(f"\n输出文件:")
for f in OUTPUT_DIR.glob("enterprise_network_topology_*"):
    print(f"  {f.name}  ({f.stat().st_size / 1024:.1f} KB)")
print("=" * 60)
