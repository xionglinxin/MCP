"""绘图辅助 + 核心绘图操作 — 节点放置、连接线、导出、增量编辑"""
from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from config import (
    DEFAULT_LINE_COLOR,
    DEFAULT_LINE_WEIGHT,
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    DEFAULT_SPACING_X,
    MAX_BATCH_SIZE,
    MAX_EDGES,
    MAX_NODES,
    OUTPUT_DIR,
    PAGE_MARGIN,
    STENCIL_DIR,
    get_zone_color,
)
from layout import (
    _auto_layout,
    _auto_page_size,
    _extract_groups,
)
from session import (
    VIS_FIXED_FORMAT_PDF,
    VIS_OPEN_HIDDEN,
    VIS_OPEN_RO,
    _visio_session,
    _with_timeout,
    get_session_manager,
)

logger = logging.getLogger(__name__)

# Visio LinePattern 映射
_LINE_PATTERN_MAP = {
    "solid": 1,
    "dashed": 2,
    "dotted": 3,
}

# 节点大小缩放因子
_SIZE_SCALE = {"small": 0.6, "medium": 1.0, "large": 1.4}


# ══════════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════════


@contextmanager
def _open_document(visio, path: Path, flags: int) -> Iterator:
    """打开文档的上下文管理器"""
    doc = None
    try:
        doc = visio.Documents.OpenEx(str(path), flags)
        yield doc
    finally:
        if doc is not None:
            try:
                doc.Close()
            except Exception as e:
                logger.debug("Error closing document: %s", e)


def _set_cell(shape, cell: str, formula: str) -> None:
    """设置 Visio ShapeSheet 单元格公式"""
    shape.CellsU(cell).FormulaU = formula


def _add_textbox(page, x1: float, y1: float, x2: float, y2: float,
                 text: str, size: int = 10, color: str = "RGB(0,0,0)") -> Any:
    """在页面上放置文本框"""
    shape = page.DrawRectangle(x1, y1, x2, y2)
    shape.Text = text
    _set_cell(shape, "FillPattern", "0")
    _set_cell(shape, "LinePattern", "0")
    _set_cell(shape, "Char.Size", f"{size} pt")
    _set_cell(shape, "Char.Color", color)
    return shape


def _find_master_by_keyword(stencil_doc, keyword: str):
    """根据关键词在 stencil 中查找 Master"""
    kw = keyword.lower().strip()
    for master in stencil_doc.Masters:
        if kw in master.NameU.strip().lower():
            return master
    names = [master.NameU for master in stencil_doc.Masters]
    raise ValueError(f"Master containing {keyword!r} not found. Available: {names}")


# ══════════════════════════════════════════════════════════
#  路径安全
# ══════════════════════════════════════════════════════════


def _contained_path(root: Path, candidate: Path) -> Path:
    """Resolve symlinks and compare path components, never string prefixes."""
    path = candidate.resolve()
    path.relative_to(root.resolve())
    return path


def _existing_file(root: Path, candidate: Path, suffixes: tuple[str, ...]) -> Path:
    path = _contained_path(root, candidate)
    if not path.is_file() or path.suffix.lower() not in suffixes:
        raise ValueError(f"Invalid file: {candidate}")
    return path


def _resolve_stencil_path(stencil: str) -> Path:
    return _existing_file(STENCIL_DIR, STENCIL_DIR / stencil, (".vss", ".vssx"))


def _safe_output_path(output_name: str, suffix: str) -> Path:
    """生成安全的输出文件路径（自动追加唯一 ID 防止覆盖）"""
    safe_name = "".join(
        c for c in output_name if c.isalnum() or c in ("_", "-", ".")
    ).strip()
    if not safe_name:
        safe_name = "diagram"
    file_id = uuid.uuid4().hex[:8]
    return _contained_path(OUTPUT_DIR, OUTPUT_DIR / f"{safe_name}_{file_id}.{suffix}")


# ══════════════════════════════════════════════════════════
#  绘图辅助
# ══════════════════════════════════════════════════════════


