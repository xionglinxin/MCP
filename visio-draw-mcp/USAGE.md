# Visio Draw MCP 使用指南

## 快速开始

### 1. 安装依赖

```powershell
cd visio-draw-mcp
pip install mcp pydantic pywin32
```

### 2. 准备图标库

将华为图标库复制到 stencils 目录：

```powershell
# 复制 VSS 格式图标库（推荐）
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 安全(VSS,蓝).vss" "stencils\"
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 AR路由器(VSS,蓝).vss" "stencils\"
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 交换机&无线(VSS,蓝).vss" "stencils\"
```

### 3. 配置 Claude Code

编辑 Claude Code 配置文件：

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "visio-draw": {
      "command": "python",
      "args": ["D:\\Desk\\Temporary\\MCP\\visio-draw-mcp\\server.py"],
      "env": {}
    }
  }
}
```

**重要**: 将路径替换为你的实际项目路径。

### 4. 重启 Claude Code

配置完成后，重启 Claude Code 使配置生效。

## 测试 MCP 服务器

### 方法 1: 在 Claude Code 中测试

重启 Claude Code 后，输入：

```
请列出可用的 Visio 图标库
```

如果配置正确，Claude 会调用 `list_available_stencils` 工具并返回图标库列表。

### 方法 2: 直接运行测试

```powershell
# 测试服务器是否能正常启动
python server.py
```

按 Ctrl+C 停止服务器。

### 方法 3: 使用 MCP Inspector

```powershell
# 安装 MCP Inspector
npm install -g @modelcontextprotocol/inspector

# 运行 Inspector
mcp-inspector python server.py
```

在浏览器中打开显示的 URL，可以交互式测试所有工具。

## 使用示例

### 示例 1: 查看图标库

**提示词**:
```
请列出 stencils 目录下的所有 Visio 图标库文件
```

**Claude 操作**:
- 调用 `list_available_stencils`

**预期输出**:
```json
{
  "ok": true,
  "stencils": [
    "企业网络产品 AR路由器(VSS,蓝).vss",
    "企业网络产品 交换机&无线(VSS,蓝).vss",
    "企业网络产品 安全(VSS,蓝).vss"
  ]
}
```

### 示例 2: 查看图标

**提示词**:
```
请列出"企业网络产品 安全(VSS,蓝).vss"中的所有图标名称
```

**Claude 操作**:
- 调用 `list_stencil_masters`

**预期输出**:
```json
{
  "ok": true,
  "stencil": "企业网络产品 安全(VSS,蓝).vss",
  "masters": ["Firewall", "IPS", "WAF", "Server", "Database", ...]
}
```

### 示例 3: 生成系统架构图

**提示词**:
```
请使用 Visio 生成一个学生管理系统架构图，包含：
1. 用户
2. Vue 前端
3. Spring Boot 后端
4. MySQL 数据库
5. Redis 缓存

使用"企业网络产品 安全(VSS,蓝).vss"图标库，从左到右布局。
```

**Claude 操作**:
1. 调用 `list_stencil_masters` 获取可用图标
2. 构造 DiagramSpec
3. 调用 `validate_diagram_spec` 验证
4. 调用 `draw_visio_diagram` 生成图表
5. 返回生成的 .vsdx 文件路径

**预期输出**:
```
已生成 Visio 图表：outputs/student_system_a1b2c3d4.vsdx
```

### 示例 4: 导出为图片

**提示词**:
```
请将刚才生成的 Visio 图表导出为 PNG 图片
```

**Claude 操作**:
- 调用 `export_visio_diagram`

**预期输出**:
```
已导出图片：outputs/student_system_a1b2c3d4.png
```

## 常见问题

### Q1: MCP 服务器无法启动

**症状**: Claude Code 提示 MCP 服务器连接失败

**解决方案**:
1. 检查配置文件路径是否正确
2. 确保 Python 在系统 PATH 中
3. 手动运行 `python server.py` 查看错误信息
4. 检查依赖是否安装：`pip list | findstr "mcp pydantic pywin32"`

### Q2: Visio COM 对象不可用

**症状**: 错误信息 "Microsoft Visio COM object is not available"

**解决方案**:
1. 确保已安装 Microsoft Visio
2. 确保 Visio 版本支持 COM 自动化
3. 尝试手动启动 Visio 一次

### Q3: Master 图标找不到

**症状**: 错误信息 "Master not found: Server"

**解决方案**:
1. 使用 `list_stencil_masters` 查看实际可用的 Master 名称
2. Master 名称区分大小写
3. 不同图标库包含不同的 Master

### Q4: 生成的图表为空

**症状**: .vsdx 文件生成了，但打开后没有内容

**解决方案**:
1. 检查节点坐标是否合理
2. 检查 Master 名称是否正确
3. 查看返回的 warnings 信息

### Q5: 无法导出图片

**症状**: 导出 PNG 或 PDF 失败

**解决方案**:
1. 确保输入文件路径正确
2. 确保文件在 outputs 目录内
3. 检查 Visio 是否支持该导出格式

## 高级用法

### 自定义布局

```json
{
  "layout": {
    "direction": "TB"  // 从上到下
  }
}
```

支持的布局：
- `LR`: 从左到右（默认）
- `TB`: 从上到下
- `GRID`: 网格布局（4 列）
- `LAYERED`: 分层拓扑布局（推荐用于网络拓扑）

### 手动指定坐标

```json
{
  "nodes": [
    {
      "id": "server1",
      "label": "服务器 1",
      "master": "Server",
      "x": 2.0,
      "y": 5.0
    }
  ]
}
```

坐标单位为英寸。

### 分组节点

```json
{
  "nodes": [
    {
      "id": "web1",
      "label": "Web 服务器 1",
      "master": "Server",
      "group": "Web 层"
    },
    {
      "id": "web2",
      "label": "Web 服务器 2",
      "master": "Server",
      "group": "Web 层"
    }
  ]
}
```

注意：`group` 字段会自动绘制分组边框，同组节点在布局时聚拢在一起。

## 性能优化

### 限制图表规模

- 最大节点数: 100
- 最大边数: 300

超过限制会返回错误。

### 批量生成

如果需要生成多个图表，建议：
1. 使用不同的 `output_name`
2. 避免频繁启动/关闭 Visio
3. 考虑使用后台任务

## 安全注意事项

1. **路径限制**: 所有文件操作限制在项目目录内
2. **文件覆盖**: 自动生成唯一文件名，避免覆盖
3. **输入验证**: 所有输入都经过 Pydantic 验证
4. **COM 安全**: Visio 以不可见（无头）模式运行，不会弹出窗口

## 下一步

- 查看 `examples/` 目录中的示例文件
- 阅读 `README.md` 了解更多功能
- 参考 `代码/visio_draw_mcp_design.md` 了解设计思路
