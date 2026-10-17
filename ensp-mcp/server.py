"""eNSP Draw MCP Server — 让 AI Agent 通过自然语言生成 eNSP 拓扑和设备配置

基于 MCP (Model Context Protocol) 和 FastMCP 框架，提供拓扑生成、
设备配置模板管理功能。

启动方式:
    python server.py                    # stdio 模式（本地）
    python server.py --http 8000        # Streamable HTTP 模式（远程）
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from config import EXAMPLE_DIR, OUTPUT_DIR, TEMPLATE_DIR
from schema import TopologySpec, ValidationResult
from ensp_driver import (
    generate_topology,
    validate_topology,
    list_templates,
    load_template,
)

# ── 常量 ──────────────────────────────────────────────────────

SERVER_NAME = "ensp_draw_mcp"
SERVER_VERSION = "0.2.0"

# ── 生命周期管理 ──────────────────────────────────────────────

@asynccontextmanager
async def app_lifespan(app):
    """管理服务器生命周期内的共享资源"""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    state = {
        "template_dir": str(TEMPLATE_DIR),
        "output_dir": str(OUTPUT_DIR),
    }
    yield state

# ── 服务器实例 ────────────────────────────────────────────────

mcp = FastMCP(SERVER_NAME, lifespan=app_lifespan)

# ── 资源定义（Resources）─────────────────────────────────────

@mcp.resource("templates://list")
def template_list_resource() -> str:
    """以资源形式暴露配置模板列表"""
    result = list_templates()
    if result["ok"]:
        return "\n".join(result["templates"])
    return f"Error: {result.get('error', 'Unknown')}"


@mcp.resource("outputs://list")
def output_list_resource() -> str:
    """以资源形式暴露已生成的文件列表"""
    files = sorted(
        str(f.relative_to(OUTPUT_DIR)) for f in OUTPUT_DIR.rglob("*")
        if f.is_file() and not any(part.startswith(".staging-") for part in f.relative_to(OUTPUT_DIR).parts)
    )
    if not files:
        return "(empty)"
    return "\n".join(files)

# ── 工具定义（Tools）─────────────────────────────────────────

@mcp.tool(
    name="ensp_list_templates",
    annotations={
        "title": "列出可用的设备配置模板",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ensp_list_templates(ctx: Context | None = None) -> dict[str, Any]:
    """列出 templates/ 目录下所有可用的设备配置模板。

    Returns:
        dict: {
            "ok": bool,
            "templates": list[str],  # 模板名称列表
        }

    Example:
        当用户问"有哪些配置模板？"时调用此工具。
    """
    if ctx:
        await ctx.debug(f"Listing available templates in {TEMPLATE_DIR}")
    return list_templates()


@mcp.tool(
    name="ensp_load_template",
    annotations={
        "title": "加载配置模板内容",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ensp_load_template(
    template_name: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """加载指定配置模板的内容。

    Args:
        template_name: 模板名称（不含 .txt 扩展名）

    Returns:
        dict: {
            "ok": bool,
            "name": str,
            "content": str,  # 模板内容
            "error": str | None,
        }

    Example:
        当用户想查看某个模板的内容时调用。
    """
    if ctx:
        await ctx.info(f"Loading template: {template_name}")
    return load_template(template_name)


@mcp.tool(
    name="ensp_validate_topology",
    annotations={
        "title": "验证 eNSP 拓扑规格",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ensp_validate_topology(
    spec: TopologySpec,
    ctx: Context | None = None,
) -> ValidationResult:
    """验证拓扑规格的合法性，不实际生成文件。

    检查：
    - 设备 ID 是否重复
    - 连接线是否引用不存在的设备
    - 是否有孤立设备

    Args:
        spec: TopologySpec 拓扑规格对象

    Returns:
        ValidationResult: {
            "ok": bool,
            "errors": list[str],
            "warnings": list[str],
        }
    """
    if ctx:
        await ctx.debug(f"Validating topology: {spec.title}")

    result = validate_topology(spec)
    return ValidationResult(**result)


@mcp.tool(
    name="ensp_generate_topology",
    annotations={
        "title": "生成 eNSP 拓扑和配置文件",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def ensp_generate_topology(
    spec: TopologySpec,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """根据 TopologySpec 规格生成 eNSP .topo 文件和设备配置脚本。

    流程：
    1. 验证规格合法性
    2. 自动布局设备位置（如果启用）
    3. 生成 .topo XML 文件
    4. 生成各设备的配置脚本

    Args:
        spec: TopologySpec 拓扑规格对象，包含:
            - title (str): 拓扑标题
            - devices (list[DeviceSpec]): 设备列表
            - links (list[LinkSpec]): 连接线列表
            - output_name (str): 输出文件名前缀
            - auto_layout (bool): 是否自动布局

    Returns:
        dict: {
            "ok": bool,
            "topo_file": str | None,  # .topo 文件路径
            "config_files": list[str],  # 配置脚本文件路径列表
            "warnings": list[str],
            "error": str | None,
        }

    Example:
        用户："生成一个包含 2 个路由器和 1 个交换机的拓扑" →
        1. 构造 TopologySpec
        2. 可选：调用 ensp_validate_topology 验证
        3. 调用此工具生成拓扑和配置
    """
    if ctx:
        await ctx.info(f"Generating topology: {spec.title}")
        await ctx.report_progress(0.1, message="验证规格...")

    # 验证
    validation = await ensp_validate_topology(spec)
    if not validation.ok:
        return {
            "ok": False,
            "error": f"验证失败: {'; '.join(validation.errors)}",
            "warnings": validation.warnings,
        }

    if ctx:
        await ctx.report_progress(0.3, message="生成拓扑文件...")

    try:
        result = generate_topology(spec)
    except Exception as exc:
        if ctx:
            await ctx.error(f"Generation failed: {exc}")
        return {"ok": False, "error": str(exc), "warnings": []}

    if ctx:
        if result.get("ok"):
            await ctx.report_progress(
                1.0, message=f"已生成: {result.get('topo_file', 'unknown')}"
            )
        else:
            await ctx.error(f"Generation failed: {result}")

    return result


@mcp.tool(
    name="ensp_generate_simple_topology",
    annotations={
        "title": "快速生成简单拓扑（示例）",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def ensp_generate_simple_topology(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """生成一个预定义的简单拓扑示例（3 台路由器串联）。

    这是一个快速演示工具，包含：
    - R1 (AR1220)
    - R2 (AR2220)
    - R3 (AR1220)
    - 基础配置脚本

    Returns:
        dict: {
            "ok": bool,
            "topo_file": str,
            "config_files": list[str],
        }
    """
    if ctx:
        await ctx.info("Generating simple topology example")
        await ctx.report_progress(0.2, message="准备生成示例拓扑...")

    spec = TopologySpec(
        title="简单三路由器拓扑",
        devices=[
            {
                "id": "R1",
                "name": "边界路由器",
                "device_type": "AR_Router",
                "model": "AR1220",
                "config_script": """interface GigabitEthernet0/0/0
 ip address 192.168.1.1 255.255.255.252
 undo shutdown
