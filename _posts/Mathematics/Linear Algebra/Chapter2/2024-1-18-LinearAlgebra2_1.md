---
title: Linear Algebra - 2.1 Matrix Operations
date: 2024-1-18 11:29:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra, Matrix Notations, Matrix Operations]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리**   
> * Matrix Notation (행렬 표기법)
> * Matrix Sum (행렬 덧셈)
> * Scalar Multiple (선형 변환)
> * Matrix Multiplication (행렬 곱)
> * The transpose of a matrix (행렬의 전치)
{: .prompt-info}

<br>

## Matrix Notation - 행렬 표기법

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_01.png){: : width="600" .normal }

- $A$ 가 $m$ x $n$ 행렬이면 i 번째 행, j 번째 열에 있는 항목은 $a_{ij}$ 로 표기한다. 또한 $A$ 의 $(i,j)$ 항목이라고 부른다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem1. </span>***    
> Let $A, \, B, \,$ and $C$ be matrices of the same size, and let $r$ and $s$ be scalars.   
>    
> a.  $A + B = B + A$                  d.  $r(A + B) = rA + rB$   
> b.  $(A + B) + C = A + (B + C)$         e.  $(r + s)A = rA + sA$   
> c.  $A + 0 = A $                        f.  $r(sA) = (rs)A$   
{: .prompt-tip}

- Chapter 1 에서 공부했던 $\mathbb{R}^{n}$ space 에서 vector 의 성질과 동일하다.
- 각각의 **<span style="color:#179CFF">matrix 는 column vector</span>** 로 이루어져 있다. 따라서 vector 의 성질을 만족하게 되어 theorem 1 을 만족하게 된다.

<br>
<br>

## Matrix Multiplication - 행렬 곱

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_02.png){: : width="600" .normal }

- Matrix Multiplication 과 Scalar Multiplication 은 다르다. Matrix Multiplication 에서는 matrix size 가 중요하다.

<br>

- $m$ x $n$ matrix A 와 $n$ x $p$ matrix B 를 곱하면 $m$ x $p$ matrix AB 를 생성한다.
- AB 는 Ab1, Ab2, Ab3 를 나열한 matrix 이다.
- 행렬 곱셈은 내적을 통해서도 빠르게 연산이 가능하다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_03.png){: : width="600" .normal }


   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_04.png){: : width="600" .normal }


   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_05.png){: : width="600" .normal }

<br>
<br>


> ***<span style="color:#179CFF">Theorem2. </span>***    
> Let $A$ be an $m \times n$ matrix, and let $B$ and $C$ have sizes for which the indicated sums and products are defined.   
>    
> a.  $A(BC) = (AB)C$   
> b.  $A(B + C) = AB + BC$   
> c.  $(B + C)A = BA + CA$    
> d.  $r(AB) = (rA)B = A(rB)$    for any scalar $r$   
> e.  $I_mA = A = AI_n$
{: .prompt-tip}  

- A, B, C 가 같은 size 를 갖고 있으면 위 성질을 만족한다. 주의! $AB \ne BA$

<br>

> $\mathbf{WARNINGS:}$   
> $\mathbf{1.}$  In general, $AB \ne BA$.   
> $\mathbf{2.}$  The cancellation laws do ***not*** hold for matrix multiplication. That is, if $AB = AC$, then it is ***not true*** in general that $B = C$.   
> $\mathbf{3.}$  If a product $AB$ is the zero matrix, you ***cannot*** conclude in general that either $A = 0$ or $B = 0$.
{: .prompt-warning}  

- 일반적인 실수체계에서는 $AB = BA$ 가 성립하지만, matrix 체계에서는 성립하지 않는다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_07.png){: : width="600" .normal }


<br>
<br>

## The Transpose of a Matrix - 행렬의 전치

- 행렬의 전치(transpose of a matrix) 는 column 과 row 를 바꾼 것이다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_1_08.png){: : width="600" .normal }

<br>
<br>

> ***<span style="color:#179CFF">Theorem3. </span>***    
> Let $A$ and $B$ denote matrices whose sizes are appropriate for the following sums and products.   
>    
> a.  $(A^T)^T = A$   
> b.  $(A + B)^T = A^T + B^T$   
> c.  For any scalar $r$, $(rA)^T = rA^T$    
> d.  $(AB)^T = B^TA^T$   
{: .prompt-tip}  

- 성질 d 를 주의해야한다. transpose 를 하게 되면 matrix 의 size 가 변하므로.. 순서를 바꿔 size 를 동일하게 한다.