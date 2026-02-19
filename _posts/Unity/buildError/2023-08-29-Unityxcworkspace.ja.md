---
title: Unity - xcworkspace が生成されない問題の解決
date: 2023-08-29 14:38:00 +/-TTTT
categories: [Unity, Build Error]
tags: [unity, build, xcworkspace, ios, pod install]
difficulty: intermediate
lang: ja
toc: true
---

## 目次

- [1. 主な症状と分析](#主な症状と分析)
- [2. 解決方法](#解決方法)

---

## Unity iOS プロジェクトビルド時に xcworkspace が生成されない問題

<br>

## 主な症状と分析

- **主症状**: macOS 環境で Jenkins + fastlane + build script によるリモートビルド中、cocoapods バージョン関連で問題が発生し、`Pods` フォルダと `xcworkspace` が生成されなかった。
- iOS Resolver 側で Integration は `xcworkspace` に設定済み、`Use Shell to Execute Cocoapod Tool` の ON/OFF に関係なく生成されなかった。

- iOS Resolver パス  
Assets - External Dependency Manager - iOS Resolver - Settings

<img src="/assets/img/post/unity/xcworkspaceissue01.png" width="500" height="700" title="256" alt="build1">

<br>

- 不思議だったのは、深掘り前にも数回同様の現象があり、cocoapods/gems バージョンを変えていないのに発生したりしなかったりした点。
- Unity プロジェクトを手動ビルドすると `xcworkspace` は正常生成される。

<br>

- Unity iOS Resolver 設定ミスの可能性
- mac-mini 側 cocoapods と ruby gems のバージョン衝突可能性

1. **cocoapods バージョン衝突チェック**
- terminal で cocoapods bin フォルダに移動して `pod --version`。
- 下はログ抜粋。

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

2. **cocoapods / ruby gem の更新**
- 現在バージョン確認後、最新へ更新。

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

3. **cocoapods ダウングレードが正解?**
- 検索すると `1.10.xx` 推奨が出るが、私の原因は別だった。
- 結論は NO。ダウングレード不要。原因は terminal locale/encoding 側だった。
- 下の解決方法で詳述。
> [Unity iOS Resolver で xcworkspace が生成されない問題](https://phillip5094.github.io/ios/unity/Unity-iOS-Resolver%EC%97%90%EC%84%9C-xcworkspace-%EC%83%9D%EC%84%B1%EB%90%98%EC%A7%80-%EC%95%8A%EB%8A%94-%EC%9D%B4%EC%8A%88/)

- Jenkins で `pod install` 実行時エラー:

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

## 解決方法
- cocoapods / ruby gem を最新化し、Xcode プロジェクトフォルダで `pod install` すると Pods と xcworkspace が正常生成されることを確認。
- これを基に Jenkins から mac terminal に入って `pod install` を実行して解決。
> fastlane にも cocoapods action がある: [fastlane cocoapods](https://docs.fastlane.tools/actions/cocoapods/)

- Jenkins Shell Script:

```
# Jenkins Shell Script

echo ------------------------------------- Pod Install
cd /Users/YOUR_USERNAME/Xcode
/opt/homebrew/bin/pod install
cd /Users/YOUR_USERNAME/.jenkins/workspace/ios_fastlane

```

- ただしこれでも同じエラーが出た。
- まず Jenkins の locale を確認。

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

- locale が韓国語設定だった。
- 英語に変更して確認:

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

- それでも Jenkins では失敗した。
- ここで、Jenkins 環境設定と mac-mini シェル設定が別であると判明。
- なので Jenkins shell script 内に locale export を追加する必要がある。

```
# can also add near init env setup
locale
export LANG=en_US.UTF-8
locale
```

- Jenkins 出力ログ:

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

- Pods と xcworkspace が正常生成されることを確認できた。
- Jenkins 側と mac 側の環境差が根本だった。
