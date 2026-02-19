---
title: Mac で Jekyll をインストールしてセットアップする方法
date: 2023-10-30 13:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [mac, jekyll, ruby, rbenv, gem]
difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

> このブログ投稿も Jekyll ベースで、GitHub posts を使って公開しています。  
最近、開発環境が Windows から Mac に変わったため、MacBook に新しい環境を構築する必要がありました。  
Homebrew インストール -> Ruby インストール -> Ruby バージョン管理用 rbenv インストール -> bundler, jekyll インストール、という流れです。

## Jekyll セットアップ手順

<br>

ターミナルを開きます。

#### 1. Homebrew をインストール

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

brew を更新:

```
brew update
```

<br>
<br>

#### 2. Ruby と rbenv をインストール

まず brew で `rbenv` をインストールします。  
`rbenv` は Ruby をバージョンごとに管理できるパッケージです。

```
brew install rbenv ruby-build
```

* rbenv で利用可能なインストール済み Ruby バージョンを確認する方法:

```
rbenv versions
```

<br>

現在選択されているバージョンを確認できます。

![Desktop View](/assets/img/post/common/macSetting00.png){: : width="600" .normal }

<br>

* インストール可能な Ruby バージョンを確認する方法:

```
rbenv install -l
```

<br>

> 2023-10-30 時点では `3.2.2` が最新バージョンです。

![Desktop View](/assets/img/post/common/macSetting01.png){: : width="600" .normal }

<br>

#### 3. rbenv に最新 Ruby をインストールし、そのバージョンを global に設定

* 使いたいバージョンを選んでインストール:

```
rbenv install 3.2.2
```

* 希望バージョンをグローバル設定:

```
rbenv global 3.2.2
```

<br>

> ただし、この直後に bundler / jekyll gem をインストールしようとすると、次のエラーが発生する場合があります。

```
Gem::FilePermissionError: You don't have write permissions for the /usr/local/bin directory.

ERROR:  While executing gem ... (Gem::FilePermissionError)
    You don't have write permissions for the /Library/Ruby/Gems/2.3.0 directory.
```

<br>

#### 4. `Gem::FilePermissionError` の解決方法

* `.zshrc` に rbenv の設定を反映する必要があります。vim エディタを開いて `.zshrc` を編集します。

```
vim ~/.zshrc
```

* ファイルを編集するには INSERT モードに入る必要があります。

<br>

![Desktop View](/assets/img/post/common/macSetting02.png){: : width="300" .normal }

<br>

この状態で `i` キーを押して INSERT モードへ入ります。

<br>

* INSERT モード

![Desktop View](/assets/img/post/common/macSetting03.png){: : width="300" .normal }

<br>

* 入力可能になります

![Desktop View](/assets/img/post/common/macSetting04.png){: : width="300" .normal }

<br>

* ESC を押して INSERT モードから NORMAL モードに戻ります。

* `:` を入力すると終了・保存などのコマンドを実行できます。

```
:q    // 終了
:w    // 保存
:wq   // 保存して終了
:q!   // 保存せず終了
:wq!  // 強制保存して終了
```

<br>

![Desktop View](/assets/img/post/common/macSetting05.png){: : width="300" .normal }

<br>
<br>

* 下記内容をコピーして、同じ手順で `.zshrc` に追記します。

```
[[ -d ~/.rbenv  ]] && \
export PATH=${HOME}/.rbenv/bin:${PATH} && \
eval "$(rbenv init -)"
```


<br>

#### 5. bundler をインストール

```
gem install bundler
```


#### 6. 投稿用ブログフォルダに移動して bundler をインストール

```
bundler install
```

その後は GitHub Pages 側で毎回ビルドしなくても、Jekyll サーバーを起動してローカルでプレビューできます。

* Jekyll server 起動

```
bundle exec jekyll s
bundle exec jekyll serve

どちらでも実行可能
```

ローカルホスト URL

```
http://127.0.0.1:4000/
```
