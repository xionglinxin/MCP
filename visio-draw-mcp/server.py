"""Visio Draw MCP Server v2 — 智能布局 + 会话复用 + 增量编辑

基于 MCP (Model Context Protocol) 和 FastMCP 框架，通过 Visio COM 自动化
提供图标库浏览、图表生成、增量编辑和导出功能。

启动方式:
    python server.py                    # stdio 模式（本地）
    python server.py --http 8000        # Streamable HTTP 模式（远程）
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from config import OUTPUT_DIR, STENCIL_DIR
from schema import (
    BatchSpec,
    DiagramSpec,
    EditSpec,
    ValidationResult,
)
from visio_driver import (
    delete_output,
    draw_batch,
    draw_diagram,
    export_diagram,
    init_session_manager,
    list_masters,
    list_outputs,
    list_stencils,
    update_diagram,
)

# ── 日志 ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# ── 常量 ──────────────────────────────────────────────────

SERVER_NAME = "visio_draw_mcp"
SERVER_VERSION = "2.1.0"

# ── 生命周期管理 ──────────────────────────────────────────


@asynccontextmanager
async def app_lifespan(app):
    """管理 Visio 会话和缓存"""
    STENCIL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    mgr = init_session_manager()

    state = {
        "stencil_dir": str(STENCIL_DIR),
        "output_dir": str(OUTPUT_DIR),
        "session_manager": mgr,
    }
    yield state

    # 清理：关闭 Visio
    mgr.shutdown()


# ── 服务器实例 ────────────────────────────────────────────

mcp = FastMCP(SERVER_NAME, lifespan=app_lifespan)


# ── 资源定义（Resources）─────────────────────────────────


@mcp.resource("stencils://list")
def stencil_list_resource() -> str:
    """以资源形式暴露图标库列表"""
    result = list_stencils()
    if result["ok"]:
        return "\n".join(result["stencils"])
    return f"Error: {result.get('error', 'Unknown')}"


@mcp.resource("outputs://list")
def output_list_resource() -> str:
    """以资源形式暴露已生成的文件列表"""
    result = list_outputs()
    if result["ok"] and result["files"]:
        lines = []
        for f in result["files"]:
            lines.append(f"{f['name']}  ({f['size_kb']} KB, {f['format']}, {f['created']})")
        return "\n".join(lines)
    return "(empty)"


# ── 工具定义（Tools）─────────────────────────────────────


@mcp.tool(
    name="visio_list_stencils",
    annotations={
        "title": "列出可用的 Visio 图标库",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_list_stencils(ctx: Context | None = None) -> dict[str, Any]:
    """列出 stencils/ 目录下所有可用的 Visio 图标库文件（.vss / .vssx）。

    这是使用其他 Visio 工具的第一步 — 先查看有哪些图标库可用。

    Returns:
        dict: {"ok": bool, "stencils": list[str]}

    Example:
        当用户问"有哪些图标库？"时调用此工具。
    """
    return list_stencils()


@mcp.tool(
    name="visio_list_masters",
    annotations={
        "title": "列出图标库中的 Master 图标",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_list_masters(
    stencil: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """列出指定图标库文件中所有可用的 Master 图标名称。

    ⚠️ 重要：在构造 DiagramSpec 之前，务必先用此工具确认图标名称。
    Master 名称区分大小写，必须精确匹配。

    Args:
        stencil: 图标库文件名（先用 visio_list_stencils 获取）

    Returns:
        dict: {"ok": bool, "stencil": str, "masters": list[str]}
    """
    if ctx:
        await ctx.info(f"Listing masters for {stencil}")
        await ctx.report_progress(0.3, message="正在读取图标库...")

    result = list_masters(stencil)

    if ctx:
        await ctx.report_progress(1.0, message="完成")

    return result


@mcp.tool(
    name="visio_validate_spec",
    annotations={
        "title": "验证 Visio 图表规格",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_validate_spec(
    spec: DiagramSpec,
    ctx: Context | None = None,
) -> ValidationResult:
    """验证图表规格（DiagramSpec）的合法性，不实际生成图表。

    建议在调用 visio_draw_diagram 之前先用此工具检查：
    - 节点 ID 是否重复
    - 连接线是否引用不存在的节点
    - 是否有孤立节点（无连接线）

    Args:
        spec: DiagramSpec 图表规格对象

    Returns:
        ValidationResult: {"ok": bool, "errors": list[str], "warnings": list[str]}
    """
    errors: list[str] = []
    warnings: list[str] = []

    node_ids = [node.id for node in spec.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("节点 ID 重复。每个节点必须有唯一的 id。")

    node_id_set = set(node_ids)

    for edge in spec.edges:
        if edge.from_ not in node_id_set:
            errors.append(f"连接线的源节点 '{edge.from_}' 不存在。请检查节点 ID 是否拼写正确。")
        if edge.to not in node_id_set:
            errors.append(f"连接线的目标节点 '{edge.to}' 不存在。请检查节点 ID 是否拼写正确。")

    connected_nodes: set[str] = set()
    for edge in spec.edges:
        connected_nodes.add(edge.from_)
        connected_nodes.add(edge.to)

    isolated_nodes = node_id_set - connected_nodes
    if isolated_nodes and spec.edges:
        warnings.append(
            f"以下节点没有连接线，可能是孤立的: {', '.join(sorted(isolated_nodes))}"
        )

    # 检查 group 一致性
    groups = set()
    for node in spec.nodes:
        if node.group:
            groups.add(node.group)
    if groups:
        warnings.append(f"检测到 {len(groups)} 个分组: {', '.join(sorted(groups))}。分组将自动绘制边框。")

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


@mcp.tool(
    name="visio_draw_diagram",
    annotations={
        "title": "生成 Visio 图表",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def visio_draw_diagram(
    spec: DiagramSpec,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """根据 DiagramSpec 规格自动生成 Visio 图表（.vsdx）。

    📋 推荐流程:
    1. visio_list_stencils → 选择图标库
    2. visio_list_masters → 确认可用图标名称（精确匹配！）
    3. visio_validate_spec → 预检规格
    4. visio_draw_diagram → 生成图表
    5. visio_export_diagram → 导出为 PNG/PDF

    💡 布局建议:
    - 网络拓扑/架构图 → 使用 direction="LAYERED"（自动分层）
    - 简单线性流程 → 使用 direction="LR"（从左到右）
    - 层级结构 → 使用 direction="TB"（从上到下）
    - 设备列表 → 使用 direction="GRID"（网格排列）

    🎨 高级特性:
    - 节点分组: 设置 group 字段，同组节点自动聚拢并绘制边框
    - 节点颜色: 设置 color 字段（如 "RGB(200,50,50)"）
    - 连接线样式: 设置 style 为 "solid"/"dashed"/"dotted"
    - 连接线颜色: 设置 color 字段

    Args:
        spec: DiagramSpec 图表规格对象

    Returns:
        dict: {"ok": bool, "file": str | None, "warnings": list[str], "error": str | None}
    """
    if ctx:
        await ctx.info(f"Drawing diagram: {spec.title} with {spec.stencil}")
        await ctx.report_progress(0.1, message="验证规格...")

    # 验证
    validation = await visio_validate_spec(spec)
    if not validation.ok:
        return {
            "ok": False,
            "error": f"规格验证失败: {'; '.join(validation.errors)}",
            "warnings": validation.warnings,
        }

    if ctx:
        await ctx.report_progress(0.3, message="正在生成图表...")

    result = draw_diagram(spec.model_dump(by_alias=True))

    # 合并验证警告
    if result.get("ok") and validation.warnings:
        result["warnings"] = validation.warnings

    if ctx:
        if result.get("ok"):
            await ctx.report_progress(1.0, message=f"已生成: {result.get('file', 'unknown')}")
        else:
            await ctx.error(f"生成失败: {result}")

    return result


@mcp.tool(
    name="visio_export_diagram",
    annotations={
        "title": "导出 Visio 图表为 PNG / PDF / SVG",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def visio_export_diagram(
    input_file: str,
    format: str = "png",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """将已生成的 .vsdx 图表导出为 PNG 图片、PDF 文档或 SVG 矢量图。

    Args:
        input_file: .vsdx 文件完整路径（从 visio_draw_diagram 返回的 file 字段获取）
        format: 导出格式 — "png"（默认）、"pdf" 或 "svg"

    Returns:
        dict: {"ok": bool, "file": str | None, "error": str | None}
    """
    if ctx:
        await ctx.info(f"Exporting {input_file} as {format}")
        await ctx.report_progress(0.3, message="正在导出...")

    result = export_diagram(input_file, format)

    if ctx:
        await ctx.report_progress(1.0, message="导出完成")

    return result


@mcp.tool(
    name="visio_update_diagram",
    annotations={
        "title": "增量编辑已有 Visio 图表",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def visio_update_diagram(
    edit: EditSpec,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """增量编辑已有的 .vsdx 图表 — 支持添加/删除/修改节点和连接线。

    适用场景:
    - 在已有拓扑图上添加新设备
    - 删除不需要的节点（自动级联删除关联连接线）
    - 修改节点标签文本
    - 添加新的连接关系

    Args:
        edit: EditSpec 编辑规格对象，包含:
            - input_file: 要编辑的 .vsdx 文件路径
            - add_nodes: 要添加的节点列表
            - add_edges: 要添加的连接线列表
            - remove_nodes: 要删除的节点 ID 列表
            - update_nodes: 要修改的节点属性列表

    Returns:
        dict: {"ok": bool, "file": str | None, "warnings": list[str], "error": str | None}

    Example:
        用户："在刚才的拓扑图上再加一台服务器" →
        1. 用 visio_list_masters 确认图标名
        2. 构造 EditSpec（input_file 用上次的 file 路径，add_nodes 加新服务器）
        3. 调用此工具
    """
    if ctx:
        await ctx.info(f"Updating diagram: {edit.input_file}")
        await ctx.report_progress(0.2, message="正在编辑...")

    result = update_diagram(edit.model_dump(by_alias=True))

    if ctx:
        if result.get("ok"):
            await ctx.report_progress(1.0, message="编辑完成")
        else:
            await ctx.error(f"编辑失败: {result}")

    return result


@mcp.tool(
    name="visio_draw_batch",
    annotations={
        "title": "批量生成多个 Visio 图表",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def visio_draw_batch(
    batch: BatchSpec,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """批量生成多个 Visio 图表 — 复用同一 Visio 会话，效率更高。

    最多一次生成 10 个图表。所有图表共享同一 Visio 实例，比逐个生成快约 3-5 倍。

    Args:
        batch: BatchSpec 批量规格，包含 diagrams 列表（每个都是 DiagramSpec）

    Returns:
        dict: {
            "ok": bool,
            "results": list[dict],  # 每个图表的生成结果
            "success": int,         # 成功数量
            "failed": int,          # 失败数量
        }
    """
    if ctx:
        await ctx.info(f"Batch drawing: {len(batch.diagrams)} diagrams")
        await ctx.report_progress(0.1, message="开始批量生成...")

    specs = [d.model_dump(by_alias=True) for d in batch.diagrams]
    result = draw_batch(specs)

    if ctx:
        await ctx.report_progress(
            1.0,
            message=f"批量完成: {result['success']} 成功, {result['failed']} 失败",
        )

    return result


@mcp.tool(
    name="visio_list_outputs",
    annotations={
        "title": "列出已生成的图表文件",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_list_outputs(ctx: Context | None = None) -> dict[str, Any]:
    """列出 outputs 目录下所有已生成的图表文件。

    返回文件名、大小、格式和创建时间，按时间倒序排列。

    Returns:
        dict: {"ok": bool, "files": list[dict], "total": int}
    """
    return list_outputs()


@mcp.tool(
    name="visio_delete_output",
    annotations={
        "title": "删除输出文件（移到回收站）",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def visio_delete_output(
    filename: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """安全删除 outputs 目录中的文件 — 文件会被移到回收站，可恢复。

    Args:
        filename: 要删除的文件名（不含路径，从 visio_list_outputs 获取）

    Returns:
        dict: {"ok": bool, "message": str | None, "error": str | None}
    """
    if ctx:
        await ctx.info(f"Deleting: {filename}")

    return delete_output(filename)


@mcp.tool(
    name="visio_draw_redundant_gateway_topology",
    annotations={
        "title": "生成冗余网关 MSTP/VRRP 案例拓扑",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_draw_redundant_gateway_topology(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """生成预制的冗余网关配置拓扑图（MSTP 单域多实例 + VRRP）。

    这是一个一键生成的预定义案例拓扑，包含核心交换机、接入交换机、PC 等设备。

    Returns:
        dict: {"ok": bool, "vsdx": str, "png": str, "pdf": str}

    Requires:
        图标库 "企业网络产品 交换机&无线(VSS,蓝).vss" 在 stencils/ 目录中。
    """
    if ctx:
        await ctx.info("Generating redundant gateway topology")
        await ctx.report_progress(0.2, message="准备生成预置拓扑...")

    from generate_redundant_gateway_topology import generate

    try:
        result = generate()
    except Exception as exc:
        if ctx:
            await ctx.error(f"Generation failed: {exc}")
        return {"ok": False, "error": str(exc)}

    if ctx:
        await ctx.report_progress(1.0, message="预置拓扑已生成")

    return result


@mcp.tool(
    name="visio_draw_firewall_case_topology",
    annotations={
        "title": "生成华为防火墙配置案例拓扑",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_draw_firewall_case_topology(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """生成预制的华为防火墙配置案例拓扑图。

    包含 trust/untrust/OM 安全区域、防火墙策略标注、
    PC、路由器、服务器、Internet 云等设备。

    Returns:
        dict: {"ok": bool, "vsdx": str, "png": str, "pdf": str}

    Requires:
        图标库 "企业网络产品 安全(VSS,蓝).vss" 在 stencils/ 目录中。
    """
    if ctx:
        await ctx.info("Generating firewall case topology")
        await ctx.report_progress(0.2, message="准备生成防火墙案例...")

    from generate_firewall_case_28 import generate

    try:
        result = generate()
    except Exception as exc:
        if ctx:
            await ctx.error(f"Generation failed: {exc}")
        return {"ok": False, "error": str(exc)}

    if ctx:
        await ctx.report_progress(1.0, message="防火墙案例已生成")

    return result


@mcp.tool(
    name="visio_get_help",
    annotations={
        "title": "获取 Visio MCP 使用指南",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def visio_get_help(ctx: Context | None = None) -> dict[str, Any]:
    """返回 Visio Draw MCP 的使用指南和最佳实践。

    当不确定如何使用时调用此工具。

    Returns:
        dict: 包含工具列表、推荐流程和布局建议
    """
    return {
        "ok": True,
        "version": SERVER_VERSION,
        "tools": {
            "visio_list_stencils": "列出可用图标库",
            "visio_list_masters": "列出图标库中的图标（⚠️ 绘图前必用）",
            "visio_validate_spec": "验证规格合法性（建议绘图前调用）",
            "visio_draw_diagram": "生成图表（核心工具）",
            "visio_export_diagram": "导出为 PNG/PDF/SVG",
            "visio_update_diagram": "增量编辑已有图表",
            "visio_draw_batch": "批量生成多个图表",
            "visio_list_outputs": "列出已生成的文件",
            "visio_delete_output": "删除输出文件（回收站）",
            "visio_draw_redundant_gateway_topology": "一键生成 MSTP/VRRP 案例",
            "visio_draw_firewall_case_topology": "一键生成防火墙案例",
            "visio_get_help": "显示此帮助信息",
        },
        "recommended_workflow": [
            "1. visio_list_stencils → 选择图标库",
            "2. visio_list_masters(stencil) → 确认可用图标名（精确匹配！）",
            "3. 构造 DiagramSpec（nodes 的 master 必须与步骤 2 的名称完全一致）",
            "4. visio_validate_spec(spec) → 预检",
            "5. visio_draw_diagram(spec) → 生成 .vsdx",
            "6. visio_export_diagram(file, 'png') → 导出预览图",
        ],
        "layout_guide": {
            "LAYERED": "推荐用于网络拓扑、架构图等有向图。自动按拓扑层级分层排列。",
            "LR": "从左到右，适合简单线性流程。",
            "TB": "从上到下，适合层级结构（如组织架构图）。",
            "GRID": "网格排列，适合设备列表、组件展示。",
        },
        "tips": [
            "Master 名称区分大小写，必须精确匹配",
            "设置 group 字段可以自动绘制分组边框",
            "direction='LAYERED' 对网络拓扑效果最好",
            "可以用 color 字段自定义节点和连接线颜色",
            "批量生成用 visio_draw_batch，比逐个生成快 3-5 倍",
        ],
    }


# ── 入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--http":
        port = int(sys.argv[2])
        print(f"Visio Draw MCP Server v{SERVER_VERSION} — HTTP mode on port {port}")
        mcp.run(transport="streamable-http", host="127.0.0.1", port=port)
    else:
        mcp.run()
