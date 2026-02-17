---
title: Mathematical Thinking - 집합과 명제, 공리
date: 2024-7-15 17:42:00 +/-TTTT
categories: [Mathematics, Mathematical Thinking]
tags: [mathematics, set theory, proposition, axiom, cantor]

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **이 글의 목적**
> 대학원 논문을 읽기 위해서는 수학적 수식과 증명을 이해하는 것이 필수적이다. 이 글은 그 출발점으로서 **집합, 명제, 공리**의 핵심 개념을 정리한다.
{: .prompt-info}

> Understanding, not just doing.
{: .prompt-tip}

<br>

## 들어가며 - 수학에서 진위 판단

수학에서 주제의 진위 판단을 하는 주요 수단은 **"증명"**이다.

수학적인 주장은 언제나 **참**과 **거짓**만 취급한다. 즉, 어떤 주장에 대해 **Yes** or **No**를 판단한다는 것이며, 이는 **특정 집합에 속하는 여부로 판단하는 것과 같다.**

<br>

## I. 논리 연결사 (Logical Connectives)

수학적 명제를 구성하고 조합하는 데 사용되는 기본 연결사들이다.

### 1. and (그리고, 논리곱)

$$p \land q$$

두 명제 $p$와 $q$가 **모두 참**일 때만 참이다.

| $p$ | $q$ | $p \land q$ |
|-----|-----|-------------|
| T   | T   | T           |
| T   | F   | F           |
| F   | T   | F           |
| F   | F   | F           |

### 2. or (또는, 논리합)

$$p \lor q$$

두 명제 중 **하나 이상이 참**이면 참이다. (수학에서의 or는 inclusive or이다)

| $p$ | $q$ | $p \lor q$ |
|-----|-----|------------|
| T   | T   | T          |
| T   | F   | T          |
| F   | T   | T          |
| F   | F   | F          |

### 3. not (부정)

$$\neg p$$

명제 $p$의 진리값을 **반전**시킨다. 참이면 거짓, 거짓이면 참.

### 4. implies (내포하다, 함의)

$$p \Rightarrow q$$

"$p$이면 $q$이다." $p$가 참이고 $q$가 거짓인 경우에만 거짓이다.

| $p$ | $q$ | $p \Rightarrow q$ |
|-----|-----|--------------------|
| T   | T   | T                  |
| T   | F   | F                  |
| F   | T   | T                  |
| F   | F   | T                  |

> $p$가 거짓일 때 $p \Rightarrow q$가 항상 참인 이유: "거짓인 전제로부터는 무엇이든 도출할 수 있다" (vacuous truth)
{: .prompt-warning}

### 5. for all (모든, 전칭 한정사)

$$\forall x \in S, \; P(x)$$

집합 $S$의 **모든** 원소 $x$에 대해 명제 $P(x)$가 참이다.

### 6. there exists (존재한다, 존재 한정사)

$$\exists x \in S, \; P(x)$$

집합 $S$에 명제 $P(x)$를 만족하는 원소 $x$가 **적어도 하나 존재**한다.

<br>

---

## II. 집합 (Set)

> **용어 정리**
> * Set = Collection (집합) =? Family (집합족)
{: .prompt-info}

### 원소와 집합의 관계

**예시)** 강아지는 고양이가 아니다.

$$\iff \text{강아지는 고양이의 모임에 속하지 않는다.}$$

$$\iff \text{강아지} \notin \{\text{고양이1}, \text{고양이2}, \text{고양이3}, \cdots\}$$

여기서 $\notin$는 "속해있지 않다"는 표현이며, $\in$의 부정이다.

이를 **추상화**하면:

- 강아지 $\Leftrightarrow x$
- 고양이의 모임 $\Leftrightarrow S$

$$\implies x \notin S$$

- $x$는 **원소(element)**, $S$는 **집합(Set)**이라 부른다.
- **원소란?** 어떤 집합에 속한 것.

### 집합이란 무엇인가?

> 어떤 기준을 만족시키는 원소들을 모은 것

이라고 수학의 정석에서 배웠다. 하지만 정말 그럴까?

### 러셀의 역설 (Russell's Paradox)

**이발사 왈:** "자신의 수염을 스스로 자르지 않는 사람들에게만 수염을 잘라주겠다."

- 기준 정립 → 집합 $S$ = {이발사가 수염을 깎아주는 이들의 모임}
- 그러면, 이발사 $x$는 $S$의 **원소이면서 동시에** $S$의 원소이면 안 된다. **모순!**

이것을 **이발사의 역설**이라 부른다.

> **문제점:** 집합을 단순히 "원소를 모은 것"으로 여겼으므로, 집합을 규정하는 과정에서 무언가가 더 필요하다. 여기서 '무언가'를 우리는 **공리(axiom)**라 부른다.
{: .prompt-danger}

<br>

---

## III. 수 체계와 집합의 크기

### 수 체계 포함 관계

$$\mathbb{N} \subset \mathbb{Z} \subset \mathbb{Q} \subset \mathbb{R}$$

| 기호 | 이름 | 예시 |
|------|------|------|
| $\mathbb{N}$ | 자연수 | $1, 2, 3, 4, \cdots$ |
| $\mathbb{Z}$ | 정수 | $\cdots, -2, -1, 0, 1, 2, \cdots$ |
| $\mathbb{Q}$ | 유리수 | $\frac{2}{3}, -\frac{5}{7}, \cdots$ |
| $\mathbb{R}$ | 실수 | $\sqrt{2}, \pi, 3.14\cdots$ |

### 직관을 깨는 질문들

1. 정수의 집합은 자연수 집합보다 크다?
2. 유리수의 집합은 정수의 집합보다 크다?

> 이 모든 질문의 답은 전부 **거짓**이다!
{: .prompt-warning}

<br>

### 1) 자연수 ↔ 정수: 일대일 대응

자연수의 집합을 **짝수의 모임**과 **홀수의 모임**으로 나누자.

**짝수의 경우:**

