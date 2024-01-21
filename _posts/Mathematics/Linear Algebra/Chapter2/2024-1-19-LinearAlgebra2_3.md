---
title: Linear Algebra - 2.3 Characterizations of Invertible Matrices of 
date: 2024-1-19 18:15:00 +/-TTTT
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
> * Invertible Linear Trnasformation (역선형 변환)
{: .prompt-info}

<br>

> ***<span style="color:#179CFF">Theorem8. </span>***    
> Let $ A $ be a square $n \times n$ matrix. Then the following statements are equivalent. That is, for a given $A$, the statements are **either all true or all false**    
>    
> a.  $A$ is an invertible matrix.   
> b.  $A$ is row equivalent to the $n \times n$ identity matrix.   
> c.  $A$ has $n$ pivot positions.   
> d.  The equation $A\mathbf{x} = 0$ has only the trivial solution.   
> e.  The columns of $A$ form a linearly independent set.   
> f.  The linear transformation $\mathbf{x} \mapsto A\mathbf{x}$ is one-to-one.   
> g.  The equation $A\mathbf{x} = \mathbf{b}$ has at least one solution for each $\mathbf{b}$ in $ \mathbb{R}^{n} $ .   
> h.  The columns of $A$ span $ \mathbb{R}^{n} $.   
> i.  The linear transformation  $\mathbf{x} \mapsto A\mathbf{x}$ maps $ \mathbb{R}^{n} $ onto $ \mathbb{R}^{m} $ .    
> j.  There is an $n \times n$ matrix $C$ such that $CA = I$.    
> k.  There is an $n \times n$ matrix $D$ such that $AD = I$.   
> l.  $ \mathbb{A}^{T} $ is an invertible matrix.   
{: .prompt-tip}

- $A$ 가 invertible 이면 위 조건을 다 만족하고, not invertible 이면 위 조건을 다 만족하지 않는다.
- $A\mathbf{x} = 0$ 은 trivial solution만을 갖으므로 linearly independent 이며 n pivot position을 만족한다.
- n개의 pivot position을 만족하므로 one-to-one 도 성립하고 $A$ 는 solution이 있으므로 $A$는 $ \mathbb{R}^{n} $ space에 span 하며 이로 인해 onto 역시 성립하게 된다.

- 부연 설명을 하면, onto 이기 위해서는 Ax=b 의 식에서 임의의 b in Rn 이 모두 해를 가져야한다. 즉 A 의 모든 row 가 pivot 을 가지고 있으며, invertible 한 것이다.
- invertible 하기에 solution 이 unique 하므로 one-to-one 이 성립된다. 반대로 one-to-one 일 경우 invertible 하다.


<br>


## 예제

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_3_01.png){: : width="600" .normal }

- R3 공간의 3x3 행렬이고 scalar multiplication 이 없고 눈대중으로 row reduction 을 해도 inconsistent 한 row 가 없으므로 3개의 pivot postion 을 가지고 trivial solution 임을 확인할 수 있다.
- 따라서 linearly independent 하므로 A matrix 는 invertible 하다고 볼 수 있다.

<br>
<br>

## Invertible Linear Transformation - 역선형 변환

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_3_01.png){: : width="600" .normal }

- x 에서 Ax 로 가는 선형변환이 있을 때, 다시 x 로 돌아오는 변환이 있으면 역선형변환이라고 한다.
- **<span style="color:#179CFF"> S 함수가 존재하는 경우에 T는 invertible 하다고 한다.</span>** 

<br>
<br>

> ***<span style="color:#179CFF">Theorem9. </span>***    
> Let $T$ : $\mathbb{R}^{n} \rightarrow \mathbb{R}^{n} $ be a linear transformation and let $A$ be the standard matrix for $T$ . Then $T$ is invertible **if and only if** $A$ is an invertible matrix. In that case, the linear transformation $S$ given by $S(\mathbf{x}) = \mathbb{A}^{-1}\mathbf{x}$ is the unique function satisfying equations (1) and (2)   
{: .prompt-tip}

- linear transformation은 항상 standard matrix 가 존재한다. **<span style="color:#179CFF">$T$ 가 invertible 이면 $A$ (standard matrix) 도 invertible 하다. (역행렬을 가질 수 있음) </span>** 
- 또 linear transformation $S$ 함수는 $S(\mathbf{x}) = \mathbb{A}^{-1}\mathbf{x}$ (1)과 (2) 에 대해 유일함수임을 만족한다.