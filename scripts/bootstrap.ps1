# Windows x64 bootstrap. No Python, administrator rights, or shell activation required.
param([string]$RuntimeRoot, [string]$CondaExe, [switch]$CheckOnly,
      [switch]$AcceptMinicondaTerms, [switch]$Repair)
$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
if (-not $RuntimeRoot) { $RuntimeRoot = $env:TEACHING_VIDEO_HOME }
if (-not $RuntimeRoot) { $RuntimeRoot = Join-Path $env:LOCALAPPDATA 'TeachingVideoSkill' }
$RuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)
$env:TEACHING_VIDEO_HOME = $RuntimeRoot
New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$configPath = Join-Path $RuntimeRoot '.env'
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $skillRoot 'assets\config-template.txt') -Destination $configPath
}
$prefix = Join-Path $RuntimeRoot 'envs\teaching-video'
$miniRoot = Join-Path $RuntimeRoot 'miniconda3'
$python = Join-Path $prefix 'python.exe'
$stage = 'preflight'
function Finish([int]$Code, [string]$Status, [string]$Next) {
    $record = [ordered]@{status=$Status;stage=$stage;exit_code=$Code;runtime=$RuntimeRoot;config_file=$configPath;
        conda=$CondaExe;python=$python;next_step=$Next;cloud_tested=$false;browser_connection='agent_must_verify'}
    $json = $record | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText((Join-Path $RuntimeRoot 'bootstrap-report.json'),$json,[Text.UTF8Encoding]::new($false))
    Write-Output $json
    exit $Code
}
function Healthy-Conda([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try { & $Path --version *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}
try {
    $arch = $env:PROCESSOR_ARCHITEW6432
    if (-not $arch) { $arch = $env:PROCESSOR_ARCHITECTURE }
    if ($arch -ne 'AMD64') { Finish 23 'unsupported_platform' 'Use Windows x64; see first-run.md for portable platforms.' }
    if ($CondaExe -and -not (Healthy-Conda $CondaExe)) {
        Finish 22 'specified_conda_unusable' 'Correct -CondaExe; no other installation was changed.'
    }
    if (-not $CondaExe) {
        $candidates = @($env:CONDA_EXE, (Join-Path $miniRoot 'Scripts\conda.exe'))
        $command = Get-Command conda.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) { $candidates += $command.Source }
        foreach ($base in @($env:USERPROFILE,$env:LOCALAPPDATA,$env:ProgramData)) {
            if ($base) {
                foreach ($name in @('miniconda3','anaconda3','Miniconda3','Anaconda3')) {
                    $candidates += Join-Path $base "$name\Scripts\conda.exe"
                }
            }
        }
        foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
            if (Healthy-Conda $candidate) { $CondaExe=$candidate; break }
        }
    }
    if ($CheckOnly) {
        $status = if ($CondaExe) {'conda_found'} else {'miniconda_required'}
        Finish 0 $status 'Run bootstrap without -CheckOnly; if conda is absent, review Miniconda terms first.'
    }
    if (-not $CondaExe) {
        $stage='miniconda_install'
        if (-not $AcceptMinicondaTerms) {
            Finish 20 'needs_miniconda_terms' 'Open https://www.anaconda.com/legal in the user-selected browser. After user acceptance, rerun with -AcceptMinicondaTerms.'
        }
        if (Test-Path -LiteralPath $miniRoot) {
            Finish 22 'partial_miniconda_preserved' 'Inspect the partial installation or choose a new -RuntimeRoot.'
        }
        $manifest = Get-Content -Raw -LiteralPath (Join-Path $skillRoot 'assets\miniconda-installers.json') | ConvertFrom-Json
        $entry = $manifest.'windows-x86_64'
        $url = 'https://repo.anaconda.com/miniconda/' + $entry.filename
        $cache = Join-Path $RuntimeRoot 'downloads'
        New-Item -ItemType Directory -Force -Path $cache | Out-Null
        $installer = Join-Path $cache $entry.filename
        if (-not (Test-Path -LiteralPath $installer)) {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $partial = "$installer.partial"
            Invoke-WebRequest -Uri $url -OutFile $partial -UseBasicParsing -TimeoutSec 600
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $partial).Hash.ToLowerInvariant() -ne $entry.sha256) {
                Finish 21 'installer_hash_mismatch' 'Do not execute this file. Recheck the official manifest.'
            }
            Move-Item -LiteralPath $partial -Destination $installer
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant() -ne $entry.sha256) {
            Finish 21 'cached_installer_hash_mismatch' 'Do not execute this file; inspect it and obtain the official pinned package.'
        }
        # NSIS requires /D to be the final, unquoted argument, including paths with spaces.
        $arguments = "/InstallationType=JustMe /AddToPath=0 /RegisterPython=0 /S /D=$miniRoot"
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
        if ($process.ExitCode -notin @(0,3010)) { Finish 21 'miniconda_install_failed' 'Inspect installer result; preserve partial files and see recovery.md.' }
        $CondaExe = Join-Path $miniRoot 'Scripts\conda.exe'
        if (-not (Healthy-Conda $CondaExe)) { Finish 22 'installed_conda_unusable' 'Inspect installation; do not fall back to system Python.' }
    }
    $stage='environment'
    $env:PATH = "$prefix;$prefix\Scripts;$prefix\Library\bin;" + $env:PATH
    $env:PYTHONDONTWRITEBYTECODE='1'
    $healthy=$false
    if (Test-Path -LiteralPath $python) {
        & $python -X utf8 (Join-Path $PSScriptRoot 'doctor.py') --health-only
        $healthy=($LASTEXITCODE -eq 0)
    }
    if (-not $healthy) {
        if ((Test-Path -LiteralPath $prefix) -and -not $Repair) {
            Finish 22 'existing_environment_needs_repair' 'Inspect the existing environment then use -Repair, or choose a new runtime.'
        }
        if (Test-Path -LiteralPath $prefix) {
            if (-not (Test-Path -LiteralPath (Join-Path $prefix 'conda-meta\history'))) {
                Finish 22 'incomplete_environment_preserved' 'Choose a new runtime; this folder is not a recognized conda environment.'
            }
            & $CondaExe install --yes --prefix $prefix --override-channels -c conda-forge --file (Join-Path $skillRoot 'assets\conda-win-64.lock.txt')
        } else {
            & $CondaExe create --yes --prefix $prefix --override-channels -c conda-forge --file (Join-Path $skillRoot 'assets\conda-win-64.lock.txt')
        }
        if ($LASTEXITCODE -ne 0) { Finish 22 'environment_setup_failed' 'Read conda output; resolve network, disk, permission or terms issues before retrying.' }
    }
    $stage='health'
    & $python -X utf8 (Join-Path $PSScriptRoot 'doctor.py')
    if ($LASTEXITCODE -ne 0) { Finish 22 'health_failed' 'See recovery.md; no cloud requests were made.' }
    Finish 0 'ready_local' 'Fill the local .env, choose an image provider and verify browser connection if needed.'
} catch {
    Write-Warning ("Setup stopped at " + $stage + "; error type: " + $_.Exception.GetType().Name)
    Finish 21 'setup_interrupted' 'Check disk, permissions and network; preserve existing files. See recovery.md.'
}
