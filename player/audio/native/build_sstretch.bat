@echo off
rem Builds sstretch.dll (Signalsmith Stretch behind a C door) next to this file.
rem Needs MinGW-w64 g++ on PATH. Static, so the DLL needs no runtime DLLs.
cd /d "%~dp0"
g++ -std=c++11 -O2 -shared -static -static-libgcc -static-libstdc++ -o sstretch.dll sstretch.cpp
if errorlevel 1 exit /b 1
echo sstretch.dll built
