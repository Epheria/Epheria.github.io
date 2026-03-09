---
title: "Fibonacci Sequence and the Golden Ratio — Hidden Mathematics in Nature, Music, and Game Soundtracks"
lang: en
date: 2026-03-09 10:00:00 +0900
categories: [Mathematics, Mathematical Thinking]
tags: [Fibonacci, Golden Ratio, Music, HoYoverse, Genshin Impact, HOYO-MiX, Game Music, Mathematics]
difficulty: beginner
math: true
toc: true
toc_sticky: true
tldr:
  - "The ratio of consecutive Fibonacci numbers converges to the Golden Ratio (phi approx 1.618), and this ratio appears throughout nature"
  - "The structure of piano keys (13 notes, 8 white keys, 5 black keys, 3-2 grouping) is itself a Fibonacci sequence"
  - "Genshin Impact's Yu-Peng Chen applied the Fibonacci sequence to the Sumeru battle track 'Gilded Runner' to create ever-changing rhythms"
---

[![Hits](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio.svg?view=today-total&label=visitors&color=11b48a)](https://hits.sh/epheria.github.io/posts/FibonacciGoldenRatio/)

## Introduction — The Secret Behind Spine-Tingling Moments in Game Music

The moment you enter the Azhdaha boss fight in Genshin Impact, Chinese vocals reminiscent of the *Chu Ci* poetry rise over orchestra and electric guitar, delivering a spine-chilling climax. The battle music in Sumeru's tropical rainforest unfolds with subtly different rhythms each time you hear it, leaving you wondering: "Why does this track never get old?"

The secret lies in the **Fibonacci Sequence**.

Genshin Impact's composer **Yu-Peng Chen** revealed in an official behind-the-scenes video that he actually used the Fibonacci sequence in Sumeru's battle music. A sequence discovered 800 years ago by an Italian mathematician studying rabbit breeding patterns is now creating "the more you listen, the more captivating" rhythms in 21st-century game soundtracks.

This article explores **how the Fibonacci sequence and the Golden Ratio work in music, centering on the Genshin Impact OST**. We trace the beauty that mathematics creates — from classical music to modern rock.

---

## Part 1: Fibonacci Sequence and the Golden Ratio — A Quick Overview

### 1.1 What Is the Fibonacci Sequence?

In 1202, Italian mathematician **Leonardo Fibonacci** posed an interesting problem in his book *Liber Abaci*:

> "If a pair of rabbits produces one new pair every month, and each new pair begins breeding one month after birth, how many pairs will there be after one year?"

The answer to this problem is the Fibonacci sequence:

$$1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, ...$$

**The rule is simple**: add the two preceding numbers to get the next one.

$$F(n) = F(n-1) + F(n-2)$$

Yet the patterns this simple rule creates are hidden throughout the natural world.

### 1.2 Fibonacci in Nature

| Natural Phenomenon | Fibonacci Number |
|-------------------|-----------------|
| Spiral count in sunflower seeds | 34, 55 |
| Pine cone spirals | 8, 13 |
| Petal count (lily 3, portulaca 5, cosmos 8) | 3, 5, 8, 13 |
| Spiral structure of typhoons and galaxies | Golden spiral |

Why does nature "choose" the Fibonacci sequence? The reason is **spatial optimization**. For sunflowers to pack seeds as densely as possible, they must arrange them at the golden angle (approximately 137.5 degrees), which derives from the Golden Ratio. Evolution doesn't know mathematics, but billions of years of natural selection found the most efficient answer.

> **Note**: Visual analysis of the sunflower golden ratio can be found in IAAC's [research on golden ratio in sunflower seed distribution](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/). Meanwhile, the Nautilus shell is often cited as a prime example of the golden spiral, but it is actually a type of **logarithmic spiral**, not an exact golden spiral ([reference](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)).

### 1.3 The Golden Ratio — phi = 1.618...

Something interesting happens when you calculate the ratio of consecutive Fibonacci numbers:

| n | F(n) | F(n)/F(n-1) |
|---|------|-------------|
| 5 | 5 | 5/3 = **1.667** |
| 6 | 8 | 8/5 = **1.600** |
| 7 | 13 | 13/8 = **1.625** |
| 8 | 21 | 21/13 = **1.615** |
| 10 | 55 | 55/34 = **1.618** |

As the sequence progresses, this ratio converges to a single constant:

$$\varphi = \frac{1 + \sqrt{5}}{2} \approx 1.6180339887...$$

This is the **Golden Ratio (phi)**. It has the unique property that its reciprocal shares the same decimal digits:

$$\frac{1}{\varphi} = \varphi - 1 \approx 0.6180339887...$$

This **0.618** plays a key role in music. The **61.8% point** of a piece is the golden section, and many renowned compositions place their climax at this point.

---

## Part 2: The Skeleton of Music — Fibonacci and Scales

### 2.1 The Secret of Piano Keys

Take a close look at one octave on a piano, and the Fibonacci sequence reveals itself:

```
+--+-+--+-+--+--+-+--+-+--+-+--+--+
|  |#|  |#|  |  |#|  |#|  |#|  |  |
|  | |  | |  |  | |  | |  | |  |  |
| C| | D| | E| F| | G| | A| | B| C|
+--+-+--+-+--+--+-+--+-+--+-+--+--+
```

| Component | Count | Fibonacci? |
|-----------|-------|-----------|
| Total semitones in one octave | **13** notes | F(7) |
| White keys | **8** | F(6) |
| Black keys | **5** | F(5) |
| Black key grouping | **3** + **2** | F(4) + F(3) |

> **Reference diagram**: The Fibonacci mapping can be visually confirmed in Figure 1 of Gur & Karabey's paper ["Use of Golden Section in Music"](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music).

This is no coincidence. The Western **diatonic scale** naturally converged on Fibonacci numbers in the quest to divide the octave most harmoniously.

### 2.2 Fibonacci in Chords and Frequencies

The constituent notes of the most basic **Major Chord** are the 1st, 3rd, and 5th notes — all Fibonacci numbers. These three notes create the **major triad**, which sounds most stable to the human ear.

The Golden Ratio also appears in frequency ratios:

| Interval | Frequency Ratio | Difference from phi |
|----------|----------------|-------------------|
| Perfect 5th | 3:2 = 1.500 | 0.118 |
| Major 6th | 5:3 = 1.667 | 0.049 |
| **Minor 6th** | **8:5 = 1.600** | **0.018** |

The **minor 6th (8:5)** is closest to the Golden Ratio. Intervals created by ratios of Fibonacci numbers (5:3, 8:5, 13:8...) sound most "beautiful" to human ears.

---

## Part 3: Genshin Impact — Battle Music Built on Fibonacci

This is the core part of the article. We analyze how Genshin Impact's composer Yu-Peng Chen wove the Fibonacci sequence into actual game music.

### 3.1 "Gilded Runner" — Building Rhythms with Fibonacci

The Sumeru battle track **"Gilded Runner"** is a piece where Yu-Peng Chen experimentally applied the Fibonacci sequence. He revealed this directly in HOYO-MiX's official behind-the-scenes video ["Travelers' Reverie"](https://genshin.hoyoverse.com/en/news/detail/24845):

> *"In one of the pieces, I experimented with the Fibonacci sequence to create rich and varied rhythmic changes, which make it sound very modern."*
> — Yu-Peng Chen, Music Producer

Conductor and music producer **Robert Ziegler** noted that this track (internal codename **x063**) features many changing patterns like "12 12 123 12345 12."

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 1.5em 0;">
  <iframe src="https://www.youtube.com/embed/ps8oa3CRNfk"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe>
</div>
<p style="text-align: center; color: #868e96; font-size: 0.9em;">Travelers' Reverie — Behind the Scenes of Sumeru Music (HOYO-MiX Official)</p>

#### Track Breakdown

"Gilded Runner" is approximately 4 minutes 5 seconds (245 seconds), with **Fibonacci-based rhythmic sequencing** at its core. Synthesizing [Bilibili's detailed analysis video](https://www.bilibili.tv/video/4789442275312695) and community analysis:

**1) Fibonacci Rhythmic Sequencing**

The repetition cycles of rhythm patterns follow Fibonacci numbers:

```
Basic pattern:    1, 1, 2, 3, 5 beat groups
Extended pattern: 3, 5, 8, 13 measure repetition cycles
```

For example, the Tabla rhythm is presented for **3 measures**, varied for **5 measures**, then joined by the orchestra for **8 measures**. This is why it feels repetitive yet unpredictable.

**2) Sequencing Technique + Fibonacci Intervals**

