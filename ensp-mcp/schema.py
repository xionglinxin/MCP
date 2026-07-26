"""数据结构定义 — eNSP 拓扑和设备配置的 Pydantic v2 模型"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DeviceSpec(BaseModel):
    """eNSP 设备规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    id: str = Field(
        ...,
        description="设备唯一标识符（如 'R1', 'SW1', 'FW01'）",
        min_length=1,
        max_length=200,
    )
    name: str = Field(
        ...,
        description="设备显示名称（如 'Core-Switch-1', '边界路由器'）",
        min_length=1,
        max_length=200,
    )
    device_type: Literal[
        "AR_Router",
        "S_Switch",
        "CE_Switch",
        "USG_Firewall",
        "PC",
        "Server",
        "Cloud",
    ] = Field(
        ...,
        description="设备类型：AR 路由器、S 交换机、CE 数据中心交换机、USG 防火墙、PC、Server、Cloud",
    )
    model: str = Field(
        default="AR1220",
        description="设备型号（如 'AR1220', 'S5700', 'CE6800', 'USG6000V'）",
        max_length=100,
    )
    x: float | None = Field(
        default=None,
        description="拓扑图 X 坐标（像素）。None 表示未显式指定，由自动布局填充",
    )
    y: float | None = Field(
        default=None,
        description="拓扑图 Y 坐标（像素）。None 表示未显式指定，由自动布局填充",
    )
    config_script: str | None = Field(
        default=None,
        description="设备配置脚本（多行命令，\\n 分隔）",
    )


class LinkSpec(BaseModel):
    """eNSP 连接线规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    from_device: str = Field(
        ...,
        description="源设备 ID",
        min_length=1,
        max_length=200,
    )
    from_interface: str = Field(
        ...,
        description="源设备接口（如 'GE0/0/0', 'GE1/0/1'）",
        min_length=1,
        max_length=100,
    )
    to_device: str = Field(
        ...,
        description="目标设备 ID",
        min_length=1,
        max_length=200,
    )
    to_interface: str = Field(
        ...,
        description="目标设备接口（如 'GE0/0/1', 'GE1/0/2'）",
        min_length=1,
        max_length=100,
    )
    link_type: Literal["Ethernet", "Serial", "Console"] = Field(
        default="Ethernet",
        description="连接类型：以太网、串口、Console",
    )


class TopologySpec(BaseModel):
    """eNSP 拓扑规格"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    title: str = Field(
        ...,
        description="拓扑标题",
        min_length=1,
        max_length=500,
    )
    devices: list[DeviceSpec] = Field(
        ...,
        description="设备列表，至少包含 1 个设备",
        min_length=1,
        max_length=100,
    )
    links: list[LinkSpec] = Field(
        default_factory=list,
        description="连接线列表，可为空",
        max_length=300,
    )
    output_name: str = Field(
        default="topology",
        description="输出文件名（不含扩展名）。仅允许字母、数字、下划线、连字符和中文",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$",
    )
    auto_layout: bool = Field(
        default=True,
        description="是否自动布局设备位置",
    )


class ValidationResult(BaseModel):
    """拓扑验证结果"""

    model_config = ConfigDict(extra="forbid")

    ok: bool = Field(..., description="验证是否通过")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
