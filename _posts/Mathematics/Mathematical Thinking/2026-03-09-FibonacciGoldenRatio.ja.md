---
title: "フィボナッチ数列と黄金比 — 自然、音楽、そしてゲームサウンドトラックに隠された数学"
lang: ja
date: 2026-03-09 10:00:00 +0900
categories: [Mathematics, Mathematical Thinking]
tags: [Fibonacci, Golden Ratio, Music, HoYoverse, Genshin Impact, HOYO-MiX, Game Music, Mathematics]
difficulty: beginner
math: true
toc: true
toc_sticky: true
tldr:
  - "フィボナッチ数列の連続する2項の比は黄金比（φ ≈ 1.618）に収束し、この比率は自然界全般に存在する"
  - "ピアノ鍵盤の構造（13音、白鍵8、黒鍵5、3-2グループ）はそれ自体がフィボナッチ数列である"
  - "原神のYu-Peng Chenはスメール戦闘曲「Gilded Runner」にフィボナッチ数列を適用し、変化に富んだリズムを生み出した"
---

[![Hits](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio.svg?view=today-total&label=visitors&color=11b48a)](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio/)

## はじめに — 自然の数学、音楽の数学

ヒマワリの種の螺旋、松ぼっくりの配列、銀河の渦巻き——自然界のあちこちに一つの数列が繰り返し現れる。**フィボナッチ数列（Fibonacci Sequence）**だ。そしてこの数列は、音楽にも深く浸透している。

原神（Genshin Impact）の作曲家**Yu-Peng Chen（陈致逸）**は、スメールの戦闘曲にフィボナッチ数列を実際に適用したと公式メイキング映像で明かした。バルトークはこの数列を楽譜に直接刻み込み、Toolは歌詞の音節数まで数列に合わせた。

本記事では、**原神OSTを中心に**フィボナッチ数列と黄金比が音楽にどのように作用するかを見ていく。クラシックから現代ロックまで、自然界の数学が音楽の中でどんな役割を果たしているかを追跡する。

---

## Part 1: フィボナッチ数列と黄金比 — クイックガイド

### 1.1 フィボナッチ数列とは？

1202年、イタリアの数学者**レオナルド・フィボナッチ（Leonardo Fibonacci）**は著書*Liber Abaci（算盤の書）*で興味深い問題を出した：

> 「一組のウサギが毎月一組の子を産み、子は生まれて1ヶ月後から繁殖するなら、1年後にウサギは何組になるか？」

この問題の答えがフィボナッチ数列である：

$$1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, ...$$

**ルールは単純だ**：前の2つの数を足すと次の数になる。

$$F(n) = F(n-1) + F(n-2)$$

しかし、この単純なルールが生み出すパターンは自然界全体に隠されている。

### 1.2 自然の中のフィボナッチ

| 自然現象 | フィボナッチ数 |
|---------|-------------|
| ヒマワリの種の螺旋数 | 34個、55個 |
| 松ぼっくりの螺旋 | 8個、13個 |
| 花弁の数（ユリ3枚、マツバボタン5枚、コスモス8枚） | 3, 5, 8, 13 |
| 台風と銀河の螺旋構造 | 黄金螺旋 |

自然はなぜフィボナッチ数列を「選択」するのか？理由は**空間最適化**だ。ヒマワリが種を最も密に詰めるには、黄金角（約137.5°）で配列する必要があり、この角度は黄金比から導かれる。進化は数学を知らないが、数億年の自然淘汰が最も効率的な答えを見つけたのだ。

> **参考**：IAAC（Institute for Advanced Architecture of Catalonia）の[ヒマワリ黄金比分析研究](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/)で視覚的な分析資料を確認できる。一方、オウムガイ（Nautilus）の殻は黄金螺旋の代表例としてよく紹介されるが、実際には正確な黄金螺旋ではなく**対数螺旋（logarithmic spiral）**の一種である（[参考](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)）。

### 1.3 黄金比 — φ = 1.618...

フィボナッチ数列の連続する2項の比を求めると興味深いことが起こる：

