---
title: Linear Algebra - 2.2 The Inverse of Matrix
date: 2024-1-19 13:15:00 +/-TTTT
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
> * Invertible Matrix (역행렬이 존재하는 행렬)
> * determinant (결정자)
> * Elementary Matrix (기본 행렬)
{: .prompt-info}

<br>

## Multiplicative Inverse of a Number

- Invertible Matrix 를 알아보기 전에 숫자의 승수 역수를 살펴보자. $5$의 역수는 $5^-1$ 이다.

$$ 5^{-1} \cdot 5 = 1 \quad and \quad 5 \cdot 5^{-1} = 1 $$ 

<br>
<br>

## Invertible Matrix

> An $n \times m$ matrix $A$ is said to be **invertible** if there is an $n \times m$ matrix $C$ such that   
> $$ CA = I \quad and \quad AC = I $$   
{: .prompt-info}

- invertible 의 첫 번째 조건은  **<span style="color:#179CFF">row와 column의 size가 동일</span>**해야 한다. 또한 $AC = I$ 인 $C$ 행렬이 있어야 하며 **<span style="color:#179CFF">$C$는 unique (유일하다)</span>** 하다.

<br>

> $$ A^{-1}A = I \quad and \quad AA^{-1} = I   $$
{: .prompt-warning}

- matrix가 **<span style="color:#179CFF">not invertible 이면 singular matrix</span>** (해가 존재하지 않는 행렬) 이다.
> 후반에서 singular matrix 형태로 나오면 역행렬을 사용해서 해를 구할 수 없는 어려움을 겪는다고한다..
- **<span style="color:#179CFF">invertible 이면 nonsingular matrix</span>** (해가 존재) 이다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem4. </span>***    
> Let $ A =  \begin{bmatrix} a & b \\\ c & d \end{bmatrix} $ . If $ ad - bc \ne 0 $ , then $A$ is invertible and   
>   
> $$ A^{-1} = {1 \over {ad-bc}} \begin{bmatrix} \phantom{-}d & -b \; \\\ -c & \phantom{-}a \; \end{bmatrix}   $$   
>   
> If  $ ad - bc = 0 $ , then $A$ is not invertible.
{: .prompt-tip}

- $A$ 가 2x2 행렬일 때,  $ ad - bc \ne 0 $ 이면 $A$는 **<span style="color:#179CFF">invertible</span>** 하다.
- $ ad - bc = 0 $ 이면 **<span style="color:#179CFF">not invertible</span>** 하다.

- 여기서 **<span style="color:#179CFF"$ad - bc$> 는 pivot position 이 2개 있을 조건을 의미하며 determinant (결정자) </span>** 라고 부른다.
- 어떤 matrix 가 invertible 을 판단할 때 determinant 가 0인지 아닌지를 확인하면 된다!

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_2_01.png){: : width="600" .normal }

<br>
<br>

> ***<span style="color:#179CFF">Theorem5. </span>***    
> If $A$ is an invertible $n \times n$ matrix, then for each $\mathbf{b}$ in $ \mathbb{R}^{n} $, the equation $A\mathbf{x} = \mathbf{b}$ has the unique solution $ \mathbf{x} = A^{-1}\mathbf{b} $.
{: .prompt-tip}

- $A$ 가 invertible $n \times n$ matrix 이면 $ \mathbb{R}^{n} $ space 에 있는 $\mathbf{b}$ 에 대한 방정식 $A\mathbf{x} = \mathbf{b}$ 는  **<span style="color:#179CFF">유일한 해</span>** ( $ \mathbf{x} = A^{-1}\mathbf{b} $ )를 갖는다.
> 다시말해서, $A\mathbf{x} = \mathbf{b}$ 라는 방정식에서 $A$ 의 역행렬 $A^{-1}$ 은 단 하나만 존재한다는 것이다. $ A^{-1}\mathbf{b} $ is solution.

-**증명**

- 역행렬이 유일하다는 것을 증명하기 위해 다른 솔루션 u가 존재하는지 확인해보면 u라는 솔루션은 사실 $ A^{-1}\mathbf{b} $ 가 되어야한다. 그래서 $Au = b$라고 쓸 수 있다.

<br>

$$ A\mathbf{u} = \mathbf{b} $$

$$ A^{-1}A\mathbf{u} = A^{-1}\mathbf{b}, \quad I\mathbf{u} = A^{-1}\mathbf{b}, \quad and \quad \mathbf{u} = A^{-1}\mathbf{b}  $$

