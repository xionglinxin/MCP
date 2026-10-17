# eNSP Draw MCP 使用指南

本文档详细介绍如何使用 eNSP Draw MCP 服务器生成华为 eNSP 网络拓扑。

## 快速开始

### 1. 生成示例拓扑

最快的上手方式是生成预定义的示例拓扑：

```
👤 生成一个简单的示例拓扑
```

Claude 会调用 `ensp_generate_simple_topology` 工具，自动生成包含 3 台路由器的拓扑。

**输出文件**（UUID 为每次生成的唯一后缀，请使用工具返回的完整路径）：
- `outputs/simple_example_YYYYMMDD_HHMMSS_UUID/simple_example.topo` — 拓扑文件
- `outputs/simple_example_YYYYMMDD_HHMMSS_UUID/simple_example_R1_config.txt` — R1 配置
- `outputs/simple_example_YYYYMMDD_HHMMSS_UUID/simple_example_R2_config.txt` — R2 配置
- `outputs/simple_example_YYYYMMDD_HHMMSS_UUID/simple_example_R3_config.txt` — R3 配置

### 2. 在 eNSP 中打开拓扑

1. 启动华为 eNSP
2. 菜单：文件 → 打开
3. 选择生成的 `.topo` 文件
4. 拓扑加载完成，设备自动布局

### 3. 应用设备配置

在 eNSP 中右键点击设备 → CLI，粘贴对应的配置脚本。

## 自定义拓扑生成

### 基本流程

```
👤 生成一个企业网络拓扑，包含：
   - 1 台边界路由器（AR2220）
   - 1 台核心交换机（S6720）
   - 2 台接入交换机（S5700）
   - 配置基础 VLAN 和 IP 地址
```

Claude 会：
1. 理解需求，构造 `TopologySpec`
2. 调用 `ensp_validate_topology` 验证规格
3. 调用 `ensp_generate_topology` 生成文件

### 数据结构说明

#### DeviceSpec（设备规格）

```python
{
    "id": "R1",                    # 唯一标识（用于连接线引用）
    "name": "边界路由器",           # 显示名称
    "device_type": "AR_Router",    # 设备类型
    "model": "AR2220",             # 型号
    "x": 100.0,                    # X 坐标（可选，auto_layout=false 时必需）
    "y": 100.0,                    # Y 坐标（可选）
    "config_script": "..."         # 配置脚本（可选）
}
```

**支持的 device_type**：
- `AR_Router` — AR 路由器
- `S_Switch` — S 交换机
- `CE_Switch` — CE 数据中心交换机
- `USG_Firewall` — USG 防火墙
- `PC` — 终端
- `Server` — 服务器
- `Cloud` — 云（Internet）

#### LinkSpec（连接线规格）

```python
{
    "from_device": "R1",           # 源设备 ID
    "from_interface": "GE0/0/0",   # 源接口
    "to_device": "SW1",            # 目标设备 ID
    "to_interface": "GE1/0/1",     # 目标接口
    "link_type": "Ethernet"        # 连接类型（Ethernet/Serial/Console）
}
```

**接口命名规则**：
- 路由器/交换机：`GE0/0/0`, `GE1/0/1` （GigabitEthernet 缩写）
- 完整格式：`GigabitEthernet0/0/0`

#### TopologySpec（拓扑规格）

```python
{
    "title": "企业网络拓扑",       # 拓扑标题
    "devices": [...],              # 设备列表
    "links": [...],                # 连接线列表
    "output_name": "enterprise",   # 输出文件名前缀
    "auto_layout": true            # 自动布局
}
```

## 配置脚本编写

### 配置脚本格式

配置脚本使用华为 VRP 命令，支持多行：

```python
"config_script": """interface GigabitEthernet0/0/0
 ip address 192.168.1.1 255.255.255.252
 undo shutdown
#
interface GigabitEthernet0/0/1
 ip address 10.0.0.1 255.255.255.0
 undo shutdown
#
ospf 1
 area 0
  network 192.168.1.0 0.0.0.3
  network 10.0.0.0 0.0.0.255"""
```

### 自动添加的内容

生成的配置文件会自动添加：

```
# 设备名称 (型号) 配置脚本
# 生成时间: YYYY-MM-DD HH:MM:SS

system-view
sysname 设备名称

[你的配置脚本]

quit
save
```

### 使用配置模板

#### 查看可用模板

```
👤 有哪些配置模板？
🤖 → ensp_list_templates()
```

#### 加载模板内容

```
👤 查看 OSPF 单区域配置模板
🤖 → ensp_load_template("ospf_single_area")
```

#### 应用模板

在生成拓扑时，将模板内容填入 `config_script` 字段。

## 常见场景示例

### 场景 1：简单三层架构

```
👤 生成一个三层网络架构：
   - 核心层：2 台核心交换机（S12700）
   - 汇聚层：2 台汇聚交换机（S6720）
   - 接入层：4 台接入交换机（S5700）
```

### 场景 2：数据中心网络

```
👤 生成数据中心网络拓扑：
   - 1 台边界防火墙（USG6600）
   - 2 台核心交换机（CE12800）做 VRRP
   - 4 台接入交换机（S5700）
   - 配置 VLAN 和 Trunk
```

### 场景 3：分支互联