| n | F(n) | F(n)/F(n-1) |
|---|------|-------------|
| 5 | 5 | 5/3 = **1.667** |
| 6 | 8 | 8/5 = **1.600** |
| 7 | 13 | 13/8 = **1.625** |
| 8 | 21 | 21/13 = **1.615** |
| 10 | 55 | 55/34 = **1.618** |

数列が進むにつれ、この比率は一つの定数に収束する：

$$\varphi = \frac{1 + \sqrt{5}}{2} \approx 1.6180339887...$$

これが**黄金比（Golden Ratio, φ）**だ。そして逆数を取ると小数点以下が同じという独特な性質がある：

$$\frac{1}{\varphi} = \varphi - 1 \approx 0.6180339887...$$

この**0.618**が音楽で重要な役割を果たす。曲の**61.8%の地点**が黄金分割点であり、多くの名曲はこの地点にクライマックスを配置している。

---

## Part 2: 音楽の骨格 — フィボナッチと音階

### 2.1 ピアノ鍵盤の秘密

ピアノ鍵盤の1オクターブをよく見ると、フィボナッチ数列がそのまま現れる：

```
┌──┬─┬──┬─┬──┬──┬─┬──┬─┬──┬─┬──┬──┐
│  │♯│  │♯│  │  │♯│  │♯│  │♯│  │  │
│  │ │  │ │  │  │ │  │ │  │ │  │  │
│ C│ │ D│ │ E│ F│ │ G│ │ A│ │ B│ C│
└──┴─┴──┴─┴──┴──┴─┴──┴─┴──┴─┴──┴──┘
```

| 構成要素 | 数 | フィボナッチ？ |
|---------|-----|-------------|
| 1オクターブの総半音数 | **13**音 | ✅ F(7) |
| 白鍵 | **8**個 | ✅ F(6) |
| 黒鍵 | **5**個 | ✅ F(5) |
| 黒鍵グループ | **3**個 + **2**個 | ✅ F(4) + F(3) |

> **参考図**：Gür & Karabeyの論文["Use of Golden Section in Music"](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music)のFigure 1でフィボナッチマッピングを視覚的に確認できる。

偶然の一致ではない。西洋音楽の**全音階（diatonic scale）**は、オクターブを最も調和的に分割する方法を探す中で自然にフィボナッチ数に収束したのだ。

### 2.2 和音と周波数のフィボナッチ

最も基本的な和音である**メジャーコード（Major Chord）**の構成音は1、3、5番目の音——すべてフィボナッチ数だ。そしてこの3音が作る和音が、人間の耳に最も安定的に聞こえる**長三和音**である。

音の周波数比率にも黄金比が現れる：

| 音程 | 周波数比 | φとの差 |
|------|---------|--------|
| 完全5度 | 3:2 = 1.500 | 0.118 |
| 長6度 | 5:3 ≈ 1.667 | 0.049 |
| **短6度** | **8:5 = 1.600** | **0.018** |

**短6度（8:5）**が黄金比に最も近い。フィボナッチ数同士の比率（5:3, 8:5, 13:8...）が生み出す音程は、人間の耳に最も「美しく」感じられる。

---

## Part 3: 原神（Genshin Impact） — フィボナッチで作った戦闘曲 🎮

本記事の核心パートだ。原神の作曲家Yu-Peng Chenがどのようにフィボナッチ数列を実際のゲーム音楽に織り込んだかを分析する。

### 3.1 「Gilded Runner（流金疾驰）」 — フィボナッチ数列でリズムを積み上げる

<iframe width="560" height="315" src="https://www.youtube.com/embed/NkFQ3T7ZWAk" title="Genshin Impact - Gilded Runner" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

