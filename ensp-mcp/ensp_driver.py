"""eNSP 拓扑生成驱动 — 生成 .topo 文件和设备配置脚本"""

import xml.etree.ElementTree as ET
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from config import (
    DEVICE_TYPE_IDS,
    LAYOUT_CONFIG,
    OUTPUT_DIR,
    TEMPLATE_DIR,
)
from schema import TopologySpec, DeviceSpec


def auto_layout_devices(devices: list[DeviceSpec]) -> list[DeviceSpec]:
    """自动布局设备位置（网格布局）

    仅对未显式指定坐标（x 或 y 为 None）的设备填充网格位置；
    显式设置在原点的设备（x=0, y=0）将被保留。
    """
    grid_cols = LAYOUT_CONFIG["grid_cols"]
    spacing_x = LAYOUT_CONFIG["device_spacing_x"]
    spacing_y = LAYOUT_CONFIG["device_spacing_y"]
    start_x = LAYOUT_CONFIG["start_x"]
    start_y = LAYOUT_CONFIG["start_y"]

    for idx, device in enumerate(devices):
        if device.x is None or device.y is None:
            row = idx // grid_cols
            col = idx % grid_cols
            if device.x is None:
                device.x = float(start_x + col * spacing_x)
            if device.y is None:
                device.y = float(start_y + row * spacing_y)

    return devices


def generate_topo_xml(spec: TopologySpec) -> tuple[str, list[str]]:
    """生成 eNSP .topo XML 文件内容

    Returns:
        (xml_text, warnings): XML 字符串及生成过程中的警告列表
        （例如引用了不存在设备的连接线会被跳过并记录警告）。
    """
    warnings: list[str] = []

    root = ET.Element("topo")
    root.set("version", "1.3.00.100")

    # 基本信息
    info = ET.SubElement(root, "info")
    ET.SubElement(info, "name").text = spec.title
    ET.SubElement(info, "author").text = "Claude Code"
    ET.SubElement(info, "date").text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 设备列表
    devices_elem = ET.SubElement(root, "devices")
    device_map: dict[str, str] = {}

    for idx, device in enumerate(spec.devices):
        dev_elem = ET.SubElement(devices_elem, "device")
        dev_elem.set("id", str(idx))
        dev_elem.set("name", device.name)
        dev_elem.set("type", DEVICE_TYPE_IDS.get(device.device_type, "1"))
        dev_elem.set("model", device.model)
        dev_elem.set("x", str(int(device.x if device.x is not None else 0)))
        dev_elem.set("y", str(int(device.y if device.y is not None else 0)))

        device_map[device.id] = str(idx)

    # 连接线列表
    links_elem = ET.SubElement(root, "links")
    link_idx = 0

    for link in spec.links:
        src_device_id = device_map.get(link.from_device)
        dst_device_id = device_map.get(link.to_device)

        if src_device_id is None or dst_device_id is None:
            missing = []
            if src_device_id is None:
                missing.append(f"源设备 '{link.from_device}'")
            if dst_device_id is None:
                missing.append(f"目标设备 '{link.to_device}'")
            warnings.append(
                f"跳过连接线 {link.from_device}({link.from_interface}) -> "
                f"{link.to_device}({link.to_interface})：找不到{'、'.join(missing)}"
            )
            continue

        link_elem = ET.SubElement(links_elem, "link")
        link_elem.set("id", str(link_idx))
        link_elem.set("src_dev", src_device_id)
        link_elem.set("src_if", link.from_interface)
        link_elem.set("dst_dev", dst_device_id)
        link_elem.set("dst_if", link.to_interface)
        link_elem.set("link_type", link.link_type)
        link_idx += 1

    # 格式化输出（XML 声明 + 缩进）
    ET.indent(root, space="  ")
    xml_body = ET.tostring(root, encoding="unicode", method="xml")
    xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body
    return xml_text, warnings


def generate_config_scripts(spec: TopologySpec) -> dict[str, str]:
    """生成设备配置脚本"""
    configs = {}

    for device in spec.devices:
        if device.config_script:
            # 添加标准头部和尾部
            script = f"""# {device.name} ({device.model}) 配置脚本
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

system-view
sysname {device.name}

{device.config_script}

quit
save
"""
            configs[device.id] = script

    return configs