def _draw_group_boundaries(
    page,
    positions: dict[str, tuple[float, float]],
    groups: dict[str, list[str]],
) -> None:
    """绘制分组边框 — 使用区域配色、半透明填充、标签在框内顶部"""
    padding = 0.5
    label_height = 0.32

    for group_name, nids in groups.items():
        g_positions = [positions[nid] for nid in nids if nid in positions]
        if not g_positions:
            continue

        xs = [p[0] for p in g_positions]
        ys = [p[1] for p in g_positions]

        x1 = min(xs) - padding
        y1 = min(ys) - padding
        x2 = max(xs) + padding
        y2 = max(ys) + padding + label_height  # 向上扩展标签区域

        # 获取区域配色
        fill_color, border_color, label_color = get_zone_color(group_name)

        # 绘制区域矩形（包含标签区域）
        rect = page.DrawRectangle(x1, y1, x2, y2)
        rect.Text = ""
        _set_cell(rect, "FillForegnd", fill_color)
        _set_cell(rect, "FillPattern", "1")
        _set_cell(rect, "FillForegndTrans", "50%")
        _set_cell(rect, "LineColor", border_color)
        _set_cell(rect, "LineWeight", "1.5 pt")
        _set_cell(rect, "LinePattern", "1")  # solid
        _set_cell(rect, "Rounding", "0.15 in")  # 圆角
        try:
            rect.SendToBack()  # 区域背景沉底，让后续标签显示在上层
        except Exception as e:
            logger.debug("SendToBack failed for group rect '%s': %s", group_name, e)

        # 分组标签（框内顶部）
        title = page.DrawRectangle(
            x1 + 0.12, y2 - label_height - 0.04,
            x1 + 0.12 + len(group_name) * 0.22, y2 - 0.06,
        )
        title.Text = group_name
        _set_cell(title, "FillPattern", "0")
        _set_cell(title, "LinePattern", "0")
        _set_cell(title, "Char.Size", "12 pt")
        _set_cell(title, "Char.Style", "1")  # bold
        _set_cell(title, "Char.Color", label_color)
        _set_cell(title, "Para.HorzAlign", "0")  # left align
        try:
            title.SendToBack()
        except Exception as e:
            logger.debug("SendToBack failed for group label '%s': %s", group_name, e)


def _draw_title_banner(page, title: str, page_width: float) -> None:
    """在页面顶部绘制标题栏"""
    page_height = float(page.PageSheet.CellsU("PageHeight").ResultIU)

    # 标题区域
    x1 = PAGE_MARGIN
    y1 = page_height - 0.65
    x2 = page_width - PAGE_MARGIN
    y2 = page_height - 0.15

    banner = page.DrawRectangle(x1, y1, x2, y2)
    banner.Text = title
    _set_cell(banner, "FillPattern", "0")
    _set_cell(banner, "LinePattern", "0")
    _set_cell(banner, "Char.Size", "20 pt")
    _set_cell(banner, "Char.Style", "1")  # bold
    _set_cell(banner, "Char.Color", "RGB(40,40,40)")
    _set_cell(banner, "Para.HorzAlign", "1")  # center


def _format_node_label(shape) -> None:
    """配置节点文字块 — 标签下移至图标下方，防止与相邻图标重叠"""
    try:
        _set_cell(shape, "Char.Size", "9 pt")
        # 文字块宽度约束，让长标签自动换行而不水平溢出
        _set_cell(shape, "TxtWidth", "1.5 in")
        # 标签定位到图标下方（而非居中在图标上）
        _set_cell(shape, "TxtPinY", "Height*0.5 - 0.35 in")
        _set_cell(shape, "TxtPinX", "Width*0.5")
        _set_cell(shape, "VerticalAlign", "0")  # 顶部对齐（标签从偏移点向下展开）
        # 缩小文字块内边距
        _set_cell(shape, "LeftMargin", "0.02 in")
        _set_cell(shape, "RightMargin", "0.02 in")
        _set_cell(shape, "TopMargin", "0.01 in")
        _set_cell(shape, "BottomMargin", "0.01 in")
    except Exception as e:
        logger.debug("Failed to format node label: %s", e)


def _apply_node_style(shape, node: dict) -> None:
    """应用节点样式（颜色、大小）"""
    color = node.get("color")
    if color:
        try:
            _set_cell(shape, "FillForegnd", color)
            _set_cell(shape, "FillPattern", "1")
        except Exception as e:
            logger.debug("Failed to apply node color: %s", e)

    size = node.get("size")
    if size and size in _SIZE_SCALE:
        scale = _SIZE_SCALE[size]
        if scale != 1.0:
            try:
                current_w = float(shape.CellsU("Width").ResultIU)
                current_h = float(shape.CellsU("Height").ResultIU)
                _set_cell(shape, "Width", f"{current_w * scale} in")
                _set_cell(shape, "Height", f"{current_h * scale} in")
            except Exception as e:
                logger.debug("Failed to apply node size scale: %s", e)


