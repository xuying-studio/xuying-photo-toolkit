param(
    [string]$Python = "py",
    [switch]$SkipTests,
    [switch]$SkipSmokeTest,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir
$AppName = "旭影的摄影工具集"
$DistDir = Join-Path $ProjectDir "dist-windows"
$BuildDir = Join-Path $ProjectDir "build-windows"
$PortableDir = Join-Path $DistDir $AppName
$ZipPath = Join-Path $DistDir "$AppName-windows-x64-portable.zip"
$SetupPath = Join-Path $DistDir "$AppName-windows-x64-setup.exe"
$ChecksumPath = Join-Path $DistDir "SHA256SUMS.txt"

if ($env:OS -ne "Windows_NT") {
    throw "Windows 安装包必须在 Windows 10/11 64 位环境中构建。"
}

$PythonArch = & $Python -c "import platform; print(platform.architecture()[0])"
if ($LASTEXITCODE -ne 0 -or $PythonArch.Trim() -ne "64bit") {
    throw "请使用 64 位 Python 构建 Windows x64 安装包。"
}

if (-not $SkipTests) {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "测试失败，停止构建。" }
}

if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
New-Item -ItemType Directory -Path $DistDir | Out-Null

& $Python -m PyInstaller --clean --noconfirm --distpath $DistDir --workpath $BuildDir photo_assistant.windows.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败。" }

$PortableExe = Join-Path $PortableDir "$AppName.exe"
if (-not (Test-Path $PortableExe)) {
    throw "构建完成后未找到主程序：$PortableExe"
}

if (-not $SkipSmokeTest) {
    $SmokeProcess = Start-Process -FilePath $PortableExe -PassThru
    Start-Sleep -Seconds 5
    if ($SmokeProcess.HasExited) {
        throw "Windows 主程序启动冒烟测试失败，退出码：$($SmokeProcess.ExitCode)"
    }
    Stop-Process -Id $SmokeProcess.Id -Force
    Wait-Process -Id $SmokeProcess.Id -ErrorAction SilentlyContinue
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $PortableDir -DestinationPath $ZipPath -CompressionLevel Optimal

if (-not $SkipInstaller) {
    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($null -ne $iscc) {
        & $iscc.Source "/DSourceDir=$PortableDir" "/DOutputDir=$DistDir" installer.iss
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup 构建失败。" }
        if (-not (Test-Path $SetupPath)) { throw "未找到安装包：$SetupPath" }
    } else {
        Write-Warning "未找到 iscc.exe，已跳过 Setup.exe；便携版 ZIP 已生成。"
    }
}

$Artifacts = @($ZipPath, $SetupPath) | Where-Object { Test-Path $_ }
$ChecksumLines = foreach ($Artifact in $Artifacts) {
    $Hash = (Get-FileHash -Algorithm SHA256 -Path $Artifact).Hash.ToLowerInvariant()
    "$Hash  $(Split-Path -Leaf $Artifact)"
}
$ChecksumLines | Set-Content -Path $ChecksumPath -Encoding utf8

Write-Host "便携版：$ZipPath"
if (Test-Path $SetupPath) { Write-Host "安装版：$SetupPath" }
Write-Host "校验值：$ChecksumPath"
