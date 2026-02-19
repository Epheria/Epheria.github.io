---
title: Unity ビルド自動化 - Jenkins
date: 2023-09-01 12:59:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, build, jenkins, automation]
difficulty: intermediate
lang: ja
toc: true
---

## Jenkins について
- Jenkins はクライアント/サーバー両方のビルドを支える共通ツール。
- Toyverse ではサーバー/クライアントとも Jenkins でビルドと配布を実施した。
> プロジェクトは Alpha / Dev / Real に分割。  
Dev = 開発中ブランチ、  
Alpha = QA / 社内テストブランチ、  
Real = 本番/ストア向けブランチ。

   - 実際に作成されていた Jenkins jobs
   ![Desktop View](/assets/img/post/unity/jenkins002.png){: : width="800" .normal }

   - jobs の構成図
   ![Desktop View](/assets/img/post/unity/jenkins004.png){: : width="800" .normal }

<br>

- クライアント側は Alpha/Dev/Real 向け aos/ios ビルド jobs を運用。
- サーバー側は API / CMS / Realtime ビルドを運用。

<br>

## 押さえておく Jenkins 基本
- Jenkins ローカル workspace パス: `./jenkins - workspace`
- Dashboard で作った job はビルドマシンの workspace に個別フォルダとして増える。
> ディスク消費はかなり大きい。専用ビルドマシンを置く理由になるレベル。Jenkins backup/plugin/cache/job 一式で 600GB 近くまで増えることもある。

- 下画像は mac finder 上の Jenkins job プロジェクト群。ほぼ Unity プロジェクトなので容量増加が大きい。

   ![Desktop View](/assets/img/post/unity/jenkins001.png){: : width="800" .normal }

- 一見すると分割しすぎで非効率に見えるが、理由がある。


- 1. Hotfix ブランチ

   ![Desktop View](/assets/img/post/unity/jenkins008.png){: : width="800" .normal }

   - 本番開始後は QA 未検出バグや高負荷由来バグが必ず出る。
   - この時、本番ブランチ基準の hotfix ブランチで迅速対応が必要。
   - 開発中の develop をそのまま本番に出すことはできない。
   - この運用上の理由で Dev / Real / Alpha に jobs を分割する。

<br>

- 2. iOS Certificates / Identifiers / Profiles
   - iOS 開発では Ad hoc/In House、Enterprise、Distribution、Development などを使い分ける。
   - Apple Login / IAP 等の可否がプロファイル別に異なる。
   - 例えば Enterprise では使えないが In House ではテスト可能、といった差がある。
   - これも jobs 分割理由の一つ。

<br>

- 3. 最大の理由は本番サーバーと Dev サーバーの分離。DB/API が異なるため、ビルドラインも分離が必要。

<br>
<br>

## Jenkins plugin と環境変数
- 初期セットアップ情報は多いので、ここでは必須寄りの plugin / env var に限定。
- 場所: Jenkins Dashboard - Jenkins 管理 - System Configuration

   ![Desktop View](/assets/img/post/unity/jenkins003.png){: : width="800" .normal }


- #### Plugin
   - Jenkins 機能拡張のため plugin は必須。
   - 代表例: Xcode integration, Unity3d plugin, App Center, Slack Notifications, Gradle, GitLab, Github Branch Source, Ant。

   ![Desktop View](/assets/img/post/unity/jenkins005.png){: : width="800" .normal }

- #### 環境変数
   - Jenkins 全体で使う key/value (パス、ID、トークン等) を設定。
   - 代表値: ビルドマシン project path、Unity path、apk/ipa upload path、Slack key、Apple Developer team ID など。

   ![Desktop View](/assets/img/post/unity/jenkins009.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins006.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins007.png){: : width="800" .normal }

<br>

