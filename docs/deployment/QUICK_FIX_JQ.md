# Quick Fix: jq Installation

## The Problem
You're seeing: `jq: command not found`

## The Solution (30 seconds)

```bash
# Install jq on WSL/Ubuntu
sudo apt-get update && sudo apt-get install -y jq

# Verify it works
jq --version
```

Expected output: `jq-1.6` or higher

## What is jq?
`jq` is a lightweight command-line JSON processor. It's used by some scripts for parsing JSON output.

## Alternative: Install All Dependencies at Once

```bash
# Run the automated installer
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

This installs ALL required dependencies including jq, Python packages, Rust, Node.js, and more.

## More Information
See [DEPENDENCY_INSTALLATION.md](DEPENDENCY_INSTALLATION.md) for complete installation guide.
