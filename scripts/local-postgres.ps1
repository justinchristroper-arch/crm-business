param([ValidateSet('start','stop')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskData = [IO.Path]::GetFullPath((Join-Path $taskRoot 'artifacts/postgres'))
if (-not $taskData.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Invalid cluster path' }
$taskBin = 'C:\Program Files\PostgreSQL\17\bin'
if (-not (Test-Path (Join-Path $taskBin 'initdb.exe'))) { throw 'PostgreSQL 17 is not installed at the expected path.' }
if ($Action -eq 'stop') {
    & (Join-Path $taskBin 'pg_ctl.exe') -D $taskData stop -m fast
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot 'artifacts') | Out-Null
if (-not (Test-Path (Join-Path $taskData 'PG_VERSION'))) {
    & (Join-Path $taskBin 'initdb.exe') -D $taskData -U crm_local -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Cluster initialization failed' }
}
# A separate, loopback-only disposable cluster. It never touches the installed database service.
Start-Process -FilePath (Join-Path $taskBin 'postgres.exe') -ArgumentList @('-D', ('"'+$taskData+'"'), '-p', '55432', '-h', '127.0.0.1') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot 'artifacts/postgres.stdout.log') -RedirectStandardError (Join-Path $taskRoot 'artifacts/postgres.stderr.log')
