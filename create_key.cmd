@echo off
setlocal
if "%~1"=="" (
  echo Usage: create_key.cmd https://fsdsdfsdfasdfcxv.onrender.com ADMIN_TOKEN [days] [count]
  echo Example: create_key.cmd https://fsdsdfsdfasdfcxv.onrender.com MySecret 30 1
  exit /b 1
)
set URL=%~1
set TOKEN=%~2
set DAYS=%~3
set COUNT=%~4
if "%DAYS%"=="" set DAYS=30
if "%COUNT%"=="" set COUNT=1

curl -s -X POST "%URL%/v1/admin/create" ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-Token: %TOKEN%" ^
  -d "{\"days\":%DAYS%,\"note\":\"manual\",\"count\":%COUNT%}"
echo.
endlocal
