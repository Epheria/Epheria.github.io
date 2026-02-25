---
title: "Unity Androidビルドエラー解決 - DexArchiveMergerException & MultiDex"
date: 2024-02-26 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 自動化, Android, DexArchiveMergerException, multiDexEnabled, mergeDexRelease, gradle build failed, Minify]
lang: ja
difficulty: intermediate
toc: true
---

## エラー原因の把握

- 既存のUnityバージョン 2022.3.4f1 から 2022.3.19f1 へアップグレード
- ビルドマシンのMac Miniを MacOS Sonoma 14.3.1 へ、Xcodeを 15.2 へアップデート
- Jenkinsでリモートビルド中、DEV Androidで原因不明のエラーが発生しました。

<br>
<br>

## 最初の失敗原因と解決方法：MultiDexを有効にする

```
User
ERROR:/Users/YOUR_USERNAME/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/unityLibrary/build/.transforms/f5f2117adcaee1eb1097391e7bb3025e/transformed/classes/classes.dex: D8: Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: ...
com.android.builder.dexing.DexArchiveMergerException: Error while merging dex archives: 
Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: ...
```

- `com.google.firebase.MessagingUnityPlayerActivity` という重複したクラスが定義されたことが原因だったようです。特に2回以上定義されたクラスは、2つのdexアーカイブで競合を引き起こすとのことです。
- これを解決するには **MultiDex** の有効化が必要でした。Unityフォーラムやディスカッションでもいくつか問題が報告されていました。
- 2014年から始まって最新のものは2019年ではありましたが... このビルドを解決するためには、どんな手を使ってでも多方面のテストが必要だったため、このMultiDexオプションをオンにする方法で進めることにしました。

**[StackOverflowの最後の回答を参照](https://stackoverflow.com/questions/31141210/how-to-enable-multi-dex-option-for-android-in-unity3d/55960144#55960144)**

**[1. Unityフォーラム MultiDex](https://forum.unity.com/threads/multidex-support-on-android.325429/)**

**[2. Unityディスカッション MultiDex](https://discussions.unity.com/t/too-many-method-references-when-i-export-android-build/120436/1)**

- 上記のフォーラムとディスカッションの投稿を見ると、`DexArchiveMergerException` エラーを解決するには `multiDexEnabled true` で有効にする必要があるとのことです。
- 調べた結果、Plugin - Android フォルダ内部に `mainTemplate.gradle` というファイルが存在します。このファイルに次のようなコードを追加すれば良いです。

```gradle
android {
    ...

    defaultConfig {
        ...
        multiDexEnabled true
    }

    ...
}
```

![Desktop View](/assets/img/post/unity/unityaosbuilderror_01.png){: : width="500" .normal }

- ところで、下の写真を見るとファイル名の後ろに `DISABLED` が付いているので、ビルドに含まれないか無効化されたファイルに見えますが... なぜビルドに影響を与えるのかは疑問です...

![Desktop View](/assets/img/post/unity/unityaosbuilderror_02.png){: : width="200" .normal }

#### 最終結果：MultiDexを有効にすると該当エラーは解決しました。しかし、また別のエラーが発生してしまいました...

<br>
<br>

## 2番目の失敗原因と解決方法：Execution failed for task ':launcher:mergeDexRelease' および gradle build failed エラー発生

```
FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':launcher:mergeDexRelease'.
> A failure occurred while executing com.android.build.gradle.internal.tasks.DexMergingTaskDelegate
   > There was a failure while executing work items
      > A failure occurred while executing com.android.build.gradle.internal.tasks.DexMergingWorkAction
         > com.android.builder.dexing.DexArchiveMergerException: Error while merging dex archives: 
           Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: 
```

- 同様にJenkinsビルド中に上記のログが発生しました。おそらくMultiDexを有効にしたことで発生したエラーだと思われます。

**[app:mergeDexRelease エラー関連資料](https://github.com/facebook/react-native/issues/33670)**

**[Gradle Build Failed エラー対応ブログ](https://devparklibrary.tistory.com/20)**

- エラー対応ブログも古いバージョンのため、設定環境が大きく異なります。
- ~~ProjectSettings - Android - Publishing Settings - Minify - Release オプションにチェックボックスが存在します。該当チェックボックスを有効にすれば解決します。~~
- ただし注意点として、Strip Engine Code のように特定のバイナリファイルを除外してビルドする可能性があると警告してくれます... それがどんな問題を引き起こすかは誰にも分かりません...

- **2024.3.6 追記：Java Codeバイナリファイルを削除または含めないと書かれていますが、実際にそうでした... Adjustがビルドに含まれなかったため、該当オプションを再度無効にする必要があります。**

![Desktop View](/assets/img/post/unity/unityaosbuilderror_03.png){: : width="400" .normal }

- 警告文...

![Desktop View](/assets/img/post/unity/unityaosbuilderror_04.png){: : width="500" .normal }

#### 最終結果：プロジェクト設定の該当オプションを有効にすれば解決します！！しかし... また別のエラーが発生... ただし、この部分は会社プロジェクト内部コードの問題でした。

<br>
<br>

## 3番目の失敗原因と解決方法：Native Crash Reporting（この部分は会社プロジェクト内部コードの原因）

```
Filename: Assets/Editor/Build/ShaderCleanup.cs Line: 68


=================================================================
	Native Crash Reporting
=================================================================
Got a segv while executing native code. This usually indicates
a fatal error in the mono runtime or one of the native libraries 
used by your application.
=================================================================

=================================================================
	Native stacktrace:
=================================================================
```

- ビルド後処理で不要なシェーダーを削除する作業を行うコードなのですが... 以前は問題なかったのに今になって発生しました... `ImportAsset` この部分が問題だと推定されます。
- Native Crash なので詳細なエラーログは確認できませんでした... おそらく存在しないシェーダーを削除しようとしたと推定されます。

```csharp
public void OnPreprocessBuild(BuildReport report)
{
    // 使用しないシェーダーまたはアセットを識別して無効化するロジックを追加

    // 例：使用しないシェーダーをすべて見つけて無効化
    DeactivateUnusedShaders();
}

 private void DeactivateUnusedShaders()
{
  ...

     AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(shaderPath), ImportAssetOptions.ForceUpdate);

  ...
}
```

- コメントアウトしてビルドを進めて解決...