def _add_connector(
    page,
    src_shape,
    dst_shape,
    style: str = "solid",
    color: str | None = None,
) -> Any:
    """在两个形状之间添加连接线"""
    connector = src_shape.AutoConnect(dst_shape, 0)
    if connector is None:
        return None

    try:
        _set_cell(connector, "LineWeight", DEFAULT_LINE_WEIGHT)

        # 线型
        pattern = _LINE_PATTERN_MAP.get(style, 1)
        _set_cell(connector, "LinePattern", str(pattern))

        # 颜色
        line_color = color if color else DEFAULT_LINE_COLOR
        _set_cell(connector, "LineColor", line_color)

        # 垂直距离大的连接用正交走线
        try:
            sy = float(src_shape.CellsU("PinY").ResultIU)
            dy = float(dst_shape.CellsU("PinY").ResultIU)
            if abs(sy - dy) > 2.0:
                _set_cell(connector, "ConLineRouteExt", "1")
        except Exception as e:
            logger.debug("Failed to set orthogonal routing: %s", e)
    except Exception as e:
        logger.debug("Failed to style connector: %s", e)

    return connector


def _draw_edge_label(
    page,
    positions: dict[str, tuple[float, float]],
    src_id: str,
    dst_id: str,
    label: str,
) -> None:
    """在两个节点的连线中点绘制一个独立的标签文本框"""
    if not label or src_id not in positions or dst_id not in positions:
        return

    sx, sy = positions[src_id]
    dx, dy = positions[dst_id]
    mx = (sx + dx) / 2
    my = (sy + dy) / 2 + 0.15  # 稍微上移避免被线遮挡

    tw = max(len(label) * 0.10 + 0.3, 0.7)
    th = 0.30

    lbl = page.DrawRectangle(mx - tw / 2, my - th / 2, mx + tw / 2, my + th / 2)
    lbl.Text = label
    _set_cell(lbl, "FillForegnd", "RGB(255,255,255)")
    _set_cell(lbl, "FillPattern", "1")
    _set_cell(lbl, "LineColor", "RGB(180,180,180)")
    _set_cell(lbl, "LineWeight", "0.5 pt")
    _set_cell(lbl, "Rounding", "0.05 in")
    _set_cell(lbl, "Char.Size", "8 pt")
    _set_cell(lbl, "Char.Color", "RGB(60,60,60)")
    _set_cell(lbl, "Para.HorzAlign", "1")
    _set_cell(lbl, "VerticalAlign", "1")
    _set_cell(lbl, "LeftMargin", "0.04 in")
    _set_cell(lbl, "RightMargin", "0.04 in")
    _set_cell(lbl, "TopMargin", "0.01 in")
    _set_cell(lbl, "BottomMargin", "0.01 in")


# ══════════════════════════════════════════════════════════
#  核心绘图操作
# ══════════════════════════════════════════════════════════


def list_stencils() -> dict:
    """列出可用的图标库文件（无需 Visio）"""
    files: list[str] = []
    for suffix in ("*.vss", "*.vssx"):
        files.extend(sorted(p.name for p in STENCIL_DIR.glob(suffix)
                            if p.is_file() and p.resolve().is_relative_to(STENCIL_DIR.resolve())))
    return {"ok": True, "stencils": sorted(set(files))}


