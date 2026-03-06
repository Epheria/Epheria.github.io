---
title: "Complete Guide to Installing Claude Code on Windows — With Real-World Troubleshooting"
lang: en
date: 2026-03-04 16:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, Windows, Installation Guide, PowerShell, Node.js, Git, Developer Tools, AI]

difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "To install Claude Code on Windows 11, you need Node.js LTS, Git, and the Git Bash path environment variable — completable in 5 Quick Start steps"
  - "The most common post-install failures are not restarting the terminal (PATH not refreshed) and missing the CLAUDE_CODE_GIT_BASH_PATH environment variable"
  - "A single PowerShell diagnostic script can identify all environment issues at a glance"
---

## Introduction

Claude Code is Anthropic's CLI-based AI coding agent. While installation is relatively straightforward on macOS/Linux, **on Windows you can get stuck at several stages including Git Bash path configuration, PowerShell execution policy, and PATH issues**.

This guide documents **the actual problems encountered and solutions** when installing Claude Code in a Windows environment. Use the Quick Start for a fast install, or refer to the step-by-step detailed guide if issues arise.

---

## 1. Verified Environment

| Item | Version/Value |
|------|--------------|
| OS | Windows 11 Home (10.0.26200) |
| Node.js | v24.12.0 (LTS) |
| npm | 11.6.2 |
| Git | 2.51.0.windows.2 |
| Claude Code | @anthropic-ai/claude-code@**2.1.63** |
| Default Model | Claude Opus 4.6 (`claude-opus-4-6`) |

### Available Claude Models

| Model | Model ID | Characteristics |
|-------|----------|----------------|
| **Opus 4.6** | `claude-opus-4-6` | Most powerful, suitable for complex tasks **(default)** |
| Sonnet 4.6 | `claude-sonnet-4-6` | Fast responses, suitable for general tasks |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | Fastest, suitable for simple tasks |

---

## 2. Quick Start (5 Steps)

