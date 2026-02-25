---
title: "Unity Addressable Error Fix - RuntimeData is null, Invalid path in TextDataProvider"
date: 2024-04-18 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Addressable, error]
lang: en
difficulty: intermediate
toc: true
---

## Major Error Analysis

- Build Machine: Mac Mini 1TB
- Occurred simultaneously on iOS and Android
- **Mac Mini storage was full**: 0.99TB / 1TB
- Suddenly occurred after working fine previously

- Error Content:

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

## Cause and Solution

- **TextDataProvider** is a built-in provider included in `settings.json`, the catalog generated during the Addressable build.
- The message "Please ensure you have built the correct Player Content" clearly indicates that the Addressable build went wrong.
- **Conclusion**: Due to **insufficient storage** on the build machine, the bundle files generated during the Addressable build were not created properly. Specifically, key files generated early in the Addressable build, like the built-in provider, seem to have been corrupted.
- Of course, these errors could occur due to other reasons, but checking disk space is a good first step.
