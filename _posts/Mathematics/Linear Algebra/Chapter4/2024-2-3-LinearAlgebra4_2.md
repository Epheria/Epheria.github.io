---
title: Linear Algebra - 4.2 The Characteristic Equation
date: 2024-2-3 10:00:00 +/-TTTT
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
> * Characteristic Equation - 특성 방정식
{: .prompt-info}

<br>

## Characteristic Equation 에 대해

- **<span style="color:#179CFF">characteristic equation 은 eigenvalue 와 밀접한 관련이 있는 equation 이다.</span>**
- 주어진 $A$ 행렬의 eigenvalue 를 구할 때 $(A - \lambda I)\mathbf{x} = \mathbf{0}$ 를 이용한다.

$$ A = \begin{bmatrix} \phantom{-}2 & \phantom{-}3 \\\ \phantom{-}3 & -6 \end{bmatrix} $$

$$(A - \lambda I)\mathbf{x} = \mathbf{0}$$

$$ A - \lambda I = \begin{bmatrix} \phantom{-}2 & \phantom{-}3 \\\ \phantom{-}3 & -6 \end{bmatrix} - \begin{bmatrix} \lambda & 0 \\\ 0 & \lambda \end{bmatrix} = \begin{bmatrix} 2 - \lambda & 3 \\\ 3 & -6 - \lambda \end{bmatrix} $$

- $A$ 가 eigenvalue를 갖고 있으려면 $A\mathbf{x} = 0$ 에서 nontrivial solution 을 갖고 있어야 한다. 이는 $A$ 가 not invertible 을 의미하고 $\mbox{det}(A) = 0$ 이 되어야 한다.

$$ \mbox{det}(A - \lambda I) = \mbox{det} \begin{bmatrix} 2 - \lambda & 3 \\\ 3 & -6-\lambda \end{bmatrix} = 0 $$

$$ \mbox{det} \begin{bmatrix} a & b \\\ c & d \end{bmatrix} = ad - bc $$

$$ \mbox{det}(A - \lambda I) = (2 - \lambda)(-6 - \lambda) - (3)(3) = -12 + 6\lambda - 2\lambda + \lambda ^2 - 9 = \lambda ^ 2 + 4\lambda - 21 $$

$$ = (\lambda -3)(\lambda + 7) $$

- 이를 통해 2차방정식의 해를 구하면, eigenvalue 는 3, -7 인것을 확인할 수 있다.

<br>

> A scalar $\lambda$ is an eigenvalue of an $n \times n$ matrix $A$ if and only if $\lambda$ satisfies the characteristic equation   
>   
> $$ \mbox{det}(A - \lambda I) = 0 $$
{: .prompt-info}

- **<span style="color:#179CFF">characteristic equation 은 $ \mbox{det}(A - \lambda I) = 0 $ 을 의미한다.</span>**
- **<span style="color:#179CFF">$\lambda$ 가 characteristic equation 을 만족하면 $\lambda$ 는 행렬 $A$ 의 eigenvalue 이다.</span>**

<br>

- **예시 문제**
- 행렬 A 의 characteristic equation 을 찾아라.

$$ A = \begin{bmatrix} \phantom{-}5 & -2 & \phantom{-}6 & -1 \\\ \phantom{-}0 & \phantom{-}3 & -8 & \phantom{-}0 \\\ \phantom{-}0 & \phantom{-}0 & \phantom{-}5 & \phantom{-}4 \\\ \phantom{-}0 & \phantom{-}0 & \phantom{-}0 & \phantom{-}1 \end{bmatrix} $$

- $A$ 는 upper triangular matrix 이다.
- 따라서 diagonal term들이 eigenvalue 이다.
- $A$ 의 det 는 diagonal term 들의 곱이다.

$$ \mbox{det}(A - \lambda I) = \mbox{det} \begin{bmatrix} 5 - \lambda & -2 & 6 & -1 \\\ 0 & 3 - \lambda & -8 & 0 \\\ 0 & 0 & 5 - \lambda & 4 \\\ 0 & 0 & 0 & 1 - \lambda \end{bmatrix} $$
$$ = (5 - \lambda)(3 - \lambda)(5 - \lambda)(1 - \lambda) = (\lambda -5)^2 (\lambda - 3)(\lambda - 1) = 0 $$

$$ \lambda^4 - 14\lambda^3 + 68\lambda^2 - 130\lambda + 75 = 0 $$

- 여기서, eigenvalue 는 5, 3, 1 이 된다.
- **<span style="color:#179CFF">eigenvalue 5 는 multiplicity 2 를 갖는다고도 한다.</span>**

<br>
<br>

## Similarity - 유사도