#
interface GigabitEthernet0/0/1
 ip address 10.0.0.1 255.255.255.0
 undo shutdown""",
            },
            {
                "id": "R2",
                "name": "核心路由器",
                "device_type": "AR_Router",
                "model": "AR2220",
                "config_script": """interface GigabitEthernet0/0/0
 ip address 192.168.1.2 255.255.255.252
 undo shutdown
#
interface GigabitEthernet0/0/1
 ip address 192.168.2.1 255.255.255.252
 undo shutdown""",
            },
            {
                "id": "R3",
                "name": "接入路由器",
                "device_type": "AR_Router",
                "model": "AR1220",
                "config_script": """interface GigabitEthernet0/0/0
 ip address 192.168.2.2 255.255.255.252
 undo shutdown
#
interface GigabitEthernet0/0/1
 ip address 172.16.0.1 255.255.255.0
 undo shutdown""",
            },
        ],
        links=[
            {
                "from_device": "R1",
                "from_interface": "GE0/0/0",
                "to_device": "R2",
                "to_interface": "GE0/0/0",
                "link_type": "Ethernet",
            },
            {
                "from_device": "R2",
                "from_interface": "GE0/0/1",
                "to_device": "R3",
                "to_interface": "GE0/0/0",
                "link_type": "Ethernet",
            },
        ],
        output_name="simple_example",
        auto_layout=True,
    )

    try:
        result = generate_topology(spec)
    except Exception as exc:
        if ctx:
            await ctx.error(f"Generation failed: {exc}")
        return {"ok": False, "error": str(exc)}

    if ctx:
        await ctx.report_progress(1.0, message="示例拓扑已生成")

    return result


# ── 入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--http":
        port = int(sys.argv[2])
        print(f"eNSP Draw MCP Server v{SERVER_VERSION} — HTTP mode on port {port}")
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
