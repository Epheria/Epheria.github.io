---
title: "Unreal Mac OSでプロジェクトロードができない時の解決方法"
date: 2025-10-21 00:25:00 +/-TTTT
categories: [Unreal, MacOS]
tags: [Unreal, Mac, Xcode, SDK]
lang: ja
difficulty: intermediate
toc: true
math: true
mermaid: true
---

<br>

## GitHubから取得した .uproject をUnreal Mac OSで開く際にエラーが発生した

- App Storeから最新バージョンのXcodeをダウンロードしても、以下のエラーが発生して開けませんでした。

<br>

```
選択されたソースコードアクセサ 'Xcode' を開くのに失敗しました。
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

## 解決方法

- 原因は **Xcodeが新しすぎる** ため、Unrealで認識できなかったことです。
- [最近のベータバージョンはXcode 26以上なので、Xcode 16をダウンロードする必要があります。](https://forums.unrealengine.com/t/platform-mac-is-not-a-valid-platform-to-build-check-that-the-sdk-is-installed-properly-and-that-you-have-the-necessary-platorm-support-files-datadrivenplatforminfo-ini-sdk-json-etc/1846659/3)

<br>

[Xcode 16 ダウンロードリンク](https://developer.apple.com/download/all/)

<br>

```bash
xcodebuild -version
xcode-select --print-path
```

まずこの2つのコマンドでXcodeがインストールされているか確認し、

<br>

```bash
xcode-select --install
```

を通じて念のため Command Line Tools がインストールされているか試します（インストールされていればエラーが出ます）。

<br>

インストールされたXcodeパッケージの内容を表示 - Contents - Developer パスをコピーして、

<br>

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

- パスを再指定します。

- `/Applications/Xcode.app/Contents/Developer` の文字列内部に、自身のXcodeがインストールされたパスを入れてください。

<br>

プロジェクトの場所に `.xcworkspace` が正しく生成されたか確認します。

<br>

プロジェクトの場所にある `.uproject` をダブルクリックしてプロジェクトを開きます。

<br>

**注意：GitHub LFS Initialize は必ず行ってください。Unrealのアセットファイルは容量が大きいためLFSでアップロードされているはずですが、Initializeしないとアセットファイルがない状態でプロジェクトが開かれます。**
