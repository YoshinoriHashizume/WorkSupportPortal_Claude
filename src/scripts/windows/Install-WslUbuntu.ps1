# Install WSL2 and Ubuntu on Windows Server / Windows 10+.
# Run in elevated PowerShell: powershell -ExecutionPolicy Bypass -File scripts\windows\Install-WslUbuntu.ps1
#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "Enabling WSL and Virtual Machine Platform..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null

Write-Host "Installing Ubuntu (WSL2)..."
wsl --install -d Ubuntu --no-launch 2>$null
if ($LASTEXITCODE -ne 0) {
    wsl --install -d Ubuntu
}

Write-Host ""
Write-Host "WSL setup initiated. Reboot the VM, then open Ubuntu from Start menu."
Write-Host "After first Ubuntu login, run in Ubuntu:"
Write-Host "  cd /mnt/c/Application/WorkSupportPortal"
Write-Host "  bash scripts/wsl/install-docker-engine.sh"