$$0\;(=2 \times 0) \to 0, \quad 2\;(=2 \times 1) \to 1, \quad 4\;(=2 \times 2) \to 2$$

일반적으로:

$$2n \to n$$

**홀수의 경우:**

$$1\;(=2 \times 0 + 1) \to -1, \quad 3\;(=2 \times 1 + 1) \to -2, \quad 5\;(=2 \times 2 + 1) \to -3$$

일반적으로:

$$2n + 1 \to -(n+1)$$

즉, 자연수와 정수는 각각 하나씩 전부 대응된다. 그러므로 **정수의 모임의 개수와 자연수의 모임의 개수는 일치**한다.

> 특히, 짝수의 모임, 홀수의 모임, 자연수의 모임이 모두 일대일 대응이 됨 또한 알 수 있다. (연습문제)
{: .prompt-tip}

<br>

### 2) 정수 ↔ 유리수: 일대일 대응

정수는 양의 정수, 0, 음의 정수로 구성되어 있고, 유리수 역시 양의 유리수, 0, 음의 유리수로 이루어져 있다. 각각의 0은 서로 대응시키면 되고, 양의 정수(즉 자연수)와 양의 유리수의 **일대일 대응 관계**를 찾아내면 된다. (음의 경우는 부호만 바꿔주면 됨)

모든 양의 유리수는 분수꼴 $\frac{m}{n}$로 나타낼 수 있으므로, 분모가 같은 수들을 다음과 같이 배치하자:

$$\frac{1}{1}, \frac{2}{1}, \frac{3}{1}, \frac{4}{1}, \frac{5}{1}, \frac{6}{1}, \frac{7}{1}, \frac{8}{1}, \cdots$$

$$\frac{1}{2}, \frac{2}{2}, \frac{3}{2}, \frac{4}{2}, \frac{5}{2}, \frac{6}{2}, \frac{7}{2}, \frac{8}{2}, \cdots$$

$$\frac{1}{3}, \frac{2}{3}, \frac{3}{3}, \frac{4}{3}, \frac{5}{3}, \frac{6}{3}, \frac{7}{3}, \frac{8}{3}, \cdots$$

$$\vdots$$

양의 정수(자연수)와 일대일 대응시키려는 것은, 양의 유리수를 하나씩 순차적으로 **세는 방법**을 찾는 것과 같다.

한 가지 방법으로, 위의 나열된 양의 유리수들을 **대각선 방향으로 세면 된다:**

$$\frac{1}{1} \to \frac{2}{1} \to \frac{1}{2} \to \frac{1}{3} \to \frac{2}{2} \to \frac{3}{1} \to \frac{4}{1} \to \frac{3}{2} \to \frac{2}{3} \to \frac{1}{4} \to \cdots$$

> 고등학교 수열 단원에서 이 세는 방법을 **'군수열'**이라 부른다. 양의 유리수를 순차적으로 셀 수 있으므로 양의 정수와 일대일 대응이 성립한다.
{: .prompt-tip}

그러므로 위의 논의에 의해 **정수와 유리수 간의 일대일 대응이 성립**한다.

<br>

### 3) 유리수 ↔ 실수: 일대일 대응이 성립하는가?

> 이 또한 대답은 **거짓**이다!
{: .prompt-danger}

우리는 결론을 **부정하며 모순을 이끌어냄**으로서 결론이 참임을 보이고자 한다. (이러한 논증을 **'귀류법'**이라 부른다)

만약에 유리수와 실수 간에 일대일대응이 성립한다고 가정하자. 그런데 우리는 이미 확인한 1), 2)로부터 **자연수와 유리수 사이에 일대일 대응이 성립함**을 알고있다. 그러므로 유리수와 실수의 일대일 대응이 성립하면 **자연수와 실수 사이에 일대일 대응이 성립해야** 한다.

이는 실수 전체의 모임을 자연수들과 대응하여 하나하나 순차적으로 세나갈 수 있다는 뜻이다. 그렇다면 **임의의 실수의 부분집합**을 선택해도 순차적으로 세나갈 수 있어야 한다. 우리는 실수의 특정 부분집합을 골라서 이것이 **불가능함**을 확인하고자 한다.

#### 칸토어의 대각선 논법 (Cantor's Diagonal Argument)

**0과 1 사이에 있는 모든 실수의 모임**을 생각하자.

0과 1 사이의 실수는 언제나 다음의 형식으로 기술된다:

$$0.a_1 a_2 a_3 a_4 \cdots \quad \text{(각 } a_n \text{은 0부터 9 사이의 어떤 숫자)}$$

$$\text{예) } 0.1, \quad 0.22, \quad 0.1234567890\cdots$$

0과 1 사이의 실수들을 순차적으로 세나갈 수 있어야 하므로 순서를 매겨서 다음과 같이 적자:

$$x_1, x_2, x_3, x_4, \cdots$$

이를 다시 적으면:

$$x_1 = 0.\color{red}{a_1^1} a_2^1 a_3^1 a_4^1 a_5^1 \cdots$$

$$x_2 = 0.a_1^2 \color{red}{a_2^2} a_3^2 a_4^2 a_5^2 \cdots$$

$$x_3 = 0.a_1^3 a_2^3 \color{red}{a_3^3} a_4^3 a_5^3 \cdots$$

$$x_4 = 0.a_1^4 a_2^4 a_3^4 \color{red}{a_4^4} a_5^4 \cdots$$

$$x_5 = 0.a_1^5 a_2^5 a_3^5 a_4^5 \color{red}{a_5^5} \cdots$$

$$\vdots$$

여기서 0과 1 사이의 모든 실수는 순차적으로 셀 수 있으므로:

$$x_* = 0.a_1^* a_2^* a_3^* a_4^* a_5^* \cdots$$

꼴로 표현되어야 한다.

이 시점에서 **다음과 같은 수를 생각해보자:**

$$X = 0.b_1 b_2 b_3 b_4 \cdots$$

여기서 각 $n$번째 자릿수 $b_n$을 다음과 같이 정한다:

- 만약 $a_n^n = 3$이라면: $b_n = 5$
- 만약 $a_n^n \neq 3$이라면: $b_n = 3$

