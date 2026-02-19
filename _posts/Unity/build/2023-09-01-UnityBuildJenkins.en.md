---
title: Unity Build Automation - Jenkins
date: 2023-09-01 12:59:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, build, jenkins, automation]
difficulty: intermediate
lang: en
toc: true
---

## About Jenkins
- Jenkins is a build support tool used across both client and server projects.
- In Toyverse, both server and client builds/deployments were done through Jenkins.
> Project branches were split into Alpha, Dev, and Real.  
Dev = ongoing development branch,  
Alpha = QA/internal test branch,  
Real = production/store branch.

   - Actual jobs created in Jenkins
   ![Desktop View](/assets/img/post/unity/jenkins002.png){: : width="800" .normal }

   - Job architecture diagram
   ![Desktop View](/assets/img/post/unity/jenkins004.png){: : width="800" .normal }

<br>

- Client side supported aos/ios build jobs for Alpha/Dev/Real.
- Server side supported API, CMS, and Realtime builds.

<br>

## Jenkins basics to understand
- Local path where Jenkins workspaces are stored: `./jenkins - workspace`
- Jobs created on Jenkins dashboard are each mapped to separate local workspace folders on build machine.
> It consumes huge disk space. Build machine is often dedicated for this reason. Jenkins backup/plugin/cache/job projects together can grow up to 600GB. This was also one reason fastlane-only flow became difficult.

- Below image shows Jenkins job projects in mac finder. Since these are all Unity projects, disk usage grows quickly.

   ![Desktop View](/assets/img/post/unity/jenkins001.png){: : width="800" .normal }

- It may look inefficient to split and duplicate this much.
- But there are practical reasons:


- 1. Hotfix branches

   ![Desktop View](/assets/img/post/unity/jenkins008.png){: : width="800" .normal }

   - After live launch, bugs not found by QA or bugs under production load inevitably appear.
   - At this point, you need a hotfix branch based on live branch for quick response.
   - You must not deploy a develop branch with in-progress content directly to live.
   - This is why jobs are separated into Dev / Real / Alpha.

<br>

- 2. iOS Certificates / Identifiers / Profiles
   - iOS builds need distinctions like Ad hoc/In House, Enterprise, Distribution, Development.
   - Availability of features (Apple login, IAP, etc.) differs by profile type.
   - For example, Enterprise may not allow Apple login/IAP test in the same way In House does.
   - This is another reason for split jobs.

<br>

- 3. Biggest reason: production and dev servers are separated. DB/API endpoints differ, so build/deploy lines must be separated.

<br>
<br>

## Jenkins plugins and environment variables
- Setup guides are widely available, so this section focuses on essential plugins/variables.
- Path: Jenkins Dashboard - Manage Jenkins - System Configuration

   ![Desktop View](/assets/img/post/unity/jenkins003.png){: : width="800" .normal }


- #### Plugins
   - Plugins are essential to extend Jenkins functionality.
   - Typical ones: Xcode integration, Unity3d plugin, App Center, Slack Notifications, Gradle, GitLab, Github Branch Source, Ant.

   ![Desktop View](/assets/img/post/unity/jenkins005.png){: : width="800" .normal }

- #### Environment variables
   - Used to set global key values (paths, IDs, tokens).
   - Common global values include build machine project path, Unity install path, apk/ipa upload path, Slack keys, Apple Developer team IDs, etc.

   ![Desktop View](/assets/img/post/unity/jenkins009.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins006.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins007.png){: : width="800" .normal }

<br>

