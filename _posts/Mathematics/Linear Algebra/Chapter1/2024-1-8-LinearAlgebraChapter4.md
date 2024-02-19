---
title: Linear Algebra - 1.4 The Matrix Equation Ax=b
date: 2024-1-8 00:00:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra, matrix equation]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리**   
> * matrix equation (행렬 방정식)
> * $ Ax = b $
{: .prompt-info}

<br>

## Product of A and X

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_01.png){: : width="800" .normal }

- **<span style="color:#179CFF">x를 weights로 사용한 A의 columns의 linear combination이다.</span>**
- 즉, x는 scalar의 vector 이다.

<br>
<br>

## Matrix equation 풀기

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_02.png){: : width="800" .normal }

<br>
<br>

## Vector equation to matrix equation - 벡터 방정식을 행렬 방정식으로 표현

- 벡터 방정식을 행렬 방정식으로 표현할 수 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_03.png){: : width="800" .normal }

- **<span style="color:#179CFF">linear combination을 matrix equation 으로 표현할 수 있다.</span>**
- 일반화 했을 경우..
   $ x_1v_1 + x_2v_2 + x_3v_3 = \begin{bmatrix} v_1, v_2, v_3 \; \end{bmatrix}  \begin{bmatrix} x_1 \\\ x_2 \\\ x_3 \; \end{bmatrix} $

<br>
<br>

## System of linear equations to matrix equation - 선형 시스템을 행렬 방정식으로 표현

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_04.png){: : width="400" .normal }

<br>
<br>

## More efficient way to compute matrix equation

- **내적을 사용해서 계산하면 더 빠르게 풀 수 있다.**

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_05.png){: : width="400" .normal }

<br>
<br>

> ***<span style="color:#179CFF">Theorem3.  </span>*** **<span style="color:#179CFF">linear system 의 3가지 표현 방법 </span>**   
> If $ A $ is a $ m \times n $, with columns $ \mathbf{a_1}, \dots, \mathbf{a_n} $, and if $ \mathbf{b} $ is in $ \mathbb{R}^{m} $, the matrix equation   
>   
> $$ A\mathbf{x} = \mathbf{b} $$   
>   
> has the same solution set as the vector equation   
>   
> $$ x_1\mathbf{a_1} + x_2\mathbf{a_2} + \dots + x_n\mathbf{a_n} = \mathbf{b} $$   
>   
> which, in turn, has the same solution set as the system of linear equation whose augmented matrix is   
>   
> $$ \begin{bmatrix} a_1 & a_2 & \dots & a_n & b \; \end{bmatrix}  $$ 
{: .prompt-tip}

- **<span style="color:#179CFF">linear system을 3가지로 표현할 수 있으며 이 3가지는 모두 동일한 solution set</span>**을 갖는다!!

<br>
<br>

> ***<span style="color:#179CFF">Theorem4.  </span>*** **<span style="color:#179CFF">A의 필요충분조건 if and only if </span>**   
> Let $ A $ be an $ m \times n $ matrix. Then the following statements are logically equivalent.   
> That is, for a particular $ A $ , either they are all true statements or they are all false.   
>   
> a.  For each $ \mathbf{b} $ in $ \mathbb{R}^{m} $ , the equation $ Ax = mathbf{b} $ has a solution.   
> b.  Each $ \mathbf{b} $ in  $ \mathbb{R}^{m} $ is a linear combination of the columns of $ A $.   
> c.  The columns of $ A $ span  $ \mathbb{R}^{m} $.   
> d.  $ A $ has a pivot position in every row.   
{: .prompt-tip}

- 4가지 조건 중 하나라도 True 이면 모두 True, 하나라도 False 이면 모두 False.

<br>

**<span style="color:#179CFF"> a.  For each $ \mathbf{b} $ in $ \mathbb{R}^{m} $ , the equation $ Ax = mathbf{b} $ has a solution. </span>**
- $ \mathbb{R}^{m} $ 공간에 있는 임의의 b에 대해서 matrix equation 인 $ Ax = b $ 는 solution 을 갖고 있다.

<br>

**<span style="color:#179CFF"> b.  Each $ \mathbf{b} $ in  $ \mathbb{R}^{m} $ is a linear combination of the columns of $ A $. </span>**
- $ \mathbb{R}^{m} $ 공간에서 b는 A의 columns의 선형 결합이다.

<br>

**<span style="color:#179CFF"> c.  The columns of $ A $ span  $ \mathbb{R}^{m} $. </span>**
- A의 열들은 $ \mathbb{R}^{m} $ 공간에서 span 하다 -> linear combination을 의미

<br>

**<span style="color:#179CFF"> d.  $ A $ has a pivot position in every row. </span>**
- A는 모든 행에 pivot position을 갖고 있다.
- **A는 coefficient matrix를 의미한다.** (주의, A는 augmented matrix가 아니다.)
- A의 행에 pivot position이 없다면 b가 pivot position 이 되고 이는 no solution을 의미한다.
> $  \begin{bmatrix} \; 0 & \dots & 0 & \mathbf{b} \; \end{bmatrix} $ with $ \mathbf{b} $ is nonzero 가 되면 안된다. 

<br>
<br>

## Identity matrix 를 곱하면?

   ![Desktop View](/assets/img/post/mathematics/linearalgebra4_06.png){: : width="600" .normal }

- 위 그림에서 대각선이 모두 1이고, 나머지는 0인 행렬을 **identity matrix** 줄여서 $ I $ 라고 한다.
- $ Ix = x $ for every $ x $ in $ \mathbb{R}^{3} $.

<br>
<br>

> ***<span style="color:#179CFF">Theorem5.  </span>***   
> If $ A $ is an $ m \times n $ matrix, $ \mathbf{v} $ and $ \mathbf{v} $ are vectors in $ \mathbb{R}^{n} $, and  $ c $ is a scalar, then:   
>   
> a.  $ A(\mathbf{u} + \mathbf{v}) = A\mathbf{u} + A\mathbf{v}; $    
> b.  $ A(c\mathbf{u}) = c(A\mathbf{u}) $    
{: .prompt-tip}

- 여기서 A는 coefficient matrix 이다.
- u, v는 벡터
- c 는 스칼라