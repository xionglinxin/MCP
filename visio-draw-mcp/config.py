"""配置文件"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.resolve()

# 图标库目录
STENCIL_DIR = BASE_DIR / "stencils"

# 输出目录
OUTPUT_DIR = BASE_DIR / "outputs"

# 限制
MAX_NODES = 100
MAX_EDGES = 300
MAX_BATCH_SIZE = 10

# COM 超时（秒）
COM_TIMEOUT = 120

# 默认页面尺寸（英寸）
DEFAULT_PAGE_WIDTH = 11.0
DEFAULT_PAGE_HEIGHT = 8.5

# 页面边距（英寸）
PAGE_MARGIN = 0.75

# 默认布局间距
DEFAULT_SPACING_X = 2.5
DEFAULT_SPACING_Y = 1.8

# 默认连接线样式
DEFAULT_LINE_WEIGHT = "1.2 pt"
DEFAULT_LINE_COLOR = "RGB(60,60,60)"
DEFAULT_LABEL_SIZE = "8 pt"

# 分组边框样式
GROUP_LINE_COLOR = "RGB(160,160,160)"
GROUP_LINE_WEIGHT = "1.0 pt"
GROUP_FILL_COLOR = "RGB(245,248,252)"
GROUP_LABEL_SIZE = "11 pt"

# 区域配色方案 — {关键词: (fill, border, label_color)}
ZONE_COLORS = {
    "出口": ("RGB(255,240,240)", "RGB(200,80,80)", "RGB(150,30,30)"),
    "核心": ("RGB(235,245,255)", "RGB(60,120,200)", "RGB(30,70,140)"),
    "服务器": ("RGB(240,255,245)", "RGB(60,170,100)", "RGB(20,100,50)"),
    "办公": ("RGB(255,250,235)", "RGB(220,160,40)", "RGB(140,100,20)"),
    "无线": ("RGB(245,240,255)", "RGB(140,100,200)", "RGB(90,50,150)"),
    "DMZ": ("RGB(255,245,238)", "RGB(220,120,60)", "RGB(150,70,30)"),
    "管理": ("RGB(240,255,255)", "RGB(80,180,180)", "RGB(30,110,110)"),
}
DEFAULT_ZONE_COLOR = ("RGB(248,248,248)", "RGB(160,160,160)", "RGB(80,80,80)")

def get_zone_color(group_name: str) -> tuple:
    """根据分组名称匹配区域配色"""
    if not group_name:
        return DEFAULT_ZONE_COLOR
    for keyword, colors in ZONE_COLORS.items():
        if keyword in group_name:
            return colors
    return DEFAULT_ZONE_COLOR

