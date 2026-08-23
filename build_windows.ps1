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

function Test-GuiExecutable {
    param(
        [string]$ExecutablePath,
        [string]$Label,
        [string]$ScreenshotPath = ""
    )

    $Process = Start-Process -FilePath $ExecutablePath -PassThru
    Start-Sleep -Seconds 5
    if ($Process.HasExited) {
        throw "$Label 启动冒烟测试失败，退出码：$($Process.ExitCode)"
    }
    if ($ScreenshotPath) {
        Add-Type -AssemblyName System.Drawing
        Add-Type -AssemblyName System.Windows.Forms
        $Bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $Bitmap = New-Object System.Drawing.Bitmap $Bounds.Width, $Bounds.Height
        $Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
        $Graphics.CopyFromScreen(
            $Bounds.Location,
            [System.Drawing.Point]::Empty,
            $Bounds.Size
        )
        $Bitmap.Save($ScreenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $Graphics.Dispose()
        $Bitmap.Dispose()
        if (-not (Test-Path $ScreenshotPath)) { throw "Windows 界面截图失败。" }
    }
    Stop-Process -Id $Process.Id -Force
    Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
}

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
    $SmokeScreenshot = Join-Path $DistDir "windows-smoke.png"
    Test-GuiExecutable `
        -ExecutablePath $PortableExe `
        -Label "Windows 便携版" `
        -ScreenshotPath $SmokeScreenshot
}

& $Python scripts/create_portable_zip.py $PortableDir $ZipPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ZipPath)) {
    throw "便携版 ZIP 生成失败。"
}

if (-not $SkipInstaller) {
    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($null -ne $iscc) {
        & $iscc.Source "/DSourceDir=$PortableDir" "/DOutputDir=$DistDir" installer.iss
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup 构建失败。" }
        if (-not (Test-Path $SetupPath)) { throw "未找到安装包：$SetupPath" }
        if (-not $SkipSmokeTest) {
            $SmokeInstallDir = Join-Path $env:TEMP "xuying-photo-toolkit-smoke-$PID"
            $SetupProcess = Start-Process -FilePath $SetupPath -ArgumentList @(
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/SP-",
                "/DIR=$SmokeInstallDir"
            ) -Wait -PassThru
            if ($SetupProcess.ExitCode -ne 0) { throw "Windows 安装版静默安装测试失败。" }
            $InstalledExe = Join-Path $SmokeInstallDir "$AppName.exe"
            if (-not (Test-Path $InstalledExe)) { throw "安装后未找到主程序。" }
            Test-GuiExecutable -ExecutablePath $InstalledExe -Label "Windows 安装版"
            $Uninstaller = Join-Path $SmokeInstallDir "unins000.exe"
            if (Test-Path $Uninstaller) {
                $UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList @(
                    "/VERYSILENT",
                    "/SUPPRESSMSGBOXES",
                    "/NORESTART"
                ) -Wait -PassThru
                if ($UninstallProcess.ExitCode -ne 0) { throw "Windows 安装版卸载测试失败。" }
            }
        }
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
