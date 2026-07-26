# eNSP Draw MCP

基于 MCP (Model Context Protocol) 的 eNSP 拓扑自动生成服务器，让 AI Agent 通过自然语言自动生成华为 eNSP 网络拓扑和设备配置。

## 功能特性

- **5 个 MCP 工具** — 模板管理、拓扑验证、拓扑生成
- **2 个 MCP 资源** — 模板列表、输出文件列表
- **自动布局** — 网格布局，自动计算设备位置
- **配置脚本生成** — 为每个设备生成配置文件
- **输出格式** — .topo 拓扑文件 + .txt 配置脚本

## 系统要求

- Windows 平台
- Python 3.10+
- 华为 eNSP（用于打开生成的 .topo 文件）

## 安装

```powershell
cd D:\Desk\Temporary\MCP\ensp-mcp
pip install mcp pydantic
```

## 配置 Claude Code

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "ensp-draw": {
      "command": "python",
      "args": [
        "D:\\Desk\\Temporary\\MCP\\ensp-mcp\\server.py"
      ]
    }
  }
}
```

重启 Claude Code 生效。

## MCP 工具

| 工具 | 描述 |
|------|------|
| `ensp_list_templates` | 列出 `templates/` 下所有配置模板 |
| `ensp_load_template` | 加载指定模板的内容 |
| `ensp_validate_topology` | 验证拓扑规格合法性（不生成文件） |
| `ensp_generate_topology` | 根据规格生成 .topo 文件和配置脚本 |
| `ensp_generate_simple_topology` | 一键生成 3 路由器示例拓扑 |

## MCP 资源

| URI | 内容 |
|-----|------|
| `templates://list` | 配置模板文件列表 |
| `outputs://list` | 已生成文件列表 |

## 使用示例

```
👤 生成一个简单的拓扑作为示例
🤖 → ensp_generate_simple_topology() → 生成 3 路由器拓扑

👤 有哪些配置模板？
🤖 → ensp_list_templates() → 模板列表

👤 生成一个包含防火墙、核心交换机和接入交换机的数据中心拓扑
🤖 → ensp_generate_topology(spec) → outputs/datacenter_xxx.topo + 配置文件
```

## 项目结构

```
ensp-mcp/
├── server.py                # MCP 服务入口
├── ensp_driver.py           # eNSP 拓扑生成驱动
├── schema.py                # Pydantic 数据模型
├── config.py                # 配置
├── README.md                # 本文件
├── USAGE.md                 # 详细使用指南
├── test.ps1                 # 测试脚本
├── templates/               # 配置模板目录
├── outputs/                 # 输出目录
└── examples/                # JSON 示例
```

## 支持的设备类型

- **AR_Router** — AR 系列路由器（AR1220, AR2220, AR3260）
- **S_Switch** — S 系列交换机（S5700, S6720, S12700）
- **CE_Switch** — CE 数据中心交换机（CE6800, CE12800）
- **USG_Firewall** — USG 防火墙（USG6000V, USG6300, USG6600）
- **PC** — 终端 PC
- **Server** — 服务器
- **Cloud** — 云（代表 Internet）

## 布局选项

- **auto_layout: true** — 自动网格布局（4 列）
- **auto_layout: false** — 使用手动指定的 x, y 坐标

## 数据结构示例

```python
{
    "title": "企业网络拓扑",
    "devices": [
        {
            "id": "R1",
            "name": "边界路由器",
            "device_type": "AR_Router",
            "model": "AR2220",
            "config_script": "interface GE0/0/0\n ip address 192.168.1.1 255.255.255.0"
        },
        {
            "id": "SW1",
            "name": "核心交换机",
            "device_type": "S_Switch",
            "model": "S6720"
        }
    ],
    "links": [
        {
            "from_device": "R1",
            "from_interface": "GE0/0/0",
            "to_device": "SW1",
            "to_interface": "GE1/0/1",
            "link_type": "Ethernet"
        }
    ],
    "output_name": "enterprise_network",
    "auto_layout": true
}
```

## 安全限制

- 文件操作限制在 `templates/` 和 `outputs/` 目录内
- 最大 100 设备 / 300 连接线
- 自动生成唯一文件名防止覆盖
- Pydantic 严格输入验证

## 更多文档

- `USAGE.md` — 详细使用指南和案例
- `test.ps1` — 自动测试脚本

## 与 Visio MCP 的区别

| 特性 | Visio MCP | eNSP MCP |
|------|-----------|----------|
| 输出格式 | .vsdx (Visio) | .topo (eNSP XML) |
| 需要软件 | Microsoft Visio | 华为 eNSP |
| 驱动方式 | COM 自动化 | XML 文件生成 |
| 配置脚本 | 不支持 | 支持（华为 CLI） |
| 图标库 | .vss/.vssx | 内置设备类型 |

## 下一步开发

1. ✅ 基础拓扑生成（已完成）
2. ✅ 配置脚本生成（已完成）
3. 🔲 更多配置模板（OSPF、BGP、VLAN、STP 等）
4. 🔲 从现有 .topo 文件读取和修改
5. 🔲 拓扑图可视化预览（PNG 导出）
6. 🔲 批量设备配置生成
