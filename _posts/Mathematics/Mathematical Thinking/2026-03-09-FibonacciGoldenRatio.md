---
title: "피보나치 수열과 황금비 — 자연, 음악, 그리고 게임 사운드트랙의 숨겨진 수학"
date: 2026-03-09 10:00:00 +0900
categories: [Mathematics, Mathematical Thinking]
tags: [Fibonacci, Golden Ratio, Music, HoYoverse, Genshin Impact, HOYO-MiX, Game Music, Mathematics]
difficulty: beginner
math: true
toc: true
toc_sticky: true
tldr:
  - "피보나치 수열의 연속된 두 항의 비는 황금비(φ ≈ 1.618)에 수렴하며, 이 비율은 자연계 전반에 존재한다"
  - "피아노 건반의 구조(13음, 8백건, 5흑건, 3-2 그룹)는 그 자체로 피보나치 수열이다"
  - "원신의 Yu-Peng Chen은 수메르 전투 음악 'Gilded Runner'에 피보나치 수열을 적용해 변화무쌍한 리듬을 만들었다"
---

[![Hits](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio.svg?view=today-total&label=visitors&color=11b48a)](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio/)

## 서론 — 게임 음악에서 소름 돋는 순간의 비밀

원신(Genshin Impact)에서 아즈다하(Azhdaha) 보스전에 돌입하는 순간, 초사(楚辭)를 읊는 듯한 중국어 보컬이 오케스트라와 일렉트릭 기타 위에 올려지며 등골이 서늘해지는 클라이맥스가 찾아온다. 수메르(Sumeru)의 열대우림을 달릴 때 들리는 전투 음악은, 들을 때마다 미묘하게 다른 리듬이 펼쳐지며 "왜 이 곡은 질리지 않을까?"라는 의문을 남긴다.

그 비밀은 **피보나치 수열(Fibonacci Sequence)**에 있다.

원신의 작곡가 **Yu-Peng Chen(陈致逸)**은 수메르 전투 음악에 피보나치 수열을 실제로 사용했다고 공식 비하인드 영상에서 밝혔다. 800년 전 이탈리아 수학자가 토끼의 번식 패턴에서 발견한 수열이, 21세기 게임 사운드트랙에 "들을수록 빠져드는" 리듬을 만들어내고 있는 것이다.

이 글에서는 **원신 OST를 중심으로** 피보나치 수열과 황금비가 음악에 어떻게 작용하는지 탐구한다. 클래식 음악에서 현대 록까지 — 수학이 만드는 아름다움을 추적해본다.

---

## Part 1: 피보나치 수열과 황금비 — 빠르게 알아보기

### 1.1 피보나치 수열이란?

1202년, 이탈리아의 수학자 **레오나르도 피보나치(Leonardo Fibonacci)**는 저서 *Liber Abaci(산반서)*에서 재미있는 문제를 냈다:

> "한 쌍의 토끼가 매달 한 쌍의 새끼를 낳고, 새끼는 태어난 지 한 달 뒤부터 번식한다면, 1년 후에 토끼는 몇 쌍이 될까?"

이 문제의 답이 바로 피보나치 수열이다:

$$1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, ...$$

**규칙은 단순하다**: 앞의 두 수를 더하면 다음 수가 된다.

$$F(n) = F(n-1) + F(n-2)$$

그런데 이 단순한 규칙이 만들어내는 패턴은 자연계 전체에 숨어있다.

### 1.2 자연 속의 피보나치

| 자연 현상 | 피보나치 수 |
|----------|-----------|
| 해바라기 씨앗의 나선 수 | 34개, 55개 |
| 솔방울 나선 | 8개, 13개 |
| 꽃잎 수 (백합 3장, 채송화 5장, 코스모스 8장) | 3, 5, 8, 13 |
| 태풍과 은하의 나선 구조 | 황금 나선 |

