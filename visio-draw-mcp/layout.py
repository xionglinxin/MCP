"""布局引擎 — 自动布局、Kahn 拓扑排序、页面尺寸计算"""
from __future__ import annotations

from collections import defaultdict, deque

from config import (
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    DEFAULT_SPACING_X,
    DEFAULT_SPACING_Y,
    PAGE_MARGIN,
)


def _topological_layers(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """用 Kahn 算法对有向图做拓扑排序，返回 {node_id: layer_index}。

    对于非 DAG 的部分（环），将剩余节点放到最后一层。
    """
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}

    for e in edges:
        src, dst = e["from"], e["to"]
        if src in in_degree and dst in in_degree:
            adj[src].append(dst)
            in_degree[dst] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    layers: dict[str, int] = {}
    current_layer = 0

    while queue:
        next_queue: deque[str] = deque()
        for nid in queue:
            layers[nid] = current_layer
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)
        queue = next_queue
        current_layer += 1

    # 处理环中的节点（未被拓扑排序覆盖的）
    for nid in in_degree:
        if nid not in layers:
            layers[nid] = current_layer

    return layers


def _auto_layout(
    nodes: list[dict],
    edges: list[dict],
    direction: str = "LR",
    spacing_x: float = DEFAULT_SPACING_X,
    spacing_y: float = DEFAULT_SPACING_Y,
    orientation: str = "vertical",
) -> dict[str, tuple[float, float]]:
    """自动计算节点位置 — 支持 4 种布局策略。

    Args:
        nodes: 节点列表，每项含 id, 可选 group
        edges: 边列表，每项含 from, to
        direction: LR | TB | GRID | LAYERED
        spacing_x: 水平间距
        spacing_y: 垂直间距
        orientation: vertical=上→下 | horizontal=左→右（仅 LAYERED 生效）

    Returns:
        {node_id: (x, y)}
    """
    positions: dict[str, tuple[float, float]] = {}
    start_x = PAGE_MARGIN + 1.5
    start_y = DEFAULT_PAGE_HEIGHT - PAGE_MARGIN - 1.5  # 留足标题栏空间

    if direction == "LAYERED":
        positions = _layout_layered(
            nodes, edges, start_x, start_y, spacing_x, spacing_y, orientation,
        )
    elif direction == "TB":
        for index, node in enumerate(nodes):
            positions[node["id"]] = (start_x, start_y - index * spacing_y)
    elif direction == "GRID":
        cols = max(1, min(4, len(nodes)))
        for index, node in enumerate(nodes):
            row = index // cols
            col = index % cols
            positions[node["id"]] = (
                start_x + col * spacing_x,
                start_y - row * spacing_y,
            )
    else:  # LR (默认)
        for index, node in enumerate(nodes):
            positions[node["id"]] = (start_x + index * spacing_x, start_y)

    # 如果有 group 字段，按组重排（非 LAYERED 模式时）
    groups = _extract_groups(nodes)
    if groups and direction not in ("LAYERED",):
        positions = _rearrange_by_groups(positions, nodes, groups, start_x, start_y, spacing_x, spacing_y)

    return positions


def _layout_layered(
    nodes: list[dict],
    edges: list[dict],
    start_x: float,
    start_y: float,
    spacing_x: float,
    spacing_y: float,
    orientation: str = "vertical",
) -> dict[str, tuple[float, float]]:
    """分组感知的分层拓扑布局。

    vertical 模式（网络拓扑推荐）:
    - 拓扑层级沿 Y 轴从上到下排列（出口在最上面）
    - 同一层级的不同分组水平并排
    - 组内节点水平展开

    horizontal 模式:
    - 拓扑层级沿 X 轴从左到右
    - 同层节点垂直居中
    """
    layers = _topological_layers(nodes, edges)
    groups = _extract_groups(nodes)
    node_group = {n["id"]: n.get("group", "") for n in nodes}

    if orientation == "vertical":
        return _layout_layered_vertical(
            nodes, edges, layers, groups, node_group,
            start_x, start_y, spacing_x, spacing_y,
        )
    else:
        return _layout_layered_horizontal(
            nodes, layers, start_x, start_y, spacing_x, spacing_y,
        )


