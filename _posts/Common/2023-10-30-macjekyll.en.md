---
title: How to Install and Set Up Jekyll on Mac
date: 2023-10-30 13:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [mac, jekyll, ruby, rbenv, gem]
difficulty: intermediate
lang: en
toc: true
---

<br>
<br>

> This blog is also built on Jekyll and published through GitHub posts.  
My development environment recently changed from Windows to Mac, so I had to set up a new environment on my MacBook:  
install Homebrew -> install Ruby -> install rbenv for Ruby version management -> install bundler and Jekyll.

## How to set up Jekyll

<br>

Open Terminal.

#### 1. Install Homebrew

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Update brew:

```
brew update
```

<br>
<br>

#### 2. Install Ruby and rbenv

First, install `rbenv` using brew.  
`rbenv` is a package that lets you manage multiple Ruby versions.

```
brew install rbenv ruby-build
```

* How to check installed Ruby versions available in rbenv:

```
rbenv versions
```

<br>

You can check the currently selected version.

![Desktop View](/assets/img/post/common/macSetting00.png){: : width="600" .normal }

<br>

* How to check which Ruby versions can be installed:

```
rbenv install -l
```

<br>

> As of 2023-10-30, `3.2.2` is the latest version.

![Desktop View](/assets/img/post/common/macSetting01.png){: : width="600" .normal }

<br>

#### 3. Install the latest Ruby version in rbenv and set it as global

* Install the version you want:

```
rbenv install 3.2.2
```

* Set your desired version globally:

```
rbenv global 3.2.2
```

<br>

> But if you try to install bundler or Jekyll gems right away, you may get this error:

```
Gem::FilePermissionError: You don't have write permissions for the /usr/local/bin directory.

ERROR:  While executing gem ... (Gem::FilePermissionError)
    You don't have write permissions for the /Library/Ruby/Gems/2.3.0 directory.
```

<br>

#### 4. Fixing `Gem::FilePermissionError`

* You need to apply rbenv settings in `.zshrc`. Open the vim editor and modify `.zshrc`.

```
vim ~/.zshrc
```

* You must enter INSERT mode to edit the file.

<br>

![Desktop View](/assets/img/post/common/macSetting02.png){: : width="300" .normal }

<br>

From that screen, press `i` to enter INSERT mode.

<br>

* INSERT mode

![Desktop View](/assets/img/post/common/macSetting03.png){: : width="300" .normal }

<br>

* Now you can type

![Desktop View](/assets/img/post/common/macSetting04.png){: : width="300" .normal }

<br>

* Press ESC to leave INSERT mode and return to NORMAL mode.

* Press `:` to run commands like quit/save.

```
:q    // quit
:w    // save
:wq   // save and quit
:q!   // quit without saving
:wq!  // force save and quit
```

<br>

![Desktop View](/assets/img/post/common/macSetting05.png){: : width="300" .normal }

<br>
<br>

* Copy the content below and add it to `.zshrc` using the same process:

```
[[ -d ~/.rbenv  ]] && \
export PATH=${HOME}/.rbenv/bin:${PATH} && \
eval "$(rbenv init -)"
```


<br>

#### 5. Install bundler

```
gem install bundler
```


#### 6. Move to your blog folder and install bundler dependencies

```
bundler install
```

After that, instead of building every time through GitHub Pages, you can run a local Jekyll server to preview your site.

* Run Jekyll server:

```
bundle exec jekyll s
bundle exec jekyll serve

Both work.
```

Local host URL:

```
http://127.0.0.1:4000/
```