Yu-Peng Chen applied **"sequencing"** — a compositional technique of repeating melodies at different pitches — using Fibonacci intervals. With each repetition, the pitch rises by a Fibonacci number of semitones, creating increasingly rich and emotional development.

```
1st repetition: Base melody (C)
2nd repetition: +1 semitone (C#)      <- F(1)
3rd repetition: +2 semitones (D)      <- F(3)
4th repetition: +3 semitones (D#)     <- F(4)
5th repetition: +5 semitones (F)      <- F(5)
```

This technique is deeply connected to **Konnakol**, a traditional South Indian vocal percussion technique. Konnakol, a rhythmic vocalization technique from Carnatic music, is called a "mathematical language" due to the close relationship between rhythm and mathematical principles (primes, Fibonacci sequences, geometric patterns). Percussionist B.C. Manjunath is famous for directly applying the Fibonacci sequence to Konnakol.

**3) Instrument Blending**

The same battle music is performed with different instruments depending on the region:

| Region | Instruments | Tone |
|--------|------------|------|
| Rainforest | Bansuri (Indian flute), Sitar, Tabla | Soft and delicate |
| Desert | Ney, Duduk (Middle Eastern woodwind) | Rough and wild |
| Common | London Symphony Orchestra | Grand |

This combination creates the unique charm of Sumeru's battle music that "feels different every time you hear it."

