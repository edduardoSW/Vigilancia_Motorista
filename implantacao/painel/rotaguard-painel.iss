; RotaGuard Painel · instalador por usuário, sem pedir administrador (spec 013).
; Compilado pelo build.py quando o Inno Setup está instalado:
;   ISCC /DVersao=0.1.0 /DOrigem=<build\painel\dist\RotaGuardPainel> /DSaida=<build\painel\pacotes> rotaguard-painel.iss
; O app precisa do Microsoft Edge WebView2 Runtime (vem no Windows 11; no Windows 10 pode faltar).

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Origem
  #define Origem "..\..\build\painel\dist\RotaGuardPainel"
#endif
#ifndef Saida
  #define Saida "..\..\build\painel\pacotes"
#endif

[Setup]
AppId={{BD6074D9-27C4-4061-A9DA-BD18A01C9CED}
AppName=RotaGuard Painel
AppVersion={#Versao}
AppVerName=RotaGuard Painel {#Versao}
AppPublisher=RotaGuard
AppCopyright=© 2026 RotaGuard
VersionInfoVersion={#Versao}
VersionInfoCompany=RotaGuard
VersionInfoDescription=Instalador do RotaGuard Painel
VersionInfoProductName=RotaGuard Painel
VersionInfoProductVersion={#Versao}
VersionInfoCopyright=© 2026 RotaGuard
DefaultDirName={localappdata}\Programs\RotaGuard Painel
DefaultGroupName=RotaGuard
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Saida}
OutputBaseFilename=RotaGuard-Painel-windows-x64-setup
SetupIconFile=..\app-teste\rotaguard.ico
UninstallDisplayIcon={app}\RotaGuardPainel.exe
UninstallDisplayName=RotaGuard Painel
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
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
Name: "{autoprograms}\RotaGuard Painel"; Filename: "{app}\RotaGuardPainel.exe"
Name: "{autodesktop}\RotaGuard Painel"; Filename: "{app}\RotaGuardPainel.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RotaGuardPainel.exe"; Description: "{cm:LaunchProgram,RotaGuard Painel}"; Flags: nowait postinstall skipifsilent
