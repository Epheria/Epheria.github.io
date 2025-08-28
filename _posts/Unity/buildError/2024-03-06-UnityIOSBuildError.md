---
title: Unity iOS 빌드 에러 해결 - BeeBuildPostprocessor, Microphone Usage Description is empty, Build failing with "command failed to write the following output file"
date: 2024-03-06 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, 자동화, iOS, BeeBuildPostProcessor, Microphone Usage Description]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

## 에러 원인 파악

- FFmpeg Unity Bind 2 라는 플러그인을 추가
- camera, microphone 접근을 하지 않다가 플러그인을 넣은 뒤로 엑세스를 하는 것으로 추정

<br>
<br>

## 에러 로그

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

UnityEditor.BuildPipeline:BuildPlayerInternalNoCheck(String[], String, String, BuildTargetGroup, BuildTarget, Int32, BuildOptions, String[], Boolean)

UnityEditor.BuildPipeline:BuildPlayerInternal(String[], String, String, BuildTargetGroup, BuildTarget, Int32, BuildOptions, String[]) (at /Users/bokken/build/output/unity/unity/Editor/Mono/BuildPipeline.bindings.cs:507)

UnityEditor.BuildPipeline:BuildPlayer(String[], String, String, BuildTargetGroup, BuildTarget, Int32, BuildOptions, String[]) (at /Users/bokken/build/output/unity/unity/Editor/Mono/BuildPipeline.bindings.cs:372)

UnityEditor.BuildPipeline:BuildPlayer(BuildPlayerOptions) (at /Users/bokken/build/output/unity/unity/Editor/Mono/BuildPipeline.bindings.cs:336)

ProjectBuilder:BuildIos(Int32, String) (at Assets/Editor/Build/ProjectBuilder.cs:304)

ProjectBuilder:BuildIOS_Dev() (at Assets/Editor/Build/ProjectBuilder.cs:233)



(Filename: /Users/bokken/build/output/unity/unity/Editor/Mono/Modules/BeeBuildPostprocessor.cs Line: 718)
```

- **[이쪽 유니티 버그 디스커션](https://forum.unity.com/threads/build-failing-with-command-failed-to-write-the-following-output-file.1238776/)** 을 보면 알겠지만, 유니티 프로젝트 내부 라이브러리에 "Library/Bee/artifacts/MacStandalonePlayerBuildProgram/Features/" 하위 폴더에 "FeatureCheckList.txt"라는 tex 파일이 존재하는데 Description 을 넣지 않으면 빌드가 안되는 문제였던것같다.

<br>

## 해결 방법

- Player Settings - other settings 내부에 들어가거나 검색창에서 description 검색

- **Camera Usage Description**
- **Microphone Usage Description**

- 두 곳에 빈칸이 존재한다면, 아무말이나 채워넣으면 빌드가 성공한다.. 진짜 어이가 없는 버그이다.

![Desktop View](/assets/img/post/unity/iosbuild_002.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosbuild_001.png){: : width="400" .normal }