> *[Forest of Jnana and Vidya/Background](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Genshin Impact Wiki. Original text of Yu-Peng Chen's Fibonacci composition mention.*
>
> *[Bilibili — Sumeru Rhythm Fibonacci Analysis Video](https://www.bilibili.tv/video/4789442275312695) — Visual breakdown of "Gilded Runner"'s rhythmic structure.*

### 3.2 "Rage Beneath the Mountains" — Golden Ratio in Climax Placement

"Rage Beneath the Mountains" — Genshin Impact's first **soundtrack featuring Chinese lyrics** — is the Azhdaha boss fight Phase 2 theme. Composed by Yu-Peng Chen, B-flat minor, 136 BPM.

There is no official statement that the Fibonacci sequence was intentionally used in this piece. However, analyzing the structure reveals interesting patterns.

#### Structural Analysis (approx. 3min 30sec = 210 seconds)

| Section | Start Point | Proportion |
|---------|-------------|-----------|
| Intro — Erhu + Strings | 0:00 | 0% |
| Vocal entry — Chu Ci lyrics begin | ~0:28 | 13.3% |
| Full orchestra | ~1:05 | 31.0% |
| **Climax — Electric guitar + peak vocals** | **~2:10** | **62.4%** |
| Coda — Aftermath | ~3:00 | 85.7% |

The climax sits at **approximately 62%** of the total length. This is very close to the golden section (61.8%). Whether intentional or intuitive, Yu-Peng Chen's musical sense follows the Golden Ratio.

The piece converges lyrics borrowing from the *Chu Ci* literary style, the mournful melody of the erhu, the intensity of electric guitar, and orchestral grandeur into one. The Shanghai Symphony Orchestra performed it live at the GENSHIN CONCERT Special Edition.

> *[Genshin Impact Wiki — Rage Beneath the Mountains](https://genshin-impact.fandom.com/wiki/Rage_Beneath_the_Mountains) — Track details and lyrics.*
>
> *[Di Zeng Piano — Ludomusicology in Genshin Impact](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media) — Analysis of Sumeru music's dual harmonic scales.*

### 3.3 The Making of Sumeru's Music — A Three-Year Journey

The HOYO-MiX team completed Sumeru's music over **three years**. Music producer Di-Meng Yuan said:

> *"Sumeru continues to be influenced by the legacy of ancient civilizations, but the prelude to new wisdom is also being composed."*

Key production facts:

- **Recording**: London Symphony Orchestra + guest folk musicians, Abbey Road Studios / Redfort Studio / Air-Edel Recording Studios
- **Regional differentiation**: Separate compositions for day/night/dusk/dawn, maintaining the same melodic structure while varying orchestration and intensity during battle transitions
- **Album**: "Forest of Jnana and Vidya" — Battle music on Disc 4 "Battles of Sumeru." 100 tracks total, released October 20, 2022

---

## Part 4: Golden Ratio in Other Games and Popular Music

### 4.1 Tool — "Lateralus" (2001): A Song That IS the Fibonacci Sequence

Rock band **Tool** is the modern artist that most overtly wove the Fibonacci sequence into music. The title track of the album *Lateralus* is literally the sequence made into a song.

**The syllable count of the lyrics follows the Fibonacci sequence:**

```
Black                               -> 1 syllable
Then                                -> 1 syllable
White are                           -> 2 syllables
All I see                           -> 3 syllables
In my infancy                       -> 5 syllables
Red and yellow then came to be      -> 8 syllables
Reaching out to me                  -> 5 syllables (descending)
Lets me see                         -> 3 syllables (descending)
```

Pattern: **1-1-2-3-5-8-5-3-2-1-1-2-3-5-8-13-8-5-3**

The sequence ascends, descends, then ascends even higher. Like a spiral growing ever larger.

**Even the time signatures are Fibonacci:**

The chorus shifts through **9/8, 8/8, and 7/8** time. According to drummer Danny Carey, the original title was "9-8-7" — until they discovered that 987 is the **16th term** of the Fibonacci sequence, prompting the rename to "Lateralus."

### 4.2 Super Mario Galaxy — Unintentional Golden Ratio

Nintendo's legendary composers **Koji Kondo** and **Mahito Yokota** have stated they don't consciously use the Fibonacci sequence. Yet according to [Kotaku's analysis](https://kotaku.com/mario-music-of-golden-proportions-5541606):

**Gusty Garden Galaxy Theme (64 measures):**

- Golden section: Measure 39.552 (64 x 0.618)
- **Actual**: Cornet and oboe enter at measures 39-40, shifting the texture

**Good Egg Galaxy Theme (52 measures):**

- Golden section: Measure 32.14 (52 x 0.618)
- **Actual**: Timpani enters at measure 32 + string crescendo

There is a hypothesis that **human aesthetic sense naturally responds to the Golden Ratio**, which may explain why transitions occur near the golden section even without conscious intent. However, this is one interpretation, and the possibility of confirmation bias (the tendency to see only the patterns we want to see) must also be considered.

### 4.3 Genesis — "Firth of Fifth"

Analysis suggests that the solo sections of progressive rock band **Genesis**'s "Firth of Fifth" are structured in **55, 34, and 13 measures** — all Fibonacci numbers. However, this was not officially stated by the band but is rather an interpretation by fans and analysts. It should be distinguished from cases where intentional use has been confirmed, such as Bartok's 3rd movement xylophone solo (see Part 5).

---

## Part 5: Golden Ratio of the Classical Masters

The roots of game music lie in classical music. Genshin Impact's Yu-Peng Chen is a classically trained composer who works with the London Symphony Orchestra. Let's briefly examine how classical masters used the Golden Ratio.

### 5.1 Bartok — The Composer Who Wrote Mathematics into Scores

**Bela Bartok (1881-1945)** was the composer who most consciously applied the Fibonacci sequence to music.

**"Music for Strings, Percussion and Celesta" (1936), 1st Movement:**

| Section | Measure Number | Fibonacci Number |
|---------|---------------|-----------------|
| Exposition length | 21 measures | F(8) |
| String mute release | 34 measures | F(9) |
| **Climax (fff)** | **55 measures** | **F(10)** |
| Total length | 89 measures | F(11) |

Climax position: $\frac{55}{89} \approx 0.618 = \frac{1}{\varphi}$

In the 3rd movement, the **rhythm pattern itself** played by the xylophone is the Fibonacci sequence:

> **1, 1, 2, 3, 5, 8, 5, 3, 2, 1, 1**

Note values expand following the Fibonacci sequence then contract like a mirror. This is recognized among scholars as the most uncontested, clear-cut example of Fibonacci in music.

> **Academic debate**: Mathematician Gareth E. Roberts pointed out cherry-picking and confirmation bias in the 1st movement analysis. The actual score may be 88 measures, and the tonal climax sits at measure 44 (not a Fibonacci number). He argues that only the 3rd movement rhythm pattern is a definitive case.
>
> *[Roberts, G.E. "Bela Bartok and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.*
>
> *[AMS Blog (2021). "Did Bartok use Fibonacci numbers?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)*

### 5.2 Debussy, Chopin, Mozart

**Debussy, "Reflets dans l'eau"**: Tonal changes arranged at Fibonacci intervals (**34, 21, 13, 8** measures). The fortissimo climax sits at the golden section. There is analysis suggesting this mathematically mimics the **refraction effect** where reflections in water appear shorter than the original.

> *Howat, Roy. [Debussy in Proportion.](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis) Cambridge UP, 1983.*

**Chopin Prelude Op.28 No.1**: Key events in the 34-measure piece fall at measures 8, 13, and 21 — four consecutive Fibonacci numbers.

**Mozart Piano Sonata No.1, 1st Movement**: Exposition 38 measures + Development+Recapitulation 62 measures = 100 measures. B / A = 62 / 38 = **1.63** — very close to the Golden Ratio.

---

## Part 6: Golden Ratio in Instrument Design — The Secret of Stradivarius

Violins crafted by **Antonio Stradivari (1644-1737)** still boast the world's finest tone centuries later. Some researchers point to the **Golden Ratio** as one of its secrets.

| Part | Proportional Relationship |
|------|--------------------------|
| Neck+pegbox+scroll : Body | approx 1 : 1.618 |
| Waist to upper bout : Waist+upper bout to total | approx 1 : 1.618 |
| F-hole spacing | Fibonacci-based placement |

Some claim these proportions create a structure optimized for **acoustic resonance**, but the tone of a Stradivarius cannot be explained by proportions alone. Multiple factors including wood density, varnish composition, and aging conditions all play a role, and the Golden Ratio is one interpretation among them.

> **Reference**: [Benning Violins' analysis](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html) shows the actual dimensions of Stradivarius instruments and their relationship to the Fibonacci sequence with photographs.

---

## Part 7: Practical Applications — For Game Developers

### 7.1 Climax Placement Formula

Where should the most intense moment of a piece be placed?

$$\text{Climax Position} = \text{Total Measures} \times 0.618$$

| Total Length | Climax Position | Nearest Fibonacci |
|-------------|----------------|------------------|
| 32 measures | Measure 20 | 21 (F8) |
| 64 measures | Measure 40 | 34 (F9) |
| 128 measures | Measure 79 | 89 (F11) |

In pop music too, bridges or final choruses often arrive at "61.8% of the song." Not 50%, not 100% — the area around **62%** delivers the greatest emotional impact.

### 7.2 Structural Design

Setting section lengths to Fibonacci numbers creates a natural flow:

```
Intro (8 measures) -> Verse 1 (13 measures) -> Chorus (8 measures)
-> Verse 2 (13 measures) -> Chorus (8 measures)
-> Bridge (5 measures) -> Final Chorus (13 measures)
-> Outro (3 measures)
```

Total 71 measures. The bridge (5 measures) beginning at measure 55 is near the golden section.

### 7.3 Ideas for Game Developers

- **Level Design**: Place tension and release cycles at Fibonacci intervals
- **UI Layout**: Guide the eye using the golden spiral
- **Difficulty Curve**: Fibonacci-based gradual progression for natural perceived difficulty
- **Sound Design**: Place BGM transition points at golden sections
- **Procedural Generation**: Generate map/dungeon structures using Fibonacci spirals
- **Electronic Sound Design**: Setting delay times to Fibonacci numbers (3, 5, 8, 13ms) creates natural echoes (practical DAW technique)

---

## Conclusion — Mathematics Is the Language of Beauty

There are various interpretations for why the Fibonacci sequence and the Golden Ratio repeatedly appear in music, nature, and art:

1. **Evolutionary interpretation**: Efficient structures in nature follow the Golden Ratio, so we evolved to perceive them as "beautiful"
2. **Mathematical interpretation**: As the most "irrational" of irrational numbers (hardest to approximate with rational numbers), it creates the most uniform divisions
3. **Cognitive science interpretation**: The brain's pattern recognition system prefers ratios that are "predictable yet slightly unexpected"

Whatever the interpretation, one thing is certain: **mathematics and art are not opposed — they are different expressions of the same beauty**.

When Yu-Peng Chen created Sumeru's battle music with the Fibonacci sequence, he was using the same mathematical principle that Fibonacci observed in rabbit breeding 800 years ago, that Bartok inscribed in his scores 100 years ago, and that sunflowers used to arrange their seeds hundreds of millions of years ago.

Next time you hear Sumeru's battle music in Genshin Impact, or encounter the spine-tingling climax of the Azhdaha boss fight — remember that Fibonacci's rabbits are running behind it all.

---

## References

### Books

- Lendvai, Erno. *Bela Bartok: An Analysis of His Music*. Kahn & Averill, 1971.
- Howat, Roy. [*Debussy in Proportion: A Musical Analysis*](https://www.cambridge.org/us/universitypress/subjects/music/twentieth-century-and-contemporary-music/debussy-proportion-musical-analysis). Cambridge University Press, 1983.

### Academic Papers

- van Gend, Robert. ["The Fibonacci Sequence and the Golden Ratio in Music."](https://nntdm.net/papers/nntdm-20/NNTDM-20-1-72-77.pdf) *Notes on Number Theory and Discrete Mathematics*, 20(1), 72-77, 2014.
- Gur, C. & Karabey, B. ["Use of Golden Section in Music."](https://www.researchgate.net/publication/280553726_Use_of_Golden_Section_in_Music)
- Bora, U. & Kaya, D. ["Investigation of Applications of Fibonacci Sequence and Golden Ratio in Music."](https://www.researchgate.net/publication/343021080_INVESTIGATION_OF_APPLICATIONS_OF_FIBONACCI_SEQUENCE_AND_GOLDEN_RATIO_IN_MUSIC) *C.U. Sosyal Bilimler Enstitusu Dergisi*, 29(3), 2020.
- Budiawan, Hery et al. ["Fibonacci Sequence and Anagram Timbre."](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5820722) *SSRN*, 2025.
- Roberts, Gareth E. ["Bela Bartok and the Golden Section."](https://mathcs.holycross.edu/~groberts/Courses/Mont2/2012/Handouts/Lectures/Bartok-web.pdf) Holy Cross Mathematics.
- Howat, Roy. ["Debussy, Ravel and Bartok: Towards Some New Concepts of Form."](http://symmetry-us.com/Journals/5-3/howat.pdf) *Symmetry*, 5(3).
- [Ohio University Honors Thesis — "The Golden Ratio and Fibonacci Sequence in Music."](https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=oduhonors1620086748612102&disposition=inline) 2021.

### Game Music Sources

- [Forest of Jnana and Vidya/Background — Genshin Impact Wiki.](https://genshin-impact.fandom.com/wiki/Forest_of_Jnana_and_Vidya/Background) — Yu-Peng Chen's official Fibonacci composition mention.
- ["Travelers' Reverie" — Behind the Scenes of the Music of Sumeru.](https://genshin.hoyoverse.com/en/news/detail/24845) HoYoverse Official.
- [Bilibili — Sumeru Rhythm Fibonacci Analysis Video.](https://www.bilibili.tv/video/4789442275312695) 2023.
- [Charles Cornell Studios — Genshin Impact Fibonacci Post.](https://www.facebook.com/charlescornellstudios/posts/this-track-from-genshin-impact-is-literally-composed-using-the-fibonacci-sequenc/1123755772451565/) Facebook, 2022.
- [VGMO — Yu-Peng Chen Interview.](http://www.vgmonline.net/yu-pengchen/)
- [Di Zeng Piano — Ludomusicology in Genshin Impact.](https://www.dizengpiano.com/game-as-a-medium-and-public-recognition-music-andas-media)
- [Kotaku — Mario Music of Golden Proportions (2010).](https://kotaku.com/mario-music-of-golden-proportions-5541606)
- [HOYO-MiX — Wikipedia.](https://en.wikipedia.org/wiki/HOYO-MiX)

### Blog / Analysis

- AMS Blog (2021). ["Did Bartok use Fibonacci numbers in his music?"](https://blogs.ams.org/jmm2021/2021/01/08/did-bartok-use-fibonacci-numbers-in-his-music/)
- Pinkney, Carla J. ["Great Music and the Fibonacci Sequence."](https://www.lancaster.ac.uk/stor-i-student-sites/carla-pinkney/2022/02/14/great-music-and-the-fibonacci-sequence/) Lancaster University STOR-i, 2022.
- [Music and the Fibonacci Sequence and Phi — The Golden Number.](https://www.goldennumber.net/music/)
- [AudioServices Studio — Golden Ratio in Music.](https://audioservices.studio/blog/golden-ratio-in-music-and-other-maths)
- [Fibonacci in Music: Tool's Lateralus — Fibonicci.com.](https://www.fibonicci.com/fibonacci/tool-lateralus/)
- [Fibonacci Series and Stradivarius Instruments — Benning Violins.](https://www.benningviolins.com/fibonacci-series-and-stradivarius-instruments.html)
- [The Nautilus Shell Spiral as a Golden Spiral — The Golden Number.](https://www.goldennumber.net/nautilus-spiral-golden-ratio/)
- [Exploring the Golden Ratio in Sunflower Seed Distribution — IAAC.](https://blog.iaac.net/exploring-the-golden-ratio-in-sunflower-seed-distribution/)
- [Auralcrave — The Golden Ratio in Music.](https://auralcrave.com/en/2020/06/28/the-golden-ratio-in-music-the-songs-of-fibonacci-sequence/)
- [NPR — Fibonacci Percussionist (Konnakol).](https://www.npr.org/2018/08/10/637470699/let-this-percussionist-blow-your-mind-with-the-fibonacci-sequence)