그러면 $X$의 각 자릿수 $b_n$은 $a_n^n$와 다르므로, $X$는 그 어떤 $x_n$와도 달라야한다.

이는 **"0과 1 사이의 모든 실수는 $x_*$ 꼴이라고 한 것"**에 위배되며 **모순이 발생**한다.

이 모순은 **자연수와 실수의 일대일 대응이 성립한다는 가정**에서 비롯된 것이므로 원하는 결론이 도출된다.

> 위의 논증을 **칸토어(Cantor, 1845-1918, 집합론 창시자)**의 **대각화 방법(diagonal method)**이라 부른다.
{: .prompt-info}

<br>

### 생각해 볼 점

자연수 집합은 정수 집합에 속한다. 자연수가 아닌 정수들이 존재하며, 정수 집합도 유리수 집합에 속한다. 역시 정수가 아닌 유리수들이 있다. **그런데도, 세 집합 사이에는 일대일 대응이 가능하다.**

어째서 (직관과 대치되는) 상황이 발생하는가? 이는 적어도 자연수 집합, 정수 집합, 유리수 집합이 전부 **무한집합**이기에 가능한 일이다.

그러나 **모든 무한집합 간에 일대일 대응이 가능한 것이 아니다.** 무한집합들 사이에도 (다소 놀랍게도) 엄연히 차이가 있다. 자연수 집합과 실수 집합의 경우처럼. 적어도 실수의 집합은 일일히 셀 수 없을만큼 자연수의 집합보다 **'크다'!**

> 집합론에서는 무한집합들을 포함하여 집합의 크기를 가수, **Cardinal Number**라 부른다.
{: .prompt-info}

<br>

### 연속체 가설 (Continuum Hypothesis)

> **질문:** 자연수의 집합보다는 '크고' 실수의 집합보다는 '작은' 무한집합이 존재하지 않는가?
{: .prompt-warning}

이 질문은 칸토어에 의해 처음 제기되었고, 다비트 힐베르트에 의해 1900년 세계 수학자 대회에서 제기된 23가지 중요한 문제들 중에서 **1번 문제**에 해당한다. 이를 **연속체 가설**이라 부른다.

- **1940년**, 쿠르트 괴델에 의해 **'반증 불가능'**이 증명되었고
- **1963년**, 폴 코헨에 의해 **'증명 불가능'**이 증명되었다

결론적으로 **답이 없다**는 것이다. 참이라고 해도 상관없고, 거짓이라고 해도 무관하다.

> 이에 대한 자세한 논의는 집합론의 **ZFC 공리계**에 대한 이해를 필요로 한다.
{: .prompt-info}

<br>

---

## IV. 공리 (Axiom)

결국 무엇을 참으로 받아들일지는 각자의 **'선택'**의 영역에 해당하며, 내 선택과 타인의 선택이 일치할 필요가 없다. 그것도 심지어 **수학의 범주 하에서조차.**

### 유클리드 기하학의 공리들

우리가 중고등학교 시절에 숨하게 접해온 수학 안에서도 혹시 실상은 참도 거짓도 아닌데도 반드시 그러해야 하는 것처럼 받아들인 명제들이 있었을까?

- **(피타고라스의 정리)** 직각삼각형의 빗변의 길이의 제곱은 직각을 이루는 두 변의 길이의 제곱합과 같다.

$$b^2 + c^2 = a^2$$

- **(삼각형 공준)** 모든 삼각형의 내각합은 $180°$이다.

$$\alpha + \beta + \gamma = 180°$$

- 직사각형이 존재한다.
- **(등거리 공준)** 평행한 두 직선의 거리는 어디에서나 일정하다.
- **(평행선 공준)** 두 직선이 한 직선과 만나 이루는 두 동측내각의 합이 두 직각보다 작다면 이 두 직선을 무한히 연장할때 그 두 동측내각과 같은쪽에서 만난다.

> 사실은, 위의 다섯 가지 문장은 수학적으로 전부 **동치**이다.
{: .prompt-warning}

기원전 3세기에 쓰여진 **유클리드 기하학**(우리가 중학교 시절에 배웠던) 원론은 다섯 가지 약속(공리)을 토대로 만들어졌고, 그 중에서 다섯번째 공리가 **평행선 공준**에 해당한다.

그리고 19세기에 와서 제 5공리를 **부정해도** 다른 공리와는 아무런 모순이 없음이 밝혀졌다. 마치 연속체 가설처럼.

> **비유클리드 기하학 (Non-Euclidean geometry)**: 제 5공리를 부정하는 기하학. 현대수학에서는 대개 **리만기하학(Riemannian geometry)**이라 부른다. 이름에 해당하는 베른하르트 리만은 가우스의 제자이다.
{: .prompt-info}

> 비유클리드 기하학은 순수학적으로만 중추에 해당하는 수학이 아니며, 현대통계학의 중추를 이루고있는 베이지안 통계학, 코딩과 정보이론, 우리가 살아가는 물리적 시공간 등등에서 수학적 모델로서 자연스럽게 등장한다.
{: .prompt-tip}

<br>

---

## V. 결론

수학적 참과 거짓을 논하려면 **공리의 선택**을 필요로 한다. 특히나 무한집합들 처럼 직관과 실체가 대치될 수 있는 수학적 대상을 다루기 위해서는 적절한 **공리의 선택은 필수불가결**하다.

그러나 적절한 공리의 체택은 각자(그리고 인간의) **합리성에 의존하는 선택과 믿음의 영역**이다. 나쁘게 표현하면 내가 주어진 대상을 어떻게 바라볼지 **'색안경'**을 정해야 그로부터 참과 거짓을 논할 수 있는 것이다.

<br>

---

# Part 2. 대학원 수준으로의 확장

> 여기서부터는 대학원 논문을 읽기 위해 반드시 익혀야 할 개념들이다. Part 1의 직관적 이해 위에 **엄밀한 정의와 증명 기법**을 쌓아올린다.
{: .prompt-info}

<br>

