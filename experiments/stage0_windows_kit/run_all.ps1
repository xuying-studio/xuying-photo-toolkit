$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Results = Join-Path $Root "results"
$Work = Join-Path $Root "work"
$Input = Join-Path $Root "input\real"
New-Item -ItemType Directory -Force $Results, $Work | Out-Null

$summary = [ordered]@{
    platform = "Windows"
    started_at = (Get-Date).ToString("o")
    keyword = ""
    input_count = 0
    steps = @()
}

function Record-Step($Name, $Status, $Detail, $Data = $null) {
    $item = [ordered]@{ name = $Name; status = $Status; detail = $Detail }
    if ($null -ne $Data) { $item.data = $Data }
    $script:summary.steps += $item
}

function Save-Summary {
    $script:summary.finished_at = (Get-Date).ToString("o")
    $script:summary | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $Results "summary.json") -Encoding UTF8
}

function Directory-Bytes($Path) {
    if (-not (Test-Path $Path)) { return 0 }
    $measure = Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum
    return [int64]($measure.Sum)
}

$BasePython = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $candidate = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0) { $BasePython = ($candidate | Select-Object -First 1).Trim() }
}
if (-not $BasePython -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $candidate = & python -c "import sys; assert sys.version_info[:2] == (3, 12); print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0) { $BasePython = ($candidate | Select-Object -First 1).Trim() }
}
if (-not $BasePython) {
    Record-Step "python" "failed" "未找到 Python 3.12；没有自动安装系统软件。"
    Save-Summary
    exit 1
}
$PythonVersion = & $BasePython --version 2>&1
Record-Step "python" "passed" "$PythonVersion" @{ executable = $BasePython }

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $BasePython -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) {
        Record-Step "venv" "failed" "无法创建本地 .venv。"
        Save-Summary
        exit 1
    }
    Record-Step "venv" "passed" "已创建本地 .venv。"
} else {
    Record-Step "venv" "passed" "复用现有本地 .venv。"
}

& $VenvPython -m pip install --upgrade pip 2>&1 |
    Set-Content (Join-Path $Results "pip-upgrade.log") -Encoding UTF8
& $VenvPython -m pip install -r (Join-Path $Root "requirements-windows.txt") 2>&1 |
    Set-Content (Join-Path $Results "pip-install.log") -Encoding UTF8
$DependencyExit = $LASTEXITCODE
Record-Step "dependencies" $(if ($DependencyExit -eq 0) { "passed" } else { "failed" }) "固定版本依赖；详情见 pip-install.log。"

& $VenvPython -m pip install `
    "winrt-runtime==3.2.1" `
    "winrt-Windows.Foundation==3.2.1" `
    "winrt-Windows.Globalization==3.2.1" `
    "winrt-Windows.Graphics.Imaging==3.2.1" `
    "winrt-Windows.Media.Ocr==3.2.1" `
    "winrt-Windows.Storage.Streams==3.2.1" `
    2>&1 | Set-Content (Join-Path $Results "pywinrt-install.log") -Encoding UTF8
$PyWinRTExit = $LASTEXITCODE
Record-Step "pywinrt" $(if ($PyWinRTExit -eq 0) { "passed" } else { "failed" }) "Windows.Media.Ocr Python 投影；详情见 pywinrt-install.log。"

$Keyword = (Get-Content (Join-Path $Root "keyword.txt") -Raw -Encoding UTF8).Trim()
if (-not $Keyword) { $Keyword = "AGI" }
$summary.keyword = $Keyword
$InputFiles = @(
    Get-ChildItem $Input -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension.ToLowerInvariant() -in @(".jpg", ".jpeg", ".png", ".heic") }
)
$summary.input_count = $InputFiles.Count
Record-Step "input" $(if ($InputFiles.Count -gt 0) { "passed" } else { "failed" }) "支持的图片数量：$($InputFiles.Count)；隐藏文件不计入。"

$RapidResult = Join-Path $Results "ocr-rapidocr.json"
& $VenvPython (Join-Path $Root "ocr_benchmark.py") `
    --backend rapidocr --input-dir $Input --keyword $Keyword --output $RapidResult
$RapidExit = $LASTEXITCODE
Record-Step "ocr-rapidocr" $(if ($RapidExit -eq 0) { "passed" } else { "failed" }) "结果：ocr-rapidocr.json"

