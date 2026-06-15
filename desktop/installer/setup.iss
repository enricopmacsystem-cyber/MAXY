; =============================================================================

; Maxy 2.0 - daisy — Inno Setup 6 (installer Windows)

; Prerequisito: python scripts/build_release.py

; =============================================================================



#include "version.iss"



#define MyAppURL "https://www.macsystem.it"

#define MyAppId "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

#define MyAppOutputDir "..\..\dist\installer"

#define MyAppDataDir "{userappdata}\MAC AI Assistant"

#ifexist "..\resources\app.ico"

#define MyAppIconFile "..\resources\app.ico"

#endif



[Setup]

AppId={#MyAppId}

AppName={#MyAppProductName}

AppVersion={#MyAppVersion}

AppVerName={#MyAppProductName}

AppPublisher={#MyAppPublisher}

AppPublisherURL={#MyAppURL}

AppSupportURL={#MyAppURL}

AppUpdatesURL={#MyAppURL}

AppContact={#MyAppDeveloper}

InfoBeforeFile=install_welcome.txt

DefaultDirName={autopf}\{#MyAppProductName}

DefaultGroupName={#MyAppProductName}

AllowNoIcons=no

OutputDir={#MyAppOutputDir}

OutputBaseFilename={#MyAppOutputBase}

#ifexist "..\resources\app.ico"

SetupIconFile=..\resources\app.ico

#endif

UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2/ultra64

SolidCompression=yes

WizardStyle=modern

PrivilegesRequired=lowest

ArchitecturesAllowed=x64compatible

ArchitecturesInstallIn64BitMode=x64compatible

MinVersion=10.0

DisableProgramGroupPage=no

DisableWelcomePage=no

UsePreviousAppDir=yes

CloseApplications=yes

RestartApplications=yes

ChangesAssociations=no

VersionInfoVersion={#MyAppVersionFull}

VersionInfoCompany={#MyAppPublisher}

VersionInfoDescription={#MyAppProductName} — Sviluppatore {#MyAppDeveloper}

VersionInfoProductName={#MyAppProductName}

VersionInfoProductVersion={#MyAppVersion}



[Languages]

Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

Name: "english"; MessagesFile: "compiler:Default.isl"



[Tasks]

Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce



[Types]

Name: "full"; Description: "Installazione completa"

Name: "compact"; Description: "Installazione compatta"

Name: "custom"; Description: "Installazione personalizzata"; Flags: iscustom



[Components]

Name: "main"; Description: "Applicazione {#MyAppProductName}"; Types: full compact custom; Flags: fixed



[Files]

Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

#ifexist "..\resources\app.ico"

Source: "..\resources\app.ico"; DestDir: "{app}"; Flags: ignoreversion

#endif

Source: "config.default.ini"; DestDir: "{#MyAppDataDir}"; DestName: "config.ini"; Flags: onlyifdoesntexist uninsneveruninstall

Source: "hub.env.default"; DestDir: "{#MyAppDataDir}"; DestName: "hub.env"; Flags: onlyifdoesntexist uninsneveruninstall

Source: "ensure_postgresql.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

Source: "install_postgresql.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

Source: "init_database.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

Source: "POSTGRESQL_SETUP.txt"; DestDir: "{app}\installer"; Flags: ignoreversion

Source: "..\dist\MAC_AI_Hub\*"; DestDir: "{app}\hub"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

#ifexist "redist\VC_redist.x64.exe"

Source: "redist\VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeedsInstall

#endif



[Dirs]

Name: "{#MyAppDataDir}"; Permissions: users-full

Name: "{#MyAppDataDir}\logs"; Permissions: users-full

Name: "{#MyAppDataDir}\cache"; Permissions: users-full



[Icons]

Name: "{group}\{#MyAppProductName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; WorkingDir: "{app}"; Comment: "Maxy AI — MacSystem s.r.l."

Name: "{group}\{cm:UninstallProgram,{#MyAppProductName}}"; Filename: "{uninstallexe}"

Name: "{autodesktop}\{#MyAppProductName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon; WorkingDir: "{app}"



[Run]

#ifexist "redist\VC_redist.x64.exe"

Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installazione Microsoft Visual C++ Runtime..."; Flags: waituntilterminated; Check: VCRedistNeedsInstall

#endif

Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\init_database.ps1"" -HubExe ""{app}\hub\MAC_AI_Hub.exe"""; StatusMsg: "Preparazione database locale..."; Flags: waituntilterminated runhidden skipifsilent; Check: HubNeedsInit

Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppProductName}"; Flags: nowait postinstall skipifsilent



[UninstallDelete]

Type: filesandordirs; Name: "{app}"



[Registry]

Root: HKCU; Subkey: "Software\MacSystem s.r.l.\{#MyAppProductName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\MacSystem s.r.l.\{#MyAppProductName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\MacSystem s.r.l.\{#MyAppProductName}"; ValueType: string; ValueName: "Developer"; ValueData: "{#MyAppDeveloper}"; Flags: uninsdeletekey



[Code]

function HubNeedsInit: Boolean;

begin

  Result := FileExists(ExpandConstant('{app}\hub\MAC_AI_Hub.exe'));

end;



function VCRedistNeedsInstall: Boolean;

var

  Version: String;

begin

  if not FileExists(ExpandConstant('{tmp}\VC_redist.x64.exe')) then

  begin

    Result := False;

    Exit;

  end;

  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version) then

    Result := (CompareText(Copy(Version, 2, 2), '14') < 0)

  else

    Result := True;

end;


