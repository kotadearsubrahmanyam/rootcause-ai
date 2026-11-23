# Start the Next.js workspace and Google sign-in on Windows using Node 22+.
$ErrorActionPreference = 'Stop'
$web = Join-Path $PSScriptRoot 'web'
$localConfig = Join-Path $PSScriptRoot '.env'
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Install Node.js 22 or later with npm, then reopen PowerShell.'
}
$major = [int](node -p "process.versions.node.split('.')[0]")
if ($major -lt 22) { throw 'This launcher requires Node.js 22 or later.' }

& (Join-Path $PSScriptRoot 'setup.ps1')
Push-Location $web
try {
    $next = Join-Path $web 'node_modules/next/dist/bin/next'
    if (-not (Test-Path $next)) {
        $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $npm) { throw 'Install Node.js 22 or later with npm, then reopen PowerShell.' }
        & $npm.Source install
        if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
    }
    # Keep the existing OAuth callback on port 3000. The API can run separately.
    $env:NEXTAUTH_URL = 'http://localhost:3000'
    if (-not $env:API_URL) { $env:API_URL = 'http://127.0.0.1:8000' }
    & node "--env-file=$localConfig" $next dev --hostname 127.0.0.1 --port 3000
    if ($LASTEXITCODE -ne 0) { throw 'The web server exited with an error.' }
} finally {
    Pop-Location
}