def list_masters(stencil: str) -> dict:
    """列出图标库中的所有 Master 名称（优先使用缓存）"""
    try:
        mgr = get_session_manager()
        masters = mgr.get_stencil_masters_cached(stencil)
        return {"ok": True, "stencil": stencil, "masters": masters}
    except RuntimeError:
        # 回退：独立会话
        pass

    stencil_path = _resolve_stencil_path(stencil)
    try:
        with _visio_session() as visio:
            with _open_document(visio, stencil_path, VIS_OPEN_RO | VIS_OPEN_HIDDEN) as stencil_doc:
                masters = sorted(master.NameU for master in stencil_doc.Masters)
        return {"ok": True, "stencil": stencil, "masters": masters}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_diagram(spec: dict) -> dict:
    """根据规格绘制 Visio 图表"""
    stencil_path = _resolve_stencil_path(spec["stencil"])

    nodes: list[dict] = spec.get("nodes", [])
    edges: list[dict] = spec.get("edges", [])
    layout = spec.get("layout", {})
    direction = layout.get("direction", "LR")
    spacing_x = layout.get("spacing_x", DEFAULT_SPACING_X)
    spacing_y = layout.get("spacing_y", 1.8)
    orientation = layout.get("orientation", "vertical")
    show_groups = layout.get("show_groups", True)
    page_auto_size = layout.get("page_auto_size", True)

    # Bug fix 1e: return error dict instead of raising ValueError
    if len(nodes) > MAX_NODES:
        return {"ok": False, "error": f"Too many nodes: {len(nodes)} > {MAX_NODES}", "warnings": []}
    if len(edges) > MAX_EDGES:
        return {"ok": False, "error": f"Too many edges: {len(edges)} > {MAX_EDGES}", "warnings": []}

    def _do_draw():
        mgr = get_session_manager()
        visio = mgr.get()

        with _open_document(visio, stencil_path, VIS_OPEN_RO | VIS_OPEN_HIDDEN) as stencil_doc:
            doc = visio.Documents.Add("")
            try:
                page = visio.ActivePage
                page.Name = spec.get("title", "Diagram")

                # 计算布局
                positions = _auto_layout(
                    nodes, edges, direction, spacing_x, spacing_y, orientation,
                )

                # 页面自适应
                if page_auto_size:
                    pw, ph = _auto_page_size(positions)
                    page.PageSheet.CellsU("PageWidth").FormulaU = f"{pw} in"
                    page.PageSheet.CellsU("PageHeight").FormulaU = f"{ph} in"
                else:
                    pw = DEFAULT_PAGE_WIDTH
                    ph = DEFAULT_PAGE_HEIGHT

                # 绘制标题栏
                _draw_title_banner(page, spec.get("title", "Diagram"), pw)

                # 放置节点
                shape_map: dict[str, Any] = {}
                for node in nodes:
                    node_id = node["id"]
                    x = node.get("x")
                    y = node.get("y")
                    if x is None or y is None:
                        x, y = positions[node_id]

                    try:
                        master = stencil_doc.Masters.ItemU(node["master"])
                    except Exception:
                        raise ValueError(
                            f"图标 '{node['master']}' 在图标库中不存在。"
                            f"请使用 visio_list_masters 查看可用图标名称。"
                        )

                    shape = page.Drop(master, x, y)
                    # 多行标签合并为单行，避免文本块过高与图标重叠
                    shape.Text = node["label"].replace("\n", " ")
                    # Bug fix 1d: set shape name to node ID for incremental editing
                    try:
                        shape.NameU = node_id
                    except Exception as e:
                        logger.debug("Failed to set shape NameU for '%s': %s", node_id, e)
                    _apply_node_style(shape, node)
                    _format_node_label(shape)
                    shape_map[node_id] = shape

                # 绘制分组边框
                if show_groups:
                    groups = _extract_groups(nodes)
                    if groups:
                        _draw_group_boundaries(page, positions, groups)

                # 连接节点（先画线，再画标签，确保标签在最上层）
                for edge in edges:
                    source_id = edge["from"]
                    target_id = edge["to"]
                    if source_id not in shape_map:
                        raise ValueError(f"连接线的源节点不存在: {source_id}")
                    if target_id not in shape_map:
                        raise ValueError(f"连接线的目标节点不存在: {target_id}")

                    _add_connector(
                        page,
                        shape_map[source_id],
                        shape_map[target_id],
                        edge.get("style", "solid"),
                        edge.get("color"),
                    )

                # 最后绘制连接线标签（独立文本框，确保在所有形状之上）
                for edge in edges:
                    label = edge.get("label", "")
                    if label:
                        _draw_edge_label(
                            page, positions,
                            edge["from"], edge["to"], label,
                        )

                # 保存
                output_path = _safe_output_path(
                    spec.get("output_name", "diagram"), "vsdx"
                )
                doc.SaveAs(str(output_path))
                return {"ok": True, "file": str(output_path), "warnings": []}

            finally:
                doc.Close()

    try:
        return _with_timeout(_do_draw)
    except TimeoutError as e:
        get_session_manager().reset()
        return {"ok": False, "error": str(e), "warnings": []}
    except Exception as e:
        return {"ok": False, "error": str(e), "warnings": []}


