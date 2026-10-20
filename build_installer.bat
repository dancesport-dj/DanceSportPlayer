@echo off
rem Wrap a finished build into a Windows installer (Inno Setup 6).
rem   build_installer.bat        -> lite   (from dist\DanceSport-Planner-Player)
rem   build_installer.bat full   -> full   (from dist\DanceSport-Planner-Player-Full)
rem   build_installer.bat player -> player (from dist\DanceSport-Player)
rem A build from another commit is built again first. The setup lands in
rem dist\installer\<name>-<version>-setup.exe; see installer\dancesport.iss.
rem Plain ASCII on purpose - this prints through a cp1252 Windows console.
setlocal
cd /d "%~dp0"

set FLAVOR=lite
set APP_NAME=DanceSport-Planner-Player
if /I "%~1"=="full" set FLAVOR=full
if /I "%~1"=="full" set APP_NAME=DanceSport-Planner-Player-Full
if /I "%~1"=="player" set FLAVOR=player
if /I "%~1"=="player" set APP_NAME=DanceSport-Player

rem The build must come from this very commit (build_exe.bat stamps it):
rem an older dist folder would ship old code under the current version.
set HEAD=
for /f %%H in ('git rev-parse HEAD 2^>nul') do set HEAD=%%H
set BUILT=
if exist "%~dp0dist\%APP_NAME%\build_commit.txt" for /f "usebackq" %%H in ("%~dp0dist\%APP_NAME%\build_commit.txt") do set BUILT=%%H
if not exist "%~dp0dist\%APP_NAME%\%APP_NAME%.exe" set BUILT=none
if not "%BUILT%"=="%HEAD%" (
  echo The build in dist\%APP_NAME% is not from this commit - building it first.
  rem build_exe.bat already paused on its own error.
  call "%~dp0build_exe.bat" %FLAVOR% || exit /b 1
)
if not exist "%~dp0dist\%APP_NAME%\%APP_NAME%.exe" goto :no_build

rem Inno Setup installs per user or for all users; ISCC on the PATH wins.
set ISCC=
for %%I in (ISCC.exe) do set ISCC=%%~$PATH:I
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not defined ISCC goto :no_iscc

rem The version the build itself names (planner.version): the release tag in
rem CI, else VERSION in the code.
set PY=%~dp0.venv\Scripts\python.exe
if not exist "%PY%" set PY=py
rem Windows wants plain numbers in the file properties, so both come along.
set VERSION=
for /f "tokens=1,2" %%V in ('call "%PY%" -c "from planner.version import build_version, numbers; v = build_version(); print(v, '.'.join(map(str, numbers(v))))"') do (
  set VERSION=%%V
  set NUMBERS=%%W
)
if not defined VERSION goto :no_version

"%ISCC%" /Q /DFlavor=%FLAVOR% /DAppVersion=%VERSION% /DAppNumbers=%NUMBERS% "%~dp0installer\dancesport.iss" || goto :failed

echo.
echo Built dist\installer\%APP_NAME%-%VERSION%-setup.exe
endlocal
exit /b 0

:no_build
echo ERROR: no dist\%APP_NAME%\%APP_NAME%.exe - run build_exe.bat %~1 first.
goto :stop

:no_iscc
echo ERROR: Inno Setup 6 not found (ISCC.exe).
echo   fix: winget install JRSoftware.InnoSetup
goto :stop

:no_version
echo ERROR: could not read the version from planner.version.
goto :stop

:failed
echo ERROR: the installer build failed - see the ISCC output above.
goto :stop

:stop
echo.
pause
endlocal
exit /b 1
