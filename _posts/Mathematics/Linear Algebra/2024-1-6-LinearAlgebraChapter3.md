---
title: Linear Algebra - 1.3 Vector Equations
date: 2024-1-6 00:00:00 +/-TTTT
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
> * vectors in $ \mathbb{R}^{n} $ - algebraic properties (대수학적 성질)
> * linear combination (선형 결합)
> * vector equation (벡터 방정식)
> * Span (공간을 포괄하다) 
{: .prompt-info}

<br>

## Vectors in $ \mathbb{R}^{2} $ - 2차원 실수체계에서의 벡터

- $ \mathbb{R}^{2} $ 는 2차원 실수체계를 의미한다.

- 벡터의 표현 방법은 다음과 같다.

### (1) 대괄호

$$

\mathbf{u} =

\begin{bmatrix}
   \phantom{-}3 \\\ -1 \quad 
\end{bmatrix}   

\quad 
\quad 

\mathbf{v} =

\begin{bmatrix}
   .2 \\\ .3 \,
\end{bmatrix}

\quad 
\quad 

\mathbf{w} =

\begin{bmatrix}
   w_1 \\\ w_2 \,
\end{bmatrix}

$$

<br>

### (2) coordinate - 좌표

- $ \mathbf{u} = (3, -1) \quad \mathbf{v} = (.2, .3)  $

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_01.png){: : width="300" .normal }

<br>

### (3) arrows - 화살표

- 원점에서부터 vector point 까지 화살표를 그려 표현
   
   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_02.png){: : width="300" .normal }

<br>
<br>

## Vector summation - 벡터 덧셈

- 2차원 실수체계 공간에서 두 개의 벡터가 주어졌을때 덧셈이 가능

$$

\begin{bmatrix}
   \phantom{-}1 \\\ -2 \quad 
\end{bmatrix}   

+

\begin{bmatrix}
   2 \\\ 5 \,
\end{bmatrix}   

=

\begin{bmatrix}
  \phantom{-}1 + 2 \\\ -2 + 5 \,
\end{bmatrix}   

=

\begin{bmatrix}
   3 \\\ 3 \,
\end{bmatrix}   

$$

<br>
<br>

## Scalar multiplication - 스칼라 곱

- 스칼라와 벡터를 곱할 수 있다. 스칼라는 단 하나의 값을 의미한다.

$$

\mathbf{u} =

\begin{bmatrix}
   \phantom{-}3 \\\ -1 \quad 
\end{bmatrix}   

\quad and \quad c = 5 \, , \quad then \quad c\mathbf{u} = 5 
\begin{bmatrix}
   \phantom{-}3 \\\ -1 \quad 
\end{bmatrix}   =

\begin{bmatrix}
   \phantom{-}15 \\\ -5 \quad 
\end{bmatrix}   

$$

<br>
<br>

## Geometric descriptions of $ \mathbb{R}^{2} $ - 2차원 실수체계 공간에서의 기하학적 표현

- 벡터를 다음과 같이 기하학적으로 표현이 가능하다.

### (1) Geometric descriptions of vector summation 

<br>

$$
\mathbf{u} =
\begin{bmatrix}
   2 \\\ 2 \,
\end{bmatrix}   
\,
,
\mathbf{v} =
\begin{bmatrix}
   -6 \\\ \phantom{-}1 \,
\end{bmatrix}   
\,
,

and \quad \mathbf{u} + \mathbf{v} = 
\begin{bmatrix}
   -4 \\\ \phantom{-}3 \,
\end{bmatrix}   

$$

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_03.png){: : width="400" .normal }

<br>

### (2) Geometric descriptions of scalar multiplication

<br>

$$

Let \; \mathbf{u} =
\begin{bmatrix}
   \phantom{-}3 \\\ -1 \,
\end{bmatrix}   
\,

Display \; the \; vectors \; \mathbf{u} \, , 2\mathbf{u} \, , and \, -{2 \over 3}\mathbf{u} \; on \; a \; graph.

$$

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_04.png){: : width="600" .normal }

- 스칼라곱으로 u 벡터와 동일선상에 있는 모든 것을 표현할 수 있다.

<br>
<br>

## Vectors in $ \mathbb{R}^{3} $ - 3차원 실수체계 공간에서의 벡터

<br>

$
\mathbf{a} =
\begin{bmatrix}
   1 \\\ 5 \\\ 4 \,
\end{bmatrix}   
\,
$

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_05.png){: : width="400" .normal }


<br>
<br>

##  Vectors in $ \mathbb{R}^{n} $ - n차원 실수체계 공간에서의 벡터

<br>

$$
\mathbf{u} =
\begin{bmatrix}
   u_1 \\\ u_2 \\\ \vdots \\\ u_n  \,
