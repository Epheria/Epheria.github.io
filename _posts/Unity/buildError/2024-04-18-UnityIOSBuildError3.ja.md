---
title: "Unity Addressableエラー解決 - RuntimeData is null, Invalid path in TextDataProvider"
date: 2024-04-18 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Addressable, error]
lang: ja
difficulty: intermediate
toc: true
---

## 主要エラー現象分析

- ビルドマシン：Mac Mini 1TB
- iOS、Android の両方で同時に発生
- **Mac Miniの容量不足**：0.99TB / 1TB
- 以前は正常に動作していたが、突然エラーが発生

- エラー内容：

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

## 原因と結果および解決方法

- **TextDataProvider** は built-in provider で、Addressableビルド時に生成するカタログである `settings.json` に含まれています。
- "Please ensure you have built the correct Player Content" というメッセージは、明らかにAddressableビルドが間違っていることを意味します。
- **結論**：ビルドマシンの容量不足により、Addressableビルド時に生成されるバンドルファイルが正しく生成されず、特に built-in provider のようなAddressableビルド初期に生成される主要ファイルが破損して発生したエラーと見られます。
- もちろん、他の原因でこれらのエラーが発生する場合もありますが、まずはディスク容量を確認することが重要です。
