---
title: Linear Algebra - 4.3 Diagonalization
date: 2024-2-8 10:00:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra, diagonalization]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리**   
> * Diagonalization - 대각화
{: .prompt-info}

<br>

## Diagonalization - 대각화

- 정사각행렬(square matrix) **<span style="color:#179CFF"> $A$ 가 대각 행렬(diagonal matrix)과 similar 하면 $A$ 를 diagonalizable 하다고 한다.</span>**
- 행렬의 대각화(matrix diagonalization)는 고유값(eigenvalue) 과 고유벡터(eigenvector) 를 활용하기 위한 하나의 방법론이다. **Eigendecomposition (고유값 분해)** 라고도 불린다. 또한 행렬의 대각화를 통해 LU Decomposition, QR Decomposition 과 같이 행렬을 고유값과 고유벡터로 구성된 부분 행렬들로 분해할 수 있으며 이는 어떤 반복적인 선형방정식을 풀 때 굉장히 유용한 특성을 갖고있다.
- $A = PDP^{-1}$ 일 때, $A$ 가 diagonalizable 이라고 한다.

<br>

- **예시 문제 1**
- diagonal matrix 의 제곱(square)은 diagonal term의 제곱이다.

$$ D = \begin{bmatrix} 5 & 0 \\\ 0 & 3 \end{bmatrix} $$

$$ D^2 =  \begin{bmatrix} 5 & 0 \\\ 0 & 3 \end{bmatrix}   \begin{bmatrix} 5 & 0 \\\ 0 & 3 \end{bmatrix}  =  \begin{bmatrix} 5^2 & 0 \\\ 0 & 3^2 \end{bmatrix} $$

$$ D^3 = DD^2 = \begin{bmatrix} 5 & 0 \\\ 0 & 3 \end{bmatrix}  \begin{bmatrix} 5^2 & 0 \\\ 0 & 3^2 \end{bmatrix} = \begin{bmatrix} 5^3 & 0 \\\ 0 & 3^3 \end{bmatrix} $$

$$ D^k = \begin{bmatrix} 5^k & 0 \\\ 0 & 3^k \end{bmatrix} \quad \mbox{for} \; k \ge 1 $$

<br>

- **예시 문제 2**
- 만약 $A$ 가 $D$ 와 similar 하다면, $A^k$ 를 쉽게 구할 수 있다.
- $A$ 가 diagonalizable 할 때, $A^k$ 를 구하라.

$$ A = \begin{bmatrix} \phantom{-}7 & \phantom{-}2 \\\ -4 & \phantom{-}1 \end{bmatrix} $$

$$ A = PDP^{-1} $$

<br>

$$ P = \begin{bmatrix} \phantom{-}1 & \phantom{-}1 \\\ -1 & -2 \end{bmatrix} \quad \mbox{and} \quad D = \begin{bmatrix} 5 & 0 \\\ 0 & 3 \end{bmatrix} $$

$$ P^{-1} = \begin{bmatrix} \phantom{-}2 & \phantom{-}1 \\\ -1 & -1 \end{bmatrix} $$

$$ A^2 = (PDP^{-1})(PDP^{-1}) = PD(PP^{-1})DP^{-1} = PDDP^{-1} = PD^2P^{-1}$$

- 여기서 **<span style="color:#179CFF"> $PP^{-1} = I$ </span>**

$$ PD^2P^{-1} = \begin{bmatrix} \phantom{-}1 & \phantom{-}1 \\\ -1 & -2 \end{bmatrix} \begin{bmatrix} 5^2 & 0 \\\ 0 & 3^2 \end{bmatrix} \begin{bmatrix} \phantom{-}2 & \phantom{-}1 \\\ -1 & -1 \end{bmatrix} $$

$$ A^3 = (PDP^{-1})A^2 = (PDP^{-1})PD^2P^{-1} = PDD^2P^{-1} = PD^3P^{-1}$$

