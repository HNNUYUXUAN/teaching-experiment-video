param(
    [string]$RuntimeRoot,
    [ValidateSet('doctor','pipeline','images','media_audit','draft_ops','verify_codec','project','test_pipeline','test_portable')]
    [string]$Script = 'doctor',
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$ScriptArgs
)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeRoot) { $RuntimeRoot = $env:TEACHING_VIDEO_HOME }
if (-not $RuntimeRoot) { $RuntimeRoot = Join-Path $env:LOCALAPPDATA 'TeachingVideoSkill' }
$env:TEACHING_VIDEO_HOME = [IO.Path]::GetFullPath($RuntimeRoot)
$prefix = Join-Path $env:TEACHING_VIDEO_HOME 'envs\teaching-video'
if ($env:TEACHING_VIDEO_ENV) { $prefix = $env:TEACHING_VIDEO_ENV }
$python = Join-Path $prefix 'python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run scripts/bootstrap.ps1 first; dedicated Python is missing.' }
$env:PATH = "$prefix;$prefix\Scripts;$prefix\Library\bin;" + $env:PATH
$env:PYTHONDONTWRITEBYTECODE = '1'
& $python -X utf8 (Join-Path $PSScriptRoot "$Script.py") @ScriptArgs
exit $LASTEXITCODE