def draw_batch(specs: list[dict]) -> dict:
    """批量生成多个图表 — 复用同一 Visio 会话"""
    if len(specs) > MAX_BATCH_SIZE:
        return {"ok": False, "error": f"批量数量超限: {len(specs)} > {MAX_BATCH_SIZE}"}

    results: list[dict] = []
    for i, spec in enumerate(specs):
        result = draw_diagram(spec)
        results.append({
            "index": i,
            "title": spec.get("title", f"diagram_{i}"),
            **result,
        })

    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "ok": ok_count > 0,
        "results": results,
        "success": ok_count,
        "failed": len(results) - ok_count,
    }


def export_diagram(input_file: str, format: str = "png") -> dict:
    """导出 Visio 图表为图片或 PDF"""
    if format not in ("png", "pdf", "svg"):
        return {"ok": False, "error": f"Unsupported format: {format!r}. Use 'png', 'pdf', or 'svg'."}

    try:
        input_path = _existing_file(OUTPUT_DIR, Path(input_file), (".vsdx",))
        output_path = _contained_path(OUTPUT_DIR, input_path.with_suffix(f".{format}"))
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}

    def _do_export():
        mgr = get_session_manager()
        visio = mgr.get()
        doc = visio.Documents.Open(str(input_path))
        try:
            page = visio.ActivePage
            if format == "pdf":
                doc.ExportAsFixedFormat(VIS_FIXED_FORMAT_PDF, str(output_path), 1, 0)
            elif format == "svg":
                # Visio 原生支持 SVG 导出
                page.Export(str(output_path))
            else:
                page.Export(str(output_path))

            if not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError(f"Export did not create a valid {format.upper()} file")
        finally:
            doc.Close()

    try:
        _with_timeout(_do_export)
        return {"ok": True, "file": str(output_path)}
    except TimeoutError as e:
        get_session_manager().reset()
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════
#  增量编辑
# ══════════════════════════════════════════════════════════


def update_diagram(edit_spec: dict) -> dict:
    """增量编辑已有 .vsdx 文件"""
    input_file = edit_spec["input_file"]
    try:
        input_path = _existing_file(OUTPUT_DIR, Path(input_file), (".vsdx",))
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e), "warnings": []}

    add_nodes: list[dict] = edit_spec.get("add_nodes", [])
    add_edges: list[dict] = edit_spec.get("add_edges", [])
    remove_nodes: list[str] = edit_spec.get("remove_nodes", [])
    update_nodes: list[dict] = edit_spec.get("update_nodes", [])

    def _do_update():
        mgr = get_session_manager()
        visio = mgr.get()
        doc = visio.Documents.Open(str(input_path))
        try:
            page = visio.ActivePage
            shape_map: dict[str, Any] = {}

            # 建立已有形状索引（通过 NameU/Name 字段匹配 id）
            for shape in page.Shapes:
                try:
                    name = shape.NameU
                    if name and not name.startswith("."):
                        shape_map[name] = shape
                except Exception:
                    try:
                        name = shape.Name
                        if name and not name.startswith("."):
                            shape_map[name] = shape
                    except Exception as e:
                        logger.debug("Failed to read shape name: %s", e)

            # 删除节点（级联删除关联边）
            removed_ids = set(remove_nodes)
            for nid in remove_nodes:
                if nid in shape_map:
                    try:
                        shape_map[nid].Delete()
                        del shape_map[nid]
                    except Exception as e:
                        logger.debug("Failed to delete shape '%s': %s", nid, e)

            # 修改节点
            for upd in update_nodes:
                nid = upd["id"]
                if nid in shape_map:
                    shape = shape_map[nid]
                    if upd.get("label"):
                        shape.Text = upd["label"]
                    if upd.get("color"):
                        try:
                            _set_cell(shape, "FillForegnd", upd["color"])
                            _set_cell(shape, "FillPattern", "1")
                        except Exception as e:
                            logger.debug("Failed to update color for '%s': %s", nid, e)

            # 添加节点（放在页面空白区域）
            existing_xs = [s.CellsU("PinX").ResultIU / 72.0 for s in shape_map.values()]
            max_x = max(existing_xs) if existing_xs else 2.0
            new_x = max_x + DEFAULT_SPACING_X

            for i, node in enumerate(add_nodes):
                x = node.get("x", new_x + i * DEFAULT_SPACING_X)
                y = node.get("y", 4.0)

                # 需要在 stencil 中找 master
                try:
                    master = None
                    for st_doc in visio.Documents:
                        try:
                            master = st_doc.Masters.ItemU(node["master"])
                            break
                        except Exception:
                            continue

                    if master is None:
                        # 回退：画一个矩形代替
                        shape = page.DrawRectangle(x - 0.5, y - 0.3, x + 0.5, y + 0.3)
                    else:
                        shape = page.Drop(master, x, y)

                    shape.Text = node["label"]
                    shape.NameU = node["id"]
                    _apply_node_style(shape, node)
                    shape_map[node["id"]] = shape
                except Exception as e:
                    logger.debug("Failed to add node '%s': %s", node.get("id", "?"), e)

            # 添加连接
            for edge in add_edges:
                src_id = edge["from"]
                dst_id = edge["to"]
                if src_id in removed_ids or dst_id in removed_ids:
                    continue
                if src_id in shape_map and dst_id in shape_map:
                    # Bug fix 1a: correct parameter order — style then color
                    _add_connector(
                        page,
                        shape_map[src_id],
                        shape_map[dst_id],
                        edge.get("style", "solid"),
                        edge.get("color"),
                    )

            doc.Save()
            return {"ok": True, "file": str(input_path), "warnings": []}

        finally:
            doc.Close()

    try:
        return _with_timeout(_do_update)
    except TimeoutError as e:
        get_session_manager().reset()
        return {"ok": False, "error": str(e), "warnings": []}
    except Exception as e:
        return {"ok": False, "error": str(e), "warnings": []}