\end{bmatrix}   
\,
$$

<br>
<br>

## Algebraic properties of $ \mathbb{R}^{n} $ - $ \mathbb{R}^{n} $ 공간에서 대수학적 성질

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_06.png){: : width="600" .normal }

- 이 8가지 성질은 당연한것같지만 만족하지 않는 세계도 존재한다.
- 벡터는 이 8가지 성질을 만족한다.

<br>
<br>

## Linear combinations - 선형 결합

<br>

> Given vectors $ v_1, v_2, \dots , v_p $ in $ \mathbb{R}^{n} $ and given scalars $ c_1, c_2, \dots , c_p $, the vector $ \mathbf{y} $ defined by $$ \mathbf{y} = c_1\mathbf{v_1} + \dots +  c_p\mathbf{v_p} $$
>   
> - 이것을 weights($ c_1, \dots, c_p $)가 있는 $ v_1, \dots, v_p $ 의 **linear combination** (선형 결합)이라고 한다.
> - weights 는 각각의 vector에 곱해진 scalar를 의미한다.
{: .prompt-tip}

<br>
<br>

## 벡터 방정식은 선형 시스템의 augmented matrix와 같은 해를 갖고 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_07.png){: : width="800" .normal }

- **vector equation과 augmented matrix는 same solution set을 갖고있다.**

<br>

$$
\mathbf{a_1} =
\begin{bmatrix}
   \phantom{-}1 \\\ -2 \\\ -5 \,
\end{bmatrix}   
\,
,
\mathbf{a_2} =
\begin{bmatrix}
   2 \\\ 5 \\\ 6 \,
\end{bmatrix}   
\,
,
\mathbf{a_3} =
\begin{bmatrix}
   \phantom{-}7 \\\ \phantom{-}4 \\\ -3 \,
\end{bmatrix}   
\,

$$

<br>

- $ a_1, a_2, b $ 가 주어졌을 때, $ a_1, a_2 $ 의  linear combination 으로 $ b $를 표현할 수 있다.

<br>

$$
   x_1\mathbf{a_1} + x_2\mathbf{a_2} = \mathbf{b}
$$

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_08.png){: : width="400" .normal }

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_09.png){: : width="400" .normal }

<br>

- 이제 이 augmented matrix에 row reduction을 이용해 reduced echelon form을 얻고 solution을 도출할 수 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_10.png){: : width="600" .normal }

- $ x_1 = 3, x_2 = 2 $ 의 solution 을 구할 수 있다.

<br>
<br>

## Span {$ v_1, \dots, v_p $} 의 의미

- $ v_1, \dots, v_p $ 가 있을 때 span은 $ c_1v_1 + \dots + c_pv_p $ 형태의 linear combination을 의미한다.
- 즉, **span은 linear combination을 간단히 표현한 것**

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_11.png){: : width="800" .normal }

<br>

> ***<span style="color:#179CFF">Q1</span>***  Is a vector $ \mathbf{b} $ is span {$ v_1, \dots, v_p $}?   
> ***<span style="color:#179CFF">Q2</span>***  Does the following vector equation have a solution?    $ x_1v_1 + x_2v_2 + \dots + x_nv_n = \mathbf{b} $   
> ***<span style="color:#179CFF">Q3</span>***  Does the following augmented matrix have a solution?    $ \begin{bmatrix} v_1, \dots, v_n, \mathbf{b} \, \end{bmatrix} $
>
> Q1, Q2, Q3 세가지로 전부 다 나타낼 수 있다.
> ***<span style="color:#179CFF">Q1</span>***  $ \iff $  ***<span style="color:#179CFF">Q2</span>***  $ \iff $   ***<span style="color:#179CFF">Q3</span>***
{: .prompt-warning}

<br>
<br>

## $ \mathbb{R}^{3} $ 공간에서 Span{v} 와 Span{u,v} 의 기하학적 표현

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_12.png){: : width="800" .normal }

- Span{v} 는 3차원에서 직선
- Span{u,v} 는 3차원에서 평면으로 나타낼 수 있다.
- u와 v는 다른 벡터라는 조건에서 Span{u,v}로 표현이 가능하다.

<br>
<br>

## b가 Span{$ a_1, a_2 $}에 존재하는지 확인하기

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_13.png){: : width="800" .normal }

- $ a_1, a_2, b $를 augmented matrix로 표현하고 row reduction을 통해 reduced echelon form을 만들어 solution을 확인

   ![Desktop View](/assets/img/post/mathematics/linearalgebra3_14.png){: : width="800" .normal }

- 여기서 3row를 방정식으로 표현하면, 0 = -2 가 되고 이는 **inconsistent** 즉 no solution 이므로
- **b is not in Span{$ a_1, a_2 $}**