## VI. 증명 기법 (Proof Techniques)

대학원 논문에서 가장 자주 마주치는 것이 증명이다. 증명의 패턴을 알면 논문이 **읽히기** 시작한다.

### 1. 직접 증명 (Direct Proof)

가정 $P$로부터 논리적 단계를 밟아 결론 $Q$에 도달하는 방법.

**예시:** $n$이 짝수이면 $n^2$도 짝수이다.

> **증명.** $n$이 짝수이므로 $n = 2k$ ($k$는 정수). 그러면 $n^2 = (2k)^2 = 4k^2 = 2(2k^2)$. $2k^2$는 정수이므로 $n^2$은 짝수이다. $\blacksquare$

### 2. 대우 증명 (Proof by Contrapositive)

$P \Rightarrow Q$를 직접 보이기 어려울 때, 논리적으로 동치인 $\neg Q \Rightarrow \neg P$를 증명한다.

$$P \Rightarrow Q \;\equiv\; \neg Q \Rightarrow \neg P$$

**예시:** $n^2$이 홀수이면 $n$도 홀수이다.

> **증명.** 대우: "$n$이 짝수이면 $n^2$도 짝수이다." 이는 위에서 이미 증명했다. $\blacksquare$

> 논문에서 "we prove the contrapositive"라는 문구가 나오면 이 패턴이다.
{: .prompt-tip}

### 3. 귀류법 (Proof by Contradiction)

결론을 부정하고 모순을 이끌어내는 방법. Part 1의 칸토어 대각선 논법이 대표적인 예시였다.

**구조:**
1. 증명하고 싶은 것: $P$
2. $\neg P$를 가정한다
3. 논리적 추론을 통해 모순($Q \land \neg Q$)에 도달
4. 따라서 $\neg P$가 거짓이므로 $P$가 참

**고전적 예시:** $\sqrt{2}$는 무리수이다.

> **증명.** $\sqrt{2}$가 유리수라 가정하자. 그러면 $\sqrt{2} = \frac{p}{q}$ (단, $p, q$는 서로소인 정수)로 쓸 수 있다. 양변을 제곱하면 $2 = \frac{p^2}{q^2}$, 즉 $p^2 = 2q^2$. 그러므로 $p^2$은 짝수이고, 따라서 $p$도 짝수이다. $p = 2m$으로 놓으면 $4m^2 = 2q^2$, 즉 $q^2 = 2m^2$. 그러므로 $q$도 짝수. 그런데 $p$와 $q$가 모두 짝수이면 서로소라는 가정에 **모순**. $\blacksquare$

### 4. 수학적 귀납법 (Mathematical Induction)

자연수에 관한 명제 $P(n)$을 모든 $n$에 대해 증명하는 기법.

**구조:**
1. **기저 단계 (Base case):** $P(1)$이 참임을 보인다
2. **귀납 단계 (Inductive step):** $P(k)$가 참이라고 가정하고 ($\leftarrow$ 귀납 가정), $P(k+1)$이 참임을 보인다

**예시:** $1 + 2 + 3 + \cdots + n = \frac{n(n+1)}{2}$

> **증명.**
> - **Base:** $n = 1$일 때 좌변 $= 1$, 우변 $= \frac{1 \cdot 2}{2} = 1$. 성립. $\checkmark$
> - **Inductive step:** $1 + 2 + \cdots + k = \frac{k(k+1)}{2}$이 성립한다고 가정. 양변에 $(k+1)$을 더하면:
>
> $$1 + 2 + \cdots + k + (k+1) = \frac{k(k+1)}{2} + (k+1) = \frac{k(k+1) + 2(k+1)}{2} = \frac{(k+1)(k+2)}{2}$$
>
> 이는 $P(k+1)$과 일치. $\blacksquare$

### 5. 강한 귀납법 (Strong Induction)

귀납 단계에서 $P(k)$만이 아니라 $P(1), P(2), \cdots, P(k)$ **전부**를 가정하고 $P(k+1)$을 보인다. 재귀적 구조의 증명에서 자주 등장한다.

### 6. 구성적 증명 vs 비구성적 증명

| 구성적 (Constructive) | 비구성적 (Non-constructive) |
|---|---|
| 존재를 주장할 때 **실제로 만들어서** 보인다 | 존재하지 않으면 모순임을 보인다 (만들지는 않음) |
| 알고리즘으로 직접 전환 가능 | 존재는 알지만 찾는 방법은 모를 수 있음 |

> 게임 개발에서는 **구성적 증명의 사고방식**이 더 유용하다. "이런 게 존재한다"가 아니라 "이렇게 만들면 된다"로 생각하는 습관.
{: .prompt-tip}

<br>

---

## VII. 집합 연산 (Set Operations)

### 기본 연산

$A$와 $B$가 집합일 때:

| 연산 | 표기 | 정의 |
|------|------|------|
| 합집합 (Union) | $A \cup B$ | $\{x \mid x \in A \text{ or } x \in B\}$ |
| 교집합 (Intersection) | $A \cap B$ | $\{x \mid x \in A \text{ and } x \in B\}$ |
| 차집합 (Difference) | $A \setminus B$ | $\{x \mid x \in A \text{ and } x \notin B\}$ |
| 여집합 (Complement) | $A^c$ | $\{x \in U \mid x \notin A\}$ (전체집합 $U$ 기준) |
| 대칭차집합 | $A \triangle B$ | $(A \setminus B) \cup (B \setminus A)$ |

### 드 모르간 법칙 (De Morgan's Laws)

$$\neg(P \land Q) \equiv (\neg P) \lor (\neg Q)$$

$$\neg(P \lor Q) \equiv (\neg P) \land (\neg Q)$$

집합으로 표현하면:

$$(A \cap B)^c = A^c \cup B^c$$

$$(A \cup B)^c = A^c \cap B^c$$

> 논문에서 **한정사의 부정**을 할 때 항상 등장한다:
> - $\neg(\forall x, P(x)) \equiv \exists x, \neg P(x)$ — "모두가 P"의 부정은 "P가 아닌 것이 존재"
> - $\neg(\exists x, P(x)) \equiv \forall x, \neg P(x)$ — "P가 존재"의 부정은 "모두가 P가 아님"
{: .prompt-warning}