If you already have Node.js and Git installed, you can install in just 5 steps below. If issues occur, refer to the [Step-by-Step Detailed Guide](#3-step-by-step-detailed-guide).

### Pre-Check

Open PowerShell and check your current status with the following commands:

```powershell
node -v          # Version appears → Skip Node.js in Step 2
npm -v           # Version appears → npm is fine
git --version    # Version appears → Skip Git in Step 2
claude --version # Version appears → Already installed! Just check "Upgrade" section
```

### Step 1. Set Execution Policy (One-Time)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Step 2. Install Required Programs

```powershell
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```

> **You must completely close and reopen the PowerShell terminal after installation.** Opening a new terminal refreshes the PATH so that `node` and `git` commands are recognized.
{: .prompt-warning }

### Step 3. Set Git Bash Path Environment Variable (One-Time)

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

> The last argument `"User"` is not your actual username. It's a keyword indicating the **scope** of the Windows environment variable. Do not replace it with your username.
{: .prompt-info }

### Step 4. Install Claude Code

```powershell
# Method A: Official script (recommended)
irm https://claude.ai/install.ps1 | iex

# Method B: npm direct install (when Method A doesn't work)
npm install -g @anthropic-ai/claude-code
```

### Step 5. Verify Installation

```powershell
claude --version
# Example: 2.1.63 (Claude Code) ← Version number appearing means success!
```

---

## 3. Step-by-Step Detailed Guide

If you encountered issues with Quick Start, check the detailed troubleshooting for each step in this section.

### 3-1. PowerShell Execution Policy Setting

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

Verify the setting:

```powershell
Get-ExecutionPolicy -List
# The CurrentUser entry should be RemoteSigned
```

| Policy | Description | Recommended |
|--------|------------|-------------|
| Restricted | Blocks all scripts (Windows default) | |
| **RemoteSigned** | Allows local scripts, requires signatures for remote | **Recommended** |
| Unrestricted | Allows all scripts | Security risk |

**Why is this needed?** Windows blocks PowerShell script execution by default (`Restricted`). You need to change this policy to `RemoteSigned` to run the Claude Code installation script.

---

### 3-2. Node.js Installation

```powershell
winget install -e --id OpenJS.NodeJS.LTS
```

Verify installation (in a new terminal):

```powershell
node -v  # Example: v24.12.0
npm -v   # Example: 11.6.2
```

#### When winget Doesn't Work

If winget is unavailable on older Windows versions, install manually:

1. Visit [https://nodejs.org/](https://nodejs.org/)
2. Download the LTS version
3. Run the installer (.msi)
4. Install with default options
5. Open a new terminal

#### "Command not found" with `node -v`

**Cause:** Node.js path is not registered in PATH.

**Resolution steps:**

1. Completely close and reopen the terminal
2. If still not working, reboot the system
3. If still not working, add PATH manually:
   - Start → Search "environment variables" → "User environment variables"
   - Edit Path → Add `C:\Program Files\nodejs\`

---

### 3-3. Git Installation

```powershell
winget install -e --id Git.Git
```

Verify installation:

```powershell
git --version  # Example: git version 2.51.0.windows.2
```

#### When winget Doesn't Work

1. Visit [https://gitforwindows.org/](https://gitforwindows.org/)
2. Download and run the installer
3. Keep default installation options (Git Bash is included)
4. Open a new terminal

---

### 3-4. Git Bash Path Environment Variable Setting

**Why is this needed?** Claude Code internally uses a bash shell. On Windows it uses Git Bash, but sometimes it can't find the path automatically, so you need to specify it manually.

```powershell
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
```

Verify the setting (in a new terminal):

```powershell
echo $env:CLAUDE_CODE_GIT_BASH_PATH
# Example: C:\Program Files\Git\bin\bash.exe
```

> `"User"` parameter explanation
>
> | Value | Meaning | Note |
> |-------|---------|------|
> | `"User"` | Current logged-in user's environment variable | **Recommended (use as-is)** |
> | `"Machine"` | System-wide environment variable | Requires administrator privileges |
> | `"Process"` | Valid only for current terminal session | Disappears when terminal is closed |
{: .prompt-info }

#### When Git is Installed in a Different Path

```powershell
# Check Git installation location
where git
# Example: C:\Program Files\Git\cmd\git.exe
# → bash.exe is in the bin folder under the same Git directory

# Common Git Bash paths:
# C:\Program Files\Git\bin\bash.exe        ← 64-bit (most cases)
# C:\Program Files (x86)\Git\bin\bash.exe  ← 32-bit

# Set environment variable with confirmed path
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "actual_path", "User")
```

#### Using WSL (Alternative)

```powershell
wsl --install  # Install WSL (one-time, reboot required)
```

While WSL also works, the Git Bash path setting is simpler, so **the Git Bash method is recommended**.

---

### 3-5. Claude Code Installation

#### Method A: Official Installation Script (Recommended)

```powershell
irm https://claude.ai/install.ps1 | iex
```

When the above command doesn't work:

```powershell
# Variant 1: Execute as scriptblock
& ([scriptblock]::Create((irm https://claude.ai/install.ps1))) latest

# Variant 2: Use CMD script
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

#### Method B: npm Direct Install (When Method A Fails)

```powershell
npm install -g @anthropic-ai/claude-code
```

> Pay attention to npm command syntax:
> ```powershell
> npm install -g package-name    # ✅ Correct syntax
> npm i -g package-name          # ✅ Shorthand
> npm --install package-name     # ❌ Wrong syntax
> npm -install package-name      # ❌ Wrong syntax
> ```
{: .prompt-warning }

---

### 3-6. Installation Verification and PATH Troubleshooting

```powershell
claude --version
# Example: 2.1.63 (Claude Code)
```

#### When `claude` Command is Not Found

```powershell
# 1. Close terminal and open a new one

# 2. Check npm global path
npm config get prefix
# Example: C:\Users\username\AppData\Roaming\npm

# 3. Check if that path is in PATH
echo $env:PATH

# 4. If not in PATH, add it ($env:USERPROFILE auto-completes user path)
[Environment]::SetEnvironmentVariable(
  "Path",
  [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:USERPROFILE\AppData\Roaming\npm",
  "User"
)

# 5. Open new terminal and try again
claude --version
```

#### How to Check Your Windows Username

When you need to manually type your `username` in a path:

```powershell
# Method 1: Full user profile folder path
echo $env:USERPROFILE
# Example: C:\Users\JohnDoe  ← "JohnDoe" is the username

# Method 2: Username only
echo $env:USERNAME
# Example: JohnDoe

# Method 3: whoami
whoami
# Example: DESKTOP-ABC123\JohnDoe  ← After "\" is the username
```

> Using `$env:USERPROFILE` allows you to auto-complete the path without knowing the username, so use this variable instead of typing manually whenever possible.
{: .prompt-tip }

---

## 4. Post-Installation Configuration

### Configuration File Locations

| File | Path | Purpose |
|------|------|---------|
| Global settings | `%USERPROFILE%\.claude\settings.json` | Language, status bar, etc. |
| Project settings | `project-folder\.claude\settings.local.json` | Project-specific permissions, etc. |
| Project context | `project-folder\CLAUDE.md` | Rules/instructions to pass to AI |

### Global Settings Example

`%USERPROFILE%\.claude\settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline-command.sh"
  },
  "language": "Korean"
}
```

The `"language": "Korean"` setting makes Claude Code respond in Korean.

---

## 5. Basic Claude Code Usage

### Run Commands

```powershell
# Start interactive session in project folder
cd C:\MyProject
claude

# One-line question (immediate answer without interactive session)
claude -p "Find bugs in this code"

# Pipe input
cat main.cpp | claude -p "Review this code"

# Run with specific model
claude --model claude-sonnet-4-6

# Continue previous conversation
claude --continue

# Resume most recent conversation
claude --resume
```

### Slash Commands During Conversation

| Command | Description |
|---------|------------|
| `/help` | Show help |
| `/model` | Check/change model |
| `/compact` | Compress conversation context (useful for long conversations) |
| `/clear` | Reset conversation |
| `/cost` | Check current session cost |
| `/fast` | Toggle Fast mode (same model, faster output) |
| `/commit` | Create Git commit for changes |
| `/simplify` | Auto-review and improve changed code |
| `/batch` | Parallel changes across large codebase |

> For detailed explanations of `/simplify` and `/batch`, refer to the [Claude Memory Goes Free and /simplify, /batch](/posts/ClaudeMemoryAndCodeSkills/) post.
{: .prompt-info }

---

## 6. Upgrading

### Method A: npm update (Recommended)

```powershell
npm update -g @anthropic-ai/claude-code
```

### Method B: Force Install Latest Version

```powershell
npm install -g @anthropic-ai/claude-code@latest
```

Post-upgrade verification:

```powershell
# Open a new terminal
claude --version

# Existing configuration files are automatically preserved.
```

---

## 7. Full Diagnostic Script

When you don't know where the issue is, paste this script into PowerShell to diagnose the entire environment at once.

```powershell
Write-Host "=== Claude Code Environment Diagnostic ===" -ForegroundColor Cyan

Write-Host "`n[Node.js]" -ForegroundColor Yellow
try { node -v } catch { Write-Host "  ❌ Not installed" -ForegroundColor Red }

Write-Host "`n[npm]" -ForegroundColor Yellow
try { npm -v } catch { Write-Host "  ❌ Not installed" -ForegroundColor Red }

Write-Host "`n[Git]" -ForegroundColor Yellow
try { git --version } catch { Write-Host "  ❌ Not installed" -ForegroundColor Red }

Write-Host "`n[Git Bash Path]" -ForegroundColor Yellow
$gitBash = [Environment]::GetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "User")
if ($gitBash) { Write-Host "  $gitBash" } else { Write-Host "  ❌ Not configured" -ForegroundColor Red }

Write-Host "`n[Execution Policy]" -ForegroundColor Yellow
Get-ExecutionPolicy -Scope CurrentUser

Write-Host "`n[Claude Code]" -ForegroundColor Yellow
try { claude --version } catch { Write-Host "  ❌ Not installed" -ForegroundColor Red }

Write-Host "`n[npm Global Path]" -ForegroundColor Yellow
npm config get prefix
```

Example output:

```
=== Claude Code Environment Diagnostic ===

[Node.js]
v24.12.0

[npm]
11.6.2

[Git]
git version 2.51.0.windows.2

[Git Bash Path]
  C:\Program Files\Git\bin\bash.exe

[Execution Policy]
RemoteSigned

[Claude Code]
2.1.63 (Claude Code)

[npm Global Path]
C:\Users\username\AppData\Roaming\npm
```

If all items are normal, installation is complete. If you see a red `❌`, refer to the troubleshooting section for that item.

---

## 8. Troubleshooting Summary

| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `node -v` doesn't work | Node.js not installed or PATH not registered | [3-2. Node.js Installation](#3-2-nodejs-installation) |
| `irm ... \| iex` blocked | Execution policy is Restricted | [3-1. Execution Policy Setting](#3-1-powershell-execution-policy-setting) |
| `npm --install` error | Wrong npm syntax | Use `npm install -g` |
| Shell error running `claude` | Git Bash path not set | [3-4. Git Bash Path Setting](#3-4-git-bash-path-environment-variable-setting) |
| `claude` command not found | npm global path not registered | [3-6. PATH Troubleshooting](#3-6-installation-verification-and-path-troubleshooting) |
| Nothing works | Terminal not restarted | **Close and reopen terminal** |

---

## File Path Summary

| Item | Path |
|------|------|
| Claude executable | `%USERPROFILE%\AppData\Roaming\npm\claude.cmd` |
| npm global packages | `%USERPROFILE%\AppData\Roaming\npm\` |
| Claude global settings | `%USERPROFILE%\.claude\settings.json` |
| Claude project settings | `project\.claude\settings.local.json` |
| Git Bash | `C:\Program Files\Git\bin\bash.exe` |

---

## Conclusion

The three most common blockers when installing Claude Code on Windows:

1. **Not restarting the terminal** — PATH doesn't refresh, so installed programs aren't recognized
2. **`CLAUDE_CODE_GIT_BASH_PATH` not set** — Claude Code can't find bash and fails to run
3. **`"User"` parameter confusion** — Mistaking the environment variable Scope keyword for your actual username

If you watch out for these three things, you can resolve most installation issues. When problems occur, run the [Diagnostic Script](#7-full-diagnostic-script) first.

---

## References

- Anthropic. (2026). *Claude Code Documentation*. [https://docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code)
- Anthropic. (2026). *Claude Code GitHub*. [https://github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
- Node.js. *Node.js Official Site*. [https://nodejs.org/](https://nodejs.org/)
- Git for Windows. *Git for Windows*. [https://gitforwindows.org/](https://gitforwindows.org/)
