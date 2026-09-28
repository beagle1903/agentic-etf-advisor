# Service-free regression for the exact PowerShell gate retained in the runbook.
# Keep Continue: the former nonterminating ConvertFrom-Json behavior must fail this probe.
$ErrorActionPreference = 'Continue'
$runbook = Get-Content (Join-Path $PSScriptRoot '../docs/runbooks/local-development.md') -Raw
$section = ($runbook -split '### Required real-store delivery gate')[1]
$block = [regex]::Match($section, '(?s)```powershell\r?\n(.*?)```').Groups[1].Value
if (-not $block.Contains('$env:RUN_REAL_STORE_TESTS')) { throw 'Documented gate not found.' }
$gate = [scriptblock]::Create($block.Substring($block.IndexOf('$env:RUN_REAL_STORE_TESTS')))
$probeProject = 'etf-advisor-contract-0123456789ab'
$probeName = 'a' * 64
$savedIntegrationOptIn = [Environment]::GetEnvironmentVariable('RUN_REAL_STORE_TESTS', 'Process')

function uv {
    "REAL_STORE_PROJECT=$probeProject"
    "REAL_STORE_VOLUMES=$($script:probe.Json)"
    $global:LASTEXITCODE = $script:probe.PytestExit
}

function docker {
    $script:inspections++
    $command = $args -join ' '
    if (-not $command.Contains("label=com.docker.compose.project=$probeProject") -and
        -not $command.Contains("name=^${probeName}$")) {
        throw 'Gate attempted an unrelated resource query.'
    }
    $global:LASTEXITCODE = $script:probe.DockerExit
    if ($script:probe.Leftover -and $command.Contains('name=')) { $probeName }
}

function ConvertFrom-Json {
    [CmdletBinding()]
    param([Parameter(ValueFromPipeline = $true)][string] $InputObject)
    process {
        if ($InputObject -eq '[parser-error-probe]') {
            Write-Error 'Injected nonterminating JSON parser error.'
            return
        }
        Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject -ErrorAction $ErrorActionPreference
    }
}

$cases = @(
    @{ Name = 'malformed-json'; Json = '[invalid]'; Reject = $true; Inspections = 0 },
    @{ Name = 'parser-error'; Json = '["unterminated]'; Reject = $true; Inspections = 0 },
    @{ Name = 'nonterminating-parser-error'; Json = '[parser-error-probe]'; Reject = $true; Inspections = 0 },
    @{ Name = 'wrong-type'; Json = '{"volumes":[]}'; Reject = $true; Inspections = 0 },
    @{ Name = 'nonstring-name'; Json = '[123]'; Reject = $true; Inspections = 0 },
    @{ Name = 'duplicate-name'; Json = '["' + $probeName + '","' + $probeName + '"]'; Reject = $true; Inspections = 0 },
    @{ Name = 'invalid-name'; Json = '["unrelated"]'; Reject = $true; Inspections = 0 },
    @{ Name = 'empty-array'; Json = '[]'; Reject = $false; Inspections = 2 },
    @{ Name = 'valid-array'; Json = '["' + $probeName + '"]'; Reject = $false; Inspections = 3 },
    @{ Name = 'pytest-failure'; Json = '[]'; Reject = $true; Inspections = 2; PytestExit = 1 },
    @{ Name = 'inspection-failure'; Json = '[]'; Reject = $true; Inspections = 2; DockerExit = 1 },
    @{ Name = 'anonymous-leftover'; Json = '["' + $probeName + '"]'; Reject = $true; Inspections = 3; Leftover = $true }
)
try {
    foreach ($script:probe in $cases) {
        if (-not $script:probe.ContainsKey('PytestExit')) { $script:probe.PytestExit = 0 }
        if (-not $script:probe.ContainsKey('DockerExit')) { $script:probe.DockerExit = 0 }
        $script:inspections = 0
        $script:messages = @()
        $rejected = $false
        try {
            & $gate 2>&1 | ForEach-Object { $script:messages += $_ }
        } catch {
            $rejected = $true
        }
        if ($rejected -ne $script:probe.Reject -or $script:inspections -ne $script:probe.Inspections) {
            throw "Gate regression failed: $($script:probe.Name)."
        }
        $confirmed = @($script:messages | Where-Object { "$_" -like 'Cleanup verified for *' }).Count
        if (($script:probe.Inspections -eq 0 -or $script:probe.DockerExit -or $script:probe.Leftover) -and $confirmed) {
            throw "Rejected inventory certified cleanup: $($script:probe.Name)."
        }
        if (-not $rejected -and $confirmed -ne 1) {
            throw "Valid inventory did not certify cleanup: $($script:probe.Name)."
        }
        "PASS $($script:probe.Name): rejected=$rejected inspections=$script:inspections cleanupConfirmations=$confirmed"
    }
} finally {
    [Environment]::SetEnvironmentVariable('RUN_REAL_STORE_TESTS', $savedIntegrationOptIn, 'Process')
}
"All $($cases.Count) documented-gate probes passed. No services or resource mutations."
