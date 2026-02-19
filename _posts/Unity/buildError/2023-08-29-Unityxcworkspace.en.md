---
title: Unity - Fix for xcworkspace Not Being Generated
date: 2023-08-29 14:38:00 +/-TTTT
categories: [Unity, Build Error]
tags: [unity, build, xcworkspace, ios, pod install]
difficulty: intermediate
lang: en
toc: true
---

## Table of Contents

- [1. Main Symptoms and Analysis](#main-symptoms-and-analysis)
- [2. Solution](#solution)

---

## Fixing issue where xcworkspace is not generated when building Unity iOS project

<br>

## Main symptoms and analysis

- **Main symptom**: Environment was macOS. During remote build with Jenkins + fastlane + build scripts, cocoapods version issues occurred during Unity iOS build, and neither `Pods` folder nor `xcworkspace` was generated.
- Even though iOS Resolver integration was correctly set to `xcworkspace`, and regardless of `Use Shell to Execute Cocoapod Tool` checkbox, `xcworkspace` was not generated.

- iOS Resolver path  
Assets - External Dependency Manager - iOS Resolver - Settings

<img src="/assets/img/post/unity/xcworkspaceissue01.png" width="500" height="700" title="256" alt="build1">

<br>

- Another odd point: this issue had happened intermittently even before deep debugging. cocoapods and ruby gems versions were unchanged, yet it sometimes worked and sometimes failed.
- Manual Unity build generated `xcworkspace` normally.

<br>

- Possible Unity iOS Resolver misconfiguration
- Possible version conflict between cocoapods and ruby gems on mac-mini

1. **Check possible cocoapods version conflict**
- Move to cocoapods bin folder and run `pod --version`.
- Part of terminal logs below:

```
# find cocoapods bin path
YOUR_USERNAME@YOUR_MACHINE Xcode % which pod
/opt/homebrew/bin/pod

# move to bin folder
YOUR_USERNAME@YOUR_MACHINE Xcode % cd /opt/homebrew/bin

# cocoapods version check
YOUR_USERNAME@YOUR_MACHINE bin % pod --version
1.12.1

# gem version check
YOUR_USERNAME@YOUR_MACHINE Xcode % gem --version
3.4.19
```

<br>

2. **Update cocoapods and ruby gem to latest versions**
- Check current versions and update to latest.

```
# uninstall/install cocoapods via brew
# used homebrew due repeated permission issues with sudo
# uninstall
YOUR_USERNAME@YOUR_MACHINE bin % brew uninstall cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
Warning: Calling the `appcast` stanza is deprecated! Use the `livecheck` stanza instead.
Please report this issue to the adoptopenjdk/openjdk tap (not Homebrew/brew or Homebrew/homebrew-core), or even better, submit a PR to fix it:
  /opt/homebrew/Library/Taps/adoptopenjdk/homebrew-openjdk/Casks/adoptopenjdk11.rb:9

Uninstalling /opt/homebrew/Cellar/cocoapods/1.12.1... (13,430 files, 27.8MB)
YOUR_USERNAME@YOUR_MACHINE bin % brew unstall cocoapods -v 1.10.1

# install
YOUR_USERNAME@YOUR_MACHINE bin % brew install cocoapods
Warning: Treating cocoapods as a formula. For the cask, use homebrew/cask/cocoapods
==> Fetching cocoapods
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/manifests/1.12.1
Already downloaded: /Users/YOUR_USERNAME/Library/Caches/Homebrew/downloads/092af1d0eed5d8e2252554a1d84826de8e271bcb598c43452362a690991fa2bd--cocoapods-1.12.1.bottle_manifest.json
==> Downloading https://ghcr.io/v2/homebrew/core/cocoapods/blobs/sha256:6f1fca1cb0df79912e10743a80522e666fe605a1eaa2aac1094c501608fb7ee4
Already downloaded: /Users/YOUR_USERNAME/Library/Caches/Homebrew/downloads/abfa7f252c7ffcc49894abb0d1afe0e47accb0b563df95a47f8f04ad93f8f681--cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
==> Pouring cocoapods--1.12.1.arm64_ventura.bottle.tar.gz
🍺  /opt/homebrew/Cellar/cocoapods/1.12.1: 13,430 files, 27.8MB
==> Running `brew cleanup cocoapods`...
Disable this behaviour by setting HOMEBREW_NO_INSTALL_CLEANUP.
Hide these hints with HOMEBREW_NO_ENV_HINTS (see `man brew`).
```

<br>

3. **Is downgrading cocoapods the answer?**
- Many posts suggest `1.10.xx`, but my root cause was different.
- Answer: NO, downgrade is unnecessary. Error looked like terminal locale/encoding issue.
- Detailed in solution section below.
> [Issue where xcworkspace is not generated in Unity iOS Resolver](https://phillip5094.github.io/ios/unity/Unity-iOS-Resolver%EC%97%90%EC%84%9C-xcworkspace-%EC%83%9D%EC%84%B1%EB%90%98%EC%A7%80-%EC%95%8A%EB%8A%94-%EC%9D%B4%EC%8A%88/)

- Error when running `pod install` from Jenkins:

```
#+ echo ------------------------------------- Pod Install
#------------------------------------- Pod Install
#+ cd /Users/YOUR_USERNAME/Xcode
#+ /opt/homebrew/bin/pod install
#    33mWARNING: CocoaPods requires your terminal to be using UTF-8 encoding.
#    Consider adding the following to ~/.profile:
#
#    export LANG=en_US.UTF-8
#    0m
#/opt/homebrew/Cellar/ruby/3.2.2_1/lib/ruby/3.2.0/unicode_normalize/normalize.rb:141:in `normalize': Unicode Normalization not #appropriate for ASCII-8BIT (Encoding::CompatibilityError)
# ... (same stack trace)
#Build step 'Execute shell' marked build as failure
#Finished: FAILURE
```

<br>

## Solution
- After updating cocoapods and ruby gem to latest, running `pod install` in Xcode project folder generated Pods and xcworkspace correctly.
- Based on this, I solved it by calling `pod install` from Jenkins shell on mac terminal.
> fastlane also has cocoapods action: [fastlane cocoapods](https://docs.fastlane.tools/actions/cocoapods/)

- Jenkins shell script:

```
# Jenkins Shell Script

echo ------------------------------------- Pod Install
cd /Users/YOUR_USERNAME/Xcode
/opt/homebrew/bin/pod install
cd /Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane

```

- But this still failed with the above error.
- So first inspect Jenkins-reported locale values.

```
# locale check
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="ko_KR.UTF-8"
LC_COLLATE="ko_KR.UTF-8"
LC_CTYPE="ko_KR.UTF-8"
LC_MESSAGES="ko_KR.UTF-8"
LC_MONETARY="ko_KR.UTF-8"
LC_NUMERIC="ko_KR.UTF-8"
LC_TIME="ko_KR.UTF-8"
LC_ALL=
```

- All locale values were Korean.
- Change to English and verify:

```
# set LC_ALL to en
YOUR_USERNAME@YOUR_MACHINE bin % export LC_ALL=en_US.UTF-8
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="ko_KR.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL="en_US.UTF-8"

# also set LANG
YOUR_USERNAME@YOUR_MACHINE bin % export LANG=en_US.UTF-8
YOUR_USERNAME@YOUR_MACHINE bin % locale
LANG="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL="en_US.UTF-8"
```

- Even with this on mac mini, Jenkins build still failed.
- The key insight: Jenkins environment settings are different from machine shell settings.
- Therefore add locale export inside Jenkins shell script itself.

```
# can also add near init env setup
locale
export LANG=en_US.UTF-8
locale
```

- Jenkins output logs:

```
# locale check
+ locale
LANG=""
LC_COLLATE="C"
LC_CTYPE="C"
LC_MESSAGES="C"
LC_MONETARY="C"
LC_NUMERIC="C"
LC_TIME="C"
LC_ALL=

# convert
+ export LANG=en_US.UTF-8
+ LANG=en_US.UTF-8

# locale check
+ locale
LANG="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_CTYPE="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_ALL=

# pod install runs successfully
+ echo ------------------------------------- Pod Install
------------------------------------- Pod Install
+ cd /Users/YOUR_USERNAME/Xcode
+ /opt/homebrew/bin/pod install
Analyzing dependencies
Downloading dependencies
Installing Firebase (10.1.0)
Installing FirebaseAnalytics (10.1.0)
Installing FirebaseAuth (10.1.0)
Installing FirebaseCore (10.1.0)
Installing FirebaseCoreInternal (10.12.0)
Installing FirebaseInstallations (10.12.0)
Installing FirebaseMessaging (10.1.0)
Installing GTMSessionFetcher (2.3.0)
Installing GoogleAppMeasurement (10.1.0)
Installing GoogleDataTransport (9.2.3)
Installing GoogleUtilities (7.11.4)
Installing PromisesObjC (2.3.1)
Installing nanopb (2.30909.0)
Generating Pods project
Integrating client project

[!] Please close any current Xcode sessions and use `Unity-iPhone.xcworkspace` for this project from now on.
Pod installation complete! There are 4 dependencies from the Podfile and 13 total pods installed.
+ cd /Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane
Finished: SUCCESS
```

- Confirmed that Pods and xcworkspace were generated normally.
- I didn't expect Jenkins env and mac shell env to differ this much.
