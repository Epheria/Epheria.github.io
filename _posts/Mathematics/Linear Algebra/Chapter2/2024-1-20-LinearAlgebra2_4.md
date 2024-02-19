---
title: Linear Algebra - 2.4 Partitioned Matrices
date: 2024-1-20 13:32:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra, partitioned matrix, block matrix]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리**   
> * Partitioned Matrix or Block Matrix (분할 행렬 or 블록 행렬)   
> * Column-row expansion AB (AB의 열-행 확장)   
> * Inverse of partitioned matrix (분할 행렬의 역행렬)
{: .prompt-info}

<br>

## Partitioned Matrix or Block Matrix - 분할 행렬 or 블록 행렬

- matrix 가 주어졌을 때 **<span style="color:#179CFF">임의로 row 와 column </span>**을 나눈다.
- 이를 **<span style="color:#179CFF">submatrix 로 표현한 것을 partitioned matrix (분할 행렬) 또는 block matrix (블록 행렬)</span>**이라고 한다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_01.png){: : width="600" .normal }

- 여기서 A 행렬은 총 6개의 파티션으로 나누어졌고, 각 파티션들의 인덱스들은 일반 행렬의 요소들 처럼 취급된다. 따라서 같은 형식으로 파티션이 나뉘어진 행렬들은 똑같은 행렬 연산 (행렬 곱셈, 행렬 덧셈)이 가능하다.

<br>
<br>

## Multiplication of Partitioned Matrix - 분할 행렬의 곱셈

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_02.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_03.png){: : width="600" .normal }

- **<span style="color:#179CFF"> 각각의 block을 단일 entry로 다뤄서 기존의 matrix multiplication 을 이용하면 된다. </span>**
- 이렇게 AB 행렬과 같이 파티션이 나누어져 곱연산이 가능한 형태를 **<span style="color:#179CFF">comfortable</span>** 이라고 한다.


![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_04.png){: : width="600" .normal }

<br>
<br>

> ***<span style="color:#179CFF">Theorem10. Column-Row Expansion of AB </span>***    
> If $A$ is $m \times n$ and $B$ is $n \times p$, then   
> $$ AB = \begin{bmatrix} col_1(A) & col_2(A) & \dots & col_n(A) \end{bmatrix} \begin{bmatrix} row_1(A) \\\ row_2(A) \\\ \dots \\\ row_n(A) \end{bmatrix} $$   
> $$ = col_1(A)row_1(B) + \dots + col_n(A)row_n(B) $$ 
{: .prompt-tip}

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_05.png){: : width="300" .normal }

- **<span style="color:#179CFF"> $m \times n$ 분할 행렬 $A$ 와 $n \times p$ 분할 행렬 $B$ 를 곱하면 $m \times p$ 행렬이 만들어진다.</span>**

<br>
<br>

## Inverses of Partitioned Matrix - 분할 행렬의 역행렬

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_06.png){: : width="600" .normal }

- $A$ matrix 의 form이 block upper triangular 로 주어지고 $A_11$ 은 $p \times p$, $A_22$ 는 $q \times q$ 이고 $A$ 가 invertible 이라고 가정할 때 $A^{-1}$ 을 찾아보자.

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_07.png){: : width="400" .normal }

- 여기서 B 는 A 의 역행렬이다. Multiplication을 적용하면 4개의 식이 도출된다.

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_08.png){: : width="300" .normal }

- 위 식을 $A^{-1}$ 를 찾을 수 있다.

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_09.png){: : width="300" .normal }

![Desktop View](/assets/img/post/mathematics/linearalgebra2_4_10.png){: : width="600" .normal }

- $B_{11}, B_{12}, B_{21}, B_{22}$를 구했으므로 B 행렬(A의 역행렬)을 표현할 수 있다.