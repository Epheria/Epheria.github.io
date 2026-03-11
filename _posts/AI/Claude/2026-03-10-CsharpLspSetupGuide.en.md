---
title: "Complete Guide to Setting Up C# LSP for Claude Code on macOS — From csharp-ls Installation to Troubleshooting"
lang: en
date: 2026-03-10 10:00:00 +0900
categories: [AI, Claude]
tags: [Claude Code, C#, LSP, csharp-ls, dotnet, macOS, dev environment, AI]
difficulty: beginner
toc: true
toc_sticky: true
prerequisites:
  - /posts/ClaudeCodeInsights/
tldr:
  - "To use C# LSP in Claude Code, you only need 4 things: .NET SDK + csharp-ls + 2 environment variables + plugin activation"
  - "90% of installation failures are caused by not setting the DOTNET_ROOT environment variable — the path differs between Apple Silicon and Intel Macs"
  - "If there's no .sln file in the project root, csharp-ls cannot index symbols"
---

## Introduction

Claude Code supports LSP (Language Server Protocol) for various languages, enabling code analysis, symbol navigation, refactoring, and more. Among these, **C# LSP is an essential tool for improving code quality in Unity and .NET projects**.

However, setting up C# LSP on macOS is trickier than on Windows. There are **several points where things can go wrong** across .NET SDK paths, environment variables, and plugin activation.

This article is a practical guide that documents **real problems encountered and their solutions** while setting up Claude Code's C# LSP (csharp-ls) on macOS. Use the Quick Start for a fast installation, or refer to the manual setup guide if issues arise.

---

## 1. Verified Environment

| Item | Value |
|------|-------|
| macOS | Sequoia 26.1 |
| Architecture | arm64 (Apple Silicon) |
| Rosetta | Installed |
| .NET SDK | 10.0.101 (Homebrew) |
| csharp-ls | 0.22.0 |
| Claude Code | Latest version |

---

## 2. Quick Start (6 Steps)

If you already have Homebrew installed, you can set everything up in these 6 steps. If you encounter problems, refer to the [Manual Setup Guide](#4-manual-setup-guide).

### Pre-check

Open a terminal and check your current state:

```bash
dotnet --version     # If a version shows → Skip Step 1
csharp-ls --version  # If a version shows → Skip Step 2
echo $DOTNET_ROOT    # If a path shows → Skip Step 3
```

### Step 1. Install .NET SDK

```bash
brew install dotnet
```

Verify after installation:

```bash
dotnet --version
# Output: 10.0.101
```

### Step 2. Install csharp-ls

```bash
dotnet tool install --global csharp-ls
```

Verify after installation:

```bash
csharp-ls --version
# Output: 0.22.0
```

> If you get `csharp-ls: command not found`, proceed with the PATH setup in Step 3 first.
{: .prompt-tip }

### Step 3. Set Environment Variables (.zshrc)

**This step is the most important.** Add the following 2 lines to your `~/.zshrc` file:

```bash
# Apple Silicon Mac (M1/M2/M3/M4)
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"
export PATH="$PATH:$HOME/.dotnet/tools"
```

Reload the shell:

```bash
source ~/.zshrc
```

> **For Intel Macs**, the DOTNET_ROOT path is different:
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

### Step 4. Activate Claude Code Plugin

Add to `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "csharp-lsp@claude-plugins-official": true
  }
}
```

To also activate per-project, add the same to `<project>/.claude/settings.json`.

### Step 5. Verify .sln File in Project

csharp-ls indexes symbols through the `.sln` → `.csproj` path. A `.sln` file must exist in the project root.

```bash
ls *.sln
# Example output: MyProject.sln
```

If no `.sln` file exists, create one:

```bash
dotnet new sln -n MyProject
dotnet sln add path/to/MyProject.csproj
```

### Step 6. Verify Installation

Once all settings are done, run the final verification:

```bash
# Success if all output correctly
dotnet --version          # .NET SDK version
which csharp-ls           # ~/.dotnet/tools/csharp-ls
csharp-ls --version       # 0.22.0
echo $DOTNET_ROOT         # /opt/homebrew/opt/dotnet/libexec
```

Launch Claude Code and verify that LSP features work in your C# project directory.

---

## 3. Understanding the Architecture

The Quick Start is sufficient, but understanding the overall structure helps when diagnosing issues.

### Component Relationship Diagram

```
Claude Code
    │
    ├── csharp-lsp plugin (activated in settings.json)
    │       │
    │       └── csharp-ls (LSP server)
    │               │
    │               ├── DOTNET_ROOT → references .NET SDK location
    │               │
    │               └── .sln file → .csproj → symbol indexing
    │
    └── PATH → ~/.dotnet/tools (csharp-ls binary location)
```

### Role of Each Component

| Component | Role | Installation Path |
|-----------|------|-------------------|
| .NET SDK | C# compiler and runtime | `/opt/homebrew/Cellar/dotnet/10.0.101/` |
| csharp-ls | LSP server (symbol navigation, autocomplete, etc.) | `~/.dotnet/tools/csharp-ls` |
| DOTNET_ROOT | Environment variable for csharp-ls to find the SDK | `/opt/homebrew/opt/dotnet/libexec` |
| .sln file | Defines project structure (indexing entry point) | Project root |
| Plugin | Connects Claude Code with csharp-ls | `~/.claude/plugins/` |

### Plugin File Structure

Files automatically generated when the plugin is activated:

```
~/.claude/plugins/
├── cache/claude-plugins-official/csharp-lsp/1.0.0/README.md
└── marketplaces/claude-plugins-official/plugins/csharp-lsp/
    ├── LICENSE
    └── README.md
```

---

## 4. Manual Setup Guide

A detailed step-by-step guide for when issues occur during the Quick Start.

### 4-1. Manual .NET SDK Installation and Verification

If Homebrew installation doesn't work, use the official Microsoft install script:

```bash
# Official install script
curl -sSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --channel LTS
```

In this case, the installation path will be `~/.dotnet`, so adjust environment variables accordingly:

```bash
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools"
```

Verify installation:

```bash
dotnet --info
```

Check the following items in the `dotnet --info` output:
- **Base Path** — The actual path where the SDK is installed
- **Runtime Environment: OS** — Verify architecture is `arm64` (Apple Silicon) or `x64` (Intel)

### 4-2. Manual csharp-ls Installation and Verification

If the default installation fails:

```bash
# Clear cache and reinstall
dotnet nuget locals all --clear
dotnet tool install --global csharp-ls

# Install a specific version
dotnet tool install --global csharp-ls --version 0.22.0
```

If already installed, update:

```bash
dotnet tool update --global csharp-ls
```

Directly verify the binary:

```bash
# Check file existence
ls -la ~/.dotnet/tools/csharp-ls

# Check architecture (should be arm64)
file ~/.dotnet/tools/csharp-ls
# Example output: Mach-O 64-bit executable arm64
```

### 4-3. Environment Variable Debugging

How to check one by one when environment variable issues are suspected:

```bash
# 1. Check DOTNET_ROOT
echo $DOTNET_ROOT
# Empty string → not set (most common failure cause)

# 2. Verify actual SDK exists at DOTNET_ROOT path
ls $DOTNET_ROOT/sdk/
# Should contain a directory like 10.0.101

# 3. Check if csharp-ls binary is in PATH
which csharp-ls
# No output → ~/.dotnet/tools is not in PATH

# 4. Verify ~/.dotnet/tools is included in PATH
echo $PATH | tr ':' '\n' | grep dotnet
```

### 4-4. Creating .sln Files (Unity Projects)

For Unity projects, the `.sln` file is auto-generated by Unity Editor:

1. Open Unity Editor
2. Go to **Edit → Preferences → External Tools**
3. Set the **External Script Editor** (e.g., Visual Studio Code)
4. Click **Regenerate project files**

To create manually:

```bash
cd /path/to/unity-project
dotnet new sln -n MyUnityProject

# Add Assembly-CSharp.csproj etc.
dotnet sln add Assembly-CSharp.csproj
```

### 4-5. Manual Plugin Activation Verification

How to verify the plugin is properly activated:

```bash
# Check global settings
cat ~/.claude/settings.json | grep -A2 "enabledPlugins"

# Check project-specific settings
cat .claude/settings.json | grep -A2 "enabledPlugins"

# Check if plugin files have been downloaded
ls ~/.claude/plugins/cache/claude-plugins-official/csharp-lsp/
```

---

## 5. Troubleshooting

### Case 1: `csharp-ls: command not found`

**Cause**: `~/.dotnet/tools` is not in PATH

**Solution**:

```bash
# 1. Verify binary exists
ls ~/.dotnet/tools/csharp-ls

# 2. Add to PATH (~/.zshrc)
export PATH="$PATH:$HOME/.dotnet/tools"
source ~/.zshrc

# 3. Verify
which csharp-ls
```

### Case 2: csharp-ls Cannot Find SDK at Runtime

**Cause**: DOTNET_ROOT environment variable not set (most common cause)

**Solution**:

```bash
# Apple Silicon Mac
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# Intel Mac
export DOTNET_ROOT="/usr/local/share/dotnet"

# Verify — SDK directory should be visible
ls $DOTNET_ROOT/sdk/
```

### Case 3: Conflict with OmniSharp

**Symptom**: csharp-ls is installed but LSP behaves abnormally

**Cause**: OmniSharp installed alongside can cause conflicts

**Solution**:

```bash
# Check if OmniSharp is installed
dotnet tool list -g | grep omnisharp

# If installed, uninstall it
dotnet tool uninstall -g omnisharp
```

> Mono (`/opt/homebrew/bin/mono`) does not conflict with csharp-ls. Having Mono installed is fine.
{: .prompt-info }

### Case 4: .sln File Exists but Symbol Indexing Doesn't Work

**Cause**: `.csproj` is not registered in the `.sln` file, or the `.csproj` path is incorrect

**Solution**:

```bash
# Check projects registered in .sln
cat MyProject.sln | grep "\.csproj"

# If empty → need to register .csproj
dotnet sln add path/to/MyProject.csproj
```

### Case 5: LSP Features Not Working in Claude Code

**Diagnostic sequence**:

```bash
# Step 1: Check if csharp-ls itself works
csharp-ls --version

# Step 2: Check DOTNET_ROOT
echo $DOTNET_ROOT

# Step 3: Check plugin activation
cat ~/.claude/settings.json

# Step 4: Check .sln file exists
ls *.sln

# Step 5: Restart Claude Code
# After changing plugin settings, you must restart Claude Code
```

### Case 6: Conflict Between Homebrew dotnet and Official Install Script dotnet

**Symptom**: `dotnet` runs but csharp-ls can't find the SDK

**Cause**: Homebrew and the official script install SDKs in different paths, causing DOTNET_ROOT to point to the wrong SDK

**Solution**:

```bash
# Check which dotnet is running
which dotnet
dotnet --info

# If it's the Homebrew version
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"

# If it's the official script version
export DOTNET_ROOT="$HOME/.dotnet"

# Recommended to keep only one
# Remove Homebrew version
brew uninstall dotnet

# Or remove official script version
rm -rf ~/.dotnet
```

---

## 6. New Mac Setup Checklist

A checklist for setting up from scratch on a new Mac. Copy and follow step by step.

```bash
# ✅ Step 1: Install .NET SDK
brew install dotnet

# ✅ Step 2: Set environment variables (add to ~/.zshrc)
echo '' >> ~/.zshrc
echo '# .NET & csharp-ls configuration' >> ~/.zshrc
echo 'export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"' >> ~/.zshrc
echo 'export PATH="$PATH:$HOME/.dotnet/tools"' >> ~/.zshrc

# ✅ Step 3: Reload shell
source ~/.zshrc

# ✅ Step 4: Install csharp-ls
dotnet tool install --global csharp-ls

# ✅ Step 5: Verify installation
which csharp-ls          # ~/.dotnet/tools/csharp-ls
csharp-ls --version      # 0.22.0

# ✅ Step 6: Activate Claude Code plugin
# Add the following to ~/.claude/settings.json:
# {
#   "enabledPlugins": {
#     "csharp-lsp@claude-plugins-official": true
#   }
# }

# ✅ Step 7: Verify .sln file in project root
ls *.sln
```

> **For Intel Macs**, change the DOTNET_ROOT in Step 2 to:
> ```bash
> export DOTNET_ROOT="/usr/local/share/dotnet"
> ```
{: .prompt-warning }

---

## 7. FAQ

### Q. Do I need to install OmniSharp too?

**No.** csharp-ls alone is sufficient. It's actually cleaner not to install OmniSharp. Having two LSP servers coexist can cause conflicts.

### Q. Is it okay that Mono is installed?

**Yes.** Mono (`/opt/homebrew/bin/mono`) operates independently of csharp-ls and does not cause conflicts.

### Q. Do I need Rosetta on Apple Silicon Mac?

**It's not required.** csharp-ls installs as an arm64 native binary. However, some .NET tools only support x64, so having Rosetta installed improves compatibility.

### Q. Do I need to configure the plugin for each project?

Setting it globally in `~/.claude/settings.json` applies to all projects. If you want to use it only for specific projects, configure it only in `<project>/.claude/settings.json`.

### Q. How do I update csharp-ls?

```bash
dotnet tool update --global csharp-ls
```

---

## 8. workspaceSymbol Limitation and Alternatives

### What is workspaceSymbol?

`workspace/symbol` is a standard LSP request that **searches for symbols by name across the entire workspace**.

```
Client → Server: { method: "workspace/symbol", params: { query: "GamePauseLayer" } }
Server → Client: [ { name: "GamePauseLayer", kind: Class, location: {...} }, ... ]
```

In IDEs, this is the `Ctrl+T` (Go to Symbol in Workspace) functionality.

### Why It Doesn't Work in Claude Code

Claude Code's LSP tool spec is **missing the `query` parameter** that `workspaceSymbol` requires:

```json
{
    "operation": "workspaceSymbol",
    "filePath": "string (required)",    // ← unnecessary for workspaceSymbol
    "line": "integer (required)",       // ← unnecessary for workspaceSymbol
    "character": "integer (required)"   // ← unnecessary for workspaceSymbol
    // No query parameter!
}
```

As a result, an empty query (`query: ""`) is sent, returning only the **first 100 symbols** from the entire workspace. In large projects, the desired symbol is unlikely to be included.

> Example: In a Unity project (18,500+ symbols), searching for `GamePauseLayer` returned 100 proto auto-generated files sorted alphabetically, with no game code symbols included.
{: .prompt-warning }

### Other LSP Operations Work Fine

| Operation | Requires Query? | Status | Notes |
| --- | --- | --- | --- |
| `documentSymbol` | No (file specified) | **Works** | File structure analysis |
| `hover` | No (position specified) | **Works** | Rich type + docs |
| `findReferences` | No (position specified) | **Works** | Semantic search |
| `goToDefinition` | No (position specified) | **Works** | Precise navigation |
| `goToImplementation` | No (position specified) | **Works** | Interface → implementation |
| `incomingCalls` / `outgoingCalls` | No (position specified) | **Works** | Call tracing |
| `workspaceSymbol` | **Yes (query required)** | **Unusable** | No query parameter |

`workspaceSymbol` is the only operation that requires a `query` string, and Claude Code's tool doesn't support it.

### Alternatives: Symbol Search Strategy

#### Finding File/Class Locations

| Method | Speed | Accuracy |
| --- | --- | --- |
| **With Rider:** `find_files_by_name_keyword` → `documentSymbol` | Instant (~0.1s + ~0.5s) | 100% |
| **Without Rider:** `Glob **/ClassName.cs` → `documentSymbol` | Instant (~0.1s + ~0.5s) | 100% |
| `Grep "class ClassName"` | Fast (~1s) | 100% |
| `workspaceSymbol` | Slow (~3s) | **0%** (large projects) |

#### Searching Symbol Name Patterns

| Method | Example |
| --- | --- |
| **Rider:** `search_in_files_by_text "class.*Pause"` → `documentSymbol` | Semantic search + structure analysis |
| **No Rider:** `Glob **/*Pause*.cs` → `documentSymbol` on each file | File search + structure analysis |
| `Grep "class.*Pause"` | Text matching |

#### Finding Symbol References

| Method | Accuracy |
| --- | --- |
| `LSP findReferences` | **Best** (code references only) |
| `Grep "ClassName"` | Includes strings/comments |

### Recommended Workflow

```
┌──────────────────────────────────────────────────────────┐
│  Optimal Symbol Search Strategy                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  "Where is this class file?"                             │
│  → [Rider] find_files_by_name_keyword "ClassName"        │
│  → [No Rider] Glob **/ClassName.cs                       │
│  → LSP documentSymbol (structure check)                  │
│                                                          │
│  "Find all Pause-related classes"                        │
│  → [Rider] search_in_files_by_text "class.*Pause"        │
│  → [No Rider] Glob **/*Pause*.cs                         │
│  → LSP documentSymbol on each file                       │
│                                                          │
│  "Where is this symbol used?"                            │
│  → LSP findReferences (file + position specified)        │
│                                                          │
│  "What's the structure of this file?"                    │
│  → LSP documentSymbol                                    │
│                                                          │
│  ✗ workspaceSymbol → Do NOT use                          │
│    (query parameter unsupported, 100 result limit)       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Conclusion

The key to C# LSP setup is **2 environment variable lines**:

```bash
export DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec"  # SDK path
export PATH="$PATH:$HOME/.dotnet/tools"                # Binary path
```

If these 2 lines are in your `.zshrc`, csharp-ls is installed, and the plugin is activated, Claude Code can perfectly analyze your C# code.

If issues arise, follow the diagnostic sequence in the [Troubleshooting section](#5-troubleshooting) to resolve most problems. Just remember that the most common cause is **DOTNET_ROOT not being set**.
