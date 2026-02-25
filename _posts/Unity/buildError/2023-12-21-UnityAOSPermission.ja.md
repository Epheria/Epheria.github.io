---
title: Unity Android Permission が削除されない問題の解決方法
date: 2023-12-21 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 自動化, Android Permission]
lang: ja
difficulty: intermediate
toc: true
---

- **Unity Android Permission が削除されない問題が発生しました。**
- **使用していない `READ_EXTERNAL_STORAGE` 外部ストレージ権限が、ビルドに含まれ続けていました。**

   ![Desktop View](/assets/img/post/unity/unityaosperm01.png){: : width="800" .normal }

<br>

## **原因分析**

- まず `AndroidManifest` ファイル内には該当権限を使用している場所はありませんでした。
- 全体検索で使用している場所を探してみましたが...

   ![Desktop View](/assets/img/post/unity/unityaosperm04.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/unityaosperm03.png){: : width="800" .normal }

- `Unity.Notifications.Tests` の internal class である `PostprocessorTests` というUnityパッケージキャッシュファイルが存在し、
- そこで該当権限を使用していました... さらに深く調べてみると、これが Mobile Notification パッケージ内に入っているクラスでした。

   ![Desktop View](/assets/img/post/unity/unityaosperm05.png){: : width="800" .normal }

<br>

## **解決方法**

1. `AndroidManifest` ファイルに削除したい権限があるか確認します。私の場合は `READ_EXTERNAL_STORAGE` でした。
2. コンパイラ（RiderまたはVisual Studio）の全体検索モードで削除したい権限を検索し、使用している場所があるか確認します。

- 権限の例
```xml
  <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
```

3. もし削除したい権限があれば、思い切って削除しましょう。
4. しかし、Unityパッケージやプラグインなどに含まれている場合があるため、確実に処理する必要があります。

- **`remove` を明示することで解決できました。**
```xml
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" tools:node="remove" />
```

- 結果
   ![Desktop View](/assets/img/post/unity/unityaosperm02.png){: : width="800" .normal }