# ══════════════════════════════════════════════════════════
#  文件管理
# ══════════════════════════════════════════════════════════


def list_outputs() -> dict:
    """列出 outputs 目录中的所有文件"""
    files = []
    for p in sorted((f for f in OUTPUT_DIR.glob("*") if f.is_file()
                     and f.resolve().is_relative_to(OUTPUT_DIR.resolve())),
                    key=lambda f: f.stat().st_mtime, reverse=True):
        if p.resolve().is_relative_to(OUTPUT_DIR.resolve()) and p.is_file() and p.suffix.lower() in (".vsdx", ".png", ".pdf", ".svg"):
            stat = p.stat()
            files.append({
                "name": p.name,
                "path": str(p),
                "size_kb": round(stat.st_size / 1024, 1),
                "format": p.suffix.lstrip("."),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return {"ok": True, "files": files, "total": len(files)}


def delete_output(filename: str) -> dict:
    """安全删除输出文件（移到回收站）"""
    if not filename or any(c in filename for c in ("/", "\\", ":", "\x00")) or filename in (".", ".."):
        return {"ok": False, "error": "Expected a plain output filename"}
    try:
        target = _existing_file(OUTPUT_DIR, OUTPUT_DIR / filename, (".vsdx", ".png", ".pdf", ".svg"))
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}

    # Windows 回收站
    try:
        import subprocess
        quoted_target = str(target).replace("'", "''")
        ps_cmd = (
            f"Add-Type -AssemblyName Microsoft.VisualBasic; "
            f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
            f"'{quoted_target}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
        )
        subprocess.run(
            ["powershell.exe", "-Command", ps_cmd],
            capture_output=True, check=True, timeout=10,
        )
        # 验证
        if target.exists():
            return {"ok": False, "error": "File still exists after recycle attempt"}
        return {"ok": True, "message": f"已移到回收站: {filename}"}
    except Exception as e:
        logger.debug("Recycle bin failed, falling back to .trash: %s", e)
        # 回退：移到 .trash 目录
        try:
            trash_dir = _contained_path(OUTPUT_DIR, OUTPUT_DIR / ".trash")
            trash_dir.mkdir(exist_ok=True)
            dest = _contained_path(OUTPUT_DIR, trash_dir / f"{uuid.uuid4().hex}_{filename}")
            target.rename(dest)
            return {"ok": True, "message": f"已移到 {dest}（回收站不可用）"}
        except Exception as e2:
            return {"ok": False, "error": f"Delete failed: {e2}"}