$$ A^k = PD^kP^{-1} = \begin{bmatrix} \phantom{-}1 & \phantom{-}1 \\\ -1 & -2 \end{bmatrix} \begin{bmatrix} 5^k & 0 \\\ 0 & 3^k \end{bmatrix} \begin{bmatrix} \phantom{-}2 & \phantom{-}1 \\\ -1 & -1 \end{bmatrix} $$

$$ = \begin{bmatrix} 2 \cdot 5^k - 3^k & 5^k - 3^k \\\ 2 \cdot 3^k - 2 \cdot 5^k & 2 \cdot 3^k - 5^k \end{bmatrix} $$

<br>

> ***<span style="color:#179CFF">Theorem4. The Diagonalization Theorem </span>***    
>   
> An $n \times n$ matrix $A$ is diagonalizable if and only if $A$ has $n$ linearly independent eigenvectors.    
>     
> In fact, $A = PDP^{-1} ,$ with $D$ a diagonal matrix, if and only if the columns of $P$ are $n$ linearly independent eigenvectors of $A$ . In this case, the diagonal entries of $D$ are eigenvalues of $A$ that correspond, respectively, to the eigenvectors in $P$ .
{: .prompt-tip}

- $n \times n$ 행렬 $A$ 가 diagonalizable 하다면 **<span style="color:#179CFF"> $A$ 는 $n$ 개의 linearly independent eigenvector 를 갖고 있다.</span>**
- 즉, $D$ 가 diagonal matrix 이고 $A = PDP^{-1}$ 이면, $P$ 의 column은 $A$ 의 $n$ 개의 linearly independent eigenvector 로 이루어져 있다.
- 이 경우에 $D$ 의 diagonal entries 는 $P$ 를 구성하는 eigenvector 각각에 대한 $A$ 의 eigenvalues 이다.

<br>

- **증명**
- $P$ 가 $v_1, \dots, v_p$ 로 이루어진 $n \times n$ 행렬이고 $D$ 가 eigenvalues 를 diagonal entries 로 갖고 있는 diagonal matrix 이면 다음과 같다.

$$ AP = A[v_1 v_2 \dots v_n] = [Av_1 \quad Av_2 \quad \dots \quad Av_n] $$

<br>

$$ PD = P \begin{bmatrix} \lambda _1 & 0 & \dots & 0 \\\ 0 & \lambda _2 & \dots & 0 \\\ \vdots & \vdots & \ddots & \vdots \\\ 0 & 0 & \dots & \lambda _n \end{bmatrix} = [\lambda _1v_1 \quad \lambda _2v_2 \quad \dots \quad \lambda _nv_n ] $$

<br>

$$ AP = PD $$

$$ Av_1 = \lambda _1v_1 \; , \quad Av_2 = \lambda _2v_2 \; , \quad \dots \; , \quad Av_n = \lambda _nv_n  $$

- $P$ 가 invertible 이므로 $A = PDP^{-1}$ 가 성립하게 된다.
- 주의할점!! eigenvalues 는 distinct 일 필요가 없다. 즉, eigenvalue 가 중복이 되어도 상관없다!

> eigenvalues no need to be **distinct.**
{: .prompt-warning}

- 중복되더라도 n 개의 eigenvector 가 나올 수 있다.

<br>
<br>

## Diagonalizing Matrices - 행렬 대각화하기

- **<span style="color:#179CFF">행렬을 대각화(diagonalization) 하는 방법을 단계별로 알아보자. </span>**

<br>

> ***<span style="color:#179CFF"> Step1. Find the eigenvalues of $A$ . </span>***     
>     
> 첫 번째로, 행렬의 eigenvalues 를 찾아야 한다.    
> eigenvalues 는 characteristic equation 을 이용해서 찾을 수 있다.     
>     
> $ 0 = \mbox{det} (A - \lambda I) $
{: .prompt-tip}

<br>

> ***<span style="color:#179CFF"> Step2. Find three linearly independent eigenvectors of $A$ . </span>***     
>     
> 두 번째로, 행렬의 eigenvector 를 찾아야 한다.    
> 이는 $\lambda$ 에 대한 basis를 의미한다.    
> eigenvector 를 찾기 위해서 $(A - \lambda)x = 0$ 의 general solution 을 찾고, eigenvector 를 찾고, eigenspace 를 찾아서 basis를 찾는다.    
>      
> eigenvector 를 찾았으면 $n$ 개인지 확인해야한다.    
> eigenvector 가 $n$ 개 보다 작으면 diagonalization 이 불가능함!!
{: .prompt-tip}

