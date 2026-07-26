# Visio Draw MCP

基于 MCP (Model Context Protocol) 的 Visio 自动绘图服务器，让 AI Agent 通过自然语言自动生成 Visio 图表。

## 功能

- **12 个 MCP 工具** — 图标库浏览、图表生成、增量编辑、格式导出、批量生成
- **2 个 MCP 资源** — stencil 列表、output 列表以 resource 形式暴露
- **13 个华为图标库** — 路由器、交换机、安全、接入网、传送网
- **4 种自动布局** — LR（左→右）、TB（上→下）、GRID（网格）、LAYERED（分层拓扑）
- **2 个预置案例** — 防火墙配置拓扑、MSTP/VRRP 冗余网关拓扑
- **导出** — PNG / PDF / SVG

## 系统要求

- Windows + Microsoft Visio（COM 自动化）
- Python 3.10+

## 安装

```powershell
cd D:\Desk\Temporary\MCP\visio-draw-mcp
pip install mcp pydantic pywin32
```

## 配置 Claude Code

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "visio-draw": {
      "command": "python",
      "args": [
        "D:\\Desk\\Temporary\\MCP\\visio-draw-mcp\\server.py"
      ]
    }
  }
}
```

重启 Claude Code 生效。

## MCP 工具

| 工具 | 描述 |
|------|------|
| `visio_list_stencils` | 列出 `stencils/` 下所有 .vss/.vssx 图标库 |
| `visio_list_masters` | 列出指定图标库中的 Master 图标名称 |
| `visio_validate_spec` | 验证 DiagramSpec 合法性（不生成图表） |
| `visio_draw_diagram` | 根据规格生成 .vsdx 图表 |
| `visio_export_diagram` | 导出 .vsdx 为 PNG / PDF / SVG |
| `visio_update_diagram` | 增量编辑已有 .vsdx 图表 |
| `visio_draw_batch` | 批量生成多个图表 |
| `visio_list_outputs` | 列出已生成的文件 |
| `visio_delete_output` | 删除输出文件（移到回收站） |
| `visio_draw_redundant_gateway_topology` | 一键生成 MSTP/VRRP 冗余网关案例 |
| `visio_draw_firewall_case_topology` | 一键生成华为防火墙配置案例 |
| `visio_get_help` | 获取使用指南和最佳实践 |

## MCP 资源

| URI | 内容 |
|-----|------|
| `stencils://list` | 图标库文件列表 |
| `outputs://list` | 已生成文件列表 |

## 使用示例

```
👤 有哪些 Visio 图标库？
🤖 → visio_list_stencils → 13 个图标库

👤 安全图标库中有哪些图标？
🤖 → visio_list_masters("企业网络产品 安全(VSS,蓝).vss")

👤 画一个网络拓扑图：Internet → 防火墙 → 交换机 → 服务器
🤖 → visio_draw_diagram(spec) → outputs/network_topology_xxx.vsdx

👤 导出为 PNG
🤖 → visio_export_diagram("outputs/...vsdx", "png")
```

## 项目结构

```
visio-draw-mcp/
├── server.py                             # MCP 服务入口
├── visio_driver.py                       # 兼容性门面（facade）
├── session.py                            # Visio COM 会话管理
├── layout.py                             # 布局引擎（拓扑排序、自动布局）
├── drawing.py                            # 绘图辅助 + 核心操作
├── schema.py                             # Pydantic 数据模型
├── config.py                             # 配置
├── pyproject.toml                        # 依赖声明
├── generate_firewall_case_28.py          # 防火墙案例
├── generate_redundant_gateway_topology.py # 冗余网关案例
├── test.ps1                              # 自动诊断脚本
├── test_generate_topology.py             # 端到端测试
├── stencils/                             # 图标库 (.vss)
├── outputs/                              # 生成输出
└── examples/                             # JSON 示例
```

## 布局选项

- `LR` — 从左到右（默认）
- `TB` — 从上到下
- `GRID` — 4 列网格
- `LAYERED` — 分层拓扑（推荐用于网络拓扑、架构图）

## 安全限制

- 文件操作限制在 `stencils/` 和 `outputs/` 目录内
- 最大 100 节点 / 300 边
- 自动生成唯一文件名防止覆盖
- Pydantic 严格输入验证

## 更多文档

- `USAGE.md` — 详细使用指南
- `DEPLOYMENT.md` — 部署和测试指南
- `落地方案总结.md` — 项目方案总结
- `项目交付报告.md` — 项目交付报告
