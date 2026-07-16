# Renmark installer - Windows PowerShell.
# Mirror of install.sh for vibe coders on native Windows (not WSL).
#
# Usage (from a regular PowerShell window, run inside the extracted zip dir):
#   PS> .\install.ps1               # install plugin + CLI + register with Claude Code
#   PS> .\install.ps1 -Uninstall    # remove everything
#
# Does NOT require admin/elevation in the default path - uses junctions
# (Windows directory aliases that don't need privileges) instead of symlinks
# where possible, and falls back to a directory copy if even junctions fail.
#
# If junction creation fails entirely (rare - usually means a corporate
# AppLocker policy), the script falls back to copying the plugin tree into
# ~/.claude/plugins/cache/renmark-local/renmark/<version>/, which works
# but means edits to the source repo don't propagate until you re-run install.ps1.

param(
    [switch]$Uninstall,
    [switch]$NoCodex   # skip the codex prompt (for scripted installs)
)

$ErrorActionPreference = "Stop"

# Paths

$InstallDir       = (Resolve-Path $PSScriptRoot).Path
$VersionFile      = Join-Path $InstallDir "VERSION"
$Version          = (Get-Content $VersionFile -Raw).Trim()
$ClaudeDir        = Join-Path $env:USERPROFILE ".claude"
$PluginsDir       = Join-Path $ClaudeDir "plugins"
$SettingsJson     = Join-Path $ClaudeDir "settings.json"
$InstalledJson    = Join-Path $PluginsDir "installed_plugins.json"
$PluginSourceDir  = Join-Path $InstallDir "plugin"
$ConvenienceLink  = Join-Path $PluginsDir "renmark"
$CacheDir         = Join-Path $PluginsDir "cache\renmark-local\renmark\$Version"
$CodexPluginDir   = Join-Path $env:USERPROFILE "plugins\renmark"
$CodexMarketplaceJson = Join-Path $env:USERPROFILE ".agents\plugins\marketplace.json"

# Vibe-coder note: PowerShell prints with Write-Host; we do plain ASCII to
# avoid encoding glitches in older Windows Terminal versions.

function Show-Banner {
    Write-Host ""
    Write-Host "renmark v$Version - Windows installer"
    Write-Host "Installing to $ClaudeDir"
    Write-Host ""
}

