---
title: Linear Algebra - 3.2 Properties of Determinants
date: 2024-1-31 10:00:00 +/-TTTT
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


> ***<span style="color:#179CFF">Theorem3. Row Operations </span>***    
>   
> Let $A$ be a square matrix.    
>    
> a.  If a multiple of one row of $A$ is added to another row to produce a matrix $B$ , then $\mbox{det} B = \mbox{det} A$ .      
> b.  If two rows of $A$ are interchanged to produce $B$ , then $\mbox{det} B = -\mbox{det} A$ .    
> c.  If one row of $A$ is multiplied by $k$ to produce $B$ , then $\mbox{det} B = k \cdot \mbox{det} A$ .
{: .prompt-tip}

- a. 는 row replacement, b. 는 interchange, c. 는 scailing 을 의미한다.
- 이 **<span style="color:#179CFF">세 가지 성질을 이용해서 row reduction 을 통해 echelon form 을 만든 후 cofactor expansion 을 이용하면 determinant 를 쉽게 구할 수 있다.</span>**

<br>

#### $ \mbox{det} EA = (\mbox{det} E)(\mbox{det} A) $ 동일하다.

- $E$ 는 elementary matrix (기본 행렬) 을 의미한다.

$$ E_1 = \begin{bmatrix} 0 & 1 \\\ 1 & 0 \end{bmatrix} \quad E_2 = \begin{bmatrix} 1 & 0 \\\ 0 & k \end{bmatrix} \quad E_3 = \begin{bmatrix} 1 & k \\\ 0 & 1 \end{bmatrix} \quad E_4 = \begin{bmatrix} 1 & 0 \\\ k & 1 \end{bmatrix} \quad A = \begin{bmatrix} a & b \\\ c & d \end{bmatrix}$$

- $E_1$ 은 interchange, $E_2$ 는 second row $k$ scailing,
- $E_3$ 는 second row 에 $k$ scailing 한 것을 first row 에 더한 replacement
- $E_4$ 는 first row 에 $k$ scailing 한 것을 second row 에 더한 replacement를 의미한다.

- 각각의 det 는 다음과 같다.

$$ \begin{vmatrix} E_1 \end{vmatrix} = -1 \quad \begin{vmatrix} E_2 \end{vmatrix} = k \quad \begin{vmatrix} E_3 \end{vmatrix} = 1 \quad \begin{vmatrix} E_4 \end{vmatrix} = 1 \quad \begin{vmatrix} A \end{vmatrix} = ad - bc $$

<br>

- $ \mbox{det} EA = (\mbox{det} E)(\mbox{det} A) $ 의 증명

$ \begin{vmatrix} E_1A \end{vmatrix} = \begin{vmatrix} c & d \\\ a & b \end{vmatrix} = -(ad - bc) = - \begin{vmatrix} A \end{vmatrix} = \begin{vmatrix} E_1 \end{vmatrix} \begin{vmatrix} A \end{vmatrix}$

$ \begin{vmatrix} E_2A \end{vmatrix} = \begin{vmatrix} a & b \\\ kc & kd \end{vmatrix} = -(kad - kbc) = k \begin{vmatrix} A \end{vmatrix} = k \begin{vmatrix} E_2 \end{vmatrix} \begin{vmatrix} A \end{vmatrix}$

$ \begin{vmatrix} E_3A \end{vmatrix} = \begin{vmatrix} a + kc & b + kd \\\ c & d \end{vmatrix} = (ad + kcd - bc - kcd) = \begin{vmatrix} A \end{vmatrix} = \begin{vmatrix} E_3 \end{vmatrix} \begin{vmatrix} A \end{vmatrix}$

$ \begin{vmatrix} E_4A \end{vmatrix} = \begin{vmatrix} a & b \\\ c + ka & d + kb \end{vmatrix} = (ad + kab - bc - kab) = \begin{vmatrix} A \end{vmatrix} = \begin{vmatrix} E_4 \end{vmatrix} \begin{vmatrix} A \end{vmatrix}$

