---
title: Linear Algebra - 6.1 Diagonalization of Symmetric Matrices
date: 2024-2-28 10:00:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [mathematics, linear algebra, symmetric, orthogonally diagonalizable, spectral theorem, spectral decomposition, spectrum]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true
use_math: true
mermaid: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

> **용어 정리** 
> * multiplicity - 중근    
> * Symmetric - 대칭의     
> * Symmetric Matrix - 대칭 행렬     
> * Orthogonally Diagonalization - 직교 대각화     
> * Spectral Theorem - 스펙트럼 정리     
> * Spectral Decomposition - 스펙트럼 분해     
{: .prompt-info}

<br>

- Symmetrix Matrix 의 Orthogonally Diagonalization 은 선형대수학의 꽃인 SVD 를 유도하기 위해 필수적인 부분이다.

<br>

## Symmetrix Matrix - 대칭 행렬

- Symmetric Matrix 는 행렬 $A$ 가 Square Matrix (정사각 행렬) 이고, $A^T = A$ 를 만족하는 행렬이다.

> 1. $\quad A$ is Square Matrix     
> 2. $\quad A^T = A$
{: .prompt-tip}

- 위 두 가지 조건을 만족하면 Symmetric Matrix 이다.

<br>

- Symmetric Matrix 의 예시

$$ \mbox{Symmetric : } \quad \begin{bmatrix} \phantom{-}1 & \phantom{-}0 \\\ \phantom{-}0 & -3 \end{bmatrix} \; , \; \begin{bmatrix} \phantom{-}0 & -1 & \phantom{-}0 \\\ -1 & \phantom{-}5 & \phantom{-}8 \\\ \phantom{-}0 & \phantom{-}8 & -7 \end{bmatrix} \; , \; \begin{bmatrix} a & b & c \\\ b & d & e \\\ c & e & f \end{bmatrix} $$

<br>

- Symmetrix Matrix 아닌 경우

$$ \mbox{Nonsymmetric : } \quad \begin{bmatrix} \phantom{-}1 & -3 \\\ \phantom{-}3 & \phantom{-}0 \end{bmatrix} \; , \; \begin{bmatrix} \phantom{-}1 & -4 & \phantom{-}0 \\\ -6 & \phantom{-}1 & -4 \\\ \phantom{-}0 & -6 & \phantom{-}1 \end{bmatrix} \; , \; \begin{bmatrix} 5 & 4 & 3 & 2 \\\ 4 & 3 & 2 & 1 \\\ 3 & 2 & 1 & 0 \end{bmatrix} $$

<br>
<br>

---

## Diagonalization - 대각화 복습

