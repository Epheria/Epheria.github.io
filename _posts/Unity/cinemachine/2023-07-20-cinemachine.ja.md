---
title: Unity Cinemachine Jittering イシュー
date: 2023-07-20 15:59:00 +/-TTTT
categories: [Unity, Cinemachine]
tags: [unity, cinemachine, jittering, damping algorithm, ccd]
difficulty: intermediate
lang: ja
toc: true
---

<br>
<br>

## 1. Cinemachine Method Update について
<br>
<br>

## 主な現象
- Cinemachine カメラの Damping アルゴリズムにより、キャラクターや飛行船が高速移動すると Jittering が発生する。

## キャラクターの Rigidbody 設定
<img src="/assets/img/post/unity/cine01.png" width="512px" height="512px" title="256" alt="cine1">
<img src="/assets/img/post/unity/cine02.png" width="512px" height="512px" title="256" alt="cine2">

## Cinemachine Brain (Main Camera)
<img src="/assets/img/post/unity/cine03.png" width="512px" height="512px" title="256" alt="cine3">

## 原因分析
- `Rigidbody.Interpolate` は物理ベース移動キャラクターの CCD 補間に関係する。  
Cinemachine Camera の Follow / LookAt がそのプレイヤーを追うと、Update Method で更新される Transform 値と、  
Damping 補間後の Transform 値に差が生じてズレが発生する。

## 解決方法
1. 物理ベース移動プレイヤーの `Rigidbody -> Interpolate` をオフにする。
2. プレイヤー移動コード (`rigidbody.velocity`, `rigidbody.AddForce()` など) を `FixedUpdate` で処理する。
3. Cinemachine Camera の `Update Method` と `Blend Update Method` を `Fixed Update` に設定する。
4. `Virtual Camera -> Inherit Position` をオフにする。
