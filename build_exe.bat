@echo off
rem Build the Windows one-folder exe (see dancesport.spec for details).
rem   build_exe.bat        -> lite  (dist\DanceSport-Planner-Player)
rem   build_exe.bat full   -> full  (dist\DanceSport-Planner-Player-Full, + Demucs)
rem   build_exe.bat player -> player (dist\DanceSport-Player, no analysis stack)
rem Double-clicking it builds the lite flavor; on an error the window stays
rem open long enough to read what went wrong.
rem Plain ASCII on purpose - this prints through a cp1252 Windows console.
setlocal
cd /d "%~dp0"

set DANCESPORT_BUILD=lite
set APP_NAME=DanceSport-Planner-Player
if /I "%~1"=="full" set DANCESPORT_BUILD=full
if /I "%~1"=="full" set APP_NAME=DanceSport-Planner-Player-Full
if /I "%~1"=="player" set DANCESPORT_BUILD=player
if /I "%~1"=="player" set APP_NAME=DanceSport-Player

set PY=%~dp0.venv\Scripts\python.exe
if not exist "%PY%" goto :no_venv

rem PyInstaller bundles whatever it finds in this interpreter, so a venv that is
rem missing a dependency still "builds" - it just yields an .exe that dies on
rem launch with "PySide6 not found". Check before spending the build time.
rem The player flavor is built without librosa on purpose (see BUILD.md), so
rem demanding it here would refuse the very venv that flavor wants.
set DEPS=PySide6, numpy, mutagen
if /I not "%DANCESPORT_BUILD%"=="player" set DEPS=PySide6, librosa, numpy, mutagen
"%PY%" -c "import %DEPS%" || goto :no_deps
"%PY%" -c "import PyInstaller" || goto :no_pyinstaller

"%PY%" -m PyInstaller "%~dp0dancesport.spec" --noconfirm || goto :failed

rem ffmpeg is looked up next to the .exe first (shared.audio_probes.find_ffmpeg), and
rem PyInstaller wipes dist\%APP_NAME% on every build - so put it back each time.
rem It is not in the repository (see BUILD.md); without it the packaged app
rem does no loudness analysis and asks for one on first start.
set FFMPEG=%~dp0ffmpeg.exe
if not exist "%FFMPEG%" set FFMPEG=%~dp0ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe
if exist "%FFMPEG%" (
  copy /y "%FFMPEG%" "%~dp0dist\%APP_NAME%\ffmpeg.exe" >nul
  echo Copied ffmpeg.exe next to the app.
) else (
  echo NOTE: no ffmpeg.exe found next to build_exe.bat - see BUILD.md.
  echo       The packaged app will ask for one on first start.
)

echo.
echo Built dist\%APP_NAME%\%APP_NAME%.exe
echo Data (database, settings, playlists) stays next to the .exe in that folder.
echo Copy an existing audio_features.db in there to reuse analysed features.
endlocal
exit /b 0

:no_venv
echo ERROR: no build venv at .venv\Scripts\python.exe
echo   fix: py -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt pyinstaller
goto :stop

:no_deps
echo ERROR: the build venv is missing one of: %DEPS%
echo   fix: .venv\Scripts\pip install -r requirements.txt
goto :stop

:no_pyinstaller
echo ERROR: PyInstaller is not installed in the build venv
echo   fix: .venv\Scripts\pip install pyinstaller
goto :stop

:failed
echo ERROR: the %DANCESPORT_BUILD% build failed - see the PyInstaller output above.
goto :stop

:stop
echo.
pause
endlocal
exit /b 1