<br>
<br>

- 위 내용을 정리하자면, **<span style="color:#179CFF">$ \mbox{det} EA = (\mbox{det} E)(\mbox{det} A) $ 와 $\mbox{det} E = 1, -1, r$ </span>** 이라는 것을 알 수 있다.
- 따라서 각각의 row operation 은 두 개의 row 에 영향을 끼치므로 **<span style="color:#179CFF">영향을 받지 않은 row 를 기준으로 cofactor expansion 을 사용</span>**하면 $\mbox{det} A$ 를 쉽게 구할 수 있다.

$ \mbox{det} EA = a_{i1} \, (-1)^{i + 1} \, \mbox{det} B_{i1} + \dots + a_{in} \, (-1)^{i + n} \, \mbox{det} B_{in} $

$ = \alpha a_{i1} \, (-1)^{i + 1} \, \mbox{det} A_{i1} + \dots + \alpha a_{in} \, (-1)^{i + n} \, \mbox{det} A_{in} $

$ = \alpha \cdot \mbox{det} A $

<br>

- **예시 문제**

$$ A = \begin{bmatrix} \phantom{-}2 & -8 & \phantom{-}6 & \phantom{-}8 \\\ \phantom{-}3 & -9 & \phantom{-}5 & \phantom{-}10 \\\ -3 & \phantom{-}0 & \phantom{-}1 & -2 \\\ \phantom{-}1 & -4 & \phantom{-}0 & \phantom{-}6 \end{bmatrix} $$

- row reduction 을 사용하여 echelon form 으로 변환하면 det A 를 쉽게 구할 수 있다.

$$ \mbox{det} A = 2 \begin{bmatrix} \phantom{-}1 & -4 & \phantom{-}3 & \phantom{-}4 \\\ \phantom{-}3 & -9 & \phantom{-}5 & \phantom{-}10 \\\ -3 & \phantom{-}0 & \phantom{-}1 & -2 \\\ \phantom{-}1 & -4 & \phantom{-}0 & \phantom{-}6 \end{bmatrix} = 2 \begin{bmatrix} \phantom{-}1 & -4 & \phantom{-}3 & \phantom{-}4 \\\ \phantom{-}0 & \phantom{-}3 & -4 & -2 \\\ \phantom{-}0 & -12 & \phantom{-}10 & \phantom{-}10 \\\ \phantom{-}0 & \phantom{-}0 & -3 & \phantom{-}2 \end{bmatrix} $$

$$ \mbox{det} A = 2 \begin{bmatrix} \phantom{-}1 & -4 & \phantom{-}3 & \phantom{-}4 \\\ \phantom{-}0 & \phantom{-}3 & -4 & -2 \\\ \phantom{-}0 & \phantom{-}0 & -6 & \phantom{-}2 \\\ \phantom{-}0 & \phantom{-}0 & -3 & \phantom{-}2 \end{bmatrix} $$

$$ \mbox{det} A = 2 \begin{bmatrix} \phantom{-}1 & -4 & \phantom{-}3 & \phantom{-}4 \\\ \phantom{-}0 & \phantom{-}3 & -4 & -2 \\\ \phantom{-}0 & \phantom{-}0 & -6 & \phantom{-}2 \\\ \phantom{-}0 & \phantom{-}0 & \phantom{-}0 & \phantom{-}1 \end{bmatrix} = 2 \cdot (1)(3)(-6)(1) = -36 $$

<br>

- 여기서 row operation 을 통해 echelon form 을 만들면 triangular matrix 형태이고 각각의 diaogonal term 들을 곱하면 determinant 를 구할 수 있다.
- 따라서, det 는 echelon form 에서 각각의 pivot 들의 곱을 의미한다.
- 또한 row operation 성질을 이용해서 elementary matrix 의 det를 곱하면 det A 가 나오게 된다.
- 이를 다음과 같이 정의할 수 있다.

