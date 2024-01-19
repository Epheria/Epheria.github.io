---
title: Linear Algebra - 1.8 The Matrix of a Linear Transformation
date: 2024-1-17 12:42:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리**   
> * Matrix Transformation (행렬 변환)
> * Standard Matrix (표준 행렬)
> * Linear Transformation (선형 변환)
{: .prompt-info}

<br>

## How to determine a matrix transformation - 행렬 변환 결정 방법

- $ \mathbf{A}\mathbf{x} = \mathbf{T}(\mathbf{x}) $ 에서 $ \mathbf{A} $ 를 모를 때 $ \mathbf{A} $ 가 어떤 요소로 이루어져 있는지 알아보는 방법에 대한 내용이다.

<br>

$$ \mathbf{I}_2 = \begin{bmatrix} 1 & 0 \\\ 0 & 1 \; \end{bmatrix} \quad are \quad \mathbf{e}_1 = \begin{bmatrix} 1 \\\ 0 \; \end{bmatrix} \quad and \quad \mathbf{e}_2 = \begin{bmatrix} 0 \\\ 1 \; \end{bmatrix} $$

- $ \mathbf{I}_2 $ 는 identity matrix (항등 행렬)을 의미하고 $ \mathbf{e}_1, \mathbf{e}_2 $ 는 $ \mathbf{I}_2 $ 의 column을 의미한다.

<br>

- $ \mathbf{T}(\mathbf{x}) = \mathbf{A}\mathbf{x} $ 를 의미한다. $  \mathbb{R}^{2} $ domain 에서  \mathbb{R}^{3} codomain 으로 변환해주는  $ \mathbf{A} $ 를 모르고  **$ \mathbf{T}( \mathbf{e}) $ (e 의 image)를 안다고 가정**하면 이경우에 **$ \mathbf{A} $ 가 무엇인지 찾을 수 있다.**

$$ \mathbf{T}(\mathbf{e}_1) = \begin{bmatrix} \phantom{-}5 \\\ -7 \\\ \phantom{-}2 \end{bmatrix} \quad and \quad \mathbf{T}( \mathbf{e}_2) = \begin{bmatrix} -3 \\\ \phantom{-}8 \\\ \phantom{-}0 \end{bmatrix} $$

<br>

- 항등 함수의 성질과 linear transformation 의 특성을 이용하면 다음과 같이 표현이 가능하다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_01.png){: : width="600" .normal }

- 즉 이것을 통해  **<span style="color:#179CFF">$ \mathbf{A} $ 는 $ \mathbf{T}( \mathbf{e}) $ 로 이루어져 있다는 것을 확인할 수 있다.</span>**

<br>
<br>

> ***<span style="color:#179CFF">Theorem10. </span>***    
> Let $ \, T : \mathbb{R}^{n} \rightarrow \mathbb{R}^{m} $ be a linear transformation. Then there exists a unique matrix $ A $ such that   
>   
> $$ T(\mathbf{x}) = A(\mathbf{x}) \quad for \; all \; \mathbf{x} \; in \;  \mathbb{R}^{n} $$   
>   
> In fact, $ \, A  \, $ is the $  \, m \times n  \, $ matrix whose $ j $ th column is the vector $ T(\mathbf{e}_j) $, where $ \mathbf{e}_j $ is the $ j $ th column of the identity matrix in $ \mathbb{R}^{n} $ :   
>   
> $$ A =  \begin{bmatrix} T(\mathbf{e}_1) & \dots & T(\mathbf{e}_n) \end{bmatrix} $$
{: .prompt-tip}

- **<span style="color:#179CFF"> $ T(\mathbf{e}) $ 로 구성된 $ A $ 를 standard matrix (표준 행렬) for the linear transformation $T$ 라고 부른다. </span>**
- $ \mathbb{R}^{n} $ space 에 있는 identity matrix의 각각의 column을 transformation을 취한 결과 image 를 column으로 갖고있는 matrix를 standard matrix 라고 한다.

- **증명**

