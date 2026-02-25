---
title: "Unreal Mac OS Project Load Error Fix (Xcode Version Issue)"
date: 2025-10-21 00:25:00 +/-TTTT
categories: [Unreal, MacOS]
tags: [Unreal, Mac, Xcode, SDK]
lang: en
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## Error when opening a .uproject from GitHub on Unreal Mac OS

- Even after downloading the latest version of Xcode from the App Store, the following error occurred and the project would not open.

<br>

```
Failed to open selected source code accessor 'Xcode'.
```

<br>

```
Setting up bundled DotNet SDK
/Users/YOUR_USERNAME/UE_5.6/Engine/Build/BatchFiles/Mac/../../../Binaries/ThirdParty/DotNet/8.0.300/mac-arm64
Running dotnet Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll Development Mac -Project=/Users/YOUR_USERNAME/Documents/Unreal Projects/dd/dd.uproject -TargetType=Editor -Progress -NoEngineChanges -NoHotReloadFromIDE
Log file: /Users/YOUR_USERNAME/Library/Application Support/Epic/UnrealBuildTool/Log.txt
Creating makefile for ddEditor (no existing makefile)
Platform Mac is not a valid platform to build. Check that the SDK is installed properly and that you have the necessary platform support files (DataDrivenPlatformInfo.ini, SDK.json, etc).

Result: Failed (OtherCompilationError)
Total execution time: 1.09 seconds
```

<br>
<br>

## Solution

- The cause was that **Xcode was too new**, and Unreal could not recognize it.
- [Since the recent beta version is Xcode 26 or higher, you must download Xcode 16.](https://forums.unrealengine.com/t/platform-mac-is-not-a-valid-platform-to-build-check-that-the-sdk-is-installed-properly-and-that-you-have-the-necessary-platorm-support-files-datadrivenplatforminfo-ini-sdk-json-etc/1846659/3)

<br>

[Xcode 16 Download Link](https://developer.apple.com/download/all/)

<br>

```bash
xcodebuild -version
xcode-select --print-path
```

First, check if Xcode is installed with these two commands.

<br>

```bash
xcode-select --install
```

Try this to check if Command Line Tools are installed (if installed, it will show an error).

<br>

View the contents of the installed Xcode package - Contents - Developer, copy the path, and:

<br>

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

- Reassign the path.

- Replace `/Applications/Xcode.app/Contents/Developer` with your actual Xcode installation path.

<br>

Check if the `.xcworkspace` file is properly generated in the project location.

<br>

Double-click the `.uproject` file in the project location to open the project.

<br>

**Caution: Be sure to run GitHub LFS Initialize. Since Unreal asset files are large, they are uploaded via LFS. If you don't initialize, the project will open without asset files.**