def _layout_layered_vertical(
    nodes: list[dict],
    edges: list[dict],
    layers: dict[str, int],
    groups: dict[str, list[str]],
    node_group: dict[str, str],
    start_x: float,
    start_y: float,
    spacing_x: float,
    spacing_y: float,
) -> dict[str, tuple[float, float]]:
    """垂直分层布局 — 组间分层 + 组内子层级。

    改进点：
    - 同一 group 取最小拓扑 tier 作为组层级
    - 组内根据内部边的拓扑关系分子层级（如 汇聚→接入→终端）
    - 子层级之间纵向展开，连接线和标签不再挤成一团
    - 每层相对最宽层水平居中
    """
    # ── 1. 组层级（同前） ──
    group_tier: dict[str, int] = {}
    for g_name, g_nids in groups.items():
        group_tier[g_name] = min(layers.get(nid, 0) for nid in g_nids)

    grouped_ids: set[str] = set()
    for g_nids in groups.values():
        grouped_ids.update(g_nids)
    ungrouped_tiers: dict[str, int] = {}
    for node in nodes:
        nid = node["id"]
        if nid not in grouped_ids:
            ungrouped_tiers[nid] = layers.get(nid, 0)

    group_order = list(groups.keys())
    sorted_groups = sorted(group_order, key=lambda g: (group_tier[g], group_order.index(g)))

    tier_groups: dict[int, list[str]] = defaultdict(list)
    for g in sorted_groups:
        tier_groups[group_tier[g]].append(g)
    for nid, tier in ungrouped_tiers.items():
        tier_groups[tier]
    sorted_tiers = sorted(tier_groups.keys())

    # ── 2. 组内子层级（Kahn on internal edges） ──
    group_sub: dict[str, tuple[dict[str, int], int]] = {}
    for g_name, g_nids in groups.items():
        nid_set = set(g_nids)
        # 识别接收外部边的节点（对等设备标识）
        ext_recv: set[str] = set()
        for e in edges:
            if e["to"] in nid_set and e["from"] not in nid_set:
                ext_recv.add(e["to"])

        # 构建组内 DAG — 过滤对等连接（两端都接收外部边的是对等关系）
        adj: dict[str, list[str]] = defaultdict(list)
        in_deg: dict[str, int] = {nid: 0 for nid in g_nids}
        for e in edges:
            if e["from"] in nid_set and e["to"] in nid_set:
                if e["from"] in ext_recv and e["to"] in ext_recv:
                    continue  # 对等连接（如冗余核心交换机 CSS 互联）
                adj[e["from"]].append(e["to"])
                in_deg[e["to"]] += 1

        q = deque(nid for nid, d in in_deg.items() if d == 0)
        sub: dict[str, int] = {}
        sl = 0
        while q:
            nxt: deque[str] = deque()
            for nid in q:
                sub[nid] = sl
                for nb in adj[nid]:
                    in_deg[nb] -= 1
                    if in_deg[nb] == 0:
                        nxt.append(nb)
            q = nxt
            sl += 1
        for nid in g_nids:
            if nid not in sub:
                sub[nid] = 0

        sub_layers: dict[int, list[str]] = defaultdict(list)
        for nid, ssl in sub.items():
            sub_layers[ssl].append(nid)
        node_idx = {n["id"]: i for i, n in enumerate(nodes)}
        for ssl in sub_layers:
            sub_layers[ssl].sort(key=lambda nid: node_idx.get(nid, 0))

        group_sub[g_name] = (sub_layers, max(sub_layers.keys()) + 1 if sub_layers else 1)

    # ── 3. 间距参数 ──
    node_gap_x = spacing_x * 1.3
    zone_gap_x = spacing_x * 1.5
    sub_tier_gap_y = spacing_y * 0.35

    # ── 4. 计算每层宽度 + 最大内部深度 ──
    tier_widths: dict[int, float] = {}
    for tier in sorted_tiers:
        g_names = tier_groups[tier]
        total_w = 0.0
        for gi, g in enumerate(g_names):
            sub_layers, depth = group_sub[g]
            max_sw = max(
                ((len(sub_layers.get(ssl, [])) - 1) * node_gap_x
                 for ssl in range(depth)),
                default=0,
            )
            if gi > 0:
                total_w += zone_gap_x
            total_w += max_sw
        ug = [nid for nid, t in ungrouped_tiers.items() if t == tier]
        if ug:
            if total_w > 0:
                total_w += zone_gap_x
            total_w += (len(ug) - 1) * node_gap_x
        tier_widths[tier] = total_w

    max_width = max(tier_widths.values()) if tier_widths else 0

    # ── 5. 放置节点 ──
    positions: dict[str, tuple[float, float]] = {}
    tier_gap_y = spacing_y * 1.0
    current_y = start_y

    for tier in sorted_tiers:
        g_names = tier_groups[tier]
        total_w = tier_widths[tier]
        current_x = start_x + (max_width - total_w) / 2

        for g in g_names:
            sub_layers, depth = group_sub[g]
            zone_w = max(
                ((len(sub_layers.get(ssl, [])) - 1) * node_gap_x
                 for ssl in range(depth)),
                default=0,
            )

            for ssl in range(depth):
                ssl_nids = sub_layers.get(ssl, [])
                ssl_w = (len(ssl_nids) - 1) * node_gap_x
                ssl_x = current_x + (zone_w - ssl_w) / 2
                for i, nid in enumerate(ssl_nids):
                    positions[nid] = (ssl_x + i * node_gap_x, current_y - ssl * sub_tier_gap_y)

            current_x += zone_w + zone_gap_x

        ug = [nid for nid, t in ungrouped_tiers.items() if t == tier]
        if ug:
            for i, nid in enumerate(ug):
                positions[nid] = (current_x + i * node_gap_x, current_y)

        current_y -= tier_gap_y

    return positions