<br>

- 결국 어떤 다른 솔루션 u가 있다고 가정해도 모두 같다는 것을 알 수 있다.

<br>

- **예제**

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_2_02.png){: : width="600" .normal }

- 이처럼 **<span style="color:#179CFF">$A$ 의 inverse 를 이용하면 쉽게 solution </span>**을 구할 수 있다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem6. </span>***    
> a.  If $A$ is an invertible matrix, then $A^{-1}$ is invertible and   
>   
> $$ (A^{-1})^{-1} = A $$   
>   
> b.  If $A$ and $B$ are $n \times n$ invertible matrices, then so is $AB$ , and the inverse of $AB$ is the product of the inverses of $A$ and $B$ in the reverse order. That is   
>   
> $$ (AB)^{-1} = B^{-1}A^{-1} $$   
>   
> c.  If $A$ is an invertible matrix, then so is $A^T$ , and the inverse of $A^T$ is the transpose of $A^{-1}$ . that is,   
>   
> $$ (A^T)^{-1} = (A^{-1})^T $$
{: .prompt-tip}

- a. $A$ 가 invertible matrix 이면 $A^{-1}$ 또한 invertible이다. 
- b. 두 행렬의 곱의 역행렬은 순서가 바뀐 각각의 역행렬이다.
- c. $A$ 가 invertible 이면, $A^T$ 역시 invertible 이다.

<br>
<br>

## Elementary Matrices - 기본 행렬

-  **<span style="color:#179CFF">elementary matrix(기본 행렬)는 identity matrix(항등 행렬)에 row operation 을 적용해서 얻을 수 있다.</span>** 

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_2_03.png){: : width="600" .normal }

- 이것을 가지고 알 수 있는 **특성**은 다음과 같다.

> If an elementary row operation is performed on an $m \times n$ matrix $A$ , the resulting matrix can be written as $EA$ , where the $m \times m$ matrix $E$ is created by performing the same row operation on $I_m$ .
{: .prompt-warning}

- $m \times n$ matrix 에 elementary row operation을 수행했다는 것은 어떤  $m \times m$ elementary matrix가 존재한다는 의미이다.
-  **<span style="color:#179CFF">$A$ 에 적용한 row operation을 $m \times m$ identity matrix에 적용하면 $E$ 가 생성된다. </span>** 

<br>

> Each elementary matrix $E$ is invertible. The inverse of $E$ is the elementary matrix of the same type that trnasforms $E$ back into $I$ .
{: .prompt-warning}

- **elementary matrix $E$ 가 invertible 이면 $E$ 의 inverse는 $E$ 를 $I$ 로 변환하는 elemenatry matrix 이다.**

<br>
<br>

> ***<span style="color:#179CFF">Theorem7. </span>***    
> An  $n \times n$ matrix $A$ is invertible if and only if $A$ is row equivalent to $I_n$ , and in this case, any sequence of elementary row operations that reduces $A$ to $I_n$ also transforms $I_n$ into $A^{-1}$ .
{: .prompt-tip}

- $A$ 가 $n \times n$ invertible matrix 이면 $A$ 는 $I_n$ 과 row equivalent 하다. **$A$ 를 $I_n$ 으로 감소시키는 row operation 은 $I_n$을 $A^{-1}$ 로 변환한다.**

<br>

$$ A \sim E_1A \sim E_2(E_1A) \sim \dots \sim E_p(E_{p-1} \dots E_1A) = I_n $$

<br>

$$ E_p \dots E_1A = I_n $$

<br>

$$ (E_p \dots E_1)^{-1} (E_p \dots E_1)A = (E_p \dots E_1)^{-1} I_n $$

<br>

$$ A = (E_p \dots E_1)^{-1} $$

<br>

$$ A^{-1} = [ (E_p \dots E_1)^{-1} ]^{-1} = E_p \dots E_1 $$

<br>
<br>

## Algorithm for Finding $A^{-1}$

- **<span style="color:#179CFF">$A$ 가 $m \times n$ 이고 invertible 이면 identity matrix 를 이용해서 $A^{-1}$ 를 찾을 수 있다.</span>** 

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_2_05.png){: : width="600" .normal }

   ![Desktop View](/assets/img/post/mathematics/linearalgebra2_2_06.png){: : width="600" .normal }

- 이 방법은 4x4 부터 굉장히 복잡해지기 때문에 손으로 풀기는 불가능하다.