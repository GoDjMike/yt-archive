if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $python = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} else {
    throw "Error: python not found. Install Python and retry."
}

& $python (Join-Path $PSScriptRoot "yt-archive.py") @args
