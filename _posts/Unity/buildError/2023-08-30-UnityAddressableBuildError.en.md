---
title: Unity Addressable Build Error Fix - Animator Not Running
date: 2023-08-30 21:38:00 +/-TTTT
categories: [Unity, Build]
tags: [unity, addressable, build, ios, aos]
difficulty: intermediate
lang: en
toc: true
math: true
mermaid: true
---

## Table of Contents

- [1. Main Symptoms and Analysis](#main-symptoms-and-analysis)
- [2. Solution](#solution)

---

## Issue: Animator not running in Unity iOS/AOS build including Addressables

<br>

## Main symptoms and analysis

- This issue occurred while developing the Toyverse project.
- Home Scene used Home Character prefab, World Scene used World Character prefab.
- Home Character animations played fine, but World Character animator/animation clips did not run.
- Addressable Groups profile was `Default`, and Play Mode Script was `Use Asset DataBase (fastest)`.
> In other words, addressable bundles were included in apk/ipa build, not pulled through patch delivery.
- Character movement used FSM states, driven by Animator Controller parameters and animation states.
> At first I thought it was an FSM logic bug. In Idle -> Jump transition, it seemed to ignore GroundChecker and stay in Jump.  
But debug logs showed no logic issue. After digging more, it looked like Animator Controller for World Character was missing from Addressable build.

![Desktop View](/assets/img/post/unity/notwork.gif){: .normal }
- The image above shows behavior when Addressable build is not configured correctly.
- I checked World Character Animator Controller and found Addressable was not checked. I enabled it and rebuilt, but still got T-pose.
- Then I suspected Avatar assigned to Animator might be missing. Checking model hierarchy revealed:
- Avatar under model was also not registered in Addressable Groups.

<br>

## Solution

1. Character prefab is correctly assigned to Addressable group.
![Desktop View](/assets/img/post/unity/addrbuild01.png){: .normal }

<br>

2. Check Animator component's Animator Controller and Avatar.

![Desktop View](/assets/img/post/unity/addrbuild02.png){: .normal }
![Desktop View](/assets/img/post/unity/addrbuild04.png){: .normal }

<br>
<br>

- Avatar under character model:
<br>

![Desktop View](/assets/img/post/unity/addrbuild03.png){: .normal }

<br>

3. Another overlooked part: in previous post about Strip Engine Code -> [link](https://epheria.github.io/posts/UnityBuild/)
- At that time, IL2CPP + Strip Engine Code were enabled in Unity build options, but `link.xml` did not preserve Animator-related classes.

- link.xml code

```
<type fullname="UnityEngine.AnimationClip" preserve="all" />
<type fullname="UnityEngine.Avatar" preserve="all" />
<type fullname="UnityEngine.AnimatorController" preserve="all" />
<type fullname="UnityEngine.RuntimeAnimatorController" preserve="all" />
<type fullname="UnityEngine.Animator" preserve="all" />
<type fullname="UnityEngine.AnimatorOverrideController" preserve="all" />
```

- With IL2CPP + Strip Engine Code enabled, Unity strips unused classes at build time. If these classes are stripped, animation can break, so preserve them in `link.xml`.

<br>

#### If logic looks correct but behavior is weird, suspect Addressables first.
> Honestly it's still odd that dependent assets were not automatically registered when character prefab itself was added to Addressables.

- Character Avatar and Animator Controller were in an art-managed folder, not under Downloadable Assets folder.
- So assets can still be added to Addressable Groups even if they are outside addressable storage folder.
- This can create duplication across assets/materials, so use Addressable Analyze to check duplicates/dependencies and optimize.

![Desktop View](/assets/img/post/unity/work.gif){: .normal }
#### Animator works correctly after the fix