$NativeResult = Join-Path $Results "ocr-windows-media.json"
& $VenvPython (Join-Path $Root "ocr_benchmark.py") `
    --backend windows_media_ocr --input-dir $Input --keyword $Keyword --output $NativeResult
$NativeExit = $LASTEXITCODE
Record-Step "ocr-windows-media" $(if ($NativeExit -eq 0) { "passed" } else { "failed" }) "结果：ocr-windows-media.json；失败信息也会写入 JSON。"

$PyInstallerRoot = Join-Path $Work "pyinstaller"
New-Item -ItemType Directory -Force $PyInstallerRoot | Out-Null
& $VenvPython -m PyInstaller `
    --noconfirm --clean --windowed --onedir `
    --name XuyingStage0Proof `
    --add-data "$Root\qml\Main.qml;." `
    --distpath "$PyInstallerRoot\dist" `
    --workpath "$PyInstallerRoot\build" `
    --specpath "$PyInstallerRoot\spec" `
    "$Root\qml\main.py" `
    2>&1 | Set-Content (Join-Path $Results "pyinstaller.log") -Encoding UTF8
$PyInstallerBuildExit = $LASTEXITCODE
$PyInstallerExe = Join-Path $PyInstallerRoot "dist\XuyingStage0Proof\XuyingStage0Proof.exe"
$PyInstallerLaunchExit = $null
if ($PyInstallerBuildExit -eq 0 -and (Test-Path $PyInstallerExe)) {
    $process = Start-Process -FilePath $PyInstallerExe -Wait -PassThru
    $PyInstallerLaunchExit = $process.ExitCode
}
$PyInstallerPassed = $PyInstallerBuildExit -eq 0 -and $PyInstallerLaunchExit -eq 0
$PyInstallerBytes = Directory-Bytes (Join-Path $PyInstallerRoot "dist\XuyingStage0Proof")
Record-Step "pyinstaller" $(if ($PyInstallerPassed) { "passed" } else { "failed" }) "构建并启动最小 QML 包。" @{
    build_exit = $PyInstallerBuildExit
    launch_exit = $PyInstallerLaunchExit
    bytes = $PyInstallerBytes
    executable = $PyInstallerExe
}

$Dumpbin = Get-Command dumpbin -ErrorAction SilentlyContinue
Record-Step "dumpbin" $(if ($Dumpbin) { "passed" } else { "missing" }) $(if ($Dumpbin) { $Dumpbin.Source } else { "pyside6-deploy 可能需要 Visual Studio Build Tools；不会自动安装。" })
$DeployExe = Join-Path $Root ".venv\Scripts\pyside6-deploy.exe"
$PySideLog = Join-Path $Results "pyside6-deploy.log"
$PySideBuildExit = $null
$PySideLaunchExit = $null
$PySideArtifact = $null
if (Test-Path $DeployExe) {
    Push-Location (Join-Path $Root "qml")
    & $DeployExe main.py --name XuyingStage0ProofOfficial --mode standalone --nuitka-version 4.1.2 -f 2>&1 |
        Set-Content $PySideLog -Encoding UTF8
    $PySideBuildExit = $LASTEXITCODE
    Pop-Location
    if ($PySideBuildExit -eq 0) {
        $PySideArtifact = Get-ChildItem (Join-Path $Root "qml") -Recurse -Filter "*.exe" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($PySideArtifact) {
            $process = Start-Process -FilePath $PySideArtifact.FullName -Wait -PassThru
            $PySideLaunchExit = $process.ExitCode
        }
    }
} else {
    "pyside6-deploy.exe 不存在。" | Set-Content $PySideLog -Encoding UTF8
}
$PySidePassed = $PySideBuildExit -eq 0 -and $PySideLaunchExit -eq 0
$PySideBytes = 0
$PySideExecutable = $null
if ($PySideArtifact) {
    $PySideBytes = Directory-Bytes $PySideArtifact.Directory.FullName
    $PySideExecutable = $PySideArtifact.FullName
}
Record-Step "pyside6-deploy" $(if ($PySidePassed) { "passed" } elseif ($null -eq $PySideBuildExit) { "skipped" } else { "failed" }) "官方路径构建并启动；详情见 pyside6-deploy.log。" @{
    build_exit = $PySideBuildExit
    launch_exit = $PySideLaunchExit
    bytes = $PySideBytes
    executable = $PySideExecutable
}

Save-Summary
Write-Host "阶段 0 Windows 验证结束。请把 results 文件夹复制回 Mac。"