자연은 왜 피보나치 수열을 "선택"할까? 이유는 **공간 최적화**다. 해바라기가 씨앗을 가장 빽빽하게 채우려면, 황금각(약 137.5°)으로 배열해야 하며, 이 각도는 황금비에서 나온다. 진화는 수학을 모르지만, 수억 년의 자연선택이 가장 효율적인 답을 찾아낸 것이다.

> **참고**: IAAC(Institute for Advanced Architecture of Catalonia)의 [해바라기 황금비 분석 연구](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/)에서 시각적 분석 자료를 확인할 수 있다. 한편, 앵무조개(Nautilus) 껍데기는 흔히 황금 나선의 대표 사례로 소개되지만, 실제로는 정확한 황금 나선이 아니라 **대수 나선(logarithmic spiral)**의 일종이다 ([참고](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)).

### 1.3 황금비 — φ = 1.618...

피보나치 수열에서 연속된 두 항의 비를 구하면 흥미로운 일이 벌어진다:

| n | F(n) | F(n)/F(n-1) |
|---|------|-------------|
| 5 | 5 | 5/3 = **1.667** |
| 6 | 8 | 8/5 = **1.600** |
| 7 | 13 | 13/8 = **1.625** |
| 8 | 21 | 21/13 = **1.615** |
| 10 | 55 | 55/34 = **1.618** |

수열이 진행될수록 이 비율은 하나의 상수로 수렴한다:

$$\varphi = \frac{1 + \sqrt{5}}{2} \approx 1.6180339887...$$

이것이 바로 **황금비(Golden Ratio, φ)**다. 그리고 역수를 취하면 소수점 이하가 같다는 독특한 성질이 있다:

$$\frac{1}{\varphi} = \varphi - 1 \approx 0.6180339887...$$

이 **0.618**이 음악에서 핵심 역할을 한다. 곡의 **61.8% 지점**이 바로 황금분할점이며, 대부분의 명곡은 이 지점에 클라이맥스를 배치한다.

---

## Part 2: 음악의 뼈대 — 피보나치와 음계

### 2.1 피아노 건반의 비밀

피아노 건반을 한 옥타브만 자세히 들여다보면, 피보나치 수열이 그대로 드러난다:

```
┌──┬─┬──┬─┬──┬──┬─┬──┬─┬──┬─┬──┬──┐
│  │♯│  │♯│  │  │♯│  │♯│  │♯│  │  │
│  │ │  │ │  │  │ │  │ │  │ │  │  │
│ C│ │ D│ │ E│ F│ │ G│ │ A│ │ B│ C│
└──┴─┴──┴─┴──┴──┴─┴──┴─┴──┴─┴──┴──┘
```

| 구성 요소 | 개수 | 피보나치? |
|----------|------|----------|
| 한 옥타브의 총 반음 수 | **13**음 | ✅ F(7) |
| 흰 건반 | **8**개 | ✅ F(6) |
| 검은 건반 | **5**개 | ✅ F(5) |
| 검은 건반 그룹 | **3**개 + **2**개 | ✅ F(4) + F(3) |

> **참고 다이어그램**: Gür & Karabey의 논문 ["Use of Golden Section in Music"](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music)의 Figure 1에서 피보나치 매핑을 시각적으로 확인할 수 있다.

우연의 일치가 아니다. 서양 음악의 **온음계(diatonic scale)**는 옥타브를 가장 조화롭게 분할하는 방법을 찾다 보니 자연스럽게 피보나치 수에 수렴한 것이다.

### 2.2 화음과 주파수의 피보나치

가장 기본적인 화음인 **메이저 코드(Major Chord)**의 구성음은 1, 3, 5번째 음 — 모두 피보나치 수다. 그리고 이 세 음이 만드는 화음이 인간의 귀에 가장 안정적으로 들리는 **장3화음**이다.

음의 주파수 비율에서도 황금비가 나타난다:

| 음정 | 주파수 비 | φ와의 차이 |
|------|----------|-----------|
| 완전5도 | 3:2 = 1.500 | 0.118 |
| 장6도 | 5:3 ≈ 1.667 | 0.049 |
| **단6도** | **8:5 = 1.600** | **0.018** |

**단6도(8:5)**가 황금비에 가장 가깝다. 피보나치 수끼리의 비율(5:3, 8:5, 13:8...)이 만들어내는 음정이 인간의 귀에 가장 "아름답게" 느껴진다.

---

## Part 3: 원신(Genshin Impact) — 피보나치로 만든 전투 음악 🎮

이 글의 핵심 파트다. 원신의 작곡가 Yu-Peng Chen이 어떻게 피보나치 수열을 실제 게임 음악에 녹였는지 분석한다.

### 3.1 "Gilded Runner(流金疾驰)" — 피보나치 수열로 리듬을 쌓다

수메르(Sumeru) 지역의 전투 음악 **"Gilded Runner(流金疾驰)"**는 Yu-Peng Chen이 피보나치 수열을 실험적으로 적용한 곡이다. HOYO-MiX의 공식 비하인드 영상 ["Travelers' Reverie"](https://genshin.hoyoverse.com/en/news/detail/24845)에서 직접 밝혔다:

> *"In one of the pieces, I experimented with the Fibonacci sequence to create rich and varied rhythmic changes, which make it sound very modern."*
> — Yu-Peng Chen, Music Producer

지휘자이자 음악 프로듀서 **Robert Ziegler**는 이 곡(내부 코드명 **x063**)의 리듬에 대해 "12 12 123 12345 12" 같은 변화하는 패턴이 많다고 언급했다.

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/ps8oa3CRNfk"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲ "Travelers' Reverie" — 수메르 음악 제작 비하인드 (HOYO-MiX 공식)</p>

#### 곡 분해 분석

"Gilded Runner"는 약 4분 05초(245초)의 곡으로, **피보나치 수열 기반 리듬 시퀀싱**이 핵심이다. Bilibili의 [상세 분석 영상](https://www.bilibili.tv/video/4789442275312695)과 커뮤니티 분석을 종합하면:

**1) 피보나치 리듬 시퀀싱**

리듬 패턴의 반복 주기가 피보나치 수를 따른다:

```
기본 패턴:  1, 1, 2, 3, 5 박자 그룹
확장 패턴:  3, 5, 8, 13 마디 단위 반복 주기
```

예를 들어 타블라(Tabla) 리듬이 **3마디** 동안 제시 → **5마디** 동안 변주 → **8마디** 동안 오케스트라와 합류하는 식이다. 반복되면서도 예측 불가능한 리듬감이 생기는 이유가 여기에 있다.

**2) 시퀀싱(Sequencing) 기법 + 피보나치 간격**

Yu-Peng Chen은 **"시퀀싱"** — 멜로디의 음높이를 바꾸며 반복하는 작곡 기법 — 을 피보나치 간격으로 적용했다. 반복될수록 음높이가 피보나치 수만큼 상승하며, 점점 더 풍부하고 감정적인 전개가 이루어진다.

```
1번째 반복: 기본 멜로디 (C)
2번째 반복: +1 반음 (C#)      ← F(1)
3번째 반복: +2 반음 (D)       ← F(3)
4번째 반복: +3 반음 (D#)      ← F(4)
5번째 반복: +5 반음 (F)       ← F(5)
```

이 기법은 인도의 전통 성악 타악 기법인 **콘나콜(Konnakol)**과 깊은 연관이 있다. 콘나콜은 남인도 카르나틱 음악의 리듬 발성 기법으로, "수학적 언어"라고 불릴 만큼 리듬과 수학적 원리(소수, 피보나치 수열, 기하학적 패턴) 사이에 밀접한 관계가 있다. 타악기 연주자 B.C. Manjunath는 콘나콜에 피보나치 수열을 직접 적용한 것으로 유명하다.