## Jenkins 活用法
- Jenkins には Pipeline script、General plugin 設定など様々な方法がある。
- 個人的には **Execute shell** スクリプトで回すのが最も簡単だった。
- build trigger / environment / post-build action は、後処理をスクリプト化していれば大きく触らなくて良い。
> [build script 参考](https://epheria.github.io/posts/UnityBuildAutobuildpipeline/)  
  [fastlane 参考](https://epheria.github.io/posts/UnityBuildAuto/)

#### General タブ - パラメータ追加
- string / bool パラメータを作ってビルド時に利用できる。
- 例: branch name パラメータを使って特定ブランチ最新版をビルド。

   ![Desktop View](/assets/img/post/unity/jenkins010.png){: : width="400" .normal }

- bool は環境別分岐に便利 (例: Apple Login は InHouse のみ、Enterprise では失敗するケース)。

   ![Desktop View](/assets/img/post/unity/jenkins011.png){: : width="400" .normal }

- パラメータ付き build では次のように入力 UI が出る。
- ここで branch 名や bool 値を指定する。

   ![Desktop View](/assets/img/post/unity/jenkins014.png){: : width="400" .normal }


#### General タブ - Git ブランチ
- 上で作った branch パラメータを使って対象ブランチを checkout してビルドする。
- repository URL は正しく設定すること。

   ![Desktop View](/assets/img/post/unity/jenkins012.png){: : width="400" .normal }

   ![Desktop View](/assets/img/post/unity/jenkins013.png){: : width="400" .normal }

#### Execute shell
- プロジェクトビルド用 shell script を実行。バックグラウンド terminal に近いイメージ。
- コマンドは通常 terminal で使うものと同じ。

   ![Desktop View](/assets/img/post/unity/jenkins015.png){: : width="700" .normal }

<br>

#### iOS ビルドスクリプト

- aos より複雑。Unity project -> Xcode project -> ipa の順で進むため。

```
rm -rf /Users/YOUR_USERNAME/Build/toyverse_ipa
mkdir /Users/YOUR_USERNAME/Build/toyverse_ipa
```
- 最終 ipa 出力先を一度クリアして再生成。

```
pwd
locale
export LANG=en_US.UTF-8
locale
```
- [xcworkspace 生成問題](https://epheria.github.io/posts/Unityxcworkspace/) 対応で追加した部分。

```
XCODE_PATH=/Users/YOUR_USERNAME/Xcode
ENTITLEMENTS=Entitlements.entitlements
TMP_FILE=tmp.txt

rm -rf ${XCODE_PATH}
mkdir ${XCODE_PATH}
```
- Unity 側 iOS ビルドで Xcode プロジェクトが生成されるため、その出力先も初期化。

```
echo ------------------------------------- FASTLANE_SETTING
rm -rf "${WORKSPACE}/fastlane/Fastfile"
rm -rf "${WORKSPACE}/fastlane/Gymfile"
cp "${WORKSPACE}/fastlane/Fast/Fastfile_enterprise" "${WORKSPACE}/fastlane/Fastfile"
cp "${WORKSPACE}/fastlane/Gym/Gymfile_enterprise" "${WORKSPACE}/fastlane/Gymfile"
```
- fastlane の Fastfile / Gymfile を設定。
- `WORKSPACE` は Jenkins job のローカルパスを指す。

```
echo ------------------------------------- INIT
/opt/homebrew/bin/fastlane init
```
- fastlane 初期化。

```
echo ------------------------------------- FIREBASE_SETTING
rm -rf "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
cp "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Config/GoogleService-Info_enterprise.plist" "${WORKSPACE}/Assets/Scripts/Manager/Firebase/Setting/GoogleService-Info.plist"
echo ------------------------------------- UNITY IOS PROJECT BUILD
/Applications/Unity/Hub/Editor/2022.3.4f1/Unity.app/Contents/MacOS/Unity -projectPath "/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)ios" -batchmode -nographics -quit -buildTarget iOS -executeMethod ProjectBuilder.BuildIOS_Dev -logfile "" build_num:${BUILD_NUMBER}
```
- Unity project build を batchmode 実行。
- fastlane 経由の Unity build は制約が多く、最終的に batchmode 直実行にした。

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
- Xcode ビルド前に `pod install` が必要。

```
echo ------------------------------------- XCODE PROJECT BUILD
/opt/homebrew/bin/fastlane ios build_ios_gym
echo ------------------------------------- UPLOAD APPCENTER
/opt/homebrew/bin/fastlane ios upload_appcenter
```
- gym file で Xcode build。
- AppCenter upload は Fastfile 側に定義済み。

<br>

#### AOS ビルドスクリプト

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

#### Addressable スクリプト

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
