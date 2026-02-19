---
title: Unity Build Automation - fastlane
date: 2023-08-03 11:35:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, build, automation, buildpipeline, fastlane, jenkins]
difficulty: intermediate
lang: en
toc: true
---

## Table of Contents

> [1. How to install fastlane](#fastlane-setup)  
> [2. How to install plugins](#plugin-setup)  
> [3. How to configure FastFile](#fastfile-setup)

---

## Introduction
> At work, I became responsible for overall iOS/AOS build operations. At first I used Jenkins only and succeeded with Android build automation through Unity Build Pipeline -> AppCenter upload -> Slack notification. But while automating iOS builds, I had difficulty automating Xcode settings such as certificates, provisioning signing, BitCode on/off, and auto signing.  
Then our CTO introduced `fastlane`, and it was much more convenient than Jenkins-only pipelines. I could install required plugins selectively via terminal and customize lanes by editing Fastfile for different build environments. This post records overall setup/integration for fastlane, Jenkins, and Unity Build Pipeline.

<br>

## Prerequisites / Reference
1. macOS
2. Homebrew and Bundler installed via Terminal
3. Xcode and Unity installed

<br>
<br>

## 1. fastlane setup

#### Install fastlane
1. Install with Homebrew
   - Open terminal and run `brew install fastlane`
   - If permission issues occur, run `sudo brew install fastlane`

<br>

2. Install bundler
   - Run `gem install bundler`
   - If `gem` is missing, install Ruby gem first.

<br>

<img src="/assets/img/post/unity/buildAuto01.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

3. Set folder where fastlane will be installed
   - First move to your target path in terminal.
   ``` terminal
   # "cd path"
   cd /Users/..../GitLab/YourProject
   ```

   - ~~Since fastlane uses Xcode command line tools, for Unity projects you should install fastlane in the iOS build output folder.~~
   - ~~(There may be other ways.) Also, separate the Xcode folder used for actual project build and the one used for fastlane. If you rebuild project with replace, FastFile can be overwritten.~~
   - In practice, since source control is used, you can install fastlane inside project and merge to develop/master branch.
   - Build machine must be macOS (we used Mac mini). fastlane does not run on Windows.

<br>

4. Initialize fastlane
   - Move to path containing Xcode project, then run `fastlane init`.
       <img src="/assets/img/post/unity/buildAuto02.png" width="1920px" height="1080px" title="256" alt="build1">
    - Keep pressing `continue by pressing enter`, then you'll see Apple ID/password input step. (This can be edited in AppFile later.)

<br>

#### fastlane file structure
   - After authentication, files are generated at target path: `Gemfile`, `Gemfile.lock`, `fastlane/AppFile`, `fastlane/FastFile`. Installing plugins also generates `PluginFile`.
    <img src="/assets/img/post/unity/buildAuto03.png" width="1920px" height="1080px" title="256" alt="build1">
    <img src="/assets/img/post/unity/buildAuto04.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### AppFile configuration
   - Remove commented `#` lines.
   - Set `app_identifier` (e.g. `com.companyname.projectname`)
   - Set `apple_id` as well (e.g. `xxxx@coconev.co.jp`)
    <img src="/assets/img/post/unity/buildAuto05.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### Plugin setup

| Type | Link |
| ------------ | ------------- |
| Unity build | [fastlane-plugin-unity](https://github.com/safu9/fastlane-plugin-unity)  |
| AppCenter upload | [fastlane-plugin-appcenter](https://github.com/microsoft/fastlane-plugin-appcenter)  |
| Slack bot | [fastlane-plugin-slack_bot](https://github.com/crazymanish/fastlane-plugin-slack_bot)  |

<br>
<br>

- Run `sudo fastlane add_plugin xxx`. After installation, `Pluginfile` is generated as below.

<img src="/assets/img/post/unity/buildAuto06.png" width="500px" height="500px" title="256" alt="build1">

<br>

<img src="/assets/img/post/unity/buildAuto07.png" width="1920px" height="1080px" title="256" alt="build1">

<br>

#### FastFile setup
- The final and core part of fastlane is **FastFile**.  
With Jenkins, you can use fastlane + Unity project on build machine for remote build/deploy.  
Using Jenkins *Execute Shell*, you can run fastlane init -> Addressable Build -> Unity Project Build -> AppCenter Upload.

> fastlane docs: [fastlane doc](https://docs.fastlane.tools/)  
FastFile is Ruby, so I edited it with VS Code.

<br>

1. platform
   - platform means iOS/Android. Use names that are easy to understand in terminal/CI logs.
   ```ruby
   platform :android do
   platform :ios do
   ```

2. desc
   - `desc` is description text and appears in fastlane logs.
   ```ruby
   platform: android do
      desc "Build AOS"
   end
   ```

3. lane
   - You define what plugin actions run in each lane.  
   You can split multiple lanes for various build settings/environments.
   ```ruby
   platform :android do
      desc "Build AOS"
      lane :aos_build do
      end
   end
   ```

4. lane - plugin  
If plugins are installed, configure like below.

   - **unity** plugin

   ```ruby
   # unity plugin
   unity(
   build_target: "Android",
   execute_method: "ProjectBuilder.BuildAndroid", # static method used in Unity Build Pipeline
   unity_path: "Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" # path to installed Unity version
   project_path: "/path/to/your/jenkins/workspace/android_fastlane" # Unity project path
   )
   ```
<br>

   - **upload_appcenter** plugin

   ```ruby
   # appcenter_upload
   appcenter_upload(
      api_token: "YOUR_APPCENTER_API_TOKEN", # appcenter - settings - API Token
      owner_name: "YOUR_OWNER_NAME", # appcenter owner name
      app_name: "toyverse_alpha_android", # app name on AppCenter
      file: "/path/to/your/build/output.aab", # final file path (.apk / .aab)
      destinations: "*", # distribute to all groups
      destination_type: "group", # group distribution type
      notify_testers: false, # email notification setting
      mandatory_update: true # see docs
   )
   ```
   <br>

   - **Android final example**

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

   - **iOS Unity build**

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

   - **Xcode build**

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
   - Xcode build has various commands (`build_app` etc.), but `gym` was simplest with fewer manual settings.
   - Especially for auto signing, bitcode, and library version issues, `gym` reduced many manual tasks.
   - Example GymFile  
   To use `gym`, configure GymFile: scheme, export method, provisioning profile, output path/name. In my case, setting provisioning in FastFile was unstable, while GymFile worked reliably up to ipa output.

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

   - Certificate registration: [>>click<<](https://ios-development.tistory.com/247)
   - Unity Xcode auto-signing / provisioning profile setup
      - #1. Player Settings - Other Settings -> Identification
   <img src="/assets/img/post/unity/unityauto01.png" width="1920px" height="1080px" title="256" alt="build1">
      - #2. Preferences - External Tools -> Xcode Default Settings (on macOS, under settings)
   <img src="/assets/img/post/unity/unityauto02.png" width="1920px" height="1080px" title="256" alt="build1">
      - It's convenient to keep certificates/profiles (and Android keystore as well) managed inside project.
   <img src="/assets/img/post/unity/unityauto03.png" width="1920px" height="1080px" title="256" alt="build1">

 <br>