<br>

> ***<span style="color:#179CFF"> Step3. Construct $P$ from the vectors in step2 . </span>***     
>     
> eigenvector 로 $P$ 를 구성한다.    
> $P$ 는 column 이 각각의 eigenvector 로 구성된 행렬이다.
{: .prompt-tip}

<br>


> ***<span style="color:#179CFF"> Step4. Construct $D$ from the corresponding eigenvalues. </span>***     
>     
> $D$ 는 diagonal entries 가 eigenvalues 인 diagonal matrix 이다.    
> 위에서 구한 eigenvalues 로 $D$ 행렬을 구성하면 된다.     
> 주의할 점으로는, $P$ 의 eigenvector 에 해당되는 eigenvalue 를 diagonal entry 로 두어야 한다.
{: .prompt-tip}

<br>

- **예시 문제1**
- 다음 행렬을 diagonalize 하시오.

$ A = \begin{bmatrix} \phantom{-}1 & \phantom{-}3 & \phantom{-}3 \\\ -3 & -5 & -3 \\\ \phantom{-}3 & \phantom{-}3 & \phantom{-}1 \end{bmatrix} $

- (1) $ \mbox{det} (A - \lambda I) = 0 $ 을 이용해서 $A$ 의 eigenvalue 를 찾는다.

$ 0 = \mbox{det} (A - \lambda I) = -\lambda ^3 - 3\lambda ^2 + 4 $

$ = -(\lambda -1)(\lambda + 2)^2 $

$ \mbox{eigenvaleus are} \; \lambda = 1 \; \mbox{and} \; \lambda = -2 $ .

<br>

- (2) $A$ 의 eigenspace 의 basis를 찾는다.
- eigenspace 의 basis 는 $(A - \lambda I)x = 0$ 의 general solution 을 구하여 찾을 수 있다.

$ \mbox{Basis for} \; \lambda = 1 : \quad \mathbf{v_1} = \begin{bmatrix} \phantom{-}1 \\\ -1 \\\ \phantom{-}1 \end{bmatrix} $

$ \mbox{Basis for} \; \lambda = -2 : \quad \mathbf{v_2} =  \begin{bmatrix} -1 \\\ \phantom{-}1 \\\ \phantom{-}0 \end{bmatrix} \quad \mbox{and} \quad \begin{bmatrix} -1 \\\ \phantom{-}0 \\\ \phantom{-}1 \end{bmatrix} $

- 각각의 vector가 independent set 인지 확인해야한다.
- 또한 vector 의 개수가 $n$ 인지 확인한다.
- 만약 $n$ 보다 적으면 diagonalization 이 불가능하다.

<br>

- (3) eigenvector 를 이용해서 행렬 $P$ 를 구성한다.

$$ P = [\mathbf{v_1} \quad \mathbf{v_2} \quad \mathbf{v_3}] = \begin{bmatrix} \phantom{-}1 & -1 & -1 \\\ -1 & \phantom{-}1 & \phantom{-}0 \\\ \phantom{-}1 & \phantom{-}0 & \phantom{-}1 \end{bmatrix} $$

<br>

- (4) eigenvalue 를 이용하여 행렬 $D$ 를 구성한다.
- 위에서 $\lambda = 1$ 이고 multiplicity 는 1 , $\lambda = -2 $ multiplicity 는 2 임을 찾았고, eigenvalue는 distinct 할 필요가 없으므로 $\mathbf{v_2}, \mathbf{v_3}$ 는 중복된 eigenvalue 를 갖고있으므로..

$$ D = \begin{bmatrix} \phantom{-}1 & \phantom{-}0 & \phantom{-}0 \\\ \phantom{-}0 & -2 & \phantom{-}0 \\\ \phantom{-}0 & \phantom{-}0 & -2 \end{bmatrix} $$

<br>
<br>