function Ensure-Dir($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Remove-LinkOrDir($path) {
    # Junctions appear as directories; Remove-Item handles them.
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Uninstall path

if ($Uninstall) {
    Show-Banner
    Write-Host "Uninstalling renmark"

    Remove-LinkOrDir $ConvenienceLink
    Write-Host "  removed $ConvenienceLink"
    Remove-LinkOrDir $CodexPluginDir
    Write-Host "  removed $CodexPluginDir"
    if (Get-Command codex -ErrorAction SilentlyContinue) {
        & codex plugin remove "renmark@personal" 2>$null | Out-Null
    }

    # Wipe the entire renmark cache (all versions)
    $CacheRoot = Join-Path $PluginsDir "cache\renmark-local"
    Remove-LinkOrDir $CacheRoot
    Write-Host "  removed $CacheRoot"

    # Remove entries from settings.json + installed_plugins.json
    if (Test-Path $SettingsJson) {
        $s = Get-Content $SettingsJson -Raw | ConvertFrom-Json
        $changed = $false
        if ($s.PSObject.Properties.Name -contains "extraKnownMarketplaces" -and
            $s.extraKnownMarketplaces.PSObject.Properties.Name -contains "renmark-local") {
            $s.extraKnownMarketplaces.PSObject.Properties.Remove("renmark-local")
            $changed = $true
        }
        if ($s.PSObject.Properties.Name -contains "enabledPlugins" -and
            $s.enabledPlugins.PSObject.Properties.Name -contains "renmark@renmark-local") {
            $s.enabledPlugins.PSObject.Properties.Remove("renmark@renmark-local")
            $changed = $true
        }
        if ($changed) {
            $s | ConvertTo-Json -Depth 10 | Set-Content $SettingsJson -Encoding UTF8
            Write-Host "  cleaned settings.json"
        }
    }
    if (Test-Path $InstalledJson) {
        $d = Get-Content $InstalledJson -Raw | ConvertFrom-Json
        if ($d.plugins -and $d.plugins.PSObject.Properties.Name -contains "renmark@renmark-local") {
            $d.plugins.PSObject.Properties.Remove("renmark@renmark-local")
            $d | ConvertTo-Json -Depth 10 | Set-Content $InstalledJson -Encoding UTF8
            Write-Host "  cleaned installed_plugins.json"
        }
    }
    if (Test-Path $CodexMarketplaceJson) {
        $m = Get-Content $CodexMarketplaceJson -Raw | ConvertFrom-Json
        if ($m.plugins) {
            $m.plugins = @($m.plugins | Where-Object { $_.name -ne "renmark" })
            $m | ConvertTo-Json -Depth 10 | Set-Content $CodexMarketplaceJson -Encoding UTF8
            Write-Host "  cleaned Codex personal marketplace"
        }
    }

    Write-Host ""
    Write-Host "renmark uninstalled."
    Write-Host "Reload Claude Code and start a new Codex task to drop the plugin."
    exit 0
}

# Install path

Show-Banner

Ensure-Dir $PluginsDir
Ensure-Dir (Split-Path $CacheDir)

# 1. Plugin "install" - try junction (no admin needed), fall back to copy.
function Install-Plugin($target, $source) {
    Remove-LinkOrDir $target
    try {
        # Junction: works without admin, only works for dirs, only on NTFS.
        New-Item -ItemType Junction -Path $target -Value $source -ErrorAction Stop | Out-Null
        Write-Host "  $target  (junction -> $source)"
        return $true
    } catch {
        # Fall back to copy. Edits to source won't propagate until reinstall.
        Write-Host "  (junction failed, falling back to copy)"
        Copy-Item -Recurse -Force $source $target
        Write-Host "  $target  (copy of $source)"
        return $false
    }
}

Write-Host "Plugin source:"
$IsLive = Install-Plugin $ConvenienceLink $PluginSourceDir
$null = Install-Plugin $CacheDir $PluginSourceDir

if (-not $IsLive) {
    Write-Host ""
    Write-Host "NOTE: Junctions weren't available so we copied the plugin tree."
    Write-Host "      To pick up changes to the source repo later, re-run install.ps1."
}

# 2. Python package (editable). Required for renmark.doctor + renmark.init.
Write-Host ""
Write-Host "Python package:"
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        & python -m pip install -q -e $InstallDir 2>&1 | Select-Object -Last 3
        Write-Host "  renmark editable install OK"
    } catch {
        Write-Host "  pip install skipped (see above)"
    }
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    try {
        & python3 -m pip install -q -e $InstallDir 2>&1 | Select-Object -Last 3
        Write-Host "  renmark editable install OK"
    } catch {
        Write-Host "  pip install skipped (see above)"
    }
} else {
    Write-Host "  python not found. Install Python 3.10+ from https://python.org"
    Write-Host "  then re-run this installer."
}

