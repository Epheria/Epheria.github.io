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

현재 선택된 버전을 확인할 수 있다.

![Desktop View](/assets/img/post/common/macSetting00.png){: : width="600" .normal }

<br>

* 현재 설치할 수 있는 ruby 버전들을 체크 하는 방법

```
rbenv install -l
```

<br>

> 2023-10-30 기준 3.2.2 가 가장 최신 버전임.

![Desktop View](/assets/img/post/common/macSetting01.png){: : width="600" .normal }

<br>

#### 3. rbenv 에 최신 버전의 ruby를 설치 및 해당 버전을 global로 설정

* 본인이 원하는 버전을 선택해서 설치

```
rbenv install 3.2.2
```

* 원하는 버전을 전역으로 설정

```
rbenv global 3.2.2
```

<br>

> 하지만 곧바로 bundler, jekyll gem 을 설치하려고 하면 다음과 같은 에러가 발생한다.

```
Gem::FilePermissionError: You don't have write permissions for the /usr/local/bin directory.

ERROR:  While executing gem ... (Gem::FilePermissionError)
    You don't have write permissions for the /Library/Ruby/Gems/2.3.0 directory.
```

[관련 에러 github 토론 링크]("https://github.com/search?q=repo%3Arubygems%2Frubygems+You+don%27t+have+write+permissions+for+the+%2Fusr%2Fbin+directory.&type=Issues")

<br>

#### 4. `Gem::FilePermissionError` 에러 해결 방법

* zshrc 에 rbenv의 내용을 반영해줘야 한다고 한다.. vim 에디터를 실행하여 zshrc를 수정해주자.

```
vim ~/.zshrc
```

* INSERT 모드에 진입해야만 파일에 덮어쓰기가 가능하다.

<br>

![Desktop View](/assets/img/post/common/macSetting02.png){: : width="300" .normal }

<br>

위 상태에서 `i` 키를 눌러 INSERT 모드로 진입 해주자.

<br>

* INSERT 모드

![Desktop View](/assets/img/post/common/macSetting03.png){: : width="300" .normal }

<br>

* 입력이 가능

![Desktop View](/assets/img/post/common/macSetting04.png){: : width="300" .normal }

<br>

* ESC를 눌러서 INSERT모드에서 NORMAL 모드로 전환 후

* `:` 입력 하여 종료, 저장 등 기능을 수행 가능

```
:q    // 종료
:w    // 저장
:wq   // 저장 후 종료
:q!   // 저장하지 않고 종료
:wq!  // 강제로 저장 후 종료
```

<br>

![Desktop View](/assets/img/post/common/macSetting05.png){: : width="300" .normal }

<br>
<br>

* 아래 내용을 복사해서 위의 과정처럼 zshrc 파일에 입력

```
[[ -d ~/.rbenv  ]] && \
export PATH=${HOME}/.rbenv/bin:${PATH} && \
eval "$(rbenv init -)"
```


<br>

#### 5. bundler 설치

```
gem install bundler
```


#### 6. 포스팅할 블로그 폴더로 이동 후 bundler 설치

```
bundler install
```

이후 깃허브 페이지로 일일히 빌드하지 않고 jekyll 서버를 실행하여 로컬 호스트로 현재 페이지를 미리보기 할 수있다.

* jekyll server 실행

```
bundle exec jekyll s
bundle exec jekyll serve

둘 다 가능
```

local host 주소

```
http://127.0.0.1:4000/
```

