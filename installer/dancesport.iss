; Inno Setup script for the Windows installer, one per build flavor.
;
; Built by build_installer.bat from what build_exe.bat left in dist\, e.g.
;   ISCC.exe /DFlavor=player /DAppVersion=1.6.0 installer\dancesport.iss
; -> dist\installer\DanceSport-Player-1.6.0-setup.exe
;
; The install folder is the user's choice. Installed for all users (the
; default, admin rights for the setup only) under C:\Program Files, the app
; finds that folder read-only and keeps its data in %LOCALAPPDATA%\
; DanceSport-Planner-Player (planner.config._data_dir). A per-user install
; goes to %LOCALAPPDATA%\Programs\<name>, which takes writes, so the app keeps
; its database and settings next to the .exe as it does in a loose folder.
;
; The installer only ever writes and removes the files it ships: the
; database, the settings and the playlists the app writes beside them
; survive both an update and an uninstall.

#ifndef Flavor
  #define Flavor "lite"
#endif
#ifndef AppVersion
  #error Pass the version: /DAppVersion=1.2.3
#endif
#ifndef AppNumbers
  #define AppNumbers AppVersion
#endif

; Each flavor is an app of its own for Windows: its own AppId (never change
; one, Windows finds an installed copy by it), its own folder and its own entry
; in Apps & features, so the player and the planner can be installed side by side.
#if Flavor == "player"
  #define AppName "DanceSport-Player"
  #define AppDisplayName "DanceSport Player"
  #define AppGuid "AAFE0720-EE5E-4413-8104-7B048C563E4A"
#elif Flavor == "full"
  #define AppName "DanceSport-Planner-Player-Full"
  #define AppDisplayName "DanceSport Planner & Player (Full)"
  #define AppGuid "47A2BDEE-4B94-454E-9D37-5B9CFA1CFD1F"
#elif Flavor == "lite"
  #define AppName "DanceSport-Planner-Player"
  #define AppDisplayName "DanceSport Planner & Player"
  #define AppGuid "35484153-2577-43C8-AFC5-C56820245D62"
#else
  #error Unknown flavor: use lite, full or player
#endif

#define AppExe AppName + ".exe"
#define Source "..\dist\" + AppName
; The ID the app gives itself (APP_USER_MODEL_ID in gui/common.py) — change
; both together. A shortcut without it is not the running app to the taskbar,
; so a pin made from the running window came out as a white box.
#define AppUserModelID "danceplaylist.ai.planner.v3"

[Setup]
AppId={{{#AppGuid}}
AppName={#AppDisplayName}
AppVersion={#AppVersion}
AppVerName={#AppDisplayName} {#AppVersion}
AppPublisher=marcelkb
VersionInfoVersion={#AppNumbers}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppDisplayName}
; The folder page is shown on every install: the point of this installer is
; that the user picks where the app goes. An update proposes the folder the
; app is already in.
DisableDirPage=no
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
; For all users under C:\Program Files, with admin rights; the start offers a
; per-user install instead.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename={#AppName}-{#AppVersion}-setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppDisplayName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; A running copy holds its files open: ask to close it rather than fail.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; The bundled runtime of the previous version. Its file names change with the
; libraries, and a leftover DLL beside the new ones is dead weight at best.
; Nothing the app writes lives in _internal.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
; Named one by one, not dist\<name>\*: a build folder the app was started from
; holds that user's database and settings, which must never ship.
Source: "{#Source}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Source}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Source}\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#Source}\Manual.pdf"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#Source}\Handbuch.pdf"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#Source}\Licenses\*"; DestDir: "{app}\Licenses"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#AppDisplayName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppDisplayName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "{#AppUserModelID}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppDisplayName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runasoriginaluser
; runasoriginaluser above: started as admin, the app would find Program Files
; writable and keep its data there, apart from where every later start looks.