## How to use Jenkins
- There are many ways: pipeline scripts, adding plugins under General, and more.
- Personally, using **Execute shell** scripts was the simplest and easiest.
- Build triggers/environment/post actions often don't need extra changes if post-processing is already scripted.
> [Build script reference](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/)  
  [fastlane reference](https://epheria.github.io/posts/UnityBuildAuto/)

#### General tab - add parameters
- You can create string/bool parameters and use them during builds.
- Example: pass branch name parameter to build latest from specific branch.

   ![Desktop View](/assets/img/post/unity/jenkins010.png){: : width="400" .normal }

- bool values can control environment-specific behavior (e.g. Apple Login only for InHouse; Enterprise build may fail).

   ![Desktop View](/assets/img/post/unity/jenkins011.png){: : width="400" .normal }

- When clicking build with parameters, added fields appear like below.
- Set branch name and bool flags as needed.

   ![Desktop View](/assets/img/post/unity/jenkins014.png){: : width="400" .normal }


#### General tab - Git branch
- Use the branch parameter in Git branch field to build target branch.
- Repository URL must be correct.

   ![Desktop View](/assets/img/post/unity/jenkins012.png){: : width="400" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins013.png){: : width="400" .normal }

#### Execute shell
- Run shell scripts for project build. Think of it as background terminal commands.
- Commands are standard terminal commands.

   ![Desktop View](/assets/img/post/unity/jenkins015.png){: : width="700" .normal }

<br>

#### iOS build script

- More complex than aos. Flow is Unity project -> Xcode project -> ipa.

```
rm -rf /Users/YOUR_USERNAME/Build/toyverse_ipa
mkdir /Users/YOUR_USERNAME/Build/toyverse_ipa
```
- First clear/create output directory for final ipa.

```
pwd
locale
export LANG=en_US.UTF-8
locale
```
- Added due to [xcworkspace generation issue](https://epheria.github.io/posts/Unityxcworkspace/).

```
XCODE_PATH=/Users/YOUR_USERNAME/Xcode
ENTITLEMENTS=Entitlements.entitlements
TMP_FILE=tmp.txt

rm -rf ${XCODE_PATH}
mkdir ${XCODE_PATH}
```
- Since Unity iOS build outputs Xcode project, initialize that path too.

```
echo ------------------------------------- FASTLANE_SETTING
rm -rf "${WORKSPACE}/fastlane/Fastfile"
rm -rf "${WORKSPACE}/fastlane/Gymfile"
cp "${WORKSPACE}/fastlane/Fast/Fastfile_enterprise" "${WORKSPACE}/fastlane/Fastfile"
cp "${WORKSPACE}/fastlane/Gym/Gymfile_enterprise" "${WORKSPACE}/fastlane/Gymfile"
```
- Set fastlane `Fastfile` and `Gymfile`.
- `WORKSPACE` points to current Jenkins job local path (no extra parameter needed).

```
echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
```
- Initialize fastlane.

```
echo ------------------------------------- FIREBASE_SETTING
rm -rf "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
cp "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Config/GoogleService-Info_enterprise.plist" "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
echo ------------------------------------- UNITY IOS PROJECT BUILD
/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity -projectPath "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)ios" -batchmode -nographics -quit -buildTarget iOS -executeMethod ProjectBuilder.BuildIOS_Dev -logfile "" build_num:${BUILD_NUMBER}
```
- Run Unity project build in batchmode.
- Originally tried Unity build via fastlane, but changed to direct batchmode due constraints.

```
echo ------------------------------------- Pod Install
cd /Users/YOUR_USERNAME/Xcode
/opt/homebrew/bin/pod install
cd "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)ios"
if "${DEL_APPLE_LOGIN}"; then
	echo ------------------------------------- Delete Sign in Apple
	/usr/bin/sed '7,10d' ${XCODE_PATH}/${ENTITLEMENTS} > ${XCODE_PATH}/${TMP_FILE}
	rm -rf ${XCODE_PATH}/${ENTITLEMENTS}
	cp ${XCODE_PATH}/${TMP_FILE} ${XCODE_PATH}/${ENTITLEMENTS}
fi
```
- `pod install` is required before Xcode build.

```
echo ------------------------------------- XCODE PROJECT BUILD
/opt/homebrew/bin/fastlane ios build_ios_gym
echo ------------------------------------- UPLOAD APPCENTER
/opt/homebrew/bin/fastlane ios upload_appcenter
```
- Use gym file to build Xcode project.
- AppCenter upload lane is inside Fastfile.

<br>

#### AOS build script

```
rm -rf /Users/YOUR_USERNAME/Build/toyverse_apk
mkdir /Users/YOUR_USERNAME/Build/toyverse_apk
pwd
chmod 755 ./fastlane/change_build_num.sh
./fastlane/change_build_num.sh ${BUILD_NUMBER}

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
#echo ------------------------------------- ADDRESSABLE
#/opt/homebrew/bin/fastlane android addrressable
echo ------------------------------------- ANDROID BUILD
#/opt/homebrew/bin/fastlane android android
/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity -projectPath "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)android" -batchmode -nographics -quit -buildTarget Android -executeMethod ProjectBuilder.BuildAndroid_Dev -logfile "" build_num:${BUILD_NUMBER}
echo ------------------------------------- UPLOAD APPCENTER
/opt/homebrew/bin/fastlane android upload_appcenter
```

<br>

#### Addressable scripts

- iOS

```
pwd
locale
export LANG=en_US.UTF-8
locale

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
echo ------------------------------------- CLEAR ADDRESSABLE
rm -rf ${WORKSPACE}/ServerData/iOS/*
echo ------------------------------------- ADDRESSABLE
"/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" -projectPath "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)ios_addressable" -batchmode -nographics -quit -buildTarget iOS -executeMethod ProjectBuilder.BuildAddressable_IOS_Dev -logfile
echo ------------------------------------- S3 UPLOAD
chmod 775 ${WORKSPACE}/fastlane/upload_addressable_s3.sh
${WORKSPACE}/fastlane/upload_addressable_s3.sh ${WORKSPACE}/ServerData/iOS ios ${RESOURCE_VERSION} dev alpha
```


- AOS

```
pwd

echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
echo ------------------------------------- CLEAR ADDRESSABLE
rm -rf ${WORKSPACE}/ServerData/Android/*
echo ------------------------------------- ADDRESSABLE
"/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity" -projectPath "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)android_addressable" -batchmode -nographics -quit -buildTarget Android -executeMethod ProjectBuilder.BuildAddressable_AOS_Dev -logfile
echo ------------------------------------- S3 UPLOAD
chmod 775 ${WORKSPACE}/fastlane/upload_addressable_s3.sh
${WORKSPACE}/fastlane/upload_addressable_s3.sh ${WORKSPACE}/ServerData/Android aos ${RESOURCE_VERSION} dev alpha
```
