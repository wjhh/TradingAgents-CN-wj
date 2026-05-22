# TradingAgents-CN-wj Web 应用启动脚本
# 使用方法: 右键此文件 -> "使用 PowerShell 运行"，或在终端中执行 .\start_web.ps1

$env:PYTHONIOENCODING = 'utf-8'
$projectDir = "C:\Work\Tra\TradingAgents-CN-wj"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TradingAgents-CN-wj Web 启动器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查项目目录
if (-not (Test-Path $projectDir)) {
    Write-Host "错误: 未找到项目目录 $projectDir" -ForegroundColor Red
    Write-Host "请确认路径正确后重试" -ForegroundColor Yellow
    pause
    exit 1
}

Set-Location $projectDir

# 检查 .env 是否存在
if (-not (Test-Path ".env")) {
    Write-Host "警告: 未找到 .env 文件" -ForegroundColor Yellow
    Write-Host "正在从 .env.example 复制..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "已创建 .env，请编辑填入 API Key 后重新运行" -ForegroundColor Green
    notepad .env
    pause
    exit 0
}

# 检查 Python 是否可用
try {
    $pyVersion = python --version 2>&1
    Write-Host "Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "项目目录: $projectDir" -ForegroundColor Gray
Write-Host ""

# 启动 Web 应用
Write-Host "正在启动 Web 应用..." -ForegroundColor Green
Write-Host "浏览器将打开 http://localhost:8501" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host ""

python -X utf8 web/run_web.py

# 如果上面失败了，尝试直接启动 streamlit
if ($LASTEXITCODE -ne 0) {
    Write-Host "备用方式启动..." -ForegroundColor Yellow
    python -X utf8 -m streamlit run web/app.py --server.port 8501 --server.address localhost
}

pause