- n차 방정식에서 eigenvalue를 찾는 것은 쉽지 않기 때문에 similarity 를 주로 이용한다.
- **<span style="color:#179CFF">$ A = PBP^{-1}$ 가 성립할 때, $A$ 는 $B$ 에 similar</span>** 하다고 표현한다.
- **<span style="color:#179CFF">similarity transformation 은 $ A = P^{-1}AP $ 로 변환되는 transformation 을 의미한다.</span>**

<br>

- eigenvalue 를 찾는 방법중 하나는 similar 한 matrix 를 찾아서 eigenvalue 를 찾는것이다.

> ***<span style="color:#179CFF">Theorem3. </span>***    
>   
> If $n \times n$ matrices $A$ and $B$ are similar, then they have the same characteristic polynimial and hence the same eigenvalues (with the samce multiplicities).
{: .prompt-tip}

- A 와 B가 similar 이고 동일한 characteristic polynomial 을 갖고 있으면 두 행렬은 동일한 eigenvalue 를 갖는다.
- eigenvalue 는 동일하지만, eigen vector 와 eigen space 는 보통 다르다.

<br>

- **증명**

$$ B = P^{-1}AP , $$

$$ B - \lambda I = P^{-1}AP - \lambda P^{-1} P = P^{-1}(AP - \lambda P) = P^[-1](A - \lambda I)P $$

$$ \mbox{det}(B - \lambda I) = \mbox{det} [P^{-1}(A - \lambda I)P] = \mbox{det}(P^{-1}) \cdot \mbox{det}(A - \lambda I) \cdot \mbox{det}(P) $$

$$ \mbox{det}(P^{-1}) \cdot \mbox{det}(P) = \mbox{det}(P^{-1}P) = \mbox{det} I = 1 $$

$$ \mbox{det}(B - \lambda I) = \mbox{det}(A - \lambda I) $$

<br>
<br>

## Numerical Notes

> There is **no analytic** formula or finite algorithm to solve the characteristic equation for $n \ge 5$ .   
> 특수해를 제외하고는 해가 명시적이지 않다. 즉 n 이 5 이상인 행렬 부터는 eigenvalue 를 찾기가 매우 힘들다
{: .prompt-warning}


> The characteristic polynomial is given in the following form    
>    
> $$ (\lambda - \lambda _1)(\lambda - \lambda _2) \dots (\lambda - \lambda _n) $$    
>     
> after computing the eigenvalues first    
>     
> eigenvalue 인 $\lambda _1 , \dots , \lambda _n$ 들을 먼저 구한 뒤, characteristic polynomial 을 구할 수 있다.
{: .prompt-warning}


> **QR algorithm** is commonly used for **<span style="color:#FF0000">estimating</span>** the eigenvalues.    
> 보통 eigenvalue 를 "추정" 하는데에는 QR 알고리즘을 사용한다. 추정한다는 뜻은 에러가 존재할 수도 있다는 뜻이다. 이것은 보통 수치해석적 방법론으로 풀며 공학적으로는 Power Method, Inverse Power Method 등을 사용한다.
{: .prompt-warning}

<br>

- QR 알고리즘 맛보기

> If $A = QR$ with $Q$ is invertible, then $A$ is similar to $A_1 = RQ$
{: .prompt-tip}

- A = QR 의 형태로 factorization 을 했을 때, Q 가 invertible 하다면 행렬 A 는 RQ 와 similar 하다.

<br>

- 증명하려면 우선, 다음과 같은 성질을 지녀야한다.

$$ R = Q^{-1}A  \quad \quad A_1 = Q^{-1}AQ $$

$$ Q^{-1} = Q^T \quad \quad R = \mbox{upper triangular matrix} $$

<br>

- 알고리즘을 반복 수행을 실행한다.

1. $A = Q_1R_1$ , $A_1 = R_1Q_1$ 여기서 $A_1$ 을 다시 QR factorization 을 실행
2. $A_1 = Q_2R_2$ , $A_2 = R_2Q_2$ ... 이것을 계속 반복수행을 한다.

<br>

- 충분히 많은 k 번을 수행했을 때
- $A_k$ converges to a triangular matrix (under certain conditions) - *Wilkinson Shift* 를 통해 항상 converge 하다는 것을 확인가능.
- 특정 조건하에 무한히 많은 k번의 QR 알고리즘을 수행한다면, $A_k$ 는 triangular matrix 에 converge 한다. (현실적으로 무한히 수행이 불가능하므로 충분한 특정 횟수만큼 k 번 실행)
- 위에서 구한 $A_1, \dots , A_k$ 는 similar 하기 때문에 eigenvalue 는 같다!
- 여기서 $A_k$ 는 triangular matrix 에 converge 하므로, $A_k$ 의 diagonal term 들은 eigenvalue 들이고, 이말인즉슨 similar한 $A$ 의 diagonal term 들 역시 eigenvalue 라는 말이다.

- 사실 QR algorithm 도 상당히 무겁고 오래걸린다. $n^3$ 정도..