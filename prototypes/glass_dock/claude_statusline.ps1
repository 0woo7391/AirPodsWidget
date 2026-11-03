# Claude Code status line: saves the 5-hour and weekly usage limits Claude Code passes in,
# so the dock's AI module can show them (ai_status.py reads claude_limits.json).
# Prints nothing, so the status line itself stays empty.
$raw = [Console]::In.ReadToEnd()
try {
    $data = $raw | ConvertFrom-Json
    if ($data.rate_limits) {
        $dir = Join-Path $env:LOCALAPPDATA "GlassDock"
        New-Item -ItemType Directory -Force $dir | Out-Null
        $data.rate_limits | ConvertTo-Json -Depth 5 -Compress | Set-Content -Encoding UTF8 (Join-Path $dir "claude_limits.json")
    }
} catch {}