### 멱집합 (Power Set)

집합 $A$의 **모든 부분집합**의 집합.

$$\mathcal{P}(A) = \{S \mid S \subseteq A\}$$

**예시:** $A = \{1, 2, 3\}$일 때:

$$\mathcal{P}(A) = \{\emptyset, \{1\}, \{2\}, \{3\}, \{1,2\}, \{1,3\}, \{2,3\}, \{1,2,3\}\}$$

원소가 $n$개인 집합의 멱집합의 크기는 $2^n$이다.

> **칸토어의 정리:** 임의의 집합 $A$에 대해 $|A| < |\mathcal{P}(A)|$. 즉, 어떤 집합이든 그 멱집합보다 작다. 무한집합에서도 성립하며, 이것이 "무한에도 크기가 다른 무한이 있다"의 핵심 원리이다.
{: .prompt-info}

### 곱집합 (Cartesian Product)

$$A \times B = \{(a, b) \mid a \in A, \; b \in B\}$$

**예시:** $A = \{1, 2\}$, $B = \{x, y\}$이면 $A \times B = \{(1,x), (1,y), (2,x), (2,y)\}$

이것이 좌표계의 수학적 기초이다. $\mathbb{R} \times \mathbb{R} = \mathbb{R}^2$이 바로 2차원 평면.

<br>

---

## VIII. 관계와 함수 (Relations & Functions)

### 관계 (Relation)

집합 $A$에서 $B$로의 **관계** $R$은 곱집합 $A \times B$의 부분집합이다.

$$R \subseteq A \times B$$

$a$와 $b$가 관계 $R$에 있으면 $aRb$ 또는 $(a, b) \in R$로 쓴다.

### 동치관계 (Equivalence Relation)

집합 $A$ 위의 관계 $\sim$이 다음 세 조건을 모두 만족하면 **동치관계**라 부른다:

1. **반사성 (Reflexive):** $a \sim a$
2. **대칭성 (Symmetric):** $a \sim b \Rightarrow b \sim a$
3. **추이성 (Transitive):** $a \sim b \land b \sim c \Rightarrow a \sim c$

**예시:** 정수에서 "같은 나머지" 관계. $a \equiv b \pmod{n}$

$$7 \equiv 2 \pmod{5} \quad \text{(둘 다 5로 나눈 나머지가 2)}$$

> 동치관계는 집합을 겹치지 않는 그룹들로 나눈다. 이를 **동치류(equivalence class)**라 하고, 나뉜 결과를 **분할(partition)**이라 한다. 대학원 수학 어디서든 등장하는 핵심 개념이다.
{: .prompt-warning}

### 순서관계 (Partial Order)

관계 $\leq$가 다음을 만족하면 **반순서(partial order)**라 부른다:

1. **반사성:** $a \leq a$
2. **반대칭성 (Antisymmetric):** $a \leq b \land b \leq a \Rightarrow a = b$
3. **추이성:** $a \leq b \land b \leq c \Rightarrow a \leq c$

모든 원소쌍이 비교 가능하면 **전순서(total order)**, 아니면 **반순서**이다.

**예시:** 집합의 포함관계 $\subseteq$는 반순서. $\{1\}$과 $\{2\}$는 비교 불가.

### 함수의 엄밀한 정의

함수 $f: A \to B$는 관계 $f \subseteq A \times B$로서 **각 $a \in A$에 대해 정확히 하나의** $(a, b) \in f$가 존재하는 것이다.

| 종류 | 정의 | 직관 |
|------|------|------|
| **단사 (Injection)** | $f(a_1) = f(a_2) \Rightarrow a_1 = a_2$ | 서로 다른 입력 → 서로 다른 출력 |
| **전사 (Surjection)** | $\forall b \in B, \exists a \in A: f(a) = b$ | 모든 출력이 도달 가능 |
| **전단사 (Bijection)** | 단사 + 전사 | 완벽한 일대일 대응 |

### 칸토어-베른슈타인 정리 (Cantor-Bernstein Theorem)

$$|A| \leq |B| \text{ 이고 } |B| \leq |A| \text{ 이면 } |A| = |B|$$

즉, $A$에서 $B$로의 단사함수와 $B$에서 $A$로의 단사함수가 각각 존재하면, $A$와 $B$ 사이에 전단사함수가 존재한다. 두 집합의 크기가 같음을 보일 때 **양쪽 방향 단사만 보이면 충분**하다는 강력한 도구.

<br>

---

## IX. 대학원 논문을 위한 핵심 개념 미리보기

> 이 섹션은 각 개념의 "왜 필요한가"와 "어디서 만나는가"를 짚는다. 엄밀한 정의는 각 분야 전용 포스트에서 다룬다.
{: .prompt-info}

### 위상 (Topology) - 열린집합과 닫힌집합

**핵심 아이디어:** "가까움"을 정의하는 방법. 거리(metric) 없이도 "연속"과 "수렴"을 논할 수 있다.

집합 $X$ 위의 **위상** $\tau$는 $X$의 부분집합들의 모임으로서:

1. $\emptyset, X \in \tau$
2. $\tau$의 원소들의 임의의 합집합은 $\tau$에 속한다
3. $\tau$의 원소들의 유한 교집합은 $\tau$에 속한다

$\tau$의 원소를 **열린집합(open set)**이라 부른다.

> **어디서 만나는가:** 매니폴드(manifold) 이론, 미분기하학, ML에서의 데이터 공간 분석. 특히 그래픽스에서 mesh의 수학적 기초가 위상수학이다.
{: .prompt-tip}

### 시그마 대수 ($\sigma$-algebra) - 측도론의 기초

확률론과 적분론의 엄밀한 기초. 집합 $X$ 위의 $\sigma$-algebra $\mathcal{F}$는:

1. $X \in \mathcal{F}$
2. $A \in \mathcal{F} \Rightarrow A^c \in \mathcal{F}$ (여집합에 대해 닫힘)
3. $A_1, A_2, \cdots \in \mathcal{F} \Rightarrow \bigcup_{i=1}^{\infty} A_i \in \mathcal{F}$ (가산 합집합에 대해 닫힘)

확률공간 $(\Omega, \mathcal{F}, P)$에서 $\mathcal{F}$가 바로 이것이다. "확률을 물을 수 있는 사건들의 모임"을 정의한다.

> **어디서 만나는가:** 확률론, 통계학, ML 논문에서 기대값과 적분을 엄밀하게 다룰 때. "measurable function"이라는 표현이 논문에 나오면 이 개념이다.
{: .prompt-tip}

### 거리공간 (Metric Space)

집합 $X$와 거리함수 $d: X \times X \to \mathbb{R}$의 쌍 $(X, d)$로서:

1. $d(x, y) \geq 0$, 그리고 $d(x, y) = 0 \iff x = y$
2. $d(x, y) = d(y, x)$ (대칭성)
3. $d(x, z) \leq d(x, y) + d(y, z)$ (삼각부등식)

> **어디서 만나는가:** 최적화 이론, 수렴 증명, 알고리즘 분석. 게임에서 A* 탐색의 heuristic이 admissible하려면 삼각부등식을 만족해야 한다.
{: .prompt-tip}

### 노름과 내적 (Norm & Inner Product)

벡터공간 $V$ 위의 **노름** $\|\cdot\|$은 "길이"를, **내적** $\langle \cdot, \cdot \rangle$은 "각도"를 추상화한 것이다.

$$\|v\| = \sqrt{\langle v, v \rangle}$$

$$\cos\theta = \frac{\langle u, v \rangle}{\|u\| \cdot \|v\|}$$

> **어디서 만나는가:** 셰이더에서 `dot(normal, lightDir)`가 바로 내적이다. ML에서 코사인 유사도, 그래프 라플라시안 등 모든 곳에서 등장한다.
{: .prompt-tip}

### 수렴과 극한 (Convergence & Limits) - 엡실론-델타

함수 $f$에서 $\lim_{x \to a} f(x) = L$의 엄밀한 정의:

$$\forall \epsilon > 0, \; \exists \delta > 0 : \; 0 < |x - a| < \delta \Rightarrow |f(x) - L| < \epsilon$$

**읽는 법:** "아무리 작은 오차 $\epsilon$을 잡아도, $a$ 근처의 충분히 작은 범위 $\delta$를 찾을 수 있다."

> 이 정의 구조를 이해하면 논문에서 "$\forall \epsilon, \exists \delta$" 패턴이 나올 때마다 자연스럽게 읽힌다.
{: .prompt-warning}

<br>

---

# Part 3. 게임 개발자의 수학적 사고 실전

> 집합론, 명제 논리, 증명 기법은 단지 이론이 아니다. 게임 개발의 **설계, 디버깅, 최적화** 전 과정에서 무의식적으로 사용되는 사고 체계이다. 이 섹션은 그 연결고리를 명시적으로 드러낸다.
{: .prompt-info}

<br>

## X. 집합론적 사고 → 게임 시스템 설계

### 1. Bitmask = 멱집합의 구현

게임에서 컴포넌트 조합, 레이어 마스크, 버프/디버프 시스템은 전부 **멱집합**을 비트로 구현한 것이다.

```csharp
// Unity의 LayerMask는 32비트 정수 = 2^32개의 부분집합 표현
[Flags]
enum BuffType
{
    None     = 0,       // 공집합
    Speed    = 1 << 0,  // {Speed}
    Attack   = 1 << 1,  // {Attack}
    Defense  = 1 << 2,  // {Defense}
    Shield   = 1 << 3   // {Shield}
}

// 합집합: 버프 추가
currentBuffs |= BuffType.Speed | BuffType.Attack;

// 교집합: 특정 버프 확인
bool hasSpeed = (currentBuffs & BuffType.Speed) != 0;

// 차집합: 버프 제거
currentBuffs &= ~BuffType.Defense;
```

**수학적 대응:**

| 집합 연산 | 비트 연산 | 용도 |
|----------|----------|------|
| $A \cup B$ | `a \| b` | 상태/버프 추가 |
| $A \cap B$ | `a & b` | 조건 확인 |
| $A \setminus B$ | `a & ~b` | 상태/버프 제거 |
| $A^c$ | `~a` | 반전 |
| $\mathcal{P}(A)$ | 모든 비트 조합 | 전체 상태 공간 탐색 |

> $n$개의 버프가 있으면 가능한 조합은 $2^n$개. 버프가 20개면 백만 가지가 넘는다. 이것이 게임 밸런싱이 어려운 **수학적 이유**이다.
{: .prompt-warning}

### 2. ECS (Entity Component System) = 집합의 교집합 쿼리

Unity DOTS / ECS 아키텍처의 핵심은 **집합 연산**이다.

```
// "Position과 Velocity를 모두 가진 Entity" = 교집합
query = EntityQuery.Where(has: Position ∩ Velocity)

// "Position은 있지만 Static은 아닌 Entity" = 차집합
query = EntityQuery.Where(has: Position, exclude: Static)
// 수학적으로: {e | e ∈ Position} \ {e | e ∈ Static}
```

### 3. Collision Layer Matrix = 관계의 행렬 표현

Unity의 Physics Layer 충돌 매트릭스는 **집합 간의 관계**를 정의하는 것이다.

$$R \subseteq \text{Layers} \times \text{Layers}$$

"Player 레이어와 Enemy 레이어가 충돌한다" = $(Player, Enemy) \in R$

이 관계가 **대칭적**이라는 것은 $(A, B) \in R \Rightarrow (B, A) \in R$. 물리 엔진에서 충돌 검사를 한 방향만 해도 되는 이유.

<br>

---

## XI. 논리와 증명 → 디버깅과 알고리즘

### 1. 귀류법 → "불가능한 상태" 디버깅

버그가 발생했을 때 가장 강력한 사고 패턴:

> "만약 이 코드가 정상이라면, 이 시점에서 값은 반드시 X여야 한다. 그런데 로그를 보니 Y이다. **모순**. 따라서 이 코드 경로에 버그가 있다."

이것이 **귀류법**이다. 구체적으로:

```
[디버깅 귀류법 패턴]

1. 가정: "함수 A는 정상적으로 작동한다"
2. 가정이 참이라면: A의 출력값은 항상 양수여야 한다 (스펙)
3. 그런데 로그에서 음수가 발견됨
4. 모순 → 가정이 거짓 → A에 버그가 있다
5. A 내부를 조사하면서 같은 패턴을 재귀적으로 적용
```

### 2. 대우 → 조건문 리팩토링

$$P \Rightarrow Q \;\equiv\; \neg Q \Rightarrow \neg P$$

복잡한 조건문을 대우로 뒤집으면 더 명확해지는 경우가 많다:

```csharp
// 원래 (직접): "유효한 타겟이면 데미지를 준다"
if (target != null && target.IsAlive && !target.IsInvincible)
{
    ApplyDamage(target);
}

// 대우로 리팩토링: "데미지를 줄 수 없는 경우를 먼저 걸러낸다" (Guard Clause)
if (target == null) return;
if (!target.IsAlive) return;
if (target.IsInvincible) return;
ApplyDamage(target);
```

수학적으로 동치이지만 **가독성과 유지보수성**이 극적으로 향상된다.

### 3. 수학적 귀납법 → 재귀 알고리즘의 정당성

재귀 알고리즘이 올바르게 동작하는지 확인하는 것은 **수학적 귀납법 그 자체**이다.

```csharp
// 프랙탈 트리 생성
void GenerateBranch(Vector3 start, float length, int depth)
{
    // Base case (기저 단계): depth == 0이면 종료
    if (depth <= 0) return;  // P(0) 확인

    // Inductive step (귀납 단계):
    // "depth-1까지 올바르게 그려진다"를 가정하고 (귀납 가정)
    // depth에서도 올바름을 보인다

    Vector3 end = start + direction * length;
    DrawLine(start, end);

    // P(k) → P(k+1): 더 작은 depth로 재귀 호출
    GenerateBranch(end, length * 0.7f, depth - 1);  // 왼쪽
    GenerateBranch(end, length * 0.7f, depth - 1);  // 오른쪽
}
```

> **재귀가 무한루프에 빠지지 않음을 증명하는 법:** Base case가 반드시 도달 가능하고, 매 호출마다 어떤 값(여기선 depth)이 **순감소**함을 보이면 된다. 이것이 **정지 증명(termination proof)**이다.
{: .prompt-tip}

### 4. 구성적 증명 → 절차적 생성 (Procedural Generation)

"이런 던전이 존재한다"는 비구성적이다. 게임에서는 **"이렇게 만들면 된다"**라는 구성적 증명이 필요하다.

```
[구성적 사고로 던전 생성]

주장: "모든 방이 연결된 던전을 생성할 수 있다"

구성적 증명:
1. 방 하나를 놓는다 (기저)
2. 기존 방 중 하나를 선택하여 인접 위치에 새 방을 연결한다 (귀납)
3. 2를 n-1번 반복하면 n개의 방이 모두 연결된 던전이 만들어진다

→ 이 증명 자체가 알고리즘이다!
```

<br>

---

## XII. 전단사/가산성 → 해시, 시리얼라이제이션, ID 시스템

### 1. 전단사 = 완벽한 매핑 시스템

게임에서 **ID 시스템**을 설계할 때, 전단사(bijection)의 개념이 핵심이다:

```csharp
// Entity ID → Entity Object 매핑이 전단사여야 하는 이유:
// 단사: 같은 ID로 두 Entity가 참조되면 안 됨 (충돌 방지)
// 전사: 모든 Entity가 ID를 가져야 함 (누락 방지)
Dictionary<int, Entity> entityMap;  // 전단사 보장 필요
```

**단사가 깨지면:** 같은 키에 두 오브젝트 → 하나가 사라짐 (해시 충돌)
**전사가 깨지면:** ID 없는 오브젝트 → 관리 불가 (메모리 릭)

### 2. 해시 함수 = 전사를 포기한 대가로 속도를 얻은 함수

$$h: \text{큰 집합 (키)} \to \text{작은 집합 (버킷)}$$

가능한 키의 수 $\gg$ 버킷의 수이므로 **비둘기집 원리**에 의해 충돌은 필연적이다.

> **비둘기집 원리 (Pigeonhole Principle):** $n+1$개의 물건을 $n$개의 상자에 넣으면 적어도 하나의 상자에 2개 이상이 들어간다. 단순하지만 컴퓨터 과학 전반에서 사용되는 강력한 도구.
{: .prompt-info}

### 3. 가산/비가산 → 상태 공간의 탐색 가능성

| 상태 공간 | 가산성 | 게임에서의 의미 |
|----------|--------|--------------|
| 체스의 합법 수 | 가산 (유한) | 완전 탐색 가능 (이론적) |
| 바둑의 합법 수 | 가산 (유한이지만 거대) | 완전 탐색 불가능 → MCTS, AI 필요 |
| 연속 물리 시뮬레이션 | 비가산 | 이산화(discretization) 필수 → 고정 timestep |

> 물리 엔진이 `FixedUpdate`를 쓰는 이유: 연속적(비가산) 시간을 이산적(가산) 스텝으로 변환해야 계산이 가능하기 때문이다. 이것이 **이산화**이며, 수치해석의 핵심 아이디어이다.
{: .prompt-warning}

<br>

---

## XIII. 공리적 사고 → 게임 설계 원칙

### "게임 디자인의 공리" = 게임 규칙

유클리드 기하학이 5개의 공리로부터 모든 정리를 도출했듯이, 게임의 모든 행동과 결과는 **규칙(공리)**으로부터 도출된다.