> $ \mbox{det} A = \begin{cases}(-1)^r \cdot \begin{pmatrix} \mbox{product of} \\\ \mbox{pivots in} \, U \end{pmatrix} & \mbox{when } A \mbox{ is invertible} \\\ 0 & \mbox{when } A \mbox{ is not invertible} \end{cases} $
{: .prompt-info}

- **<span style="color:#179CFF"> $A$ 가 not invertible 이면 pivot 이 0인 row 가 존재</span>**하게 되어 pivot 들의 곱이 0이 된다.

<br>
<br>

![Desktop View](/assets/img/post/mathematics/linearalgebra3_2_01.png){: : width="600" .normal }

- cofactor expansion 을 사용해서 determinant 를 구하려면 $n!$ 의 연산이 필요했었다.
- 하지만, **<span style="color:#179CFF">row operation 을 이용하게 되면 $2n^3 / 3$ 의 연산이 필요하므로 $25 \times 25$ 이상의 행렬도 빠르게 계산이 가능하다.</span>**

<br>
<br>


> ***<span style="color:#179CFF">Theorem4. </span>***    
>   
> A square matrix $A$ is invertible if and only if $ \mbox{det} A \ne 0$ .
{: .prompt-tip}

- **<span style="color:#179CFF">$ \mbox{det} A \ne 0$ 이면 $A$ 는 invertible 이다.</span>**
- $A$ 가 not invertible 이면 $\mbox{det} A = 0$ 이다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem5. </span>***    
>   
> If $A$ is an $n \times n$ matrix, then $\mbox{det} A^T = \mbox{det} A$ .
{: .prompt-tip}

- **<span style="color:#179CFF">$A^T$ 의 det 와 det $A$ 는 동일하다.</span>**

<br>
<br>

> ***<span style="color:#179CFF">Theorem6. Multiplicative Property </span>***    
>   
> If $A$ and $B$ are $n \times n$ matrices, then $\mbox{det} AB = (\mbox{det}A)(\mbox{det}B)$ .
{: .prompt-tip}

-  $\mbox{det} AB = (\mbox{det}A)(\mbox{det}B) $ 이 만족하는지를 다음과 같이 간단한 행렬을 계산해서 알아보자.

$ A = \begin{bmatrix} 6 & 1 \\\ 3 & 2 \end{bmatrix} \quad \mbox{and} \quad B = \begin{bmatrix} 4 & 3 \\\ 1 & 2 \end{bmatrix} $

$ AB = \begin{bmatrix} 6 & 1 \\\ 3 & 2 \end{bmatrix} \begin{bmatrix} 4 & 3 \\\ 1 & 2 \end{bmatrix} = \begin{bmatrix} 25 & 20 \\\ 14 & 13 \end{bmatrix} $

$ \mbox{det} AB = 25 \cdot 13 - 20 \cdot 14 = 325 - 280 = 45 $

$ (\mbox{det} A)(\mbox{det} B) = 9 \cdot 5 = 45 = \mbox{det} AB $

- 이를 통해 **<span style="color:#179CFF">$\mbox{det} AB = (\mbox{det} A)(\mbox{det} B) $ 가 성립</span>**함을 알 수 있다.

<br>

- 여기서 주의할점은 $\mbox{det} (A + B) $ is not equal to $ \mbox{det} A + \mbox{det} B $ , in general.
- **<span style="color:#179CFF"> $\mbox{det} (A + B) $ 는 $ \mbox{det} A + \mbox{det} B $ 와 동일하지 않다!</span>**

<br>
<br>

## Determinatn Properties Table

- 위 에서 살펴본 Properties 이외에도 추가적인 Determinant 의 Properties 들을 알아보자.