```
👤 生成总部-分支互联拓扑：
   - 总部：1 台核心路由器（AR3260）+ 1 台交换机（S6720）
   - 分支1：1 台路由器（AR1220）+ 1 台交换机（S5700）
   - 分支2：1 台路由器（AR1220）+ 1 台交换机（S5700）
   - 配置 OSPF 路由协议
```

## 高级功能

### 手动坐标布局

如果需要精确控制设备位置，设置 `auto_layout: false` 并为每个设备指定坐标：

```python
{
    "title": "精确布局拓扑",
    "devices": [
        {"id": "R1", "x": 100, "y": 100, ...},
        {"id": "R2", "x": 400, "y": 100, ...},
        {"id": "SW1", "x": 250, "y": 300, ...}
    ],
    "auto_layout": false
}
```

**坐标单位**：像素（eNSP 画布坐标系）

### 验证拓扑规格

在生成前验证规格是否合法：

```
👤 验证这个拓扑规格是否正确
🤖 → ensp_validate_topology(spec)
```

**验证项**：
- 设备 ID 唯一性
- 连接线引用的设备是否存在
- 孤立设备检测（有设备但没有连接）

### 批量生成配置

如果需要为多个设备生成相似配置，可以使用 Python 脚本预处理：

```python
devices = []
for i in range(1, 11):
    devices.append({
        "id": f"SW{i}",
        "name": f"接入交换机{i}",
        "device_type": "S_Switch",
        "model": "S5700",
        "config_script": f"""vlan batch 10 20 30
interface GigabitEthernet0/0/{i}
 port link-type trunk
 port trunk allow-pass vlan 10 20 30"""
    })
```

## 故障排查

### 问题：生成的 .topo 文件无法在 eNSP 中打开

**可能原因**：
- eNSP 版本不兼容（推荐 V1.3.00.100 或更高）
- XML 格式错误

**解决方法**：
- 用文本编辑器打开 .topo 文件，检查 XML 格式
- 检查设备型号是否在 eNSP 支持列表中

### 问题：配置脚本无法应用

**可能原因**：
- VRP 命令语法错误
- 设备型号不支持某些命令

**解决方法**：
- 在 eNSP 中手动测试命令
- 参考华为官方文档确认命令格式

### 问题：设备布局重叠

**可能原因**：
- 设备数量过多，网格布局空间不足
- 手动坐标设置重复

**解决方法**：
- 调整 `config.py` 中的布局参数：
  ```python
  LAYOUT_CONFIG = {
      "grid_cols": 4,           # 增加列数
      "device_spacing_x": 200,  # 增加水平间距
      "device_spacing_y": 150,  # 增加垂直间距
  }
  ```

## 配置模板开发

### 创建新模板

在 `templates/` 目录下创建 `.txt` 文件：

```
templates/ospf_single_area.txt
```

内容示例：

```
# OSPF 单区域配置模板
interface GigabitEthernet0/0/0
 ip address 192.168.1.1 255.255.255.252
 undo shutdown
#
interface GigabitEthernet0/0/1
 ip address 10.0.0.1 255.255.255.0
 undo shutdown
#
ospf 1 router-id 1.1.1.1
 area 0
  network 192.168.1.0 0.0.0.3
  network 10.0.0.0 0.0.0.255
```

### 模板变量（计划中）

未来版本将支持模板变量替换：

```
interface GigabitEthernet0/0/0
 ip address {{wan_ip}} {{wan_mask}}
```

## 输出文件说明

### .topo 文件结构

```xml
<topo version="1.3.00.100">
  <info>
    <name>拓扑标题</name>
    <author>Claude Code</author>
    <date>2026-06-04 12:00:00</date>
  </info>
  <devices>
    <device id="0" name="R1" type="1" model="AR1220" x="100" y="100"/>
    ...
  </devices>
  <links>
    <link id="0" src_dev="0" src_if="GE0/0/0" dst_dev="1" dst_if="GE0/0/0" link_type="Ethernet"/>
    ...
  </links>
</topo>
```

### 配置文件命名

```
outputs/{output_name}_{timestamp}_{uuid}/{output_name}_{device_id}_config.txt
```

示例：
```
outputs/enterprise_20260604_120000_UUID/enterprise_R1_config.txt
outputs/enterprise_20260604_120000_UUID/enterprise_SW1_config.txt
```

## 与 Claude 的交互技巧

### 清晰描述需求

✅ 好的提问：
```
生成一个包含 1 台 AR2220 路由器、1 台 S6720 核心交换机、
2 台 S5700 接入交换机的拓扑，配置 VLAN 10、20、30
```

❌ 不好的提问：
```
生成一个网络拓扑
```

### 分步骤操作

对于复杂拓扑：
1. 先生成基础拓扑结构
2. 查看输出文件
3. 要求添加配置脚本
4. 逐步完善

### 使用示例引导

```
👤 参考简单示例拓扑的格式，生成一个类似的但包含防火墙的拓扑
```

## 最佳实践

1. **从简单开始**：先生成小规模拓扑验证流程
2. **模块化配置**：将常用配置保存为模板
3. **命名规范**：设备 ID 使用有意义的名称（R1, SW1, FW1）
4. **验证优先**：复杂拓扑先验证再生成
5. **版本控制**：输出文件自动带时间戳，不会覆盖
6. **配置注释**：在配置脚本中添加注释说明用途

## 下一步

- 查看 `README.md` 了解项目概况
- 运行 `test.ps1` 测试安装
- 浏览 `examples/` 目录查看更多示例
