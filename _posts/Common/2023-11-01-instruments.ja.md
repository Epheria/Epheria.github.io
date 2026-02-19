---
title: Mac で配布した iOS アプリのデバッグログを確認する方法 - Instruments
date: 2023-11-01 11:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [mac, instruments, ios, log]
difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

## macOS Instruments で TestFlight 配布アプリをデバッグする

> 通常の iOS 開発では、  
Unity Project ビルド -> Xcode プロジェクトビルド -> 接続したテスト端末に直接ビルドしてログを見ながらデバッグ、  
または App Center / TestFlight に配布して SRDebugger のようなアセットでログ確認、という流れが多いです。  
しかし Instruments を使えば、iPhone を接続して即座にログ確認できる方法があります。

<br>

### 1. `⌘ (Command) + Space` で Spotlight 検索を開く

- `Instruments` を検索して起動します。

![Desktop View](/assets/img/post/common/instruments01.png){: : width="600" .normal }

<br>
<br>

### 2. Instruments のプロファイリングテンプレートを Blank または Logging に設定

![Desktop View](/assets/img/post/common/instruments02.png){: : width="600" .normal }

<br>
<br>

### 3. Blank を選んだ場合は、右側の `+` ボタンを押してフィルター一覧を開く

![Desktop View](/assets/img/post/common/instruments03.png){: : width="1900" .normal }

<br>
<br>

### 4. `log` と入力し、`os_log` を選んで追加

![Desktop View](/assets/img/post/common/instruments04.png){: : width="1900" .normal }

<br>
<br>

### 5. 上部ツールバーでテスト端末を指定 -> ログ確認するアプリを選択

- テスト端末でアプリを実行し、Instruments 左上の赤い Record ボタンを押すとログ解析が始まります。

![Desktop View](/assets/img/post/common/instruments05_1.png){: : width="100" .normal }

<br>

![Desktop View](/assets/img/post/common/instruments05.png){: : width="1900" .normal }

<br>
<br>

### 6. `os_log` を展開すると、下部でアプリに含まれるプラグインやフレームワークを確認可能

![Desktop View](/assets/img/post/common/instruments06.png){: : width="500" .normal }

<br>
<br>

### 7. ここで重要なのは `UnityFramework`

- `UnityFramework` を選択すると、下部 Messages にログが出力されます。

![Desktop View](/assets/img/post/common/instruments07.png){: : width="1900" .normal }

<br>
<br>

### 8. Editor ログのようにコールスタックは確認できないため、事前にログを丁寧に入れてテストする

- エラーメッセージを通じて各種エラーを把握できます。

![Desktop View](/assets/img/post/common/instruments08.png){: : width="1900" .normal }
