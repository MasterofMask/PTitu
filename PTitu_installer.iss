; ==============================================================
;  PTitu_installer.iss
;  Organizador de Fotografías
;  Herramienta: Inno Setup 6.x  (open source)
;  
;
;  Uso:
;    1. Instala Inno Setup 6 desde la URL anterior
;    2. Abre este archivo en el IDE de Inno Setup
;    3. Pulsa F9 (Build) o usa el menú Build > Compile
;    4. El instalador se genera en la carpeta Output\
;
;  También se puede compilar desde línea de comandos:
;    iscc PTitu_installer.iss
;  O con el build.py incluido:
;    python build.py
; ==============================================================

#define AppName        "Organizador de colecciones fotograficas"
#define AppVersion     "1.0.0"
#define AppPublisher   "Universidad Autónoma de Ciudad Juárez"
#define AppExeName     "organizador.exe"
#define AppDescription "Organizador de Fotografías con redes"
#define OutputBase     "Organizador_Setup"

[Setup]
; ── Identificadores únicos ────────────────────────────────────────────────
; Genera el tuyo en: https://www.guidgenerator.com/
AppId                    = {{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName                  = {#AppName}
AppVersion               = {#AppVersion}
AppVerName               = {#AppName} {#AppVersion}
AppPublisher             = {#AppPublisher}
AppCopyright             = © 2025 {#AppPublisher}
AppComments              = {#AppDescription}

; ── Rutas ─────────────────────────────────────────────────────────────────
DefaultDirName           = {autopf}\{#AppName}
DefaultGroupName         = {#AppName}
OutputDir                = Output
OutputBaseFilename       = {#OutputBase}_{#AppVersion}_Windows_x64
UninstallDisplayIcon     = {app}\{#AppExeName}
UninstallDisplayName     = {#AppName} {#AppVersion}

; ── Apariencia ────────────────────────────────────────────────────────────
; WizardStyle moderno (requiere Inno Setup 6+)
WizardStyle              = modern
WizardSizePercent        = 110
WizardResizable          = no

; ── Compresión ────────────────────────────────────────────────────────────
; LZMA2 es el estándar en instaladores open source (igual que 7-Zip)
Compression              = lzma2/ultra64
SolidCompression         = yes
LZMAUseSeparateProcess   = yes
LZMANumBlockThreads      = 4

; ── Plataforma ────────────────────────────────────────────────────────────
ArchitecturesAllowed            = x64compatible
ArchitecturesInstallIn64BitMode = x64compatible
MinVersion                      = 10.0.17763
; Windows 10 versión 1809 mínimo (por compatibilidad con PyQt5 y PyTorch)

; ── Privilegios ───────────────────────────────────────────────────────────
; "lowest" instala sin necesitar permisos de administrador
; Cambia a "admin" si necesitas instalar para todos los usuarios
PrivilegesRequired       = lowest
PrivilegesRequiredOverridesAllowed = dialog

; ── Otros ─────────────────────────────────────────────────────────────────
DisableProgramGroupPage  = yes
DisableWelcomePage       = no
AllowNoIcons             = yes
ChangesAssociations      = no
RestartIfNeededByRun     = no

; ── Idioma de la bienvenida ───────────────────────────────────────────────
; El instalador detecta el idioma del sistema automáticamente
ShowLanguageDialog       = auto

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── Mensajes personalizados ───────────────────────────────────────────────
[CustomMessages]
spanish.WelcomeLabel2=Este asistente instalará [name/ver] en tu equipo.%n%nPTitu organiza automáticamente tu colección de fotos usando reconocimiento facial y clasificación de escenas por IA, sin necesitar conexión a internet.%n%nSe recomienda cerrar todas las demás aplicaciones antes de continuar.
english.WelcomeLabel2=This wizard will install [name/ver] on your computer.%n%nPTitu automatically organizes your photo collection using facial recognition and AI scene classification, without requiring an internet connection.%n%nIt is recommended to close all other applications before continuing.

spanish.FinishedHeadingLabel=Instalación de [name] completada
english.FinishedHeadingLabel=[name] installation complete

spanish.FinishedLabel=La instalación de [name] ha terminado correctamente.%n%nHaz clic en Finalizar para cerrar el asistente.
english.FinishedLabel=[name] has been successfully installed.%n%nClick Finish to close this wizard.

; ── Tipos y componentes ───────────────────────────────────────────────────
[Types]
Name: "full";    Description: "Instalación completa"
Name: "compact"; Description: "Instalación mínima (sin accesos directos extras)"
Name: "custom";  Description: "Instalación personalizada"; Flags: iscustom

[Components]
Name: "main";       Description: "Aplicación PTitu (requerido)";         Types: full compact custom; Flags: fixed
Name: "shortcuts";  Description: "Accesos directos (escritorio y menú)"; Types: full
Name: "readme";     Description: "Incluir instrucciones de uso (README)"; Types: full

; ── Archivos a instalar ───────────────────────────────────────────────────
[Files]
; Ejecutable principal y todas sus dependencias (carpeta dist\PTitu\)
Source: "dist\PTitu\*";               DestDir: "{app}";              \
        Flags: ignoreversion recursesubdirs createallsubdirs;        \
        Components: main

; Modelo de IA — VGG-16 entrenado para clasificación de escenas
Source: "data\models\vgg16_scene_classifier.pth"; \
        DestDir: "{app}\data\models";              \
        Flags: ignoreversion;                      \
        Components: main

Source: "data\models\training_history.json";      \
        DestDir: "{app}\data\models";              \
        Flags: ignoreversion;                      \
        Components: main

; Iconos SVG de la interfaz
Source: "src\ui\icons\*.svg";         DestDir: "{app}\src\ui\icons"; \
        Flags: ignoreversion;                      \
        Components: main

Source: "src\ui\icons\ptitu.ico";     DestDir: "{app}\src\ui\icons"; \
        Flags: ignoreversion skipifsourcedoesntexist; \
        Components: main

; Script de instalación de dependencias Python (modo desarrollo)
Source: "install_deps.bat";           DestDir: "{app}";              \
        Flags: ignoreversion;                      \
        Components: main

Source: "requirements.txt";           DestDir: "{app}";              \
        Flags: ignoreversion;                      \
        Components: main

; Documentación
Source: "README.txt";                 DestDir: "{app}";              \
        Flags: ignoreversion ;             \
        Components: readme

Source: "LICENSE.txt";                DestDir: "{app}";              \
        Flags: ignoreversion;                      \
        Components: main

; ── Accesos directos ──────────────────────────────────────────────────────
[Icons]
; Escritorio
Name: "{autodesktop}\{#AppName}";        \
      Filename: "{app}\{#AppExeName}";   \
      Comment: "{#AppDescription}";      \
      IconFilename: "{app}\src\ui\icons\ptitu.ico"; \
      Components: shortcuts

; Menú Inicio
Name: "{autoprograms}\{#AppName}\{#AppName}"; \
      Filename: "{app}\{#AppExeName}";   \
      Comment: "{#AppDescription}";      \
      IconFilename: "{app}\src\ui\icons\ptitu.ico"; \
      Components: shortcuts

Name: "{autoprograms}\{#AppName}\Desinstalar {#AppName}"; \
      Filename: "{uninstallexe}";        \
      Components: shortcuts

; ── Entradas de registro ──────────────────────────────────────────────────
; Solo información de "Agregar o quitar programas" — sin cambios en el sistema
[Registry]
Root: HKCU; Subkey: "Software\{#AppPublisher}\{#AppName}"; \
      ValueType: string; ValueName: "InstallDir"; \
      ValueData: "{app}"; \
      Flags: uninsdeletekey

; ── Ejecución post-instalación ────────────────────────────────────────────
[Run]
; Opción para abrir PTitu al terminar (checkbox en última página)
Filename: "{app}\{#AppExeName}";       \
          Description: "Iniciar {#AppName} ahora";  \
          Flags: nowait postinstall skipifsilent;    \
          Components: main

; Opción para ver el README
Filename: "{app}\README.txt";          \
          Description: "Ver instrucciones de uso";  \
          Flags: shellexec postinstall skipifsilent unchecked; \
          Components: readme

; ── Código Pascal para validaciones extra ─────────────────────────────────
[Code]

{ ── Variables globales ──────────────────────────────────────────────── }
var
  PythonPath:    string;
  PythonFound:   Boolean;
  PythonVersion: string;

{ ── Buscar Python 3.10+ en el sistema ───────────────────────────────── }
function FindPython: Boolean;
var
  RegKey: string;
  ExePath: string;
  i: Integer;
  Versions: array[0..5] of string;
begin
  Result := False;
  PythonPath := '';
  PythonVersion := '';

  { Versiones a buscar, en orden de preferencia }
  Versions[0] := '3.10';
  Versions[1] := '3.11';
  Versions[2] := '3.12';
  Versions[3] := '3.9';
  Versions[4] := '3.8';
  Versions[5] := '3.13';

  for i := 0 to 5 do
  begin
    { Buscar en registro de usuario (HKCU) }
    RegKey := 'Software\Python\PythonCore\' + Versions[i] + '\InstallPath';
    if RegQueryStringValue(HKCU, RegKey, 'ExecutablePath', ExePath) then
    begin
      if FileExists(ExePath) then
      begin
        PythonPath := ExePath;
        PythonVersion := Versions[i];
        Result := True;
        Exit;
      end;
    end;

    { Buscar en registro del sistema (HKLM) }
    if RegQueryStringValue(HKLM, RegKey, 'ExecutablePath', ExePath) then
    begin
      if FileExists(ExePath) then
      begin
        PythonPath := ExePath;
        PythonVersion := Versions[i];
        Result := True;
        Exit;
      end;
    end;
  end;

  { Fallback: buscar python.exe en PATH }
  ExePath := ExpandConstant('{sys}') + '\python.exe';
  if FileExists(ExePath) then
  begin
    PythonPath := ExePath;
    PythonVersion := 'desconocida';
    Result := True;
  end;
end;

{ ── Al iniciar el instalador ────────────────────────────────────────── }
function InitializeSetup: Boolean;
begin
  Result := True;
  PythonFound := FindPython;
end;

{ ── Página de bienvenida personalizada ──────────────────────────────── }
procedure CurPageChanged(CurPageID: Integer);
begin
  { Al llegar a la página de componentes, mostrar info de Python }
  if CurPageID = wpSelectComponents then
  begin
    if PythonFound then
      WizardForm.StatusLabel.Caption :=
        '✓ Python ' + PythonVersion + ' detectado en el sistema.'
    else
      WizardForm.StatusLabel.Caption :=
        'Python no detectado. Modo desarrollo no disponible sin Python 3.10+.';
  end;
end;

{ ── Antes de instalar: verificar espacio en disco ───────────────────── }
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

{ ── Mensaje de desinstalación con opción de conservar datos ─────────── }
function InitializeUninstall: Boolean;
begin
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
  Answer: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{app}\data');

    if DirExists(DataDir) then
    begin
      Answer := MsgBox(
        'PTitu ha sido desinstalado.' + #13#10 + #13#10 +
        '¿Deseas conservar la base de datos y los modelos?' + #13#10 +
        '(Tus fotos originales no serán afectadas en ningún caso)' + #13#10 + #13#10 +
        'Carpeta: ' + DataDir,
        mbConfirmation, MB_YESNO
      );

      if Answer = IDNO then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
