@echo off
rem Build the player-only Windows app - double-click me.
rem
rem This is build_exe.bat's "player" flavor: the same code, packaged without the
rem librosa analysis stack and locked to player mode (no startup chooser, no
rem planning controls). Roughly half the size of the lite build.
rem
rem Kept:    playback, the tempo/pitch fader, loudness equalize, Paso Doble
rem          highlight detection, cartwall, library browser, announcements.
rem Dropped: timbre similarity, BPM analysis, the chroma index, the AI
rem          suggestions, and the printed running order.
rem
rem Plain ASCII on purpose - this prints through a cp1252 Windows console.
call "%~dp0build_exe.bat" player
rem build_exe.bat pauses on an error only; this one is meant to be
rem double-clicked, so hold the window open either way.
if not errorlevel 1 pause
exit /b %ERRORLEVEL%
