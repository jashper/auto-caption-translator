# Storage Cleanup Script
# 存儲空間清理腳本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Storage Cleanup Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will delete:" -ForegroundColor Yellow
Write-Host "- All video files in storage\uploads" -ForegroundColor Yellow
Write-Host "- All subtitle files in storage\subtitles" -ForegroundColor Yellow
Write-Host "- All job records in storage\jobs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Warning: This cannot be undone!" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "Continue? (Y/N)"

if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Cleaning storage..." -ForegroundColor Green
Write-Host ""

# Get script directory and go to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "Working directory: $projectRoot" -ForegroundColor Gray
Write-Host ""

# Delete uploaded videos
Write-Host "[1/3] Deleting uploaded videos..." -ForegroundColor Cyan
if (Test-Path "storage\uploads") {
    $files = Get-ChildItem "storage\uploads\*" -File -ErrorAction SilentlyContinue
    if ($files) {
        $files | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "      Deleted $($files.Count) files" -ForegroundColor Green
    } else {
        Write-Host "      No files to delete" -ForegroundColor Yellow
    }
} else {
    Write-Host "      Folder not found" -ForegroundColor Yellow
}

# Delete generated subtitles
Write-Host "[2/3] Deleting generated subtitles..." -ForegroundColor Cyan
if (Test-Path "storage\subtitles") {
    $folders = Get-ChildItem "storage\subtitles\*" -Directory -ErrorAction SilentlyContinue
    if ($folders) {
        $folders | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "      Deleted $($folders.Count) folders" -ForegroundColor Green
    } else {
        Write-Host "      No folders to delete" -ForegroundColor Yellow
    }
} else {
    Write-Host "      Folder not found" -ForegroundColor Yellow
}

# Delete job records
Write-Host "[3/3] Deleting job records..." -ForegroundColor Cyan
if (Test-Path "storage\jobs") {
    $files = Get-ChildItem "storage\jobs\*" -File -ErrorAction SilentlyContinue
    if ($files) {
        $files | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "      Deleted $($files.Count) files" -ForegroundColor Green
    } else {
        Write-Host "      No files to delete" -ForegroundColor Yellow
    }
} else {
    Write-Host "      Folder not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Storage space has been freed." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