# 3. Codex CLI (optional)
Write-Host ""
if (-not $NoCodex) {
    if (Get-Command codex -ErrorAction SilentlyContinue) {
        $codexVersion = & codex --version 2>$null
        Write-Host "Codex:   $codexVersion (already installed)"
    } else {
        Write-Host "Codex CLI is not installed."
        Write-Host "  renmark uses Codex (OpenAI) as the cheap bulk-emission executor."
        Write-Host "  Without it, codex-tagged tasks fall back to Sonnet (more expensive,"
        Write-Host "  but works fine). Codex is OPTIONAL but recommended."
        Write-Host ""
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            $codexAns = Read-Host "Install Codex CLI now via npm? [Y/n]"
            if ([string]::IsNullOrWhiteSpace($codexAns)) { $codexAns = "Y" }
            if ($codexAns -match "^[Yy]") {
                Write-Host "  Installing @openai/codex globally"
                & npm install -g "@openai/codex" 2>&1 | Select-Object -Last 3
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Codex:   installed via npm"
                    Write-Host "         (you'll need to authenticate with 'codex login' once)"
                } else {
                Write-Host "Codex:   npm install failed - see https://github.com/openai/codex"
                }
            } else {
                Write-Host "Codex:   skipped (install later: npm install -g @openai/codex)"
            }
        } else {
            Write-Host "  npm is not installed. To enable Codex:"
            Write-Host "    1. Install Node.js from https://nodejs.org"
            Write-Host "    2. npm install -g @openai/codex"
            Write-Host "    3. codex login"
        }
    }
}

# 4. Claude Code and Codex marketplace registration (must run after pip)
Write-Host ""
Write-Host "Registering with Claude Code and Codex:"

$pyExe = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pyExe = "python3" }

if ($pyExe -ne $null) {
    $canImport = $false
    try {
        & $pyExe -c "import renmark.doctor" 2>$null
        if ($LASTEXITCODE -eq 0) { $canImport = $true }
    } catch {}

    if ($canImport) {
        & $pyExe -m renmark.doctor --fix --refresh-codex 2>&1 |
            Where-Object { $_ -match "^(Applying|  |\[|Codex source refresh)" } |
            Select-Object -First 24
    } else {
        Write-Host "  skipped - renmark.doctor not importable (pip install may have failed above)"
        Write-Host "  Once Python + pip succeed, re-run: $pyExe -m renmark.doctor --fix"
    }
} else {
    Write-Host "  skipped - Python is required to write settings.json entries."
    Write-Host "  Install Python 3.10+ then re-run install.ps1."
}

if (Get-Command codex -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "Installing renmark@personal in Codex:"
    & codex plugin add "renmark@personal" --json 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  renmark@personal installed and enabled"
    } else {
        Write-Host "  plugin add failed; run: codex plugin add renmark@personal"
    }
}

# Done

Write-Host ""
Write-Host "renmark v$Version installed."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code (or run /reload-plugins) to load this version."
Write-Host "  2. Start a new Codex task to load this version."
Write-Host "  3. Ask either host to plan, build, fix, or finish with Renmark."
Write-Host "  4. If Renmark doesn't appear, run: /renmark:doctor"
Write-Host ""
Write-Host "Skills available after restart:"
Write-Host "  /renmark:start       Vibe coder entry - describe what you want, renmark builds it"
Write-Host "  /renmark:setup       Prepare an existing project (creates CLAUDE.md, AGENTS.md, .renmark/)"
Write-Host "  /renmark:init        Scan repo: project map + dev-standards/health report"
Write-Host "  /renmark:brainstorm  Design a feature into a spec"
Write-Host "  /renmark:plan        Decompose spec into atomic tasks with cost preview"
Write-Host "  /renmark:check-plan  Validate plan before spending tokens"
Write-Host "  /renmark:orchestrate Execute plan (Haiku / Codex / Sonnet / Opus / Fable)"
Write-Host "  /renmark:verify      Confirm feature goal was achieved"
Write-Host "  /renmark:finish      Branch close - PR / merge / release"
Write-Host "  /renmark:feature     Full pipeline with branch isolation"
Write-Host "  /renmark:debug       Systematic root-cause loop"
Write-Host "  /renmark:codereview  Single-pass Codex diff review"
Write-Host "  /renmark:roadmap     Project status + token usage report"
Write-Host "  /renmark:doctor      Diagnose install health"
Write-Host "  /renmark:help        List all commands"
Write-Host ""
Write-Host "To uninstall later:  .\install.ps1 -Uninstall"
