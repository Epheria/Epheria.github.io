---
title: Mac Jekyll 설치 및 세팅 방법
date: 2023-10-30 13:12:00 +/-TTTT
categories: [Tool, Mac]
tags: [Mac, Jekyll, Ruby, rbenv, gem]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

<br>
<br>

> 이 블로그 포스팅도 jekyll 기반의 블로그를 깃허브 posts 를 사용해서 포스팅을 하고 있는데,   
최근에 개발 환경이 윈도우즈에서 맥으로 바뀌면서 맥북에 새로운 환경을 세팅해야했고   
home brew 설치 -> 루비 설치 -> 루비 버전관리용인 rbenv 설치 -> bundler, jekyll 설치를 해야했다.

## jekyll 세팅 방법

<br>

터미널을 열어주자.

#### 1. homebrew 설치

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

brew 업데이트

```
brew update
```

<br>
<br>

#### 2. ruby 및 rbenv 설치

먼저 brew 로 rbenv 를 설치해야한다.
rbenv 는 루비를 버전 별로 관리할 수 있게 해주는 패키지이다.

```
brew install rbenv ruby-build
```

* rbenv 에서 사용할 수 있는 설치된 ruby 버전들 체크 하는 방법

```
rbenv versions
```

<br>