|특성|수식|설명|
|:---|:---|:---|
|prop. 1| $ \mbox{det} \, I = 1 $ | - identity matrix 의 determinant 는 1 이다. |
|prop. 2| $ \mbox{Exchange rows} $ <br> $ \rightarrow \mbox{reverse sign of determinant} $ | - 행을 바꾸면 determinant 의 부호가 바뀐다. <br> - 홀수번 바꾸면 -1, 짝수번 바꾸면 원래 부호 그대로. |
|prop. 3-1| $ \begin{vmatrix} ta & tb \\\ c & d \end{vmatrix} = t \begin{vmatrix} a & b \\\ c & d \end{vmatrix} $ | - 행렬의 하나의 row 에 곱해진 상수는 밖으로 뺄 수 있다. |
|prop. 3-2| $ \begin{vmatrix} a + a^{\prime} & b + b^{\prime} \\\ c & d \end{vmatrix} = \begin{vmatrix} a & b \\\ c & d \end{vmatrix} +  \begin{vmatrix} a^{\prime} & b^{\prime} \\\ c & d \end{vmatrix} $ | - 행렬의 하나의 row 에 더해진 row 벡터는 분리하여 정리할 수 있다.|
|prop. 4| $ \mbox{two equal rows} $ <br> $ \rightarrow \mbox{determinants} = 0 $ | - 행렬에 두 개의 똑같은 row 가 존재하면 determinant는 0이 된다.|
|prop. 5| $ \mbox{row}_k - l * \mbox{row}_i $ <br> $\rightarrow \mbox{determinant doesn't change !}$ | - 행렬을 Gauss 소거법으로 소거하여도 determinant 의 값은 변하지 않는다.|
|prop. 6| $ \mbox{row of zeros} \rightarrow \mbox{det} A = 0 $ | - 모든 원소가 0인 row 가 하나라도 존재한다면, <br> determinant 는 0이다.|
|prop. 7| $ \mbox{det} \, U = \begin{vmatrix} d_1 & * & * & * \\\ 0 & d_2 & * & * \\\ 0 & 0 & \ddots & * \\\ 0 & 0 & 0 & d_n \end{vmatrix} = d_1 \times d_2 \times \dots \times d_n $ | - triangular matrix 의 determinant 는 대각 원소들의 곱으로 간단히 구할 수 있다. 이 때 d 들은 0이 아니어야한다. <br> - 일반 행렬들도 row operation 을 통해 echelon form을 만들고 대각 원소들의 곱으로 간단히 determinant 를 구할 수 있다.|
|prop. 8| $ \mbox{when} A \mbox{ is singular}, \rightarrow \mbox{det} \, A = 0 $ <br> $ \mbox{when} A \mbox{ is invertible}, \rightarrow \mbox{det} \, A \ne 0 $ | - 행렬 A 가 singular matrix (특이 행렬, 역행렬이 존재하지 않음) determinant 는 0이다. <br> - 역행렬이 존재하면 determinant 는 0이 아니다. <br> - 반대로 determinant 를 통해 행렬의 역행렬 존재 여부를 판별할 수 있다.|
|prop. 9| $ \mbox{det} \, AB = (\mbox{det} \, A)(\mbox{det} \, B) $ <br> $ (\mbox{det} \, A^{-1}) = {1 \over (\mbox{det} \, A)} $ <br> $ \mbox{det} \, A^2 = (\mbox{det} A)^2 $ <br> $ \mbox{det} \, 2A = 2^n \mbox{det} \, A $ | - 두 행렬의 곱 AB 의 determinant 는 각 행렬의 determinant 곱과 같다. <br> - A 의 역행렬의 determinant 는 A 의 determinant 의 역수이다. <br> - A의 제곱의 determinant 는 A 의 determinant의 제곱과 같다. <br> - A 에 상수를 곱한 determinant 는 상수의 n 승을 A 의 determinant 에 곱한것과 같다.|
|prop. 10| $ \mbox{det} \, A^T = \mbox{det} \, A $ | - 행렬 A의 trnaspose의 determinant 는 원래 행렬의 determinant 와 같다. <br> - 즉 transpose를 해도 determinant는 변하지 않는다. |