スメール（Sumeru）地域の戦闘曲**「Gilded Runner（流金疾驰）」**は、Yu-Peng Chenがフィボナッチ数列を実験的に適用した曲だ。HOYO-MiXの公式メイキング映像["Travelers' Reverie"](https://genshin.hoyoverse.com/en/news/detail/24845)で直接明かした：

> *"In one of the pieces, I experimented with the Fibonacci sequence to create rich and varied rhythmic changes, which make it sound very modern."*
> — Yu-Peng Chen, Music Producer

指揮者兼音楽プロデューサーの**Robert Ziegler**は、この曲（内部コードネーム**x063**）のリズムについて「12 12 123 12345 12」のような変化するパターンが多いと言及した。

#### 楽曲分解分析

「Gilded Runner」は約4分05秒（245秒）の曲で、**フィボナッチ数列ベースのリズムシーケンシング**が核心だ。[Bilibiliの詳細分析映像](https://www.bilibili.tv/video/4789442275312695)とコミュニティ分析を総合すると：

**1) フィボナッチ・リズム・シーケンシング**

リズムパターンの繰り返し周期がフィボナッチ数に従う：

```
基本パターン：  1, 1, 2, 3, 5 拍子グループ
拡張パターン：  3, 5, 8, 13 小節単位の繰り返し周期
```

例えばタブラ（Tabla）のリズムが**3小節**で提示 → **5小節**で変奏 → **8小節**でオーケストラと合流する形だ。繰り返しながらも予測不可能なリズム感が生まれる理由がここにある。

**2) シーケンシング技法 + フィボナッチ間隔**

Yu-Peng Chenは**「シーケンシング」**——メロディの音高を変えながら繰り返す作曲技法——をフィボナッチ間隔で適用した。繰り返すたびに音高がフィボナッチ数分だけ上昇し、より豊かで感情的な展開が生まれる。

```
1回目: 基本メロディ (C)
2回目: +1 半音 (C#)      ← F(1)
3回目: +2 半音 (D)       ← F(3)
4回目: +3 半音 (D#)      ← F(4)
5回目: +5 半音 (F)       ← F(5)
```

この技法はインドの伝統的な声楽打楽器技法**コンナコル（Konnakol）**と深い関連がある。コンナコルは南インド・カルナーティック音楽のリズム発声技法で、「数学的言語」と呼ばれるほどリズムと数学的原理（素数、フィボナッチ数列、幾何学的パターン）の間に密接な関係がある。パーカッショニストのB.C. Manjunathはコンナコルにフィボナッチ数列を直接適用したことで有名だ。

**3) 楽器ブレンディング**

同じ戦闘曲でも地域によって異なる楽器で演奏される：

| 地域 | 楽器 | トーン |
|------|------|-------|
| 熱帯雨林 | バンスリ（Bansuri、インドフルート）、シタール、タブラ | 柔らかく繊細 |
| 砂漠 | ネイ（Ney）、ドゥドゥク（Duduk、中東木管） | 荒々しく野性的 |
| 共通 | ロンドン交響楽団 | 壮大 |

この組み合わせがスメール戦闘曲の「聴くたびに違って感じる」独特な魅力を生み出している。

