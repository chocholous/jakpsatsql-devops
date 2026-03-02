@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Skryty input hesla pres PowerShell
for /f "usebackq delims=" %%p in (`powershell -Command "$p = Read-Host 'Passphrase pro provisioner_key.p8' -AsSecureString; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))"`) do (
  set PASSPHRASE=%%p
)

:: Auto-detect TSV
for %%f in (*.tsv) do (set TSV=%%f& goto :found)
echo Nenalezen zadny .tsv soubor.
pause
exit /b 1
:found

set SF_KEY_PASSPHRASE=%PASSPHRASE%
provision.exe "%TSV%"
pause
