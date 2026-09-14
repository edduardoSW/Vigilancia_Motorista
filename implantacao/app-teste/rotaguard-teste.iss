; RotaGuard Teste · instalador por usuário, sem pedir administrador (spec 010).
; Compilado pelo build.py:
;   ISCC /DVersao=0.1.0 /DOrigem=<build\app-teste\dist\RotaGuardTeste> /DSaida=<build\app-teste\pacotes> rotaguard-teste.iss

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Origem
  #define Origem "..\..\build\app-teste\dist\RotaGuardTeste"
#endif
#ifndef Saida
  #define Saida "..\..\build\app-teste\pacotes"
#endif

[Setup]
AppId={{4F0C8B7E-9A61-4D3B-8E57-2C1B6A9D0F31}
AppName=RotaGuard Teste
AppVersion={#Versao}
AppVerName=RotaGuard Teste {#Versao}
AppPublisher=RotaGuard
AppCopyright=© 2026 RotaGuard
VersionInfoVersion={#Versao}
VersionInfoCompany=RotaGuard
VersionInfoDescription=Instalador do RotaGuard Teste
VersionInfoProductName=RotaGuard Teste
VersionInfoProductVersion={#Versao}
VersionInfoCopyright=© 2026 RotaGuard
DefaultDirName={localappdata}\Programs\RotaGuard Teste
DefaultGroupName=RotaGuard
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Saida}
OutputBaseFilename=RotaGuard-Teste-windows-x64-setup
SetupIconFile=rotaguard.ico
UninstallDisplayIcon={app}\RotaGuardTeste.exe
UninstallDisplayName=RotaGuard Teste
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
Name: "{autoprograms}\RotaGuard Teste"; Filename: "{app}\RotaGuardTeste.exe"
Name: "{autodesktop}\RotaGuard Teste"; Filename: "{app}\RotaGuardTeste.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RotaGuardTeste.exe"; Description: "{cm:LaunchProgram,RotaGuard Teste}"; Flags: nowait postinstall skipifsilent