> ***<span style="color:#179CFF">Theorem5. </span>***    
>   
> An $n \times n$ matrix with $n$ distinct eigenvalues is diagonalizable.
{: .prompt-tip}

- $n$ 개의 eigenvalue 가 모두 distinct 이면, diagonalizable 하다.
- $n$ 개의 distinct eigenvalue를 갖고 있으면 그 matrix 는 $n$ 개의 independent eigenvector 를 갖는다는 의미이다. -> diagonalizable 하다는 뜻.

<br>

- **예시 문제**
- 주어진 행렬이 diagonalizable 한지 판단하시오.

$$ A = \begin{bmatrix} \phantom{-}5 & -8 & \phantom{-}1 \\\ \phantom{-}0 & \phantom{-}0 & \phantom{-}7 \\\ \phantom{-}0 & \phantom{-}0 & -2 \end{bmatrix} $$

- 행렬 $A$ 는 upper triangular matrix 이므로 diagonal term 들이 eigenvalue 이다. [이는 theorem1 에서 확인 해볼 수 있다.](https://epheria.github.io/posts/LinearAlgebra4_1/)
- 각각의 eigenvalue 가 각각 5, 0, -2 로 distinct 하므로 3개의 eigenvector 가 존재한다는 의미이다. 따라서 diagonalizable 하다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem6. </span>***    
>   
> Let $A$ be an $n \times n$ matrix whose distinct eigenvalues are $\lambda _1 , \dots , \lambda _p$ .     
>     
> a.  For $1 \le k \le p $ , the dimension of the eigenspace for $\lambda _k$ is less than or equal to the multiplicity of the eigenvalue $\lambda _k$ .    
>    
> b.  The matrix $A$ is diagonalizable if and only if the sum of the dimensions of the eigenspaces equals $n$ , and this happens if and only if $(i)$ the characteristic polynomial factors completely into linear factors and $(ii)$ the dimension of the eigenspace for each $\lambda _k$ equals the multiplicity of $\lambda _k$ .    
>     
> c.  If $A$ is diagonalizable and $\beta _k$ is a basis for the eigenspace corresponding to $\lambda _k$ for each $k$ , then the total collection of vectors in the sets $\beta _1, \dots , \beta _p$ forms an eigenvectors basis for $\mathbb{R}^n$ .
{: .prompt-tip}

- 주어진 $n \times n$ 행렬 $A$ 가 $p$ 개의 eigenvalues 를 지니고 있을 때의 정리이다.

- a.  eigenvalue 의 multiplicity 가 3이면 그에 해당하는 eigenspace 의 dim 은 3 이하이다.
- b.  eigenvalue 에 해당하는 eigenspace 의 dim 은 eigenvalue 의 multiplicity 이하이고, 별개의 eigenspace 의 dim 의 합이 $n$ 과 동일하면 diagonalizable 이다. 예를 들면, eigenvalue 의 multiplicity 가 1, 2 로 주어졌으면 각 eigenvalue 에 대한 eigenspace 의 dim 은 1, 2 이어야만 matrix 가 diagonalizable 하다는 뜻이다.

<br>

- **예시 문제**
- 다음 질문들이 trur false 인지 판단하시오.

<br>

- (1) $A$ is diagonalizable if $A$ has $n$ eigenvectors.
- 정답 : **false**. eigenvector 가 linearly independent 하다는 조건이 필요함.

<br>

- (2) If $A$ is diagonalizable, then $A$ has $n$ distinct eigenvaluse.
- 정답 : **false**. eigenvalue 는 중복될 수 있다. 중복된 수 만큼 multiplicity 로 표현됨.

<br>

- (3) If $AP = PD$ , with $D$ is diagonal, then the nonzero columns of $P$ must be eigenvectors of $A$ .
- 정답 : **true**.

<br>

- (4) If $A$ is invertible, then $A$ is diagonalizable.
- 정답 : **false**. invertible 의 의미는 $A$ 의 모든 column 이 linearly independent 를 의미한다. diagonalizable 은 $A$ 가 $n$ 개의 independent eigenvector 를 갖고 있다는 의미 이다.