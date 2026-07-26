# Visio Draw MCP 快速诊断脚本

Write-Host "=== Visio Draw MCP 诊断 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
Write-Host "[1/6] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python 未安装或不在 PATH 中" -ForegroundColor Red
    exit 1
}

# 2. 检查依赖
Write-Host "[2/6] 检查依赖..." -ForegroundColor Yellow
$requiredPackages = @("mcp", "pydantic", "pywin32")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>$null
    if ($installed) {
        Write-Host "  ✓ $package 已安装" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $package 未安装" -ForegroundColor Red
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host ""
    Write-Host "缺少依赖，是否现在安装？(Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        pip install $missingPackages
    } else {
        Write-Host "请手动安装: pip install $($missingPackages -join ' ')" -ForegroundColor Red
        exit 1
    }
}

# 3. 检查图标库
Write-Host "[3/6] 检查图标库..." -ForegroundColor Yellow
$stencilFiles = Get-ChildItem -Path "stencils" -Filter "*.vss*" -ErrorAction SilentlyContinue
if ($stencilFiles.Count -eq 0) {
    Write-Host "  ✗ stencils 目录为空" -ForegroundColor Red
    Write-Host "  提示: 运行以下命令复制图标库:" -ForegroundColor Yellow
    Write-Host '  Copy-Item "..\华为官方网络拓扑图标库（2019年10月）\*.vss" "stencils\"' -ForegroundColor Gray
} else {
    Write-Host "  ✓ 找到 $($stencilFiles.Count) 个图标库文件" -ForegroundColor Green
    foreach ($file in $stencilFiles) {
        Write-Host "    - $($file.Name)" -ForegroundColor Gray
    }
}

# 4. 测试 driver 导入
Write-Host "[4/6] 测试驱动模块导入..." -ForegroundColor Yellow
$driverTest = @"
from visio_driver import list_stencils, _visio_session, _add_textbox, _set_cell, _find_master_by_keyword
result = list_stencils()
print(f"OK: {result['ok']}, Count: {len(result['stencils'])}")
"@
try {
    $result = python -c $driverTest 2>&1
    if ($result -match "OK: True") {
        Write-Host "  ✓ $result" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $result" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ 测试失败: $_" -ForegroundColor Red
}

# 5. 测试 Visio COM
Write-Host "[5/6] 测试 Visio COM..." -ForegroundColor Yellow
$comTest = @"
import pythoncom, win32com.client
pythoncom.CoInitialize()
try:
    visio = win32com.client.Dispatch('Visio.Application')
    visio.Visible = False
    print('Visio COM OK')
    visio.Quit()
except Exception as e:
    print(f'Visio COM Error: {e}')
finally:
    pythoncom.CoUninitialize()
"@
try {
    $result = python -c $comTest 2>&1
    if ($result -match "Visio COM OK") {
        Write-Host "  ✓ Visio COM 可用" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $result" -ForegroundColor Red
        Write-Host "  提示: 确保已安装 Microsoft Visio" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ 测试失败: $_" -ForegroundColor Red
}

# 6. 检查 Claude Code 配置
Write-Host "[6/6] 检查 Claude Code 配置..." -ForegroundColor Yellow
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
    if ($config.mcpServers."visio-draw") {
        Write-Host "  ✓ visio-draw 配置已存在" -ForegroundColor Green
        $serverPath = $config.mcpServers."visio-draw".args[0]
        Write-Host "    路径: $serverPath" -ForegroundColor Gray
    } else {
        Write-Host "  ✗ 未找到 visio-draw 配置" -ForegroundColor Red
        Write-Host "  提示: 在 $configPath 中添加 visio-draw 配置" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Claude Code 配置文件不存在: $configPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 诊断完成 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "配置参考 (stdio 模式):" -ForegroundColor Yellow
Write-Host '{' -ForegroundColor White
Write-Host '  "mcpServers": {' -ForegroundColor White
Write-Host '    "visio-draw": {' -ForegroundColor White
Write-Host '      "command": "python",' -ForegroundColor White
Write-Host '      "args": ["' -NoNewline -ForegroundColor White
Write-Host "$PWD\server.py" -NoNewline -ForegroundColor Gray
Write-Host '"]' -ForegroundColor White
Write-Host '    }' -ForegroundColor White
Write-Host '  }' -ForegroundColor White
Write-Host '}' -ForegroundColor White
Write-Host ""
Write-Host "下一步: 重启 Claude Code，然后输入 '列出可用的 Visio 图标库'" -ForegroundColor Yellow
