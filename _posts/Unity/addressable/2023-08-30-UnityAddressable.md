---
title: Unity Addressable 빌드 에러 해결 - Animator 실행이 되지 않는 이슈
date: 2023-08-30 21:38:00 +/-TTTT
categories: [Unity, Addressable]
tags: [Unity, Addressable, Build, iOS, AOS]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

## 목차

- [1. 주요 현상 및 분석](#주요-현상-및-분석)
- [2. 해결 방법](#해결-방법)

---

## 유니티 iOS/AOS Addressable을 포함한 빌드 시 Animator가 실행이 되지 않는 이슈

<br>

## 주요 현상 및 분석

<figure class="thrid">
  <a href="link"><img src="/assets/img/post/unity/work.gif" width="140px"></a>
  <a href="link"><img src="/assets/img/post/unity/dummy.png" width="240px"></a>
  <a href="link"><img src="/assets/img/post/unity/notwork.gif" width="140px"></a>
  <figcaption>좌측 사진은 정상적으로 빌드가 이루어졌을 때, 우측 사진은 어드레서블 빌드가 정상적으로 이루어지지 않았을 때</figcaption>
</figure>

## 해결 방법