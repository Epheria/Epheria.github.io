---
title: "Unity iOS Build Error - Microphone Usage Description & BeeBuildPostprocessor"
date: 2024-03-06 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Automation, iOS, BeeBuildPostProcessor, Microphone Usage Description]
lang: en
difficulty: intermediate
toc: true
---

## Identifying the Cause

- Added a plugin called **FFmpeg Unity Bind 2**.
- The project did not access the camera or microphone before, but it seems to access them after adding the plugin.

<br>
<br>

## Error Log

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

- As seen in **[this Unity Bug Discussion](https://forum.unity.com/threads/build-failing-with-command-failed-to-write-the-following-output-file.1238776/)**, there is a text file named "FeatureCheckList.txt" in the "Library/Bee/artifacts/MacStandalonePlayerBuildProgram/Features/" subfolder of the Unity project internal library. It seems the build fails if the Description is not provided.

<br>

## Solution

- Go to **Player Settings - Other Settings** or search for "description" in the search bar.

- **Camera Usage Description**
- **Microphone Usage Description**

- If either of these fields is empty, fill them with any text, and the build will succeed... It's truly an absurd bug.

![Desktop View](/assets/img/post/unity/iosbuild_002.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/iosbuild_001.png){: : width="400" .normal }
