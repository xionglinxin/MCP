"""数据结构定义 — Pydantic v2 模型"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── 节点 & 边 & 布局 ──────────────────────────────────────


class NodeSpec(BaseModel):
    """Visio 节点规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    id: str = Field(
        ...,
        description="节点唯一标识符（如 'firewall_01', 'core_switch'）",
        min_length=1,
        max_length=200,
    )
    label: str = Field(
        ...,
        description="节点显示文本，支持 \\n 换行（如 '主防火墙\\nNGFW-HA'）",
        min_length=1,
        max_length=500,
    )
    master: str = Field(
        ...,
        description="stencil 中的 Master 图标名称（精确匹配，区分大小写）。"
        "先用 visio_list_masters 获取可用图标名称。",
        min_length=1,
        max_length=500,
    )
    group: str | None = Field(
        default=None,
        description="可选分组名称。同 group 的节点会被聚拢在一起并绘制分组边框。",
    )
    x: float | None = Field(
        default=None,
        description="手动指定 X 坐标（英寸），不指定时自动布局",
    )
    y: float | None = Field(
        default=None,
        description="手动指定 Y 坐标（英寸），不指定时自动布局",
    )
    color: str | None = Field(
        default=None,
        description="节点填充颜色，Visio 公式格式（如 'RGB(200,50,50)'）。不指定则使用 Master 默认颜色。",
    )
    size: Literal["small", "medium", "large"] | None = Field(
        default=None,
        description="节点大小：small=0.6x, medium=1.0x（默认）, large=1.4x",
    )


class EdgeSpec(BaseModel):
    """Visio 连接线规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    from_: str = Field(
        ...,
        alias="from",
        description="连接线起点节点 ID",
        min_length=1,
        max_length=200,
    )
    to: str = Field(
        ...,
        description="连接线终点节点 ID",
        min_length=1,
        max_length=200,
    )
    label: str | None = Field(
        default=None,
        description="连接线标签文本（如 'HTTP API', '主链路'）",
        max_length=500,
    )
    style: Literal["solid", "dashed", "dotted"] = Field(
        default="solid",
        description="连接线样式：solid=实线, dashed=虚线, dotted=点线",
    )
    color: str | None = Field(
        default=None,
        description="连接线颜色，Visio 公式格式（如 'RGB(200,50,50)'）。不指定则使用默认灰色。",
    )


class LayoutSpec(BaseModel):
    """布局配置"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    direction: Literal["LR", "TB", "GRID", "LAYERED"] = Field(
        default="LR",
        description="布局方向: LR=从左到右, TB=从上到下, GRID=网格（4列）, "
        "LAYERED=分层拓扑（推荐用于网络拓扑和架构图，自动按层级排列）",
    )
    orientation: Literal["vertical", "horizontal"] = Field(
        default="vertical",
        description="LAYERED 模式下的排列方向: vertical=上→下（网络拓扑推荐）, "
        "horizontal=左→右。仅 direction=LAYERED 时生效。",
    )
    spacing_x: float = Field(
        default=2.5,
        description="节点间水平间距（英寸），默认 2.5",
        gt=0.5,
        le=10.0,
    )
    spacing_y: float = Field(
        default=1.8,
        description="节点间垂直间距（英寸），默认 1.8",
        gt=0.5,
        le=10.0,
    )
    show_groups: bool = Field(
        default=True,
        description="是否绘制分组边框（当节点有 group 字段时生效）",
    )
    page_auto_size: bool = Field(
        default=True,
        description="是否根据内容自动调整页面大小（推荐开启）",
    )


class DiagramSpec(BaseModel):
    """完整的 Visio 图表规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    title: str = Field(
        ...,
        description="图表标题（显示在 Visio 页面标签上）",
        min_length=1,
        max_length=500,
    )
    stencil: str = Field(
        ...,
        description="图标库文件名（如 '企业网络产品 安全(VSS,蓝).vss'）。"
        "先用 visio_list_stencils 获取可用文件。",
        min_length=1,
        max_length=500,
    )
    nodes: list[NodeSpec] = Field(
        ...,
        description="节点列表，至少包含 1 个节点",
        min_length=1,
        max_length=100,
    )
    edges: list[EdgeSpec] = Field(
        default_factory=list,
        description="连接线列表，可为空（仅放置节点）",
        max_length=300,
    )
    layout: LayoutSpec = Field(
        default_factory=LayoutSpec,
        description="布局配置，默认从左到右自动布局。"
        "推荐网络拓扑使用 LAYERED 方向。",
    )
    output_name: str = Field(
        default="diagram",
        description="输出文件名（不含扩展名），如 'enterprise_topology'",
        min_length=1,
        max_length=200,
    )


# ── 编辑操作 ──────────────────────────────────────────────


class NodeUpdate(BaseModel):
    """节点更新规格"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(..., description="要修改的节点 ID", min_length=1)
    label: str | None = Field(default=None, description="新标签文本")
    color: str | None = Field(default=None, description="新填充颜色")


class EditSpec(BaseModel):
    """增量编辑规格 — 对已有 .vsdx 文件做增删改"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    input_file: str = Field(
        ...,
        description="要编辑的 .vsdx 文件路径（从 visio_draw_diagram 返回值获取）",
        min_length=1,
    )
    add_nodes: list[NodeSpec] = Field(
        default_factory=list,
        description="要添加的新节点列表",
    )
    add_edges: list[EdgeSpec] = Field(
        default_factory=list,
        description="要添加的新连接线列表",
    )
    remove_nodes: list[str] = Field(
        default_factory=list,
        description="要删除的节点 ID 列表（级联删除关联边）",
    )
    update_nodes: list[NodeUpdate] = Field(
        default_factory=list,
        description="要修改的节点属性列表",
    )


# ── 批量生成 ──────────────────────────────────────────────


class BatchSpec(BaseModel):
    """批量生成规格"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    diagrams: list[DiagramSpec] = Field(
        ...,
        description="图表规格列表，最多 10 个",
        min_length=1,
        max_length=10,
    )


# ── 响应模型 ──────────────────────────────────────────────


class StencilInfo(BaseModel):
    """图标库信息"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="操作是否成功")
    stencil: str | None = Field(default=None, description="图标库文件名")
    masters: list[str] = Field(default_factory=list, description="Master 图标名称列表")
    error: str | None = Field(default=None, description="错误信息（仅失败时）")


class DrawResult(BaseModel):
    """绘图操作结果"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="操作是否成功")
    file: str | None = Field(default=None, description="生成的 .vsdx 文件路径")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
    error: str | None = Field(default=None, description="错误信息（仅失败时）")


class ExportResult(BaseModel):
    """导出操作结果"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="操作是否成功")
    file: str | None = Field(default=None, description="导出的文件路径")
    error: str | None = Field(default=None, description="错误信息（仅失败时）")


class ValidationResult(BaseModel):
    """规格验证结果"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="验证是否通过")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")


class OutputFileInfo(BaseModel):
    """输出文件信息"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="文件名")
    path: str = Field(..., description="完整路径")
    size_kb: float = Field(..., description="文件大小（KB）")
    format: str = Field(..., description="文件格式（vsdx/png/pdf）")
    created: str = Field(..., description="创建时间")


class OutputListResult(BaseModel):
    """输出文件列表结果"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="操作是否成功")
    files: list[OutputFileInfo] = Field(default_factory=list, description="文件列表")
    total: int = Field(default=0, description="文件总数")
    error: str | None = Field(default=None, description="错误信息")
