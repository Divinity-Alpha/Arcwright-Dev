@echo off
REM Launch UE Editor on the 5070 Ti (D3D12 adapter 0) to keep PRO 6000 free for training
REM Usage: launch_ue.bat <path_to.uproject>
REM   or:  launch_ue.bat  (defaults to ArcwrightTestBed)

set "PROJECT=%~1"
if "%PROJECT%"=="" set "PROJECT=C:\Junk\ArcwrightTestBed\ArcwrightTestBed.uproject"

echo [LAUNCH] Starting UE Editor on 5070 Ti (adapter 0)...
echo [LAUNCH] Project: %PROJECT%

"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJECT%" -skipcompile -graphicsadapter=0 -nosplash -unattended -nopause
