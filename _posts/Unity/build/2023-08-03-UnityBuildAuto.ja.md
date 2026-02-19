---
title: Unity ビルド自動化 - fastlane
date: 2023-08-03 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, build, automation, buildpipeline, fastlane, jenkins]
difficulty: intermediate
lang: ja
toc: true
---

## 目次

> [1. fastlane の導入方法](#fastlane-setup)  
> [2. Plugin の導入方法](#plugin-setup)  
> [3. FastFile の設定方法](#fastfile-setup)

---

## はじめに
> 会社で iOS/AOS ビルド全体を担当することになり、最初は Jenkins だけで Unity Build Pipeline による AOS 自動ビルド -> AppCenter アップロード -> Slack 通知までは成功しました。  
ただ、iOS 自動化では Certificates、Provisioning Signing、BitCode on/off、Auto Signing など Xcode 設定の自動化に苦戦しました。  
そこで CTO に fastlane を紹介してもらい、Jenkins Pipeline 単体よりかなり扱いやすいと感じました。必要なプラグインをターミナルで選択導入でき、Fastfile の lane をカスタムして複数ビルド環境に対応できます。本記事は fastlane / Jenkins / Unity Build Pipeline の設定・連携手順を整理したものです。

<br>

## 準備物 / 参考
1. macOS
2. Terminal で Homebrew と Bundler が導入済み
3. Xcode と Unity が導入済み

<br>
<br>

## 1. fastlane 設定方法 {#fastlane-setup}

#### fastlane インストール
1. Homebrew で fastlane を導入
   - Terminal で `brew install fastlane`
   - 権限問題時は `sudo brew install fastlane`

<br>

2. bundler インストール
   - `gem install bundler`
   - gem がない場合は先に gem 環境を導入

<br>

<img src="/assets/img/post/unity/buildAuto01.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

3. fastlane 導入先フォルダを指定
   - まず対象パスへ移動
   ``` terminal
   # "cd path"
   cd /Users/..../GitLab/YourProject
   ```

   - ~~fastlane は Xcode CLI ツールを使うため、Unity の場合は iOS 出力フォルダに入れる必要がある~~
   - ~~実ビルド用 Xcode フォルダと fastlane 管理用フォルダを分けないと、再ビルド時に FastFile が消える可能性がある~~
   - 実運用ではソース管理するため、プロジェクト内に fastlane を入れて develop/master へマージすればよい
   - ビルドマシンは macOS 必須 (Mac mini 使用)。Windows では fastlane 不可

<br>

4. fastlane 初期化
   - Xcode プロジェクトのあるパスで `fastlane init`
       <img src="/assets/img/post/unity/buildAuto02.png" width="1920px" height="1080px" title="256" alt="build1">
    - `continue by pressing enter` を進めると Apple ID / password 入力箇所が出る (AppFile で後から修正可)

<br>

#### fastlane ファイル構成
   - 認証完了後、`Gemfile`, `Gemfile.lock`, `fastlane/AppFile`, `fastlane/FastFile` が生成される。プラグイン導入後は `PluginFile` も生成される。
    <img src="/assets/img/post/unity/buildAuto03.png" width="1920px" height="1080px" title="256" alt="build1">
    <img src="/assets/img/post/unity/buildAuto04.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### AppFile 設定
   - `#` コメントを外し、
   - `app_identifier` を入力 (`com.companyname.projectname` など)
   - `apple_id` も入力 (`xxxx@coconev.co.jp` など)
    <img src="/assets/img/post/unity/buildAuto05.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### Plugin インストール {#plugin-setup}

| 種類 | リンク |
| ------------ | ------------- |
| Unity ビルド | [fastlane-plugin-unity](https://github.com/safu9/fastlane-plugin-unity)  |
| AppCenter アップロード | [fastlane-plugin-appcenter](https://github.com/microsoft/fastlane-plugin-appcenter)  |
| Slack bot | [fastlane-plugin-slack_bot](https://github.com/crazymanish/fastlane-plugin-slack_bot)  |

<br>
<br>

- `sudo fastlane add_plugin xxx` 実行後、インストールが終わると `Pluginfile` が生成される

<img src="/assets/img/post/unity/buildAuto06.png" width="500px" height="500px" title="256" alt="build1">

<br>

<img src="/assets/img/post/unity/buildAuto07.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### FastFile 設定 {#fastfile-setup}
- fastlane の核心は **FastFile**。  
Jenkins と組み合わせると、ビルドマシンの Unity プロジェクトと fastlane を使ってリモートビルド/配布が可能。  
Jenkins の *Execute Shell* で fastlane init -> Addressable Build -> Unity Project Build -> AppCenter Upload まで実行できる。

> fastlane ドキュメント: [fastlane doc](https://docs.fastlane.tools/)  
FastFile は Ruby なので VS Code で編集した。

<br>

1. platform
   - そのまま iOS/Android のプラットフォーム指定。
   ```ruby
   platform :android do
   platform :ios do
   ```

2. desc
   - 説明コメント。fastlane log にも出力される。
   ```ruby
   platform: android do
      desc "Build AOS"
   end
   ```

3. lane
   - lane 内に実行したい plugin 処理を書く。  
   複数 lane に分けてビルド設定・環境を構成可能。
   ```ruby
   platform :android do
      desc "Build AOS"
      lane :aos_build do
      end
   end
   ```

4. lane - plugin

   - **unity** plugin

   ```ruby
   # unity plugin
   unity(
   build_target: "Android",
   execute_method: "ProjectBuilder.BuildAndroid", # Unity Build Pipeline の static 関数
   unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" # Unity 実行ファイルパス
   project_path: "/path/to/your/jenkins/workspace/android_fastlane" # Unity project path
   )
   ```
<br>

   - **upload_appcenter** plugin

   ```ruby
   # appcenter_upload
   appcenter_upload(
      api_token: "YOUR_APPCENTER_API_TOKEN", # AppCenter API Token
      owner_name: "YOUR_OWNER_NAME", # owner 名
      app_name: "toyverse_alpha_android", # AppCenter 上のアプリ名
      file: "/path/to/your/build/output.aab", # 出力ファイルパス
      destinations: "*",
      destination_type: "group",
      notify_testers: false,
      mandatory_update: true
   )
   ```
   <br>

   - **Android 最終例**

   ```ruby
   platform :android do
     desc "Build AOS"
     lane :aos_build do
       unity(
         build_target: "Android",
         execute_method: "ProjectBuilder.BuildAndroid",
         unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
         project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
       )
    end

    desc "Upload AppCenter"
    lane :upload_appcenter do
       appcenter_upload(
         api_token: "YOUR_APPCENTER_API_TOKEN",
         owner_name: "YOUR_OWNER_NAME",
         app_name: "toyverse_alpha_android",
         file: "/path/to/your/build/output.aab",
         destinations: "*",
         destination_type: "group",
         notify_testers: false,
         mandatory_update: true
       )
    end

    desc "Build Addressable"
    lane :addressable do
       unity(
         build_target: "Android",
         execute_method: "ProjectBuilder.BuildAddressable",
         unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
         project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
       )
    end
   end
   ```
   <br>

   - **iOS Unity ビルド**

   ```ruby
   # build ios unity project
   desc "Build Unity Project iOS"
   lane :unity_ios do
    unity(
      build_target: "iOS",
      execute_method: "ProjectBuilder.BuildIOS",
      unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity",
      project_path: "/Users/Admin/.jenkins/workspace/android_fastlane"
    )
   ```
   <br>

   - **Xcode ビルド**

   ```ruby
   desc "Xcode build GYM"
   lane :build_ios_gym do
    clear_derived_data
    gym(
      scheme: "Unity-iPhone",
      export_method: "enterprise",
      clean: true,
      output_directory: "/Users/YOUR_USERNAME/Build/toyverse_ipa"
    )
   ```
   - Xcode ビルドには `build_app` など複数手段があるが、`gym` が最も簡単だった
   - Auto Signing、BitCode、ライブラリバージョン調整などの手作業が減る
   - GymFile 例  
   gym 用に GymFile を設定する。scheme、export_method、provisioning、ipa 出力先/名前を指定可能。FastFile 側で provisioning を書くより GymFile の方が安定した。

   ``` ruby
   scheme("Unity-iPhone")

   clean(true)
   export_method("enterprise")
   export_options({
      provisioningProfiles:{
            "com.coconev.toyverse.enterprise" => "toyverse_inhouse"
         }
      })
   output_directory("/Users/YOUR_USERNAME/Build/toyverse_ipa")
   output_name("toyverse_ios")
   ```

   - Certificate 登録: [>>リンク<<](https://ios-development.tistory.com/247)
   - Unity で Xcode Auto Signing / Provisioning Profile 設定
      - #1. Player Settings - Other Settings -> Identification を設定
   <img src="/assets/img/post/unity/unityauto01.png" width="1920px" height="1080px" title="256" alt="build1">
      - #2. Preferences - External Tools -> Xcode Default Settings を設定 (macOS は settings 経由)
   <img src="/assets/img/post/unity/unityauto02.png" width="1920px" height="1080px" title="256" alt="build1">
      - Apple Developer の Certificates / Provisioning Profile はプロジェクト管理に入れておくと便利 (Android keystore も含めて)
   <img src="/assets/img/post/unity/unityauto03.png" width="1920px" height="1080px" title="256" alt="build1">

 <br>