> 📄 *[Forest of Jnana and Vidya/Background](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Genshin Impact Wiki。Yu-Peng Chenのフィボナッチ作曲に関する言及原文。*
>
> 📄 *[Bilibili — スメールリズムフィボナッチ分析映像](https://www.bilibili.tv/video/4789442275312695) —「Gilded Runner」のリズム構造を視覚的に分解した映像。*

### 3.2 「Rage Beneath the Mountains」 — クライマックス配置の黄金比

原神初の**中国語歌詞を含むサウンドトラック**「Rage Beneath the Mountains（磅礴之下的怒号）」は、アズダハ（Azhdaha）ボス戦Phase 2テーマだ。Yu-Peng Chen作曲、B♭短調、136 BPM。

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/C1MmhgVBxWI"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲「Rage Beneath the Mountains」— アズダハボス戦Phase 2テーマ（Yu-Peng Chen & HOYO-MiX）</p>

この曲でフィボナッチ数列を意図的に使用したという公式言及はない。しかし、曲の構造を分析すると興味深いパターンが浮かび上がる。

#### 楽曲構造分析（約3分30秒 = 210秒）

| セクション | 開始点 | 比率 |
|-----------|--------|------|
| イントロ — 二胡 + 弦楽 | 0:00 | 0% |
| ボーカル導入 — 楚辞歌詞開始 | 約0:28 | 13.3% |
| オーケストラ・フルパワー | 約1:05 | 31.0% |
| **クライマックス — エレキギター + ボーカル最高潮** | **約2:10** | **62.4%** |
| コーダ — 余韻 | 約3:00 | 85.7% |

クライマックスが**全体の約62%**の地点に位置する。これは黄金分割点（61.8%）に非常に近い。意図的であれ直感的であれ、Yu-Peng Chenの音楽的感覚が黄金比に従っていることになる。

この曲は楚辞の文体を借りた歌詞、二胡の哀切な旋律、エレキギターの激しさ、そしてオーケストラの壮大さが一つに収束する曲だ。上海交響楽団がGENSHIN CONCERT Special Editionでライブ演奏したこともある。

> 📄 *[Genshin Impact Wiki — Rage Beneath the Mountains](https://genshin-impact.fandom.com/wiki/Rage_Beneath_the_Mountains) — トラック詳細情報および歌詞。*
>
> 📄 *[Di Zeng Piano — Ludomusicology in Genshin Impact](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media) — スメール音楽のデュアル・ハーモニック・スケール分析。*

### 3.3 スメール音楽の制作過程 — 3年の旅路

HOYO-MiXチームはスメールの音楽を**3年かけて**完成させた。音楽プロデューサーDi-Meng Yuanはこう述べた：

> *"Sumeru continues to be influenced by the legacy of ancient civilizations, but the prelude to new wisdom is also being composed."*

制作の要点：

- **録音**：ロンドン交響楽団 + ゲスト民族音楽家、Abbey Road Studios / Redfort Studio / Air-Edel Recording Studios
- **地域別差別化**：昼/夜/夕暮れ/夜明けの4パターン別作曲、戦闘切り替え時に同じメロディ構造を維持しながらオーケストレーションと強度を変換
- **アルバム**：「Forest of Jnana and Vidya」— Disc 4「Battles of Sumeru」に戦闘曲収録。全100トラック、2022年10月20日リリース

---

## Part 4: 他のゲームとポピュラー音楽の黄金比 🎵

### 4.1 Tool — 「Lateralus」（2001）：曲そのものがフィボナッチ数列

ロックバンド**Tool**は、フィボナッチ数列を最も露骨に音楽に織り込んだ現代アーティストだ。アルバム*Lateralus*のタイトル曲は数列そのものが曲になっている。

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/Y7JG63IuaWs"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲ Tool —「Lateralus」(2001)</p>

**歌詞の音節数がフィボナッチ数列に従う：**

```
Black                               → 1音節
Then                                → 1音節
White are                           → 2音節
All I see                           → 3音節
In my infancy                       → 5音節
Red and yellow then came to be      → 8音節
Reaching out to me                  → 5音節（下降）
Lets me see                         → 3音節（下降）
```

パターン：**1-1-2-3-5-8-5-3-2-1-1-2-3-5-8-13-8-5-3**

数列が上昇して下降し、さらに高く上昇する構造だ。まるで螺旋がどんどん大きくなるように。

**拍子までフィボナッチ：**

コーラスの拍子が**9/8 → 8/8 → 7/8**と変化する。ドラマーのダニー・キャリー（Danny Carey）によると、元の曲名は「9-8-7」だったが、987がフィボナッチ数列の**16番目の項**であることを発見し「Lateralus」に改名したという。

### 4.2 スーパーマリオギャラクシー — 意図しない黄金比

任天堂の伝説的作曲家**近藤浩治（Koji Kondo）**と**横田真人（Mahito Yokota）**は、フィボナッチ数列を意識的に使用していないと明言している。それでも[Kotakuの分析](https://kotaku.com/mario-music-of-golden-proportions-5541606)によると：

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/p0Ff06PSNkU"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲ Super Mario Galaxy —「Gusty Garden Galaxy」(近藤浩治 & 横田真人)</p>

**ウィンドガーデン（Gusty Garden Galaxy）テーマ（64小節）：**

- 黄金分割点：小節39.552（64 × 0.618）
- **実際**：小節39〜40でコルネットとオーボエが登場しテクスチャが転換

**エッグプラネット（Good Egg Galaxy）テーマ（52小節）：**

- 黄金分割点：小節32.14（52 × 0.618）
- **実際**：小節32でティンパニ進入 + 弦楽クレッシェンド

意識していないのに黄金分割点付近で転換が起こる現象について、**人間の美的感覚が黄金比に自然に反応する**という仮説がある。ただし、これは一つの解釈であり、確証バイアス（見たいパターンだけを選んで見る傾向）の可能性も考慮すべきだ。

### 4.3 Genesis — 「Firth of Fifth」

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/SD5engyVXe0"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲ Genesis —「Firth of Fifth」(1973)</p>

プログレッシブ・ロックバンド**Genesis**の「Firth of Fifth」では、ソロセクションが**55、34、13小節**で構成されているという分析がある——すべてフィボナッチ数だ。ただし、これはバンドが公式に明かしたものではなく、ファンや分析者の解釈である。バルトークの第3楽章シロフォンソロ（Part 5参照）のように意図的使用が確認された事例とは区別する必要がある。

---

## Part 5: クラシック巨匠たちの黄金比 🎻

ゲーム音楽のルーツはクラシックにある。原神のYu-Peng Chenもロンドン交響楽団と共同作業するクラシック基盤の作曲家だ。クラシック巨匠たちがどのように黄金比を使ったか簡単に見てみよう。

### 5.1 バルトーク — 数学を楽譜に刻んだ作曲家

**ベーラ・バルトーク（Béla Bartók, 1881-1945）**は、フィボナッチ数列を最も意識的に音楽に適用した作曲家だ。

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/yIKUWKD1TDw"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">▲ バルトーク — 弦楽器、打楽器とチェレスタのための音楽（Pierre Boulez / シカゴ交響楽団）</p>

**≪弦楽器、打楽器とチェレスタのための音楽≫（1936）第1楽章：**

| セクション | 小節番号 | フィボナッチ数 |
|-----------|---------|-------------|
| 提示部の長さ | 21小節 | ✅ F(8) |
| 弦楽ミュート解除 | 34小節 | ✅ F(9) |
| **クライマックス（fff）** | **55小節** | ✅ **F(10)** |
| 全体の長さ | 89小節 | ✅ F(11) |

クライマックスの位置：$\frac{55}{89} \approx 0.618 = \frac{1}{\varphi}$

第3楽章ではシロフォンが演奏する**リズムパターン自体**がフィボナッチ数列だ：

> **1, 1, 2, 3, 5, 8, 5, 3, 2, 1, 1**

音価がフィボナッチ数列に従って拡張し、鏡のように収縮する構造だ。これは学者の間でも最も議論が少ない、フィボナッチの明白な事例として認められている。

> **学術的論争**：数学者ガレス・ロバーツ（Gareth E. Roberts）は第1楽章の分析にチェリーピッキングと確証バイアスがあると指摘した。実際の楽譜は88小節かもしれず、調性的クライマックスは44小節目（フィボナッチ数ではない）に位置するという。第3楽章のリズムパターンだけが確実な事例だという主張。
>
> 📄 *[Roberts, G.E. "Béla Bartók and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.*
>
> 📄 *[AMS Blog (2021). "Did Bartók use Fibonacci numbers?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)*

### 5.2 ドビュッシー、ショパン、モーツァルト

**ドビュッシー≪水の反映≫**：調性変化がフィボナッチ間隔（**34、21、13、8**小節）で配置。フォルティッシモのクライマックスが黄金分割点に位置。水に映った像が実物より短く見える**屈折効果**を数学的に模倣したという分析がある。

> 📄 *Howat, Roy. [Debussy in Proportion.](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis) Cambridge UP, 1983.*

**ショパン前奏曲 Op.28 No.1**：全34小節中、重要イベントが8、13、21小節目に位置——連続するフィボナッチ数4つ。

**モーツァルト ピアノソナタ第1番 第1楽章**：提示部38小節 + 展開部+再現部62小節 = 100小節。B ÷ A = 62 ÷ 38 ≈ **1.63** ——黄金比に非常に近い。

---

## Part 6: 楽器設計の黄金比 — ストラディヴァリウスの秘密

**アントニオ・ストラディヴァリ（Antonio Stradivari, 1644-1737）**が製作したバイオリンは、数百年経った今でも世界最高の音色を誇る。一部の研究者はその秘密の一つとして**黄金比**を指摘する。

| 部位 | 比率関係 |
|------|---------|
| ネック+ペグボックス+スクロール : ボディ | ≈ 1 : 1.618 |
| ウエスト〜上部 : ウエスト+上部〜全体 | ≈ 1 : 1.618 |
| F字孔の間隔 | フィボナッチ数ベースの配置 |

この比率が**音響共鳴**に最適化された構造を作るという主張があるが、ストラディヴァリウスの音色は単純に比率だけでは説明できない。木材の密度、ニスの成分、経年変化など複合的な要素が作用しており、黄金比はその中の一つの解釈である。

> **参考**：[Benning Violinsの分析資料](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html)でストラディヴァリウスの実際の寸法とフィボナッチ数列の関係を写真と共に確認できる。

---

## Part 7: 実践 — ゲーム開発者のための活用法

### 7.1 クライマックス配置の公式

曲の最も強烈な瞬間をどこに置くべきか？

$$\text{クライマックス位置} = \text{全小節数} \times 0.618$$

| 全体の長さ | クライマックス位置 | 最も近いフィボナッチ |
|----------|-----------------|-------------------|
| 32小節 | 20小節目 | 21 (F₈) |
| 64小節 | 40小節目 | 34 (F₉) |
| 128小節 | 79小節目 | 89 (F₁₁) |

ポップ音楽でも「曲の61.8%地点」にブリッジやラストコーラスが来ることが多い。50%でも100%でもなく、**62%付近**が最も感情的インパクトが大きい。

### 7.2 構造設計

フィボナッチ数でセクションの長さを決めると自然な流れが生まれる：

```
イントロ（8小節）→ ヴァース1（13小節）→ コーラス（8小節）
→ ヴァース2（13小節）→ コーラス（8小節）
→ ブリッジ（5小節）→ 最終コーラス（13小節）
→ アウトロ（3小節）
```

合計71小節。ブリッジ（5小節）が始まる55小節地点が黄金分割点付近だ。

### 7.3 ゲーム開発者のためのアイデア

- **レベルデザイン**：緊張と弛緩のサイクルをフィボナッチ間隔で配置
- **UIレイアウト**：黄金螺旋をベースに視線誘導
- **難易度カーブ**：フィボナッチ級数で段階的上昇 → 自然な体感難易度
- **サウンドデザイン**：BGM転換点を黄金分割に合わせて配置
- **プロシージャル生成**：フィボナッチ螺旋でマップ/ダンジョン構造を生成
- **電子音楽サウンドデザイン**：ディレイタイムをフィボナッチ数（3, 5, 8, 13ms）に設定すると自然なエコーが生成（DAW実践テクニック）

---

## おわりに — 数学は美の言語である

フィボナッチ数列と黄金比が音楽、自然、芸術で繰り返し現れる理由について、さまざまな解釈がある：

1. **進化論的解釈**：自然で効率的な構造が黄金比に従うため、それを「美しい」と感じるように進化した
2. **数学的解釈**：無理数の中で最も「無理な」数（有理数で近似するのが最も難しい数）であるため、最も均一な分割を生む
3. **認知科学的解釈**：脳のパターン認識システムが「予測可能だが少しだけ外れる」比率を好む

どの解釈であれ、一つだけ確かなことがある：**数学と芸術は対立するものではなく、同じ美の異なる表現である**ということだ。

Yu-Peng Chenがフィボナッチ数列でスメールの戦闘曲を作った時、彼は800年前にフィボナッチがウサギの繁殖パターンで観察し、100年前にバルトークが楽譜に刻み、数億年前にヒマワリが種を配列した、その同じ数学的原理を使ったのだ。

次に原神でスメールの戦闘曲が聞こえた時、あるいはアズダハボス戦の鳥肌が立つクライマックスに出会った時——その裏でフィボナッチのウサギたちが跳ね回っていることを思い出してみよう。

---

## References

### 書籍 / Books

- Lendvai, Ernő. *Béla Bartók: An Analysis of His Music*. Kahn & Averill, 1971.
- Howat, Roy. [*Debussy in Proportion: A Musical Analysis*](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis). Cambridge University Press, 1983.

### 論文 / Academic Papers

- van Gend, Robert. ["The Fibonacci Sequence and the Golden Ratio in Music."](https://nntdm.net/papers/nntdm-20/NNTDM-20-1-72-77.pdf) *Notes on Number Theory and Discrete Mathematics*, 20(1), 72-77, 2014.
- Gür, Ç. & Karabey, B. ["Use of Golden Section in Music."](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music)
- Bora, U. & Kaya, D. ["Investigation of Applications of Fibonacci Sequence and Golden Ratio in Music."](https://www.researchgate.net/publication/343021080_INVESTIGATION_OF_APPLICATIONS_OF_FIBONACCI_SEQUENCE_AND_GOLDEN_RATIO_IN_MUSIC) *Ç.Ü. Sosyal Bilimler Enstitüsü Dergisi*, 29(3), 2020.
- Budiawan, Hery et al. ["Fibonacci Sequence and Anagram Timbre."](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5820722) *SSRN*, 2025.
- Roberts, Gareth E. ["Béla Bartók and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.
- Howat, Roy. ["Debussy, Ravel and Bartók: Towards Some New Concepts of Form."](http://symmetry-us.com/Journals/5-3/howat.pdf) *Symmetry*, 5(3).
- [Ohio University Honors Thesis — "The Golden Ratio and Fibonacci Sequence in Music."](https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=oduhonors1620086748612102&disposition=inline) 2021.

### ゲーム音楽 / Game Music Sources

- [Forest of Jnana and Vidya/Background — Genshin Impact Wiki.](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Yu-Peng Chenフィボナッチ作曲公式言及。
- ["Travelers' Reverie" — Behind the Scenes of the Music of Sumeru.](https://genshin.hoyoverse.com/en/news/detail/24845) HoYoverse Official.
- [Bilibili — スメールリズムフィボナッチ分析映像。](https://www.bilibili.tv/video/4789442275312695) 2023.
- [Charles Cornell Studios — Genshin Impact Fibonacci Post.](https://www.facebook.com/charlescornellstudios/posts/this-track-from-genshin-impact-is-literally-composed-using-the-fibonacci-sequenc/1123755772451565/) Facebook, 2022.
- [VGMO — Yu-Peng Chen Interview.](http://www.vgmonline.net/yu-pengchen/)
- [Di Zeng Piano — Ludomusicology in Genshin Impact.](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media)
- [Kotaku — Mario Music of Golden Proportions (2010).](https://kotaku.com/mario-music-of-golden-proportions-5541606)
- [HOYO-MiX — Wikipedia.](https://en.wikipedia.org/wiki/HOYO-MiX)

### ブログ / 分析資料

- AMS Blog (2021). ["Did Bartók use Fibonacci numbers in his music?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)
- Pinkney, Carla J. ["Great Music and the Fibonacci Sequence."](https://www.lancaster.ac.uk/stor-i-student-sites/carla-pinkney/2022/02/14/great-music-and-the-fibonacci-sequence/) Lancaster University STOR-i, 2022.
- [Music and the Fibonacci Sequence and Phi — The Golden Number.](https://www.goldennumber.net/music/)
- [AudioServices Studio — Golden Ratio in Music.](https://audioservices.studio/blog/golden-ratio-in-music-and-other-maths)
- [Fibonacci in Music: Tool's Lateralus — Fibonicci.com.](https://www.fibonicci.com/fibonacci/tool-lateralus/)
- [Fibonacci Series and Stradivarius Instruments — Benning Violins.](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html)
- [The Nautilus Shell Spiral as a Golden Spiral — The Golden Number.](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)
- [Exploring the Golden Ratio in Sunflower Seed Distribution — IAAC.](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/)
- [Auralcrave — The Golden Ratio in Music.](https://auralcrave.com/en/2020/06/28/the-golden-ratio-in-music-the-songs-of-fibonacci-sequence/)
- [NPR — Fibonacci Percussionist (Konnakol).](https://www.npr.org/2018/08/10/637470699/let-this-percussionist-blow-your-mind-with-the-fibonacci-sequence)