- Symmetric Matrix 의 Diagonalization 을 살펴보기 전에 이전에 배웠던 [Diagonalization 을 복습](https://epheria.github.io/posts/LinearAlgebra4_3/)해보자.
- 만약 $A$ 가 diagonal matrix 와 similar 하면 $A$ 를 Diagonalizable 하다고 한다.
- 즉, $A = PDP^{-1}$ 이면, $A$ 는 Diagonalizable 이다.

<br>

> ***Diagonalization Example***     
>      
> $$ A = \begin{bmatrix} \phantom{-}6 & -2 & -1 \\\ -2 & \phantom{-}6 & -1 \\\ -1 & -1 & \phantom{-}5 \end{bmatrix} $$
{: .prompt-warning}

- 행렬 $A$ 는 Symmetric 행렬이다.
- 대각화(혹은 Eigendecomposition) 을 하기 위해 특성 방정식(Characteristic Equation) 으로 eigenvalue 와 eigenvector 를 구하자.


<details>
<summary> 문제 풀이 </summary>
<div markdown="1">

$$ \mbox{det} (A - \lambda I) = 0 $$

- 위 식을 이용하여 $A$ 의 eigenvalue 를 찾아보자. Determinant 의 경우 Cofactor 전개를 사용하여 풀어보자.

$$ A - \lambda I = \begin{bmatrix} \phantom{-}6 - \lambda & -2 & -1 \\\ -2 & \phantom{-}6 - \lambda & -1 \\\ -1 & -1 & \phantom{-}5 - \lambda \end{bmatrix} $$

- 여기서 $a_{31}, a_{32}, a{33}$ 을 기준으로 determinant 를 풀었다. Cofactor 전개의 부호를 주의하자.. 이거 때문에 계산 실수를 해서 몇번을 다시 풀었다..

$$ \mbox{det}(A - \lambda I ) = (-1)((-1)(-2) - (6 - \lambda)(-1)) - (-1)((6 - \lambda)(-1) - (-1)(-2)) + (5 - \lambda)((6 - \lambda)(6 - \lambda) - (-2)(-2)) $$

$$ = (\lambda - 8) + (\lambda - 8) + (5 - \lambda)(\lambda^2 - 12\lambda + 32) = (2\lambda - 16) - \lambda^3 + 17\lambda^2 - 92\lambda + 160 $$

- 최종적으로 다음 식이 나오고 인수분해를 하면

$$ 0 = -\lambda^3 + 17\lambda^2 - 90\lambda + 144 = -(\lambda - 3)(\lambda - 6)(\lambda - 8) $$

- 따라서, eigenvalue 는 다음과 같다 $\lambda = 3, 6, 8$

<br>

- $A - \lambda I = 0$ 삭애 도출한 eigenvalue 값들을 넣어 3개의 eigenvector 를 구해보자.

- (1) $\quad \lambda = 3$ 인 경우

$$ A - 3 I = \begin{bmatrix} \phantom{-}3 & -2 & -1 \\\ -2 & \phantom{-}3 & -1 \\\ -1 & -1 & \phantom{-}2 \end{bmatrix}  $$

- augmented matrix 로 만들고 row reduction 을 해보면

$$ \begin{bmatrix} \phantom{-}3 & -2 & -1 & 0 \\\ -2 & \phantom{-}3 & -1 & 0 \\\ -1 & -1 & \phantom{-}2 & 0 \end{bmatrix} \sim \begin{bmatrix} -1 & 0 & 1 & 0 \\\ 0 & 1 & -1 & 0 \\\ 0 & 0 & 0 & 0 \end{bmatrix} $$

- $x_3$ 는 free varialbe 이고 $x_1 = x_3$ , $x_2 = x_3$ 이므로 다음과 같이 general solution 을 도출 할 수 있다.

$$ x_3 \begin{bmatrix} 1 \\\ 1 \\\ 1 \end{bmatrix} $$

<br>

- (2) $\quad \lambda = 6$ 인 경우

$$ A - 6 I = \begin{bmatrix} \phantom{-}0 & -2 & -1 \\\ -2 & \phantom{-}0 & -1 \\\ -1 & -1 & -1 \end{bmatrix} $$

$$ \begin{bmatrix} \phantom{-}0 & -2 & -1 & 0 \\\ -2 & \phantom{-}0 & -1 & 0 \\\ -1 & -1 & -1 & 0 \end{bmatrix} \sim \begin{bmatrix} -1 & 1 & 0 & 0 \\\ 0 & 2 & 1 & 0 \\\ 0 & 0 & 0 & 0 \end{bmatrix} $$

- $x_3$ 는 free varialbe 이고 $x_2 = - 1/2 x_3$ , $x_1 = x_2 = - 1/2 x_3 $ 이므로 다음과 같이 general solution 을 도출 할 수 있다. 분수가 있어 2를 scale 해주었다.

$$ x_3 \begin{bmatrix} - 1 \\\ - 1 \\\ 2 \end{bmatrix} $$

<br>

- (3) $\quad \lambda = 8$ 인 경우

$$ A - 8 I = \begin{bmatrix} -2 & -2 & -1 \\\ -2 & -2 & -1 \\\ -1 & -1 & -3 \end{bmatrix} $$

$$  \begin{bmatrix} -2 & -2 & -1 & 0 \\\ -2 & -2 & -1 & 0 \\\ -1 & -1 & -3 & 0 \end{bmatrix} \sim \begin{bmatrix} -2 & -2 & -1 & 0 \\\ 0 & 0 & 0 & 0 \\\ 0 & 0 & 1 & 0 \end{bmatrix} $$

- 여기서 $x_2$ 는 free variable 이고 $x_3 = 0$ , $x_1 = -x_2$ 이므로 다음과 같이 general solution 을 도출 할 수 있다.

$$ x_2 \begin{bmatrix} -1 \\\ 1 \\\ 0 \end{bmatrix} $$

<br>

- 최종적으로 eigenvector 는 다음과 같다.

$$ \mathbf{v}_1 = \begin{bmatrix} 1 \\\ 1 \\\ 1 \end{bmatrix} \; , \; \mathbf{v}_2 = \begin{bmatrix} -1 \\\ -1 \\\ 2 \end{bmatrix} \; , \; \mathbf{v}_3 = \begin{bmatrix} -1 \\\ 1 \\\ 0 \end{bmatrix} $$

- 위 3개의 eigenvector 를 서로서로 내적해보면 0이 되므로 orthgonal 하고 linearly independent 하므로 normalize 하여 orthonormal vector 로 표현이 가능하다.

$$ \mathbf{u}_1 = { 1 \over \lVert \mathbf{v}_1 \rVert } \mathbf{v}_1 = { 1 \over \sqrt{3} } \begin{bmatrix} 1 \\\ 1 \\\ 1 \end{bmatrix} = \begin{bmatrix} 1/\sqrt{3} \\\ 1/\sqrt{3} \\\ 1/\sqrt{3} \end{bmatrix} $$

$$ \mathbf{u}_2 = { 1 \over \lVert \mathbf{v}_2 \rVert } \mathbf{v}_1 = { 1 \over \sqrt{6} } \begin{bmatrix} -1 \\\ -1 \\\ 2 \end{bmatrix} = \begin{bmatrix} -1/\sqrt{6} \\\ -1/\sqrt{6} \\\ 2/\sqrt{6} \end{bmatrix} $$

$$ \mathbf{u}_3 = { 1 \over \lVert \mathbf{v}_3 \rVert } \mathbf{v}_1 = { 1 \over \sqrt{2} } \begin{bmatrix} -1 \\\ 1 \\\ 0 \end{bmatrix} = \begin{bmatrix} -1/\sqrt{2} \\\ 1/\sqrt{2} \\\ 0 \end{bmatrix} $$

- $P$ 는 eigenvector 로 이루어진 행렬이고, $D$ 는 eigenvalue 의 diagonal 행렬이다.

$$ P = \begin{bmatrix} 1/\sqrt{3} & -1/\sqrt{6} & -1/\sqrt{2} \\\ 1/\sqrt{3} & -1/\sqrt{6} & 1/\sqrt{2} \\\ 1/\sqrt{3} & 2/\sqrt{6} & 0 \end{bmatrix} \; , \; D = \begin{bmatrix} 3 & 0 & 0 \\\ 0 & 6 & 0 \\\ 0 & 0 & 8 \end{bmatrix} $$

- 여기서 $P$ 의 column 들이 orthonormal vector 로 이루어져 있기 때문에, $P^T = P^{-1}$ 라는 성질을 만족한다.
- 따라서 $A$ 행렬을 대각화하면 $A = PDP^{-1} = PDP^T$ 로 나타낼 수 있다.

</div>
</details>

---

> ***<span style="color:#179CFF">Theorem1. </span>***    
>    
> If $A$ is symmetric, then any two eigenvectors from different eigenspaces are orthogonal.
{: .prompt-tip}

- $A$ 행렬이 symmetric 이면 서로 다른 eigenspace 에 있는 두 eigenvector 는 orthogonal 하다.

- **증명**
- $\mathbf{v}_1, \mathbf{v}_2$ 가 서로 다른 eigenvalue $\lambda _1, \lambda _2$ 에 해당하는 eigenvector 일 때 $\mathbf{v}_1 \cdot \mathbf{v}_2 = 0$ 임을 증명해보자.

- [eigenvector 의 성질](https://epheria.github.io/posts/LinearAlgebra4_1/) 에서 $A\mathbf{x} = \lambda \mathbf{x}$ 임을 확인할 수 있다. 여기서 $\lambda$ 는 스칼라값.

$$ \lambda _1 \mathbf{v}_1 \cdot \mathbf{v}_2 = (\lambda _1 \mathbf{v}_1)^T \mathbf{v}_2 = (A \mathbf{v}_1)^T \mathbf{v}_2 $$

- $A$ 행렬은 symmetric 이므로 $A^T = T$ 이다.

$$ = (\mathbf{v}^T_1 A^T)\mathbf{v}_2 = \mathbf{v}^T (A \mathbf{v}_2) $$

$$ = \mathbf{v}_1^T (\lambda _2 \mathbf{v}_2) $$

$$ = \lambda _2 \mathbf{v}_1^T \mathbf{v}_2 = \lambda _2 \mathbf{v}_1 \cdot \mathbf{v}_2 $$

- 위 내용을 정리하자면

$$ \lambda _1 \mathbf{v}_1 \cdot \mathbf{v}_2  = \lambda _2 \mathbf{v}_1 \cdot \mathbf{v}_2   $$

$$ (\lambda _1 - \lambda _2)(\mathbf{v}_1 \cdot \mathbf{v}_2) = 0 $$

- 여기서 $\lambda _1 - \lambda _2 \ne 0$ 혹은 $\lambda _1 \ne \lambda _2$ 가 되는데
- 두 eigenvalue 가 서로 다른 eigenspace 애 존재하기 때문에 서로 다른 값이어야 한다. (multiplicity 가 될 수 없다.)
- 따라서 eigenvector 의 내적인 $\mathbf{v}_1 \cdot \mathbf{v}_2  = 0$ 이 될 수밖에 없다.

- 이러한 symmetric matrix 의 성질 때문에 symmetric matrix 의 diagonalization 을 **orthogonally diagonalizable** 하다고 한다.

<br>
<br>

## Orthogonally Diagonalizable - 직교 대각화

> A matrix $A$ is said to be **orthogonally diagonalizable** if there an orthogonal matrix $P$ with $P^{-1} = P^T$ and a diagonal matrix $D$ such that     
>    
> $$ A = PDP^T = PDP^{-1} $$
{: .prompt-info}

- symmetric matrix 가 orthogonally diagonalizable 하다는 것은 매우 중요한 성질이다.
- symmetric matrix 는 $A^T = A$ 를 만족한다. 실제로 만족하는지 증명해보자.
- **증명**

$$ A^T = (PDP^T)^T = P^{TT}D^TP^T = PDP^T = A $$

- 따라서 $A$ 는 symmetric 이다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem2. </span>***    
>    
> An $n \times n$ matrix $A$ is orthogonally diagonalizable if and only if $A$ is a symmetric matrix.
{: .prompt-tip}

- 행렬 $A$ 에 대해 orthogonally diagonalizable 과 symmetric matrix 는 서로 동치이다.

<br>

> ***Example 1***     
>     
> Orthogonally diagonalize the matrix $A = \begin{bmatrix} 3 & -2 & 4 \\\ -2 & 6 & 2 \\\ 4 & 2 & 3 \end{bmatrix} $
{: .prompt-warning}

- Characteristic Equation (특성 방정식)으로 eigenvalue 를 구한다.

$$ A - \lambda I = \begin{bmatrix} 3 - \lambda & -2 & 4 \\\ -2 & 6 - \lambda & 2 \\\ 4 & 2 & 3 - \lambda \end{bmatrix} $$

$$ \mbox{det}( A - \lambda I) = (3 - \lambda)((6 - \lambda)(3 - \lambda) - 4) - (-2)((3 - \lambda)(-2) - 8) + (4)(-4 - (6 - \lambda)(4)) = 0 $$

$$ -\lambda ^3 + 12 \lambda ^2 - 21 \lambda - 98 = -(\lambda - 7)^2 (\lambda + 2) = 0 $$

- $\lambda = 7$ with multiplicity = 2 , $\lambda = -2$ with multiplicity = 1 가 도출되었다.
- $\lambda = 7$ 인 경우

$$ A - 7I =  \begin{bmatrix} -4 & -2 & 4 \\\ -2 & -1 & 2 \\\ 4 & 2 & -4 \end{bmatrix} = 0 $$

$$ \begin{bmatrix} -4 & -2 & 4 & 0 \\\ -2 & -1 & 2 & 0 \\\ 4 & 2 & -4 & 0 \end{bmatrix} \sim \begin{bmatrix} -2 & -1 & 2 & 0 \\\ 0 & 0 & 0 & 0 \\\ 0 & 0 & 0 & 0 \end{bmatrix} $$

$$ \mathbf{x} = x_2 \begin{bmatrix} -1/2 \\\ 1 \\\ 0 \end{bmatrix} + x_3 \begin{bmatrix} 1 \\\ 0 \\\ 1 \end{bmatrix} $$

$$ \mathbf{v}_1 = \begin{bmatrix} 1 \\\ 0 \\\ 1 \end{bmatrix} \; , \; \mathbf{v}_2 = \begin{bmatrix} -1/2 \\\ 1 \\\ 0 \end{bmatrix} $$

<br>

- $\lambda = -2$ 인 경우

$$ A + 2I = \begin{bmatrix} 5 & -2 & 4 \\\ -2 & 8 & 2 \\\ 4 & 2 & 5 \end{bmatrix} = 0 $$

$$ \begin{bmatrix} 5 & -2 & 4 & 0 \\\ -2 & 8 & 2 & 0 \\\ 4 & 2 & 5 & 0 \end{bmatrix} \sim \begin{bmatrix} -1 & 4 & 1 & 0 \\\ 0 & 2 & 1 & 0 \\\ 0 & 0 & 0 & 0 \end{bmatrix} $$

$$ \mathbf{x} = x_3 \begin{bmatrix} -1 \\\ -1/2 \\\ 1 \end{bmatrix} $$

$$ \mathbf{v}_3 = \begin{bmatrix} -1 \\\ -1/2 \\\ 1 \end{bmatrix} $$

<br>

- 여기서 $\mathbf{v}_1 , \mathbf{v}_2$ 는 같은 eigenspace 에 있기 때문에 서로 orthogonal 하지 않다. 그리고 eigenspace 의 dimension 은 2 이므로 $\mathbf{v}_1 , \mathbf{v}_2$ 는 eigenspace 를 span 하는 basis 이므로 linearly independent 하다. 따라서 Gram-Schmidt 과정으로 두 eigenvector 를 orthogonal 하도록 만들어주자.

$$ \mathbf{z}_1 = \mathbf{v}_1 = \begin{bmatrix} 1 \\\ 0 \\\ 1 \end{bmatrix} $$

$$ \mathbf{z}_2 = \mathbf{v}_2 - { \mathbf{v}_2 \cdot \mathbf{v}_1 \over \mathbf{v}_1 \cdot \mathbf{v}_1} \mathbf{v}1 =  \begin{bmatrix} -1/2 \\\ 1 \\\ 0  \end{bmatrix} - { -1/2 \over 5/4 } \begin{bmatrix} 1 \\\ 0 \\\ 1 \end{bmatrix} = \begin{bmatrix} -1/4 \\\ 1 \\\ 1/4 \end{bmatrix} $$

<br>

- 각각의 eigenvector 들을 normalize 시켜서 orthonormal basis 로 변환해보자.

$$ \mathbf{u}_1 = { 1 \over \lVert \mathbf{z}_1 \rVert } \mathbf{z}_1 = \begin{bmatrix} 1/\sqrt{2} \\\ 0 \\\ 1/\sqrt{2} \end{bmatrix} $$ 

$$ \mathbf{u}_2 = { 1 \over \lVert \mathbf{z}_2 \rVert } \mathbf{z}_2 = \begin{bmatrix} -1 / \sqrt{18} \\\ 4 / \sqrt{18} \\\ 1 / \sqrt{18} \end{bmatrix} $$

<br>

$$ 2\mathbf{v}_3 = \begin{bmatrix} -2 \\\ -1 \\\ 2 \end{bmatrix} $$

$$ \mathbf{u}_3 = { 1 \over \lVert 2\mathbf{v}_3 \rVert } 2\mathbf{v}_3 = {1 \over 3} \begin{bmatrix} -2 \\\ -1 \\\ 2 \end{bmatrix} = \begin{bmatrix} -2 / 3 \\\ -1 /3 \\\ 2 / 3 \end{bmatrix} $$

<br>

- orthonormal vector 들로 $P$ 를 만들어준다.

$$ P = [\mathbf{u}_1 \quad \mathbf{u}_2 \quad \mathbf{u}_3] = \begin{bmatrix} 1 / \sqrt{2} & -1 / \sqrt{18} & -2 /3 \\\ 0 & 4 / \sqrt{18} & -1 / 3 \\\ 1 / \sqrt{2} & 1 / \sqrt{18} & 2 / 3 \end{bmatrix} \; , \quad D = \begin{bmatrix} 7 & 0 & 0 \\\ 0 & 7 & 0 \\\ 0 & 0 & -2 \end{bmatrix} $$

<br>

- 다음은 Orthogonally Diagonalizataion 을 단계화 해서 살펴보자.

> ***Steps : Orthogonally Diagonalizataion***      
>      
> 1. Check if $A^T = A$     
>    
> 2. Calculate **eigenspaces** for distinct eigenvalues     
>     
> 3. Find orthogonal basis for each eigenspace by the Gram-Schmidt process     
>      
> 4. Obtain orthonormal basis by normalization      
>     
> 5. Construct $P$ and $D$
{: .prompt-warning}

- $A^T = A$ 인 symmetric matrix 인지 확인하고
- characteristic equation 을 사용하여 eigenvalue 들을 구한 뒤 $A - \lambda I = 0 $ 을 통해 각 eigenspace 에 해당하는 eigenvector 들을 구하고 
- Gram-Schmidt process 를 통해 각 eigenspace 내부 벡터들 간의 orthogonal basis 를 구하고
- orthogonal basis 들을 orthonormal basis 로 normalize 한 뒤
- $P$ 와 $D$ 행렬을 구성하면 된다.

<br>
<br>

## Spectral Theorem - 스펙트럼 정리

> ***<span style="color:#179CFF">Theorem3. The Spectral Theorem for Symmetric Matrices </span>***    
>    
> An $n \times n$ symmetric matrix $A$ has the following properties:     
>     
> a.  $A$ has $n$ real eigenvalues, counting multiplicities.     
> b.  The dimension of the eigenspace for each eigenvalue $\lambda$ equals the multiplicity of $\lambda$ as a root of the characterisitic equation.     
> c.  The eigenspaces are mutually orthogonal, in the sense that eigenvectors corresponding to different eigenvalues are orthogonal.     
> d.  $A$ is orthogonally diagonalizable.
{: .prompt-tip}

- 행렬 $A$ 의 eigenvalue set 을 $A$ 의 **spectrum** 이라고 부른다. 그리고 $A$ 가 symmetric matrix 일 때, 다음 성질을 따른다.

- a. $A$ 가 $n$ 개의 eigenvalue 를 갖고 있으면 multiplicity 를 계산한다. 
- b. 각 eigenvalue 에 해당하는 eigenspace 의 dimension 은 eigenvalue 의 multiplicity 와 동일하다.
- c. eigenspace 는 서로 orthogonal 하다. 서로 다른 eigenvalue 에 해당하는 eigenvector 역시 orthogonal 하다.
- d. $A$ 는 orthogonally diagonalizable 하다.

<br>
<br>

> ***Example True or False***     
>      
>      
> 1. An $n \times n$ matrix that is orthogonally diagonalizable must be symmetric.     
> 정답 : **true**     
> 풀이 : symmetric matrix 와 orthogonally diagonalizable 은 서로 동치관계 이기 때문에 참이다.      
>     
>      
> 2. If $A^T = A$ and if vectors $\mathbf{u}$ and $\mathbf{v}$ satisfy $A\mathbf{u} = 3\mathbf{u}$ and $A\mathbf{v} = 4\mathbf{v}$ , then $\mathbf{u} \cdot \mathbf{v} = 0$ .     
> 정답 : **true**     
> 풀이 : $A^T = A$ 는 행렬 $A$ 가 symmetric 하다는 뜻이고 symmetric matrix 는 orthogonally diagonalizable 하다라는 뜻이고 $\mathbf{u}$ and $\mathbf{v}$ 두 벡터는 $A$ 의 eigenvector 를 의미하므로 두 eigenvector 는 orthogonal 하기 때문에 참이다.     
>     
>      
> 3. An $n \times n$ symmetric matrix has $n$ distinct real eigenvalues.     
> 정답 : **false**     
> 풀이 : symmetric matrix 의 eigenvalue 가 꼭 distinct 일 필요는 없다. eigenvalue 가 같으면 multiplicity 로 계산할 수 있고 동일한 eigenspace 에 linearly independent 한 eigenvector 로 존재하게 된다. 이를 orthogonally diagonalizable 하려면 Gram-Schmidt process 를 사용하여 직교하게 만들 수 있기 때문이다. 따라서 거짓      
>     
>      
> 4. Every symmetric matrix is orthogonally diagonalizable.      
> 정답 : **true**     
> 풀이 : 1번과 비슷한 내용, 동치 관계에 있기 때문에 참이다.     
>     
>      
> 5. If $B = PDP^T$ , where $P^T = P^{-1}$ and $D$ is diagonal matrix, then $B$ is a symmetric matrix.     
> 정답 : **true**     
> 풀이 : $P^T = P^{-1}$ 라는 말은 symmetric matrix의 orthogonally diagonalizable 의 성질이므로 $B = PDP^T = PDP^{-1}$ 이므로 $B$ 는 symmetric matrix 이다. 
>      
>      
> 6. An orthogonal matrix is orthogonally diagonalizable.     
> 정답 : **false**      
> 풀이 : orthogonal matrix가 symmetric 한 경우는 있겠지만, 모든 orthogonal matrix 가 symmetric 하지 않다.      
>     
>      
> 7. The dimension of an eigenspace of a symmetric matrix equals the multiplicity of the corresponding eigenvalue.     
> 정답 : **true**     
> 풀이 : 동일한 eigenvalue 는 multiplicity 로 계산하고 이는 symmetric matrix 의 eigenspace 의 dimesnion 을 결정하므로 참이다.
{: .prompt-warning} 

<br>
<br>

## Spectral Decomposition - 스펙트럼 분해

- Spectral Decomposition 은 행렬 $A$ 를 **eigenvalue(spectrum)** 으로 표현되는 조각들로 분해 하는 것이다.

- 행렬 $A$ 가 orthogonally diagonalizable 하다고 가정하고 다음과 같이 표현할 수 있다.

$$ A = PDP^T = [\mathbf{u}_1 \quad \dots \quad \mathbf{u}_n] \begin{bmatrix} \lambda _1 & & 0 \\\ & \ddots & \\\ 0 & & \lambda _n \end{bmatrix} \begin{bmatrix} \mathbf{u}_1^T \\\ \vdots \\\ \mathbf{u}_n^T \end{bmatrix} $$

- 여기서 $D$ 는 diagonal matrix 이므로 $PD$ 를 계산해보면 다음과 같다.

$$ = \begin{bmatrix} \lambda _1 \mathbf{u}_1 & \dots & \lambda _n \mathbf{u}_n \end{bmatrix} \begin{bmatrix} \mathbf{u}_1^T \\\ \vdots \\\ \mathbf{u}_n^T \end{bmatrix} $$

- 위 수식을 matrix multiplication 의 scalar ($\lambda$) 성질에 의해 다음과 같이 표현할 수 있다.

> $$ A = \lambda _1 \mathbf{u}_1 \mathbf{u}_1^T + \lambda _2 \mathbf{u}_2 \mathbf{u}_2^T + \dots + \lambda _n \mathbf{u}_n \mathbf{u}_n^T $$
{: .prompt-warning} 

- 위와 같이 표현한 것을 $A 의 spectral decomposition 이라고 부른다.ㄴ
- 여기서 $mathbf{u}_1 \mathbf{u}_1^T$ 는 행렬임을 주의하자. 그렇다면 각 요소 $mathbf{u}_k \mathbf{u}_k^T$ 는 rank 가 1인 $n \times n$ 행렬이다.
- 여기서 rank = 1 은 column space 의 dimension 이 1임을 의미한다.

- $\mathbf{u}_k^T$ 를 스칼라 곱을 해주면 다음과 같이 표현된다.

$$ \mathbf{u}_k \begin{bmatrix} u_{1k} & \dots & u_{nk} \end{bmatrix} =  [u_{1k} \mathbf{u}_k \quad \dots \quad u_{nk} \mathbf{u}_k] $$

- 전부 linearly dependent 하고 모든 column 들이 $\mathbf{u}_k$ 에 의해서 표현이 된다. 따라서 column space 의 dimension 이 1이된다.

- 그리고 $\mathbf{u}_k \mathbf{u}_k^T \mathbf{x}$ 는 projection matrix 이다. orhtogonal projection $\mathbf{x}$ 를 Span{$\mathbf{u}_k$} subspace 에 projection 한 것이다.

<br>
<br>

> ***Example 1***     
>      
> Construct a spectral decomposition of the matrix $A$ that has the orthogonal diagonalization      
>     
> $$ A = \begin{bmatrix} 5/2 & 1/2 \\\ 1/2 & 5/2 \end{bmatrix} $$
{: .prompt-warning} 

- 행렬 $A$ 를 orthogonally diagonalization 하고 $PDP^T$ 으로 spectral decomposition 한다.

$$ A = \begin{bmatrix} 1 / \sqrt{2} & -1 / \sqrt{2} \\\ 1 / \sqrt{2} & 1 / \sqrt{2} \end{bmatrix} \begin{bmatrix} 3 & 0 \\\ 0 & 2 \end{bmatrix} \begin{bmatrix} 1 / \sqrt{2} & 1 / \sqrt{2} \\\ -1 / \sqrt{2} & 1 / \sqrt{2} \end{bmatrix} $$

- $P$ 행렬을 $\mathbf{u}_1, \mathbf{u}_2$ 으로 표기하면

$$ \mathbf{u}_1 = \begin{bmatrix} 1 / \sqrt{2} \\\ 1 / \sqrt{2} \end{bmatrix} \quad \mathbf{u}_2 = \begin{bmatrix} -1 / \sqrt{2} \\\ 1 / \sqrt{2} \end{bmatrix} $$

$$ A = 3 \mathbf{u}_1 \mathbf{u}_1^T + 2 \mathbf{u}_2 \mathbf{u}_2^T $$

- 이렇게 스펙트럼 분해를 할 수 있다.

- 위 식이 진짜 만족하는지 확인해보면

$$ A = 3 \begin{bmatrix} 1 / \sqrt{2} \\\ 1 / \sqrt{2} \end{bmatrix} \begin{bmatrix} 1 / \sqrt{2} & 1 / \sqrt{2} \end{bmatrix}  + 2 \begin{bmatrix} -1 / \sqrt{2} \\\ 1 / \sqrt{2} \end{bmatrix} \begin{bmatrix} -1 / \sqrt{2} & 1 / \sqrt{2} \end{bmatrix} $$

<br>

> ***Example 2***     
>      
> Show that if $A$ is a symmetric matrix, then $A^2$ is symmetric.      
{: .prompt-warning} 

- $A$ 가 symmetric 하면 $A^2$ 도 symmetric 한지 확인해보자. symmetric matrix 의 성질인 $A = A^T$ 이므로

$$ (A^2)^T = (AA)^T = A^TA^T = AA = A^2 $$

<br>

> ***Example 3***     
>      
> Show that if $A$ is orthogonally diagonalizable , then so is $A^2$ .       
{: .prompt-warning} 

- $A$ 가 orthogonally diagonalizable 하다면 symmetric matrix 임과 동치이다.
- 위의 예제에서 살펴봤듯이 $A$ 가 symmetric 이면 $A^2$ 역시 symmetric 이므로
- $A$ 가 orhtogonally diagonalizable 이면 $A^2$ 도 orthogonally diagonalizable 이다.

<br>
