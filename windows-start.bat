CLS
@echo off
echo.

set PYTHON_LOWEST_VERSION=3.8.0

:: env setup
echo Checking environment...

:: python
for /f "tokens=2 delims= " %%a in ('python --version') do set PYTHON_VERSION=%%a
if errorlevel 1 (
    echo Python not found. Please install Python %PYTHON_LOWEST_VERSION% or higher.
    goto :errEnd
)
call :compareVersions %PYTHON_VERSION% %PYTHON_LOWEST_VERSION%
set versionCompare=%errorlevel%
if %versionCompare% == -1 (
    echo Python %PYTHON_VERSION% found, but %PYTHON_LOWEST_VERSION% or higher is required.
    goto :errEnd
)

echo Python %PYTHON_VERSION% found.
::active venv
echo activating environment...
python -m venv %~dp0venv
python -m pip install --upgrade pip
for /f "tokens=*" %%a in ('pip install -r %~dp0requirements.txt') do echo %%a
:: get input
set /p WORK_DIR=Enter the path to the directory containing the files to be processed:
echo started
python run.pyw --work_dir %WORK_DIR%
goto :end

:compareVersions  version1  version2
::
:: Compares two version numbers and returns the result in the ERRORLEVEL
::
:: Returns 1 if version1 > version2
::         0 if version1 = version2
::        -1 if version1 < version2
::
:: The nodes must be delimited by . or , or -
::
:: Nodes are normally strictly numeric, without a 0 prefix. A letter suffix
:: is treated as a separate node
::
setlocal enableDelayedExpansion
set "v1=%~1"
set "v2=%~2"
call :divideLetters v1
call :divideLetters v2
:loop
call :parseNode "%v1%" n1 v1
call :parseNode "%v2%" n2 v2
if %n1% gtr %n2% exit /b 1
if %n1% lss %n2% exit /b -1
if not defined v1 if not defined v2 exit /b 0
if not defined v1 exit /b -1
if not defined v2 exit /b 1
goto :loop


:parseNode  version  nodeVar  remainderVar
for /f "tokens=1* delims=.,-" %%A in ("%~1") do (
  set "%~2=%%A"
  set "%~3=%%B"
)
exit /b


:divideLetters  versionVar
for %%C in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do set "%~1=!%~1:%%C=.%%C!"
exit /b

:errEnd
echo.
exit /b 1

:end
echo.
exit /b 0
