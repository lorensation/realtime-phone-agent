$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing .env file at $envPath"
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $envPath) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
        continue
    }

    $separator = $trimmed.IndexOf("=")
    if ($separator -lt 1) {
        continue
    }

    $key = $trimmed.Substring(0, $separator).Trim()
    $value = $trimmed.Substring($separator + 1).Trim()
    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    $values[$key] = $value
}

function Set-EnvFromFirstAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Target,
        [Parameter(Mandatory = $true)]
        [string[]] $Sources,
        [switch] $Required
    )

    foreach ($source in $Sources) {
        if ($values.ContainsKey($source) -and -not [string]::IsNullOrWhiteSpace($values[$source])) {
            [Environment]::SetEnvironmentVariable($Target, $values[$source], "Process")
            return
        }
    }

    if ($Required) {
        throw "Missing required Opik setting for $Target. Checked: $($Sources -join ', ')"
    }
}

Set-EnvFromFirstAvailable `
    -Target "OPIK_API_KEY" `
    -Sources @("OPIK_API_KEY", "OPIK__API_KEY") `
    -Required

Set-EnvFromFirstAvailable `
    -Target "OPIK_WORKSPACE" `
    -Sources @("OPIK_WORKSPACE", "OPIK__WORKSPACE", "COMET_WORKSPACE")

Set-EnvFromFirstAvailable `
    -Target "OPIK_DEFAULT_PROJECT_NAME" `
    -Sources @("OPIK_DEFAULT_PROJECT_NAME", "OPIK_PROJECT_NAME", "OPIK__PROJECT_NAME")

$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
$env:UV_TOOL_DIR = Join-Path $repoRoot ".uv-tools"

uvx opik-mcp
