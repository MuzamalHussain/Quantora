# Dot-source from any location to use the already-installed workspace toolchain.
$quantoraRoot = Split-Path -Parent $PSScriptRoot
$env:RUSTUP_HOME = Join-Path $quantoraRoot '.tools/rustup'
$env:CARGO_HOME = Join-Path $quantoraRoot '.tools/cargo'
$env:PATH = "$env:CARGO_HOME\bin;$env:PATH"
