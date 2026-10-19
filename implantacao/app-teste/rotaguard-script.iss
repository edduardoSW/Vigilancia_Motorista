; RotaGuard Script · instalador por usuário, sem pedir administrador (spec 010).
; Compilado pelo build.py:
;   ISCC /DVersao=0.1.0 /DOrigem=<build\app-teste\dist\RotaGuardScript> /DSaida=<build\app-teste\pacotes> rotaguard-script.iss

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Origem
  #define Origem "..\..\build\app-teste\dist\RotaGuardScript"
#endif
#ifndef Saida
  #define Saida "..\..\build\app-teste\pacotes"
#endif

[Setup]
AppId={{4F0C8B7E-9A61-4D3B-8E57-2C1B6A9D0F31}
AppName=RotaGuard Script
AppVersion={#Versao}
AppVerName=RotaGuard Script {#Versao}
AppPublisher=RotaGuard
AppCopyright=© 2026 RotaGuard
VersionInfoVersion={#Versao}
VersionInfoCompany=RotaGuard
VersionInfoDescription=Instalador do RotaGuard Script
VersionInfoProductName=RotaGuard Script
VersionInfoProductVersion={#Versao}
VersionInfoCopyright=© 2026 RotaGuard
DefaultDirName={localappdata}\Programs\RotaGuard Script
DefaultGroupName=RotaGuard
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Saida}
OutputBaseFilename=RotaGuard-Script-windows-x64-setup
SetupIconFile=rotaguard.ico
UninstallDisplayIcon={app}\RotaGuardScript.exe
UninstallDisplayName=RotaGuard Script
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\RotaGuard Script"; Filename: "{app}\RotaGuardScript.exe"
Name: "{autodesktop}\RotaGuard Script"; Filename: "{app}\RotaGuardScript.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RotaGuardScript.exe"; Description: "{cm:LaunchProgram,RotaGuard Script}"; Flags: nowait postinstall skipifsilent
