---
title: Unity AOS 빌드 에러 해결 - com.android.builder.dexing.DexArchiveMergerException Error while merging dex archives
date: 2024-02-26 12:59:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Jenkins, 자동화, Android, DexArchiveMergerException, multiDexEnabled, mergeDexRelease, gradle build failed , Minify]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 에러 원인 파악

- 기존의 유니티 버전인 2022.3.4f1 에서 2022.3.19f1 으로 업그레이드
- 빌드머신인 맥미니 MacOS Sonoma 14.3.1 로 업데이트 및 Xcode 15.2 업데이트
- Jenkins 로 원격빌드 도중 DEV Android 에서 원인을 알 수없는 에러가 발생했다.

<br>
<br>

## 첫 번째 실패 원인과 해결 방법 : multiDex 활성화하기

```
User
ERROR:/Users/coconevbusan/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/unityLibrary/build/.transforms/f5f2117adcaee1eb1097391e7bb3025e/transformed/classes/classes.dex: D8: Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: /Users/coconevbusan/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/unityLibrary/build/.transforms/f5f2117adcaee1eb1097391e7bb3025e/transformed/classes/classes.dex, /Users/coconevbusan/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/launcher/build/intermediates/external_libs_dex/release/mergeExtDexRelease/classes.dex
com.android.builder.dexing.DexArchiveMergerException: Error while merging dex archives: 
Type com.google.firebase.MessagingUnityPlayerActivity is defined multiple times: /Users/coconevbusan/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/unityLibrary/build/.transforms/f5f2117adcaee1eb1097391e7bb3025e/transformed/classes/classes.dex, /Users/coconevbusan/.jenkins/workspace/(DEV)android/Library/Bee/Android/Prj/IL2CPP/Gradle/laun
```

- com.google.firebase.MessagingUnityPlayerActivity 라는 중복된 클래스가 정의되어 발생한 원인이였던거같다. 특히 두 번 이상 정의된 클래스는 두 dex 아카이브에서 충돌을 일으킨다고 한다.
- 이를 해결하기 위해서는 multiDex 활성화가 필요했었다. 유니티 포럼 및 토론에서도 몇몇 문제가 발생했었다.
- 2014년 부터 시작해서 가장 최근 것은 2019년 이긴 하지만.. 이 빌드를 해결하기 위해선 무조건 썩은 동앗줄이라도 붙잡기 위한 다방면의 테스트가 필요했기 때문에 이 multiDex 옵션을 켜보는 방법으로 밀고 나가보기로 했다.

**[스택오버플로 마지막 답변 참조](https://stackoverflow.com/questions/31141210/how-to-enable-multi-dex-option-for-android-in-unity3d/55960144#55960144)**

**[1.유니티 포럼 multiDex](https://forum.unity.com/threads/multidex-support-on-android.325429/)**

**[2.유니티 토론 multiDex](https://discussions.unity.com/t/too-many-method-references-when-i-export-android-build/120436/1)**

- 위 포럼과 토론 게시물을 살펴보면 DexArchiveMergerException 에러를 해결하기 위해서는 multiDexEnabled true 로 활성화 시켜줘야 한다고 한다.
- 찾아본 결과 Plugin - Android 폴더 내부에 mainTemplate.gradle 이라는 파일이 존재한다. 이 파일에 다음과 같은 코드를 넣어주면 된다.

```
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

- 근데 아래 사진을 보면 DISABLED 가 뒤에 붙어있는거 보면 빌드에 포함이 안되거나 비활성화된 파일같아 보이는데.. 왜 빌드에 영향을 주는건지는 의문이다..

![Desktop View](/assets/img/post/unity/unityaosbuilderror_02.png){: : width="200" .normal }

#### 최종 결과 multiDex 를 활성화 하니 해당 에러는 해결되었다. 하지만 또 다른 에러가 발생해바렸다..

<br>
<br>

## 두 번째 실패 원인과 해결 방법 : Execution failed for task ':launcher:mergeDexRelease' 및 gradle build failed 에러 발생

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

- 마찬가지로 Jenkins 빌드 도중 위의 로그가 발생했음. 아마도 multiDex 를 활성화해서 발생한 에러라고 생각한다.

**[app:mergeDexRelease 에러 관련 자료](https://github.com/facebook/react-native/issues/33670)**

**[Gradle Build Fialed 오류 대응 블로그](https://devparklibrary.tistory.com/20)**

- 오류 대응 블로그 역시 옛날 버전이라 세팅 환경이 많이 다르다.
- ~~ProjectSettings - Android - Publishing Settings - Minify - Release 옵션에 체크박스가 존재한다. 해당 체크박스를 활성화 해주면 된다.~~
- 다만 주의할 점은 Strip Engine Code 와 같이 특정 바이너리 파일을 제외하고 빌드를 할 수있다고 경고를 해준다.. 그것이 어떤 문제를 야기할지 아무도 알 수 없는 노릇..

- **2024.3.6 추가 : Java Code 바이너리 파일을 삭제 or 불포함이라고 적혀있는데, 실제로 그랬다.. adjust 가 빌드에 포함이 되지 않아 해당 옵션을 다시 바활성화 해야한다.**

![Desktop View](/assets/img/post/unity/unityaosbuilderror_03.png){: : width="400" .normal }

- 경고 문구..

![Desktop View](/assets/img/post/unity/unityaosbuilderror_04.png){: : width="500" .normal }

#### 최종 결과 프로젝트 세팅의 해당 옵션을 활성화 해주면 해결이 된다!! 하지만.. 또 다른 에러가 발생.. 다만 이부분은 토이버스 프로젝트 내부 코드의 문제였음

<br>
<br>

## 세 번째 실패 원인과 해결 방법 : Native Crash Reporting (이 부분은 회사 프로젝트 내부 코드의 원인)

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

- 빌드 후처리로 필요없는 쉐이더를 빼주는 작업을 하는 코드인데.. 특이하게 이전엔 문제가 없다가 지금와서야 발생했다.. ImportAsset 이 부분이 문제인것으로 추정된다.
- Native Crash 라서 자세한 에러 로그는 확인할 수 없었다.. 아마도 존재하지 않는 쉐이더를 빼려고 시도한걸로 추정된다.

```csharp
    public void OnPreprocessBuild(BuildReport report)
    {
        // 사용하지 않는 쉐이더 또는 에셋을 식별하고 비활성화할 로직 추가

        // 예시: 사용하지 않는 쉐이더를 모두 찾아서 비활성화
        DeactivateUnusedShaders();
    }

     private void DeactivateUnusedShaders()
    {
      ...

         AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(shaderPath), ImportAssetOptions.ForceUpdate);

      ...
    }
```

- 주석처리를 하고 빌드를 진행하여 해결..
