---
title: "Unity iOSビルドエラー解決 - Microphone Usage Description & BeeBuildPostprocessor"
date: 2024-03-06 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 自動化, iOS, BeeBuildPostProcessor, Microphone Usage Description]
lang: ja
difficulty: intermediate
toc: true
---

## エラー原因の把握

- **FFmpeg Unity Bind 2** というプラグインを追加しました。
- camera, microphone アクセスをしていなかったのですが、プラグインを入れた後からアクセスするようになったと推定されます。

<br>
<br>

## エラーログ

```
Microphone class is used but Microphone Usage Description is empty in Player Settings.

System.Exception: Microphone class is used but Microphone Usage Description is empty in Player Settings.

   at PlayerBuildProgramLibrary.FeatureExtractor.Run(CSharpActionContext ctx, Data data) in /Users/bokken/build/output/unity/unity/Editor/IncrementalBuildPipeline/PlayerBuildProgramLibrary/FeatureExtractor.cs:line 38

*** Tundra build failed (8.57 seconds), 3421 items updated, 3688 evaluated

ExitCode: 3 Duration: 8s596ms
```

<br>

```
BuildFailedException: Player build failed: 15 errors

  at UnityEditor.Modules.BeeBuildPostprocessor.PostProcess (UnityEditor.Modules.BuildPostProcessArgs args) [0x00213] in /Users/bokken/build/output/unity/unity/Editor/Mono/Modules/BeeBuildPostprocessor.cs:718

  at UnityEditor.iOS.iOSBuildPostprocessor.PostProcess (UnityEditor.Modules.BuildPostProcessArgs args) [0x002a2] in <cefdead0678a425ab2e0c2483a1910f2>:0

...

(Filename: /Users/bokken/build/output/unity/unity/Editor/Mono/Modules/BeeBuildPostprocessor.cs Line: 718)
```

- **[こちらのUnityバグディスカッション](https://forum.unity.com/threads/build-failing-with-command-failed-to-write-the-following-output-file.1238776/)** を見ると分かりますが、Unityプロジェクト内部ライブラリの "Library/Bee/artifacts/MacStandalonePlayerBuildProgram/Features/" サブフォルダに "FeatureCheckList.txt" というテキストファイルが存在し、Description を入れないとビルドができない問題だったようです。

<br>

## 解決方法

- **Player Settings - Other Settings** に入るか、検索バーで「description」を検索します。

- **Camera Usage Description**
- **Microphone Usage Description**

- この2箇所に空欄が存在する場合、適当な文言を入れて埋めればビルドが成功します... 本当に呆れるバグです。

![Desktop View](/assets/img/post/unity/iosbuild_002.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosbuild_001.png){: : width="400" .normal }