def _layout_layered_horizontal(
    nodes: list[dict],
    layers: dict[str, int],
    start_x: float,
    start_y: float,
    spacing_x: float,
    spacing_y: float,
) -> dict[str, tuple[float, float]]:
    """水平分层布局（原始模式）— 层级沿 X 轴从左到右。"""
    layer_nodes: dict[int, list[str]] = defaultdict(list)
    for nid, layer_idx in layers.items():
        layer_nodes[layer_idx].append(nid)

    node_order = {n["id"]: i for i, n in enumerate(nodes)}
    for layer_idx in layer_nodes:
        layer_nodes[layer_idx].sort(key=lambda nid: node_order.get(nid, 0))

    positions: dict[str, tuple[float, float]] = {}

    for layer_idx, nids in sorted(layer_nodes.items()):
        x = start_x + layer_idx * spacing_x
        total_height = (len(nids) - 1) * spacing_y
        y_start = start_y - total_height / 2

        for i, nid in enumerate(nids):
            positions[nid] = (x, y_start + i * spacing_y)

    return positions


def _extract_groups(nodes: list[dict]) -> dict[str, list[str]]:
    """提取分组信息: {group_name: [node_id, ...]}"""
    groups: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        g = node.get("group")
        if g:
            groups[g].append(node["id"])
    return dict(groups)


def _rearrange_by_groups(
    positions: dict[str, tuple[float, float]],
    nodes: list[dict],
    groups: dict[str, list[str]],
    start_x: float,
    start_y: float,
    spacing_x: float,
    spacing_y: float,
) -> dict[str, tuple[float, float]]:
    """按分组重新排列节点位置 — 同组节点聚拢在一起。"""
    result: dict[str, tuple[float, float]] = {}
    grouped_ids: set[str] = set()
    for nids in groups.values():
        grouped_ids.update(nids)

    ungrouped = [n["id"] for n in nodes if n["id"] not in grouped_ids]

    # 按组排列
    group_offset_x = start_x
    group_order = list(groups.keys())

    for g_name in group_order:
        g_nids = groups[g_name]
        for i, nid in enumerate(g_nids):
            result[nid] = (group_offset_x + i * spacing_x * 0.5, start_y)
        group_offset_x += len(g_nids) * spacing_x * 0.5 + spacing_x * 0.5

    # 未分组节点排在最后
    for i, nid in enumerate(ungrouped):
        result[nid] = (group_offset_x + i * spacing_x, start_y)

    return result


def _compute_bounding_box(
    positions: dict[str, tuple[float, float]],
    margin: float = PAGE_MARGIN,
) -> tuple[float, float, float, float]:
    """计算所有节点的边界框 (min_x, min_y, max_x, max_y)"""
    if not positions:
        return (margin, margin, DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT)
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    return (
        min(xs) - margin,
        min(ys) - margin,
        max(xs) + margin + 1.0,  # 右侧留空给节点宽度
        max(ys) + margin + 0.5,  # 上方留空
    )


def _auto_page_size(
    positions: dict[str, tuple[float, float]],
) -> tuple[float, float]:
    """根据节点位置计算合适的页面大小"""
    min_x, min_y, max_x, max_y = _compute_bounding_box(positions)
    width = max(DEFAULT_PAGE_WIDTH, max_x - min_x + 2 * PAGE_MARGIN)
    height = max(DEFAULT_PAGE_HEIGHT, max_y - min_y + 2 * PAGE_MARGIN)
    return (round(width, 2), round(height, 2))
