# Cleanup script to remove all test artifacts (screenshots, playwright logs, traces) from results directory
# Also cleans screenshots from root folder as a safety measure
param(
    [string]$ResultsDir = "results"
)

$ResultsPath = Join-Path $PSScriptRoot "..\$ResultsDir"
$ResultsPath = [System.IO.Path]::GetFullPath($ResultsPath)

# Root folder path (rpa-robots directory)
$RootPath = Join-Path $PSScriptRoot ".."
$RootPath = [System.IO.Path]::GetFullPath($RootPath)

Write-Host "Cleaning up test artifacts from: $ResultsPath" -ForegroundColor Cyan
if (Test-Path $RootPath) {
    Write-Host "Also cleaning screenshots from root folder: $RootPath" -ForegroundColor Cyan
}

$screenshotsDeleted = 0
$playwrightLogsDeleted = 0
$tracesDeleted = 0

# Clean up selenium screenshots from results directory
$screenshotPatterns = @(
    "selenium-screenshot-*.png",
    "selenium-screenshot-*.jpg",
    "selenium-screenshot-*.jpeg"
)

if (Test-Path $ResultsPath) {
    foreach ($pattern in $screenshotPatterns) {
        $files = Get-ChildItem -Path $ResultsPath -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            try {
                Remove-Item -Path $file.FullName -Force
                $screenshotsDeleted++
                Write-Host "Deleted from results: $($file.Name)" -ForegroundColor Gray
            } catch {
                Write-Host "Failed to delete $($file.Name): $_" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Host "Results directory not found: $ResultsPath" -ForegroundColor Yellow
}

# Clean up selenium screenshots from root folder (safety measure - should not happen but clean anyway)
if (Test-Path $RootPath) {
    foreach ($pattern in $screenshotPatterns) {
        $files = Get-ChildItem -Path $RootPath -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            try {
                Remove-Item -Path $file.FullName -Force
                $screenshotsDeleted++
                Write-Host "Deleted from root: $($file.Name)" -ForegroundColor Gray
            } catch {
                Write-Host "Failed to delete $($file.Name): $_" -ForegroundColor Yellow
            }
        }
    }
}

# Clean up playwright log files
$playwrightLogPatterns = @(
    "playwright-log*.txt",
    "playwright-log*.log"
)

foreach ($pattern in $playwrightLogPatterns) {
    $files = Get-ChildItem -Path $ResultsPath -Filter $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        try {
            Remove-Item -Path $file.FullName -Force
            $playwrightLogsDeleted++
            Write-Host "Deleted: $($file.Name)" -ForegroundColor Gray
        } catch {
            Write-Host "Failed to delete $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

# Clean up playwright trace directories
$browserDir = Join-Path $ResultsPath "browser"
if (Test-Path $browserDir) {
    $tracesDir = Join-Path $browserDir "traces"
    if (Test-Path $tracesDir) {
        $traceDirs = Get-ChildItem -Path $tracesDir -Directory -ErrorAction SilentlyContinue
        foreach ($traceDir in $traceDirs) {
            try {
                Remove-Item -Path $traceDir.FullName -Recurse -Force
                $tracesDeleted++
                Write-Host "Deleted trace directory: $($traceDir.Name)" -ForegroundColor Gray
            } catch {
                Write-Host "Failed to delete trace directory $($traceDir.Name): $_" -ForegroundColor Yellow
            }
        }
    }
}

# Print summary
$totalDeleted = $screenshotsDeleted + $playwrightLogsDeleted + $tracesDeleted
if ($totalDeleted -gt 0) {
    $summaryParts = @()
    if ($screenshotsDeleted -gt 0) {
        $summaryParts += "$screenshotsDeleted screenshot(s)"
    }
    if ($playwrightLogsDeleted -gt 0) {
        $summaryParts += "$playwrightLogsDeleted playwright log(s)"
    }
    if ($tracesDeleted -gt 0) {
        $summaryParts += "$tracesDeleted trace directory(ies)"
    }
    Write-Host "`nCleaned up $($summaryParts -join ', ')" -ForegroundColor Green
} else {
    Write-Host "`nNo test artifacts found to clean up" -ForegroundColor Yellow
}

