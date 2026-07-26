"""配置文件 — 目录路径和常量定义

注意：目录创建延迟到使用点（server 生命周期或 generate_topology 写文件前），
避免在 import 时产生文件系统副作用。
"""

from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent

# 输出目录
OUTPUT_DIR = ROOT_DIR / "outputs"

# 模板目录
TEMPLATE_DIR = ROOT_DIR / "templates"

# 示例目录
EXAMPLE_DIR = ROOT_DIR / "examples"

# eNSP 设备类型 ID（用于 .topo 文件）
DEVICE_TYPE_IDS = {
    "AR_Router": "1",
    "S_Switch": "2",
    "CE_Switch": "3",
    "USG_Firewall": "4",
    "PC": "5",
    "Server": "6",
    "Cloud": "7",
}

# 自动布局配置
LAYOUT_CONFIG = {
    "grid_cols": 4,
    "device_spacing_x": 200,
    "device_spacing_y": 150,
    "start_x": 100,
    "start_y": 100,
}
