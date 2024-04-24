---
title: Unity Addressable 에러 - RuntimeData is null, Invalid path in TextDataProvider
date: 2024-04-18 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Addressable, error]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 주요 에러 현상 분석

- 빌드머신 : 맥미니 1TB
- iOS, AOS 두 곳 동시에 발생
- 맥미니 용량이 부족했음. 0.99TB/1TB
- 기존에 잘 되다가 갑작스럽게 해당 에러들 발생

- 에러 내용

```console
Error: System.Exception: Invalid path in TextDataProvider : '/private/var/containers/Bundle/Application/5B316240-0936-4BB3-8B2C-FA98D84C8962/alphaTOYVERSE.app/Data/Raw/aa/settings.json'.
UnityEngine.AddressableAssets.Addressables:InitializeAsync()
PJX.Manager.<Init>d__2:MoveNext()
PJX.Manager.AddressableManager:Init()
<initManagers>d__63:MoveNext()
Cysharp.Threading.Tasks.UniTaskCompletionSourceCore`1:TrySetResult(TResult)
<Init>d__66:MoveNext()
UnityEngine.AsyncOperation:InvokeCompletionEvent()


Error: RuntimeData is null.  Please ensure you have built the correct Player Content.
UnityEngine.AddressableAssets.Addressables:InitializeAsync()
PJX.Manager.<Init>d__2:MoveNext()
PJX.Manager.AddressableManager:Init()
<initManagers>d__63:MoveNext()
Cysharp.Threading.Tasks.UniTaskCompletionSourceCore`1:TrySetResult(TResult)
<Init>d__66:MoveNext()
UnityEngine.AsyncOperation:InvokeCompletionEvent()
```

<br>

## 원인과 결과 및 해결 방법

- TextDataProvider 는 built-in provider 로 어드레서블 빌드 시 생성하는 카탈로그인 settings.json 에 포함되어 있음
- 올바른 Player Content 빌드를 하라는것은 분명 어드레서블 빌드가 잘못되었다는 뜻
- 결론은, 빌드머신의 용량이 부족하여 어드레서블 빌드 시 생성되는 번들 파일들이 제대로 생성되지 않았고 특히 built-in provider 와 같은 어드레서블 빌드 초기에 생성하는 주요 파일들이 손상되어 발생한 에러로 보인다.
- 당연하겠지만, 다른 원인으로 해당 에러들이 발생할 경우가 있을 수 있음.