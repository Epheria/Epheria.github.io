---
title: "Unity iOS - Xcode コード署名ガイド (証明書とプロビジョニングプロファイル)"
date: 2024-05-03 10:00:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Xcode, Code Signing, Certificates, Provisioning Profile, iOS]
lang: ja
difficulty: intermediate
toc: true
math: true
mermaid: true
---

## 目次
> [Apple Certificate](#apple-certificates---apple-証明書)      
> [App ID 生成方法](#app-id-identifier-生成方法)     
> [Device 登録方法](#device-登録方法)     
> [Provisioning Profile 生成方法](#provisioning-profile-生成方法)  

<br>
<br>

## Apple Certificates - Apple 証明書

- Appleがリリースしたデバイス（ハードウェア）でソフトウェア（アプリ、プログラムなど）を動作させるために、実際にアプリが実行されるたびにAppleから認証を受けたか確認する手続きを経ます。
- 毎回リクエストして管理するのは煩わしいため、[Apple Developer](https://developer.apple.com/account) で証明書を取得すれば、Appleが開発者を信頼してアプリを実行できる権限を付与してくれます。

<br>

## 証明書の取得方法

#### 1. キーの作成 (認証署名リクエスト)

![Desktop View](/assets/img/post/unity/ioscodesigning01.png){: : width="800" .normal }

- まず証明書を取得するために、`cmd + space` -> キーチェーンアクセスを検索するか、アプリケーション - ユーティリティ - キーチェーンアクセスアプリを開きます。

<br>

- その後、 **キーチェーンアクセス** で **CSR (Certificate Signing Request)** を先に生成する必要があります。

![Desktop View](/assets/img/post/unity/ioscodesigning02.png){: : width="800" .normal }

- 上部メニューから **キーチェーンアクセス -> 証明書アシスタント -> 認証局に証明書を要求** をクリックします。

<br>

- **認証局に証明書を要求** すると、次の作業を実行します。
> 1. 証明書の **公開鍵** と **秘密鍵** を自動的に生成します。生成されたキーはキーチェーンアプリの「キー」カテゴリで確認できます。（大切に保管する必要があります）      
> ![Desktop View](/assets/img/post/unity/ioscodesigning05.png){: : width="500" .normal }       
> 2. Appleに送る **CertificateSigningRequest.certSigningRequest** ファイルを生成します。このファイルは名前、メール、公開鍵を含んでおり、秘密鍵を利用して署名（Sign）を行います。

<br>

![Desktop View](/assets/img/post/unity/ioscodesigning03.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/ioscodesigning04.png){: : width="500" .normal }

- 上記の過程を経ると、キーチェーンアクセスのキーに先ほど作成した一般名で公開鍵、秘密鍵が作成されます。

<br>
<br>

#### 2. Certificate 発行

- [Apple Developer](https://developer.apple.com/account) -> 証明書 (Certificates) をクリックします。

![Desktop View](/assets/img/post/unity/ioscodesigning06.png){: : width="800" .normal }

<br>

---

![Desktop View](/assets/img/post/unity/ioscodesigning07.png){: : width="800" .normal }

- Certificates, Identifiers & Profiles タブが表示されます。
- 左側のタブで各種 Certificates, Identifiers, Profiles を作成したり、テスト用 Device を登録したりできます。
- "+" ボタンを押して Certificates を先に生成しましょう。

<br>

---

- 基本的に iOS Certificate は Enterprise を除き、 **Development (開発)** 用と **Distribution (配布)** 用に分かれます。
> [Apple Developer Program (リリース用)、Apple Developer Enterprise Program (社内テスト用) に関する違い](https://developer.apple.com/jp/support/roles/)      
> 要約すると、Apple Developer Program (リリース用) は実際のApp Store登録用、Enterprise は社内テスト目的で使用します。      
> もちろん Apple Developer Program で Development として Certificate を作成すれば、TestFlightを通じてテストが可能です！（必ずしもリリース目的だけではないという意味）

<br>

- Certificate を作成する際、Enterprise と Developer (リリース用) の違いは以下の通りです。

![Desktop View](/assets/img/post/unity/ioscodesigning22.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning23.png){: : width="800" .normal }

_Apple Developer Program_

<br>

---

- Apple Developer Program でのみ Development (開発) 用と Distribution (配布) 用に分かれる点を確認してください。

![Desktop View](/assets/img/post/unity/ioscodesigning10.png){: : width="800" .normal }

<br>

---

- CSR (CertificateSigningRequest) を登録後、Continue で続行します。

![Desktop View](/assets/img/post/unity/ioscodesigning11.png){: : width="800" .normal }

<br>

---

- 生成された Certificate をダウンロードした後、 **ダブルクリック** するとキーチェーンに自動的に登録されます。

![Desktop View](/assets/img/post/unity/ioscodesigning12.png){: : width="800" .normal }


![Desktop View](/assets/img/post/unity/ioscodesigning13.png){: : width="800" .normal }

- 上記の過程まで完了すれば、Appleで認証された開発者になったということです。
- しかし、アプリを Sign できるように許可を受けただけで、デバイスが私を開発者として信頼しているか確認させる必要があります。
- 新しく生成した Certificate 証明書と iOS 機器を接続させる必要があり、これを **Provisioning Profile (プロビジョニングプロファイル)** と言います。

<br>
<br>

---

## Provisioning Profile - プロビジョニングプロファイル

- Provisioning Profile は App ID, Certificate, Device 情報を持っており、iOS 機器と Apple Certificate を接続させる役割を果たします。

![Desktop View](/assets/img/post/unity/ioscodesigning14.png){: : width="800" .normal }

- 1. **App ID**: App Store に登録される Bundle ID 情報が入っています。
- 2. **Certificate**: Identifier を作成する際、上記で作成した証明書を入れれば良いです -> その Identifier を Provisioning Profile を作成する際に入れれば良いです。
- 3. **Device**: テスト用に使用するデバイス UDID。

- Provisioning Profile を生成する前に、先ほど生成した Certificate を基に App ID (Identifier) と Device 登録手続きが必要です。
- まず App ID を作ってみましょう。

<br>

---

#### App ID (Identifier) 生成方法

- 左側のタブで Identifiers をクリック -> "+" ボタンを押して App ID 生成に進みます。

![Desktop View](/assets/img/post/unity/ioscodesigning15.png){: : width="800" .normal }

<br>

---

- App IDs を選択して Continue

![Desktop View](/assets/img/post/unity/ioscodesigning16.png){: : width="800" .normal }

<br>

---

- 希望する形態のタイプを選択 (App, App Clip) - ここでは App
- ちなみに Enterprise にはこの段階がありません。

![Desktop View](/assets/img/post/unity/ioscodesigning17.png){: : width="800" .normal }

<br>

---

- Description にこのプロファイルが何の役割をするか明記し、 Bundle ID を記入します。
- Apple 公式推奨ネーミングは以下の通りです。
> We recommend using a reverse-domain name style string (i.e., com.domainname.appname). It cannot contain an asterisk (*).

![Desktop View](/assets/img/post/unity/ioscodesigning18.png){: : width="800" .normal }

<br>

---

- 使用する Capabilities を必ずチェックしましょう。（後で修正可能です）
- 主に **Push Notifications**, **Sign in with Apple** をよく使用します。（アプリ初期設定時によく忘れて入れない傾向があります）

![Desktop View](/assets/img/post/unity/ioscodesigning19.png){: : width="800" .normal }

- Continue を押した後 Register をすれば Identifier に App ID が登録されます！

<br>

---

#### Device 登録方法

- Devices をクリック -> "+" ボタンを押してデバイス登録に進みます。

![Desktop View](/assets/img/post/unity/ioscodesigning20.png){: : width="800" .normal }

<br>

---

- **Device Name** には機器の種類、モデルのような名前を書くと良いでしょう。
- **UDID** は機器固有IDで、設定で確認が可能です（またはFinder/iTunes経由）。

![Desktop View](/assets/img/post/unity/ioscodesigning21.png){: : width="800" .normal }

<br>

---

#### Provisioning Profile 生成方法

- これですべての準備 (Certificate, App ID, Device) が終わったので、 Provisioning Profile を作る必要があります。
- Profiles をクリックした後 -> "+" を押して Provisioning Profile 生成に進みます。

![Desktop View](/assets/img/post/unity/ioscodesigning24.png){: : width="800" .normal }

<br>

---

- Provisioning Profile を作る際の Enterprise と Developer (リリース用) の違いは以下の通りです。

![Desktop View](/assets/img/post/unity/ioscodesigning08.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning09.png){: : width="800" .normal }

_Apple Developer Program_

<br>

- ちなみに **Ad Hoc** は内部テスターを登録して配布が可能で、 **In House** は App Center のような場所に ipa ファイルを登録して配布が可能です。

<br>

---

- 開発用 or 配布用を選択して Continue

![Desktop View](/assets/img/post/unity/ioscodesigning25.png){: : width="800" .normal }

<br>

---

- 先ほど作った **App ID** を選択して Continue

![Desktop View](/assets/img/post/unity/ioscodesigning26.png){: : width="800" .normal }

<br>

---

- 最初に作った **Certificate** 証明書を選択して Continue

![Desktop View](/assets/img/post/unity/ioscodesigning27.png){: : width="800" .normal }

<br>

---

- **Device** を選択して...

![Desktop View](/assets/img/post/unity/ioscodesigning28.png){: : width="800" .normal }

<br>

---

- **Provisioning Profile Name** を記入し、 Generate を通じて作成すれば完了です。

![Desktop View](/assets/img/post/unity/ioscodesigning29.png){: : width="800" .normal }

<br>

---

- その後 Provisioning Profile をダウンロードして Unity Project 内部に入れましょう！
- Toyverse では `Keystore` というフォルダ内部に Development, Enterprise, App Store 用に区分してフォルダ分けしています。

![Desktop View](/assets/img/post/unity/ioscodesigning31.png){: : width="500" .normal }

<br>

---

- 各フォルダ内部には Certificate, Provisioning Profile が入っています。

![Desktop View](/assets/img/post/unity/ioscodesigning30.png){: : width="800" .normal }

<br>

---

- Provisioning Profile の場合、UnityプロジェクトをビルドしてXcodeプロジェクトとして出力する際、 **Automatically Manage Signing** オプションをチェックすると Project Setting, Preference で登録ができるため、このように入れてあります。詳細な説明は [Xcode ビルドパイプラインの投稿を参照](https://epheria.github.io/posts/UnityXcodeBuildPipeline/) してください。

![Desktop View](/assets/img/post/unity/ioscodesigning32.png){: : width="800" .normal }

- これで Code Signing 作業が終わりました！

<br>

---

- もしエラーが出る場合は **Bundle Identifier** が合っているか確認してみましょう！
- 複数の Provisioning Profile を持つことができるため、連携した App ID と実際にコンパイルしようとするプロジェクトの Bundle ID が一致しなければなりません。
