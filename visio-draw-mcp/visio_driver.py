"""Visio COM 自动化驱动 v2.1 — 智能布局 + 会话复用 + 增量编辑

此模块为兼容性门面（facade），实际实现分布在：
- session.py  — Visio 会话管理（COM 生命周期、健康检查、超时）
- layout.py   — 布局引擎（Kahn 拓扑排序、自动布局、页面尺寸）
- drawing.py  — 绘图辅助 + 核心操作（节点、连接线、导出、增量编辑）
"""
from __future__ import annotations

# ── 会话管理 ──
from session import (
    VIS_FIXED_FORMAT_PDF,
    VIS_OPEN_HIDDEN,
    VIS_OPEN_RO,
    VIS_OPEN_RW,
    VisioSessionManager,
    _visio_session,
    _with_timeout,
    get_session_manager,
    init_session_manager,
)

# ── 布局引擎 ──
from layout import (
    _auto_layout,
    _auto_page_size,
    _compute_bounding_box,
    _extract_groups,
    _layout_layered,
    _layout_layered_horizontal,
    _layout_layered_vertical,
    _rearrange_by_groups,
    _topological_layers,
)

# ── 绘图 + 核心操作 ──
from drawing import (
    _add_connector,
    _add_textbox,
    _apply_node_style,
    _draw_edge_label,
    _draw_group_boundaries,
    _draw_title_banner,
    _find_master_by_keyword,
    _format_node_label,
    _open_document,
    _resolve_stencil_path,
    _safe_output_path,
    _set_cell,
    delete_output,
    draw_batch,
    draw_diagram,
    export_diagram,
    list_masters,
    list_outputs,
    list_stencils,
    update_diagram,
)

__all__ = [
    # 会话
    "VisioSessionManager",
    "init_session_manager",
    "get_session_manager",
    "_visio_session",
    "_with_timeout",
    "VIS_OPEN_RO",
    "VIS_OPEN_HIDDEN",
    "VIS_OPEN_RW",
    "VIS_FIXED_FORMAT_PDF",
    # 布局
    "_auto_layout",
    "_auto_page_size",
    "_compute_bounding_box",
    "_extract_groups",
    "_topological_layers",
    "_layout_layered",
    "_layout_layered_vertical",
    "_layout_layered_horizontal",
    "_rearrange_by_groups",
    # 绘图
    "_set_cell",
    "_add_textbox",
    "_add_connector",
    "_draw_edge_label",
    "_draw_group_boundaries",
    "_draw_title_banner",
    "_format_node_label",
    "_apply_node_style",
    "_find_master_by_keyword",
    "_open_document",
    "_resolve_stencil_path",
    "_safe_output_path",
    # 核心操作
    "list_stencils",
    "list_masters",
    "draw_diagram",
    "draw_batch",
    "export_diagram",
    "update_diagram",
    "list_outputs",
    "delete_output",
]
