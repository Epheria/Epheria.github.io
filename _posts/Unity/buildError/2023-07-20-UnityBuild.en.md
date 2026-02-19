---
title: Unity Build Issue Fix Collection - ID 238, Strip Engine Code, cs0246
date: 2023-07-20 15:15:00 +/-TTTT
categories: [Unity, Build Error]
tags: [unity, build, error id 238, stripenginecode, cs0246]
difficulty: intermediate
lang: en
toc: true
---

<br>
<br>

## 1. Error: Could not produce class with ID 238. This could be caused by a class being stripped from the build even though it is needed. Try disabling 'Strip Engine Code' in Player Settings.

<br>
<br>

## Main symptom
- After build, specific animations/prefabs disappear or runtime errors occur.

## Cause
- When using Addressables (Asset Bundles), this can happen if classes that must be included manually are not preserved.

## Solution
- `Strip Engine Code` is a feature for reducing build size.
* [Reference](https://takoyaking.hatenablog.com/entry/strip_engine_code_unity)

The easiest workaround is disabling `Strip Engine Code` as mentioned in the link above,

but that caused build-size issues in my case.

##### So the best fix is to add required classes to `link.xml` so they are preserved in the build.

<br>
 <span style="color:red">Important caution</span>

- Even if you write entries in `link.xml`, some types may still not be included in certain cases.
- Also, when using .NET runtime, a larger .NET class library API set is provided than legacy scripting runtime, which can increase code size.  
To mitigate that size increase, `Strip Engine Code` should be enabled. (Especially because it removes unused dummy code, so it is practically required.)
* [Reference](https://docs.unity3d.com/kr/current/Manual/dotnetProfileLimitations.html)

<br>

##### In my case, animation sync was broken, so I added `AnimatorController` and `Animator` components to `link.xml`.

<img src="/assets/img/post/unity/unitybuild01.png" width="1920px" height="1080px" title="256" alt="build1">

When a crash occurs, Unity also prints the related ID value (e.g., ID 238).  
This ID maps to class IDs defined in the YAML Class ID Reference.

So to match a reported error ID, refer to the link below:
* [Class ID Reference](https://docs.unity3d.com/Manual/ClassIDReference.html)

<br>
<br>

-------

## 2. cs0246: The type or namespace name could not be found (are you missing a using directive or an assembly reference?)

<br>

## Main symptom
1. Namespace issues when writing classes.
2. If `using UnityEditor` is used -> UnityEditor classes are not included in builds.
3. If `using xxxx` is written but never used.

-> Build error occurs and build is force-stopped.

## Cause
* Basically this error occurs when a class is not declared properly or not imported via `using`.

##### Build environment when it happened
- No typos in written code.
- Runs normally in the editor.
- No functional error during editor run.
- But build fails with this error.

## Solution
1. Wrap UnityEditor code with preprocessor directives.
2. Remove unused `using` namespaces.
