; 旭影的摄影工具集 Windows per-user 安装配置
#define AppName "旭影的摄影工具集"
#define AppVersion "1.0.14"
#define AppPublisher "旭影"
#define AppExeName "旭影的摄影工具集.exe"

#ifndef SourceDir
  #define SourceDir "dist-windows\旭影的摄影工具集"
#endif
#ifndef OutputDir
  #define OutputDir "dist-windows"
#endif

[Setup]
AppId={{B3C3A6D9-9EE2-4DDC-9B4A-7A0A6E2A1D10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-windows-x64-setup
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayName={#AppName}
VersionInfoVersion=1.0.14.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Windows 安装程序

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