def save_configs(configs: dict[str, str], output_name: str, output_dir: Path = OUTPUT_DIR) -> list[str]:
    """保存配置脚本到文件"""
    saved_files = []

    for device_id, config in configs.items():
        filename = f"{output_name}_{device_id}_config.txt"
        filepath = output_dir / filename
        filepath.write_text(config, encoding="utf-8")
        saved_files.append(str(filepath))

    return saved_files


def validate_topology(spec: TopologySpec) -> dict[str, Any]:
    """验证拓扑规格"""
    errors = []
    warnings = []

    # 检查设备 ID 唯一性
    device_ids = [d.id for d in spec.devices]
    if len(device_ids) != len(set(device_ids)):
        errors.append("检测到重复的设备 ID")

    device_id_set = set(device_ids)

    # 检查连接线引用的设备是否存在
    for link in spec.links:
        if link.from_device not in device_id_set:
            errors.append(f"连接线引用了不存在的源设备: {link.from_device}")
        if link.to_device not in device_id_set:
            errors.append(f"连接线引用了不存在的目标设备: {link.to_device}")

    # 检查孤立设备
    connected_devices = set()
    for link in spec.links:
        connected_devices.add(link.from_device)
        connected_devices.add(link.to_device)

    isolated = device_id_set - connected_devices
    if isolated and spec.links:
        warnings.append(f"检测到孤立设备: {', '.join(sorted(isolated))}")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def generate_topology(spec: TopologySpec) -> dict[str, Any]:
    """生成 eNSP 拓扑文件

    接收已构造好的 TopologySpec 对象。调用方（server 层）负责先调用
    validate_topology 进行验证；本函数不再重复验证，仅负责生成产物。
    """
    warnings: list[str] = []

    # 自动布局
    if spec.auto_layout:
        spec.devices = auto_layout_devices(spec.devices)

    # 确保输出目录存在（延迟创建，避免 import 时副作用）
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {"ok": False, "error": f"无法创建输出目录: {e}", "warnings": warnings}

    # Stage the complete bundle on the same filesystem, then publish by rename.
    # Readers never see a successful-looking topology with missing configs.
    try:
        topo_xml, xml_warnings = generate_topo_xml(spec)
        warnings.extend(xml_warnings)
        bundle_name = f"{spec.output_name}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex}"
        bundle_dir = OUTPUT_DIR / bundle_name
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=OUTPUT_DIR) as staging:
            stage = Path(staging)
            topo_name = f"{spec.output_name}.topo"
            (stage / topo_name).write_text(topo_xml, encoding="utf-8")
            configs = generate_config_scripts(spec)
            staged_configs = save_configs(configs, spec.output_name, stage)
            config_files = [str(bundle_dir / Path(p).name) for p in staged_configs]
            stage.rename(bundle_dir)
        return {
            "ok": True,
            "topo_file": str(bundle_dir / topo_name),
            "config_files": config_files,
            "warnings": warnings,
        }
    except Exception as e:
        return {"ok": False, "error": f"Artifact generation failed: {e}", "warnings": warnings}


def list_templates() -> dict[str, Any]:
    """列出可用的配置模板"""
    try:
        templates = sorted(
            f.stem for f in TEMPLATE_DIR.glob("*.txt") if f.is_file()
        )
        return {"ok": True, "templates": templates}
    except Exception as e:
        return {"ok": False, "error": str(e), "templates": []}


def load_template(template_name: str) -> dict[str, Any]:
    """加载配置模板（带路径遍历防护）"""
    try:
        # 拒绝包含路径分隔符、上级目录或空字节的名称
        if (
            "/" in template_name
            or "\\" in template_name
            or ".." in template_name
            or "\x00" in template_name
        ):
            return {"ok": False, "error": f"非法的模板名称: {template_name!r}"}

        template_dir_resolved = TEMPLATE_DIR.resolve()
        candidate = (TEMPLATE_DIR / f"{template_name}.txt").resolve()

        # 二次校验：解析后的路径必须仍位于 TEMPLATE_DIR 内
        try:
            candidate.relative_to(template_dir_resolved)
        except ValueError:
            return {"ok": False, "error": f"非法的模板名称: {template_name!r}"}

        if not candidate.exists() or not candidate.is_file():
            return {"ok": False, "error": f"模板不存在: {template_name}"}

        content = candidate.read_text(encoding="utf-8")
        return {"ok": True, "name": template_name, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}