- vector x 를 $ I_n \mathbf{x} $ 라고 표현해보자 여기서 $ I $ 는 identity matrix 이다.
- 아래 식은 $ \mathbf{x} $ 를 linear combination 형태로 표현한 것이다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_02.png){: : width="600" .normal }

- **$ A $ 는 $ T(e) $ 의 열들로 구성되어 있으므로 standard matrix 이다.**

<br>
<br>

## Standard Matrix Example

$$ T : \mathbb{R}^{2} \rightarrow \mathbb{R}^{2} $$

- $T$ 는 $\mathbb{R}^{2}$ domain 에서 $\mathbb{R}^{2}$ codomain 으로 변환하는 함수이다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_03.png){: : width="600" .normal }

- 위 그림처럼 반시계 방향으로 회전하는 transformation 을 찾아보자.
-  **<span style="color:#179CFF">Identity matrix 는 transformation 결과만 알면 transformation matrix 를 도출할 수 있다.</span>**

<br>
<br>

## Geometric Linear Transformation of $\mathbb{R}^{2}$ - 2차원 실수 체계에서의 기하학적인 선형 변환

- 아래 그림들을 보면 Standard Matrix 가 작동하는 방법을 시각적으로 이해할 수 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_04.png){: : width="600" .normal }
   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_05.png){: : width="600" .normal }
   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_06.png){: : width="600" .normal }
   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_07.png){: : width="600" .normal }


<br>
<br>

## Onto - Surjective , 전사 함수

- Transformation 에서 중요한 단어 onto 와 one to one 2가지를 알아보자.
- Onto 는 임의의 $y$ 에 대해서 여러개의 $x$ 가 존재한다는 것이다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_08.png){: : width="300" .normal }

- 그림을 보면 3,4 가 C 에 겹쳐진다. 이를 Onto (one to one 일대일 대응이 아니다.)
- 이것을 Transformation 에 적용해보자.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_09.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_10.png){: : width="600" .normal }

- **<span style="color:#179CFF">Does $T$ map $\mathbb{R}^{n}$ onto $\mathbb{R}^{m}$? 의미는 Does $T(x) = b$ have at least one solution for each $b$ in $\mathbb{R}^{m}$ 을 의미한다.</span>**

- **<span style="color:#179CFF">$T$ 의 range(모든 image set)가 모두 codomain $\mathbb{R}^{m}$ 에 있을 때 $T$ 는 $\mathbb{R}^{m}$ 에 onto</span>** 한다.
- 즉, **<span style="color:#179CFF">codomain $\mathbb{R}^{m}$ 에 있는 각각의 $b$ 에 대해 $ T(x) = b $ 의 적어도 하나의 solution이 존재한다면 onto</span>**  라고 할 수 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_11.png){: : width="600" .normal }

- $\mathbb{R}^{m}$ 에서 $T(x)$ 가 $T$ 의 range에 포함되지 않는 경우가 있으면 not onto 이다.
- 모든 $\mathbb{R}^{n}$ space 가 range 그 자체면 onto 이다.
- 임의의 $b$ 에 대해 최소 1개의 solution 이 있으면 onto 이다.

<br>
<br>

## One-to-one - Injection, 단사 함수

- **domain(정의역)과 codomain(공역)이 원소 하나에 대응되는 것을 의미한다.** 일대일 함수와는 살짝 다른 점은 Y원소 개수와 X원소 개수가 같을 필요가 없다는 점이다.
- **하지만, X원소 개수 $ <= $ Y원소 개수는 만족해야한다!**

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_12.png){: : width="300" .normal }

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_13.png){: : width="600" .normal }

- **<span style="color:#179CFF">is $T$ one-to-one?의 의미는 Does $T(x) = b$ have either a unique solution or none at all?</span>** **(해가 없거나 1개)**를 의미한다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_14.png){: : width="600" .normal }

- 1:1 매칭이면 $T$ is one-to-one
- 하나의 image 가 여러 개의 vector 에 해당된다면 $T$ is not one-to-one 이다.

<br>
<br>

## onto 와 one-to-one 예제

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_15.png){: : width="600" .normal }