**3) 악기 블렌딩**

같은 전투 음악이라도 지역에 따라 다른 악기로 연주된다:

| 지역 | 악기 | 톤 |
|------|------|-----|
| 열대우림 | 반수리(Bansuri, 인도 플루트), 시타르, 타블라 | 부드럽고 섬세한 |
| 사막 | 네이(Ney), 두둑(Duduk, 중동 목관) | 거칠고 야생적인 |
| 공통 | 런던 심포니 오케스트라 | 웅장한 |

이 조합이 수메르 전투 음악의 "들을 때마다 다르게 느껴지는" 독특한 매력을 만들어낸다.

> 📄 *[Forest of Jnana and Vidya/Background](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Genshin Impact Wiki. Yu-Peng Chen의 피보나치 작곡 언급 원문 확인.*
>
> 📄 *[Bilibili — 수메르 리듬 피보나치 분석 영상](https://www.bilibili.tv/video/4789442275312695) — "Gilded Runner"의 리듬 구조를 시각적으로 분해한 영상.*

### 3.2 "Rage Beneath the Mountains" — 클라이맥스 배치의 황금비

원신 최초의 **중국어 가사가 포함된 사운드트랙**인 "Rage Beneath the Mountains(磅礴之下的怒号)"는 아즈다하(Azhdaha) 보스전 Phase 2 테마다. Yu-Peng Chen 작곡, B♭단조, 136 BPM.

이 곡에서 피보나치 수열을 의도적으로 사용했다는 공식 언급은 없다. 그러나 곡의 구조를 분석하면 흥미로운 패턴이 드러난다.

#### 곡 구조 분석 (약 3분 30초 = 210초)

| 구간 | 시작점 | 비율 |
|------|--------|------|
| 인트로 — 얼후(二胡) + 현악 | 0:00 | 0% |
| 보컬 진입 — 초사 가사 시작 | 약 0:28 | 13.3% |
| 오케스트라 풀 파워 | 약 1:05 | 31.0% |
| **클라이맥스 — 일렉 기타 + 보컬 최고조** | **약 2:10** | **62.4%** |
| 코다 — 여운 | 약 3:00 | 85.7% |

클라이맥스가 **전체의 약 62%** 지점에 위치한다. 이것은 황금분할점(61.8%)에 매우 가깝다. 의도적이든 직관적이든, Yu-Peng Chen의 음악적 감각이 황금비를 따라가고 있는 셈이다.

이 곡은 초사(楚辭)의 문체를 빌려온 가사, 얼후의 처연한 선율, 일렉트릭 기타의 격렬함, 그리고 오케스트라의 웅장함이 하나로 수렴하는 곡이다. 상하이 심포니 오케스트라가 GENSHIN CONCERT Special Edition에서 라이브 연주하기도 했다.

> 📄 *[Genshin Impact Wiki — Rage Beneath the Mountains](https://genshin-impact.fandom.com/wiki/Rage_Beneath_the_Mountains) — 트랙 상세 정보 및 가사.*
>
> 📄 *[Di Zeng Piano — Ludomusicology in Genshin Impact](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media) — 수메르 음악의 이중 화성 스케일 분석.*

### 3.3 수메르 음악의 제작 과정 — 3년의 여정

HOYO-MiX 팀은 수메르 음악을 **3년에 걸쳐** 완성했다. 음악 프로듀서 Di-Meng Yuan은 이렇게 말했다:

> *"Sumeru continues to be influenced by the legacy of ancient civilizations, but the prelude to new wisdom is also being composed."*

제작 핵심 사실:

- **녹음**: London Symphony Orchestra + 게스트 민속 음악가, Abbey Road Studios / Redfort Studio / Air-Edel Recording Studios
- **지역별 차별화**: 낮/밤/해질녘/새벽 4가지 별도 작곡, 전투 전환 시 같은 멜로디 구조를 유지하면서 오케스트레이션과 강도 변환
- **앨범**: "Forest of Jnana and Vidya" — Disc 4 "Battles of Sumeru"에 전투 음악 수록. 총 100트랙, 2022년 10월 20일 발매

---

## Part 4: 다른 게임과 대중음악의 황금비 🎵

### 4.1 Tool — "Lateralus" (2001): 곡 자체가 피보나치 수열

록 밴드 **Tool**은 피보나치 수열을 가장 노골적으로 음악에 녹인 현대 아티스트다. 앨범 *Lateralus*의 타이틀곡은 수열 자체가 곡이다.

**가사의 음절 수가 피보나치 수열을 따른다:**

```
Black                               → 1 음절
Then                                → 1 음절
White are                           → 2 음절
All I see                           → 3 음절
In my infancy                       → 5 음절
Red and yellow then came to be      → 8 음절
Reaching out to me                  → 5 음절 (하강)
Lets me see                         → 3 음절 (하강)
```

패턴: **1-1-2-3-5-8-5-3-2-1-1-2-3-5-8-13-8-5-3**

수열이 상승했다가 하강하고, 다시 더 높이 상승하는 구조다. 마치 나선이 점점 커지듯.

**박자까지 피보나치:**

코러스의 박자가 **9/8 → 8/8 → 7/8**로 변화한다. 드러머 대니 캐리(Danny Carey)에 따르면, 원래 곡 제목이 "9-8-7"이었는데 987이 피보나치 수열의 **16번째 항**이라는 사실을 발견하고 "Lateralus"로 바꿨다고 한다.

### 4.2 슈퍼 마리오 갤럭시 — 의도하지 않은 황금비

닌텐도의 전설적 작곡가 **콘도 코지(Koji Kondo)**와 **요코타 마히토(Mahito Yokota)**는 피보나치 수열을 의식적으로 사용하지 않는다고 밝혔다. 그럼에도 [Kotaku의 분석](https://kotaku.com/mario-music-of-golden-proportions-5541606)에 따르면:

**Gusty Garden Galaxy 테마 (64마디):**

- 황금분할점: 마디 39.552 (64 × 0.618)
- **실제**: 마디 39~40에서 코넷과 오보에가 등장하며 텍스처 전환

**Good Egg Galaxy 테마 (52마디):**

- 황금분할점: 마디 32.14 (52 × 0.618)
- **실제**: 마디 32에서 팀파니 진입 + 현악 크레셴도

의식하지 않았는데도 황금분할점 근처에 전환이 오는 현상에 대해, **인간의 미적 감각이 황금비에 자연스럽게 반응한다**는 가설이 있다. 다만 이는 하나의 해석이며, 확증편향(원하는 패턴만 골라 보는 경향)의 가능성도 고려해야 한다.

### 4.3 Genesis — "Firth of Fifth"

프로그레시브 록 밴드 **Genesis**의 "Firth of Fifth"에서는 솔로 구간이 **55, 34, 13마디**로 구성되어 있다는 분석이 있다 — 모두 피보나치 수다. 다만 이는 밴드가 공식적으로 밝힌 것이 아니라, 팬과 분석가들의 해석이다. 바르톡의 3악장 실로폰 솔로(Part 5 참조)처럼 의도적 사용이 확인된 사례와는 구별할 필요가 있다.

---

## Part 5: 클래식 거장들의 황금비 🎻

게임 음악의 뿌리는 클래식에 있다. 원신의 Yu-Peng Chen도 런던 심포니 오케스트라와 작업하는 클래식 기반 작곡가다. 클래식 거장들이 어떻게 황금비를 사용했는지 간략히 살펴보자.

### 5.1 바르톡 — 수학을 악보에 새긴 작곡가

**벨라 바르톡(Béla Bartók, 1881-1945)**은 피보나치 수열을 가장 의식적으로 음악에 적용한 작곡가다.

**≪현악기, 타악기, 첼레스타를 위한 음악≫ (1936) 1악장:**

| 구간 | 마디 번호 | 피보나치 수 |
|------|----------|-----------|
| 제시부 길이 | 21마디 | ✅ F(8) |
| 현악 뮤트 해제 | 34마디 | ✅ F(9) |
| **클라이맥스 (fff)** | **55마디** | ✅ **F(10)** |
| 전체 길이 | 89마디 | ✅ F(11) |

클라이맥스의 위치: $\frac{55}{89} \approx 0.618 = \frac{1}{\varphi}$

3악장에서는 실로폰이 연주하는 **리듬 패턴 자체**가 피보나치 수열이다:

> **1, 1, 2, 3, 5, 8, 5, 3, 2, 1, 1**

음가가 피보나치 수열을 따라 확장되었다가 거울처럼 수축하는 구조다. 이것은 학자들 사이에서도 가장 논쟁이 적은, 피보나치의 명백한 사례로 인정받고 있다.

> **학술적 논쟁**: 수학자 가레스 로버츠(Gareth E. Roberts)는 1악장 분석에 체리피킹과 확증편향이 있다고 지적했다. 실제 악보가 88마디일 수 있고, 조성적 클라이맥스는 44마디(피보나치 수 아님)에 위치한다는 것이다. 3악장의 리듬 패턴만이 확실한 사례라는 주장.
>
> 📄 *[Roberts, G.E. "Béla Bartók and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.*
>
> 📄 *[AMS Blog (2021). "Did Bartók use Fibonacci numbers?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)*

### 5.2 드뷔시, 쇼팽, 모차르트

**드뷔시 ≪수면의 반영≫**: 조성 변화가 피보나치 간격(**34, 21, 13, 8**마디)으로 배치. 포르티시모 클라이맥스가 황금분할점에 위치. 물에 비친 상이 실물보다 짧아 보이는 **굴절 효과**를 수학적으로 모방한 것이라는 분석이 있다.

> 📄 *Howat, Roy. [Debussy in Proportion.](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis) Cambridge UP, 1983.*

**쇼팽 전주곡 Op.28 No.1**: 전체 34마디 중 핵심 이벤트가 8, 13, 21마디에 위치 — 연속 피보나치 수 4개.

**모차르트 피아노 소나타 1번 1악장**: 제시부 38마디 + 전개부+재현부 62마디 = 100마디. B ÷ A = 62 ÷ 38 ≈ **1.63** — 황금비에 매우 가깝다.

---

## Part 6: 악기 설계의 황금비 — 스트라디바리우스의 비밀

**안토니오 스트라디바리(Antonio Stradivari, 1644-1737)**가 제작한 바이올린은 수백 년이 지난 지금도 세계 최고의 음색을 자랑한다. 일부 연구자들은 그 비밀 중 하나로 **황금비**를 지목한다.

| 부위 | 비율 관계 |
|------|----------|
| 넥+페그박스+스크롤 : 몸통 | ≈ 1 : 1.618 |
| 허리 ~ 상부 : 허리+상부 ~ 전체 | ≈ 1 : 1.618 |
| F-홀 간격 | 피보나치 수 기반 배치 |

이 비율이 **음향 공명**에 최적화된 구조를 만든다는 주장이 있으나, 스트라디바리우스의 음색이 단순히 비율만으로 설명되지는 않는다. 나무의 밀도, 바니시 성분, 숙성 상태 등 복합적 요소가 작용하며, 황금비는 그중 하나의 해석이다.

> **참고**: [Benning Violins의 분석 자료](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html)에서 스트라디바리우스의 실제 치수와 피보나치 수열의 관계를 사진과 함께 볼 수 있다.

---

## Part 7: 실전 — 게임 개발자를 위한 활용법

### 7.1 클라이맥스 배치 공식

곡의 가장 강렬한 순간을 어디에 놓아야 할까?

$$\text{클라이맥스 위치} = \text{전체 마디 수} \times 0.618$$

| 전체 길이 | 클라이맥스 위치 | 가장 가까운 피보나치 |
|----------|--------------|-------------------|
| 32마디 | 20마디째 | 21 (F₈) |
| 64마디 | 40마디째 | 34 (F₉) |
| 128마디 | 79마디째 | 89 (F₁₁) |

팝 음악에서도 "곡의 61.8% 지점"에 브릿지나 마지막 코러스가 오는 경우가 많다. 50%도, 100%도 아닌 **62% 근처**가 가장 감정적 임팩트가 크다.

### 7.2 구조 설계

피보나치 수로 섹션 길이를 정하면 자연스러운 흐름이 생긴다:

```
인트로 (8마디) → 벌스 1 (13마디) → 코러스 (8마디)
→ 벌스 2 (13마디) → 코러스 (8마디)
→ 브릿지 (5마디) → 최종 코러스 (13마디)
→ 아웃트로 (3마디)
```

총 71마디. 브릿지(5마디)가 시작되는 55마디 지점이 황금분할점 근처다.

### 7.3 게임 개발자를 위한 아이디어

- **레벨 디자인**: 긴장과 이완의 주기를 피보나치 간격으로 배치
- **UI 레이아웃**: 황금 나선을 기반으로 시선 유도
- **난이도 곡선**: 피보나치 급수로 점진적 상승 → 자연스러운 체감 난이도
- **사운드 디자인**: BGM 전환점을 황금분할에 맞춰 배치
- **절차적 생성**: 피보나치 나선으로 맵/던전 구조 생성
- **전자음악 사운드 디자인**: 딜레이 타임을 피보나치 수(3, 5, 8, 13ms)로 설정하면 자연스러운 에코 생성 (DAW 실전 기법)

---

## 마무리 — 수학은 아름다움의 언어다

피보나치 수열과 황금비가 음악, 자연, 예술에서 반복적으로 나타나는 이유에 대해 다양한 해석이 있다:

1. **진화론적 해석**: 자연에서 효율적인 구조가 황금비를 따르므로, 이를 "아름답다"고 느끼도록 진화
2. **수학적 해석**: 무리수 중 가장 "무리스러운" 수(유리수로 근사하기 가장 어려운 수)이므로, 가장 균일한 분할을 만듬
3. **인지과학적 해석**: 뇌의 패턴 인식 시스템이 "예측 가능하면서도 살짝 벗어나는" 비율을 선호

어떤 해석이든, 한 가지는 확실하다: **수학과 예술은 대립하는 것이 아니라, 같은 아름다움의 서로 다른 표현**이라는 것.

Yu-Peng Chen이 피보나치 수열로 수메르의 전투 음악을 만들었을 때, 그는 800년 전 피보나치가 관찰한 토끼의 번식 패턴과, 100년 전 바르톡이 악보에 새긴 수열과, 수억 년 전 해바라기가 씨앗을 배열한 그 같은 수학적 원리를 사용한 것이다.

다음에 원신에서 수메르 전투 음악이 들릴 때, 혹은 아즈다하 보스전의 소름 돋는 클라이맥스를 만날 때 — 그 뒤에 피보나치의 토끼들이 뛰어다니고 있다는 걸 떠올려보자.

---

## References

### 단행본 / Books

- Lendvai, Ernő. *Béla Bartók: An Analysis of His Music*. Kahn & Averill, 1971.
- Howat, Roy. [*Debussy in Proportion: A Musical Analysis*](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis). Cambridge University Press, 1983.

### 논문 / Academic Papers

- van Gend, Robert. ["The Fibonacci Sequence and the Golden Ratio in Music."](https://nntdm.net/papers/nntdm-20/NNTDM-20-1-72-77.pdf) *Notes on Number Theory and Discrete Mathematics*, 20(1), 72-77, 2014.
- Gür, Ç. & Karabey, B. ["Use of Golden Section in Music."](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music) — 피아노 건반 피보나치 다이어그램, 바이올린 황금비 도해 수록.
- Bora, U. & Kaya, D. ["Investigation of Applications of Fibonacci Sequence and Golden Ratio in Music."](https://www.researchgate.net/publication/343021080_INVESTIGATION_OF_APPLICATIONS_OF_FIBONACCI_SEQUENCE_AND_GOLDEN_RATIO_IN_MUSIC) *Ç.Ü. Sosyal Bilimler Enstitüsü Dergisi*, 29(3), 2020.
- Budiawan, Hery et al. ["Fibonacci Sequence and Anagram Timbre."](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5820722) *SSRN*, 2025.
- Roberts, Gareth E. ["Béla Bartók and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.
- Howat, Roy. ["Debussy, Ravel and Bartók: Towards Some New Concepts of Form."](http://symmetry-us.com/Journals/5-3/howat.pdf) *Symmetry*, 5(3).
- [Ohio University Honors Thesis — "The Golden Ratio and Fibonacci Sequence in Music."](https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=oduhonors1620086748612102&disposition=inline) 2021.

### 게임 음악 / Game Music Sources

- [Forest of Jnana and Vidya/Background — Genshin Impact Wiki.](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Yu-Peng Chen 피보나치 작곡 공식 인용.
- ["Travelers' Reverie" — Behind the Scenes of the Music of Sumeru.](https://genshin.hoyoverse.com/en/news/detail/24845) HoYoverse Official.
- [Bilibili — 수메르 리듬 피보나치 분석 영상.](https://www.bilibili.tv/video/4789442275312695) 2023.
- [Charles Cornell Studios — Genshin Impact Fibonacci Post.](https://www.facebook.com/charlescornellstudios/posts/this-track-from-genshin-impact-is-literally-composed-using-the-fibonacci-sequenc/1123755772451565/) Facebook, 2022.
- [VGMO — Yu-Peng Chen Interview.](http://www.vgmonline.net/yu-pengchen/)
- [Di Zeng Piano — Ludomusicology in Genshin Impact.](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media)
- [Kotaku — Mario Music of Golden Proportions (2010).](https://kotaku.com/mario-music-of-golden-proportions-5541606)
- [HOYO-MiX — Wikipedia.](https://en.wikipedia.org/wiki/HOYO-MiX)

### 블로그 / 분석 자료

- AMS Blog (2021). ["Did Bartók use Fibonacci numbers in his music?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)
- Pinkney, Carla J. ["Great Music and the Fibonacci Sequence."](https://www.lancaster.ac.uk/stor-i-student-sites/carla-pinkney/2022/02/14/great-music-and-the-fibonacci-sequence/) Lancaster University STOR-i, 2022.
- [Music and the Fibonacci Sequence and Phi — The Golden Number.](https://www.goldennumber.net/music/)
- [AudioServices Studio — Golden Ratio in Music.](https://audioservices.studio/blog/golden-ratio-in-music-and-other-maths) — DAW 실전 기법 포함.
- [Fibonacci in Music: Tool's Lateralus — Fibonicci.com.](https://www.fibonicci.com/fibonacci/tool-lateralus/)
- [Fibonacci Series and Stradivarius Instruments — Benning Violins.](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html)
- [The Nautilus Shell Spiral as a Golden Spiral — The Golden Number.](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)
- [Exploring the Golden Ratio in Sunflower Seed Distribution — IAAC.](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/)
- [Auralcrave — The Golden Ratio in Music.](https://auralcrave.com/en/2020/06/28/the-golden-ratio-in-music-the-songs-of-fibonacci-sequence/) — Genesis, Dream Theater 사례 포함.
- [NPR — Fibonacci Percussionist (Konnakol).](https://www.npr.org/2018/08/10/637470699/let-this-percussionist-blow-your-mind-with-the-fibonacci-sequence)
