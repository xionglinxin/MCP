# Visio Draw MCP 部署和测试指南

## 一、环境准备

### 1. 检查系统要求

```powershell
# 检查 Python 版本（需要 3.10+）
python --version

# 检查 Visio 是否安装
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_.DisplayName -like "*Visio*" }
```

### 2. 安装 Python 依赖

```powershell
cd D:\Desk\Temporary\MCP\visio-draw-mcp

# 安装核心依赖
pip install mcp pydantic pywin32

# 可选：安装开发依赖
pip install pytest black ruff
```

### 3. 准备图标库

```powershell
# 复制华为图标库到 stencils 目录
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 安全(VSS,蓝).vss" "stencils\"
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 AR路由器(VSS,蓝).vss" "stencils\"
Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\企业网络产品 交换机&无线(VSS,蓝).vss" "stencils\"

# 验证文件已复制
Get-ChildItem stencils\
```

## 二、配置 Claude Code

### 1. 找到配置文件

```powershell
# Windows 配置文件路径
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
Write-Host "配置文件路径: $configPath"

# 检查文件是否存在
Test-Path $configPath
```

### 2. 编辑配置文件

如果文件不存在，创建新文件：

```powershell
# 创建目录
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude"

# 创建配置文件
@"
{
  "mcpServers": {
    "visio-draw": {
      "command": "python",
      "args": ["D:\\Desk\\Temporary\\MCP\\visio-draw-mcp\\server.py"],
      "env": {}
    }
  }
}
"@ | Out-File -FilePath $configPath -Encoding utf8
```

如果文件已存在，手动编辑添加 `visio-draw` 配置。

**重要**: 将路径替换为你的实际项目路径。

### 3. 验证配置

```powershell
# 查看配置内容
Get-Content $configPath | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

## 三、测试 MCP 服务器

### 测试 1: 直接运行服务器

```powershell
# 进入项目目录
cd D:\Desk\Temporary\MCP\visio-draw-mcp

# 运行服务器
python server.py
```

**预期结果**: 服务器启动，等待 MCP 客户端连接。按 Ctrl+C 停止。

**常见错误**:
- `ModuleNotFoundError: No module named 'mcp'` → 运行 `pip install mcp`
- `ModuleNotFoundError: No module named 'pydantic'` → 运行 `pip install pydantic`
- `ModuleNotFoundError: No module named 'win32com'` → 运行 `pip install pywin32`

### 测试 2: 测试图标库读取

创建测试脚本 `test_stencils.py`:

```python
from visio_driver import list_stencils, list_masters

# 测试列出图标库
print("=== 测试列出图标库 ===")
result = list_stencils()
print(result)

# 测试读取 Master
if result["ok"] and result["stencils"]:
    stencil = result["stencils"][0]
    print(f"\n=== 测试读取 {stencil} 中的 Master ===")
    masters_result = list_masters(stencil)
    print(masters_result)
```

运行测试：

```powershell
python test_stencils.py
```

**预期输出**:
```json
=== 测试列出图标库 ===
{'ok': True, 'stencils': ['企业网络产品 AR路由器(VSS,蓝).vss', ...]}

=== 测试读取 企业网络产品 安全(VSS,蓝).vss 中的 Master ===
{'ok': True, 'stencil': '企业网络产品 安全(VSS,蓝).vss', 'masters': ['Firewall', 'IPS', ...]}
```

### 测试 3: 测试生成图表

创建测试脚本 `test_draw.py`:

```python
from schema import DiagramSpec, NodeSpec, EdgeSpec, LayoutSpec
from visio_driver import draw_diagram

# 构造简单图表
spec = DiagramSpec(
    title="测试图表",
    stencil="企业网络产品 安全(VSS,蓝).vss",
    nodes=[
        NodeSpec(id="n1", label="节点1", master="Server"),
        NodeSpec(id="n2", label="节点2", master="Database"),
    ],
    edges=[
        EdgeSpec(**{"from": "n1", "to": "n2", "label": "连接"})
    ],
    layout=LayoutSpec(direction="LR"),
    output_name="test_diagram"
)

# 生成图表
print("=== 测试生成图表 ===")
result = draw_diagram(spec.model_dump(by_alias=True))
print(result)

if result["ok"]:
    print(f"\n成功生成图表: {result['file']}")
```

运行测试：

```powershell
python test_draw.py
```

**预期输出**:
```json
=== 测试生成图表 ===
{'ok': True, 'file': 'outputs\\test_diagram_a1b2c3d4.vsdx', 'warnings': []}

成功生成图表: outputs\test_diagram_a1b2c3d4.vsdx
```

检查生成的文件：

```powershell
# 查看输出目录
Get-ChildItem outputs\

# 用 Visio 打开文件
Invoke-Item outputs\test_diagram_*.vsdx
```

### 测试 4: 测试导出功能

```python
from visio_driver import export_diagram

# 使用上一步生成的文件
input_file = "outputs\\test_diagram_a1b2c3d4.vsdx"  # 替换为实际文件名