- row 3개, pivot position 3개 있으므로 solution 이 존재한다. 무조건 **<span style="color:#179CFF">solution 이 존재하므로 $\mathbb{R}^{4}$ 에서 $\mathbb{R}^{3}$ 으로 onto</span>**  한다.
- $x_3$ 는 free varialbe 이므로 **<span style="color:#179CFF">infinitely many solution 이므로 not one-to-one</span>** 이다.

<br>
<br>


> ***<span style="color:#179CFF">Theorem11. </span>***    
> Let $ \, T : \mathbb{R}^{n} \rightarrow \mathbb{R}^{m} $ be a linear transformation. Then $T$ is one-to-one **if and only if** the equation $ T(\mathbf{x}) = 0 $ has only the **trivial solution.**
{: .prompt-tip}

- one-to-one 은 solution 이 최대 1개 또는 해가 없음을 의미한다.
- theorem11 은 $T$ 가 one-to-one 이면, $ T(\mathbf{x}) = 0 $ 방정식은 trivial solution ($x=0$)만 갖는다는 정리이다.


- **증명**
- $T$ is one-to-one 일 경우 trivial solution 만을 갖게 된다.

<br>

$$ T(\mathbf{0}) = T(0\mathbf{0}) = 0T(\mathbf{0}) = 0 $$

<br>

- 만약 $T$ is not one-to-one 인 경우 $T(u) = b$ , $T(v) = b$ one-to-one 이 아니므로 b(image)는 여러개의 vector 와 매칭된다. (해가 여러개)

$$ T(\mathbf{u} - \mathbf{v}) = T(\mathbf{u}) - T(\mathbf{v}) = 0  $$

- 위 식에서 one-to-one 이 아니므로 nontrivial solution 을 갖게 되어 $ \mathbf{u} - \mathbf{v} \ne 0 $ 을 성립한다. 따라서 $T(\mathbf{x}) = 0$ 은 1개 이상의 solution을 갖고있다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem12. </span>***    
> Let $ \, T : \mathbb{R}^{n} \rightarrow \mathbb{R}^{m} $ be a linear transformation, and let $A$ be the standard matrix for $T$. Then:   
>     
> a.  $T$ maps $\mathbb{R}^{n}$ onto $\mathbb{R}^{m}$ if and only if the columns of $A$ span $\mathbb{R}^{m}$;   
> b.  $T$ is one-to-one if and only if the columns of $A$ are linearly independent.   
{: .prompt-tip}

- $ \, T : \mathbb{R}^{n} \rightarrow \mathbb{R}^{m} $ 이 linear transformation 이면 $A$ 는 $T$ 에 대한 standard matrix 이다.
- $T$ 가 $\mathbb{R}^{n}$ onto $\mathbb{R}^{m}$ 이면 columns of $A$ 는 Span $\mathbb{R}^{m}$ 이다. 다르게 말하면, columns of $A$ 가 Span  $\mathbb{R}^{m}$ 이면 $T$ 는 $\mathbb{R}^{n}$ onto $\mathbb{R}^{m}$ 이다.

- $T$ 가 one-to-one 이면 columns of $A$ 는 linearly independent 하다. 즉, trivial solution 만을 갖는다는 의미.

<br>
<br>

- **예제**

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_16.png){: : width="600" .normal }

   - standard matrix 인 $A$ 행렬 $ \begin{bmatrix} 3 & 1 \\\ 5 & 7 \\\ 1 & 3 \end{bmatrix} $ 이 **<span style="color:#179CFF">scalar multiplication 형태로 표현되지 않는다.</span>**
   - 즉, 이는 linearly independent 한다. -> trivial solution 이 존재한다는 의미 이므로 **<span style="color:#179CFF">one-to-one</span>** 이 성립한다.

   <br>

   - $A$ 행렬에는 3개의 row 와 2개의 pivot position 이 존재한다. **<span style="color:#179CFF">모든 row 가 pivot position을 갖고 있지 않으면 not onto 이다.</span>**



   <br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra8_17.png){: : width="300" .normal }
