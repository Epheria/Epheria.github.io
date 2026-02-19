---
title: Unity Cinemachine Jittering Issue
date: 2023-07-20 15:59:00 +/-TTTT
categories: [Unity, Cinemachine]
tags: [unity, cinemachine, jittering, damping algorithm, ccd]
difficulty: intermediate
lang: en
toc: true
---

<br>
<br>

## 1. About Cinemachine Method Update
<br>
<br>

## Main symptom
- Due to Cinemachine camera damping, jittering occurs when a character or airship moves quickly.

## Character Rigidbody settings
<img src="/assets/img/post/unity/cine01.png" width="512px" height="512px" title="256" alt="cine1">
<img src="/assets/img/post/unity/cine02.png" width="512px" height="512px" title="256" alt="cine2">

## Cinemachine Brain (Main Camera)
<img src="/assets/img/post/unity/cine03.png" width="512px" height="512px" title="256" alt="cine3">

## Cause analysis
- `Rigidbody.Interpolate` handles CCD-related interpolation for physics-based moving characters.  
When Cinemachine Camera follows/looks at that player, the Transform value updated through its Update Method  
and the Transform value processed by damping interpolation can diverge.

## Solution
1. Disable `Rigidbody -> Interpolate` for physics-based player movement.
2. Handle movement code (`rigidbody.velocity`, `rigidbody.AddForce()`, etc.) in `FixedUpdate`.
3. Set Cinemachine Camera `Update Method` and `Blend Update Method` to `Fixed Update`.
4. Disable `Virtual Camera -> Inherit Position`.
