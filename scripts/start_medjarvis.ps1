param(
  [switch]$Restart,
  [int]$LlamaPort = 8080,
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Get-ListenerPid {
  param([int]$Port)

  $rows = netstat -ano -p tcp | Select-String "LISTENING"
  foreach ($row in $rows) {
    $parts = ($row.Line.Trim() -split "\s+") | Where-Object { $_ }
    if ($parts.Count -ge 5 -and $parts[1] -match ":$Port$") {
      return [int]$parts[-1]
    }
  }
  return $null
}

function Stop-PortIfRequested {
  param(
    [int]$Port,
    [string]$Name
  )

  $listenerPid = Get-ListenerPid -Port $Port
  if ($null -eq $listenerPid) {
    return
  }
  if (!$Restart) {
    Write-Host "$Name already listens on port $Port (PID $listenerPid). Use -Restart to replace it."
    return
  }
  Write-Host "Stopping $Name on port $Port (PID $listenerPid)"
  Stop-Process -Id $listenerPid -Force
  Start-Sleep -Seconds 1
}

function Start-LoggedPowerShell {
  param(
    [string]$Name,
    [string]$ScriptPath,
    [string[]]$ExtraArgs = @()
  )

  $stdout = Join-Path $LogDir "$Name.out.log"
  $stderr = Join-Path $LogDir "$Name.err.log"
  $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $ExtraArgs
  $process = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $args `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru
  Write-Host "Started $Name (PID $($process.Id)); logs: $stdout / $stderr"
}

function Test-Url {
  param([string]$Url)

  try {
    Invoke-RestMethod -Uri $Url -TimeoutSec 2 | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Wait-Url {
  param(
    [string]$Url,
    [string]$Name,
    [int]$TimeoutSeconds = 60
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-Url -Url $Url) {
      Write-Host "$Name is ready: $Url"
      return
    }
    Start-Sleep -Seconds 2
  }
  Write-Warning "$Name did not become ready in $TimeoutSeconds seconds: $Url"
}

Stop-PortIfRequested -Port $BackendPort -Name "backend"
Stop-PortIfRequested -Port $FrontendPort -Name "frontend"
Stop-PortIfRequested -Port $LlamaPort -Name "llama-server"

$llamaHealth = "http://127.0.0.1:$LlamaPort/v1/models"
if (!(Test-Url -Url $llamaHealth)) {
  Start-LoggedPowerShell `
    -Name "llama" `
    -ScriptPath (Join-Path $PSScriptRoot "start_llama.ps1") `
    -ExtraArgs @("-Port", "$LlamaPort")
  Wait-Url -Url $llamaHealth -Name "llama-server" -TimeoutSeconds 90
}

$backendHealth = "http://127.0.0.1:$BackendPort/api/health"
if (!(Test-Url -Url $backendHealth)) {
  Start-LoggedPowerShell -Name "backend" -ScriptPath (Join-Path $PSScriptRoot "start_backend.ps1")
  Wait-Url -Url $backendHealth -Name "backend" -TimeoutSeconds 90
}

if ($null -eq (Get-ListenerPid -Port $FrontendPort)) {
  Start-LoggedPowerShell -Name "frontend" -ScriptPath (Join-Path $PSScriptRoot "start_frontend.ps1")
  Wait-Url -Url "http://127.0.0.1:$FrontendPort" -Name "frontend" -TimeoutSeconds 60
}

Write-Host ""
Write-Host "MedJarvis stack:"
Write-Host "  Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "  Backend:  http://127.0.0.1:$BackendPort"
Write-Host "  LLM:      http://127.0.0.1:$LlamaPort/v1"