```
[게임 공리 시스템 예시 - 카드 게임]

공리 1: 덱은 카드의 순서가 있는 집합이다
공리 2: 플레이어는 턴마다 정확히 1장을 드로우한다
공리 3: 손패의 최대 크기는 7이다
공리 4: 마나는 턴 시작 시 1 증가하고, 최대 10이다

→ 정리: "8턴째에 플레이어의 최대 마나는 8이다" (공리 4로부터 연역)
→ 정리: "7턴 동안 카드를 쓰지 않으면 7장을 가지고 있다" (공리 2, 3)
→ 버그 탐지: "10마나인데 11마나 카드를 썼다" → 공리 위반 → 버그
```

### 공리의 일관성 (Consistency) = 게임 밸런스

유클리드의 5공리가 서로 모순되지 않듯이, **게임 규칙도 서로 모순되면 안 된다.**

```
규칙 A: "무적 버프 중에는 데미지를 받지 않는다"
규칙 B: "독 상태이상은 매 초 HP의 5%를 깎는다"

Q: 무적 + 독이 동시에 걸리면?
→ 공리 충돌! 우선순위(공리 추가) 또는 하나를 수정해야 한다.
```

> 게임에서 흔히 발견되는 "코너 케이스 버그"의 대부분은 **규칙(공리) 간의 모순**에서 발생한다. 수학자가 공리계의 무모순성을 검증하듯이, 게임 디자이너는 규칙의 무모순성을 검증해야 한다.
{: .prompt-danger}

### 공리의 독립성 (Independence) = 모듈화

유클리드의 제 5공리가 나머지 4개와 독립적이었던 것처럼, **좋은 게임 시스템은 각 시스템이 독립적**이다.

- 전투 시스템을 바꿔도 인벤토리가 깨지지 않는다 → 독립
- 이동 속도를 바꾸면 점프 높이가 달라진다 → 의존 (결합도 높음)

이것이 바로 소프트웨어 공학에서 말하는 **낮은 결합도(loose coupling)**의 수학적 기원이다.

<br>

---

## XIV. 실전 치트시트: 논문에서 만나는 기호 해독표

대학원 논문을 펼쳤을 때 가장 먼저 막히는 것은 **기호**다.

| 기호 | 읽는 법 | 의미 |
|------|--------|------|
| $\forall$ | for all | 모든 ~에 대해 |
| $\exists$ | there exists | ~가 존재한다 |
| $\exists!$ | there exists unique | 유일하게 존재한다 |
| $\in$ | element of | ~에 속한다 |
| $\subseteq$ | subset of | ~의 부분집합 |
| $\subset$ | proper subset | ~의 진부분집합 |
| $\implies$ ($\Rightarrow$) | implies | ~이면 |
| $\iff$ ($\Leftrightarrow$) | if and only if (iff) | ~일 때 그리고 그때만 (필요충분) |
| $:=$ 또는 $\triangleq$ | defined as | ~로 정의된다 |
| $\approx$ | approximately | 대략 같다 |
| $\propto$ | proportional to | ~에 비례한다 |
| $\sim$ | distributed as / equivalent | ~의 분포를 따른다 / 동치 |
| $\|x\|$ | norm of x | x의 크기(노름) |
| $\langle x, y \rangle$ | inner product | x와 y의 내적 |
| $\nabla$ | nabla (gradient) | 기울기(그래디언트) |
| $\partial$ | partial | 편미분 |
| $\sum$ | summation | 합 |
| $\prod$ | product | 곱 |
| $\int$ | integral | 적분 |
| $\circ$ | composition | 합성 ($f \circ g = f(g(\cdot))$) |
| $\mapsto$ | maps to | ~로 대응된다 ($x \mapsto x^2$) |
| $\mathbb{E}[X]$ | expectation | 기대값 |
| $\Pr(A)$ 또는 $P(A)$ | probability | 확률 |
| s.t. | subject to | ~를 만족하는 조건 하에 |
| w.r.t. | with respect to | ~에 대하여 |
| i.i.d. | independently and identically distributed | 독립 동일 분포 |
| a.s. | almost surely | 거의 확실히 (확률 1) |
| w.l.o.g. | without loss of generality | 일반성을 잃지 않고 |
| QED 또는 $\blacksquare$ | quod erat demonstrandum | 증명 끝 |

### 논문에서 자주 보는 문장 구조 해독

```
논문: "Let ε > 0 be given. Then ∃ δ > 0 s.t. ∀ x ∈ X,
       ‖x - a‖ < δ ⟹ ‖f(x) - f(a)‖ < ε."

해독: "임의의 양수 ε이 주어졌을 때, 적절한 양수 δ가 존재하여
       X의 모든 원소 x에 대해, x와 a의 거리가 δ보다 작으면
       f(x)와 f(a)의 거리도 ε보다 작다."

한줄 요약: "f는 점 a에서 연속이다."
```

```
논문: "∀ η > 0, the sequence {x_n} converges to x* a.s.,
       i.e., Pr(lim_{n→∞} x_n = x*) = 1."

해독: "수열 {x_n}은 x*로 거의 확실히 수렴한다.
       즉, x_n이 x*로 수렴할 확률이 1이다."
```

<br>

---

## 다음 시간을 위한 질문들

- 자연수 집합의 수학적 정의가 뭔가요? (혹자는 $1, 2, 3, \cdots$ 이라고 말씀하시겠지만, '$\cdots$'이라고 말하면 안 되는 것 아닌가요?)
- 왜 $1 + 1 = 2$ 인가요? (왜 당연한걸 묻어, 라고 불만을 제기하고자 하신다면 납득가능하게 설명하실 수 있나요?)
- 왜 $(-1) \times (-1) = 1$ 인가요?

<br>

---

## 참고 자료

- [기대수 관련 유튜브 강의](https://www.youtube.com/watch?v=DLzw99LIwG0)
- Lecture Note 1 (집합과 명제, 공리) - 필기 노트 기반
- Halmos, P. - *Naive Set Theory* (집합론 입문의 고전)
- Velleman, D. - *How to Prove It* (증명 기법 학습서)
- Munkres, J. - *Topology* (위상수학 표준 교재)
