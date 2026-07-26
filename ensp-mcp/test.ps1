# eNSP Draw MCP 测试脚本
# 验证安装和基础功能

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "eNSP Draw MCP 测试脚本" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. 检查 Python 版本
Write-Host "[1/6] 检查 Python 版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python 未安装或不在 PATH 中" -ForegroundColor Red
    exit 1
}

# 2. 检查依赖
Write-Host "[2/6] 检查 Python 依赖..." -ForegroundColor Yellow
$requiredPackages = @("mcp", "pydantic")
foreach ($pkg in $requiredPackages) {
    try {
        python -c "import $pkg" 2>$null
        Write-Host "  ✓ $pkg 已安装" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $pkg 未安装，正在安装..." -ForegroundColor Yellow
        pip install $pkg
    }
}

# 3. 检查项目结构
Write-Host "[3/6] 检查项目结构..." -ForegroundColor Yellow
$requiredFiles = @("server.py", "ensp_driver.py", "schema.py", "config.py")
foreach ($file in $requiredFiles) {
    $filePath = Join-Path $ProjectRoot $file
    if (Test-Path $filePath) {
        Write-Host "  ✓ $file 存在" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file 不存在" -ForegroundColor Red
        exit 1
    }
}

# 4. 检查目录
Write-Host "[4/6] 检查输出目录..." -ForegroundColor Yellow
$requiredDirs = @("outputs", "templates", "examples")
foreach ($dir in $requiredDirs) {
    $dirPath = Join-Path $ProjectRoot $dir
    if (Test-Path $dirPath) {
        Write-Host "  ✓ $dir/ 存在" -ForegroundColor Green
    } else {
        Write-Host "  ! $dir/ 不存在，正在创建..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
        Write-Host "  ✓ $dir/ 已创建" -ForegroundColor Green
    }
}

# 5. 验证导入
Write-Host "[5/6] 验证 Python 模块导入..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    python -c "from schema import TopologySpec; from ensp_driver import generate_topology; print('✓ 模块导入成功')" 2>&1 | ForEach-Object {
        if ($_ -like "*✓*") {
            Write-Host "  $_" -ForegroundColor Green
        } else {
            Write-Host "  $_" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  ✗ 模块导入失败: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# 6. 生成测试拓扑
Write-Host "[6/6] 生成测试拓扑..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    $testScript = @"
from schema import TopologySpec
from ensp_driver import generate_topology, validate_topology

spec = TopologySpec(
    title="测试拓扑",
    devices=[
        {
            "id": "R1",
            "name": "路由器1",
            "device_type": "AR_Router",
            "model": "AR1220",
        },
        {
            "id": "R2",
            "name": "路由器2",
            "device_type": "AR_Router",
            "model": "AR1220",
        }
    ],
    links=[
        {
            "from_device": "R1",
            "from_interface": "GE0/0/0",
            "to_device": "R2",
            "to_interface": "GE0/0/0",
            "link_type": "Ethernet"
        }
    ],
    output_name="test",
    auto_layout=True
)

validation = validate_topology(spec)
if not validation["ok"]:
    print(f"✗ 验证失败: {'; '.join(validation['errors'])}")
    exit(1)

result = generate_topology(spec)
if result["ok"]:
    print(f"✓ 拓扑生成成功")
    print(f"  文件: {result['topo_file']}")
else:
    print(f"✗ 生成失败: {result.get('error', 'Unknown')}")
    exit(1)
"@

    $testScript | python 2>&1 | ForEach-Object {
        if ($_ -like "*✓*") {
            Write-Host "  $_" -ForegroundColor Green
        } elseif ($_ -like "*✗*") {
            Write-Host "  $_" -ForegroundColor Red
        } else {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "  ✗ 测试失败: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "测试完成！" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 配置 Claude Code MCP 服务器" -ForegroundColor White
Write-Host "   编辑: %APPDATA%\Claude\claude_desktop_config.json" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 添加配置：" -ForegroundColor White
Write-Host '   "ensp-draw": {' -ForegroundColor Gray
Write-Host '     "command": "python",' -ForegroundColor Gray
Write-Host "     `"args`": [`"$ProjectRoot\server.py`"]" -ForegroundColor Gray
Write-Host '   }' -ForegroundColor Gray
Write-Host ""
Write-Host "3. 重启 Claude Code" -ForegroundColor White
Write-Host ""
Write-Host "查看生成的测试文件: $ProjectRoot\outputs\" -ForegroundColor Cyan