# 导出为 PNG
print("=== 测试导出 PNG ===")
result = export_diagram(input_file, "png")
print(result)

# 导出为 PDF
print("\n=== 测试导出 PDF ===")
result = export_diagram(input_file, "pdf")
print(result)
```

## 四、在 Claude Code 中测试

### 1. 重启 Claude Code

配置完成后，完全退出并重启 Claude Code。

### 2. 测试连接

在 Claude Code 中输入：

```
请列出可用的 Visio 图标库
```

**预期行为**: Claude 调用 `list_available_stencils` 工具并返回图标库列表。

### 3. 测试查看图标

```
请列出"企业网络产品 安全(VSS,蓝).vss"中的所有图标名称
```

**预期行为**: Claude 调用 `list_stencil_masters` 工具并返回 Master 列表。

### 4. 测试生成图表

```
请使用 Visio 生成一个简单的网络拓扑图：
- Internet（云）
- 防火墙
- 交换机
- 服务器

使用"企业网络产品 安全(VSS,蓝).vss"图标库，从左到右布局。
```

**预期行为**: 
1. Claude 查询可用的 Master
2. 构造 DiagramSpec
3. 生成 .vsdx 文件
4. 返回文件路径

### 5. 测试导出

```
请将刚才生成的图表导出为 PNG 图片
```

**预期行为**: Claude 调用 `export_visio_diagram` 并返回 PNG 文件路径。

## 五、故障排除

### 问题 1: MCP 服务器无法启动

**症状**: Claude Code 提示连接失败

**诊断步骤**:

```powershell
# 1. 检查 Python 是否在 PATH 中
python --version

# 2. 手动运行服务器查看错误
cd D:\Desk\Temporary\MCP\visio-draw-mcp
python server.py

# 3. 检查配置文件
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```

**解决方案**:
- 确保 Python 路径正确
- 确保所有依赖已安装
- 检查配置文件 JSON 格式是否正确

### 问题 2: Visio COM 错误

**症状**: "Microsoft Visio COM object is not available"

**诊断步骤**:

```powershell
# 检查 Visio 是否安装
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | 
    Where-Object { $_.DisplayName -like "*Visio*" }

# 测试 COM 对象
python -c "import win32com.client; visio = win32com.client.Dispatch('Visio.Application'); print('Visio COM OK')"
```

**解决方案**:
- 确保已安装 Microsoft Visio
- 尝试手动启动 Visio 一次
- 重新安装 pywin32: `pip install --upgrade --force-reinstall pywin32`

### 问题 3: Master 找不到

**症状**: "Master not found: Server"

**诊断步骤**:

```powershell
# 运行测试脚本查看实际 Master 名称
python test_stencils.py
```

**解决方案**:
- 使用 `list_stencil_masters` 查看实际可用的 Master
- Master 名称区分大小写
- 确保使用正确的图标库文件

### 问题 4: 路径错误

**症状**: "Invalid stencil path" 或 "File not found"

**诊断步骤**:

```powershell
# 检查图标库文件是否存在
Get-ChildItem stencils\

# 检查输出目录
Get-ChildItem outputs\
```

**解决方案**:
- 确保图标库文件在 `stencils/` 目录
- 确保目录权限正确
- 使用相对路径或完整路径

## 六、性能测试

### 测试生成速度

```python
import time
from schema import DiagramSpec, NodeSpec, EdgeSpec
from visio_driver import draw_diagram

# 测试不同规模的图表
for node_count in [5, 10, 20, 50]:
    nodes = [
        NodeSpec(id=f"n{i}", label=f"节点{i}", master="Server")
        for i in range(node_count)
    ]
    edges = [
        EdgeSpec(**{"from": f"n{i}", "to": f"n{i+1}"})
        for i in range(node_count - 1)
    ]
    
    spec = DiagramSpec(
        title=f"测试{node_count}节点",
        stencil="企业网络产品 安全(VSS,蓝).vss",
        nodes=nodes,
        edges=edges,
        output_name=f"perf_test_{node_count}"
    )
    
    start = time.time()
    result = draw_diagram(spec.model_dump(by_alias=True))
    elapsed = time.time() - start
    
    print(f"{node_count} 节点: {elapsed:.2f}秒 - {'成功' if result['ok'] else '失败'}")
```

## 七、下一步

测试通过后，你可以：

1. **在 Claude Code 中使用**: 直接通过自然语言生成图表
2. **查看示例**: 参考 `examples/` 目录中的 JSON 示例
3. **阅读文档**: 查看 `README.md` 和 `USAGE.md`
4. **扩展功能**: 根据需要修改代码添加新功能

## 八、清理测试文件

```powershell
# 删除测试生成的文件
Remove-Item outputs\test_*.vsdx, outputs\test_*.png, outputs\test_*.pdf -ErrorAction SilentlyContinue

# 删除测试脚本
Remove-Item test_*.py -ErrorAction SilentlyContinue
```
