---
title: Linear Algebra - 1.6 Linear Independence and Linear Dependence
date: 2024-1-12 12:42:00 +/-TTTT
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
> * linearly independent (선형 독립)
> * linearly dependent (선형 종속)
> * sets of one vector (하나의 벡터 집합)
> * sets of two vectors (두 벡터의 집합)
{: .prompt-info}

<br>

## Linearly Independent - 선형 독립

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_01.png){: : width="600" .normal }

<br>

- $ \mathbb{R}^{n} $ 공간에서 vector {$ v_1, \dots, v_p $}가 있을 때 만약 **<span style="color:#179CFF"> vector equation이 trivial solution 일 때 linearly Independent </span>** 하다고 한다.
- 즉, **<span style="color:#179CFF">trivial solution 이다 -> free variable 존재하지 않는다 -> linearly independent 하다.</span>**
> trivial solution만 존재한다는 것은 각 벡터들에 적절한 값을 곱해서 서로 같게 할 때, 결국 0을 곱해서 모두 0으로 만들어서 0 = 0 으로 만드는 방법 외에는 없다는 이야기이다.

<br>
<br>

## Linearly Dependent - 선형 종속

- 벡터 방정식 $c_1v_1 + \dots + c_pv_p = 0$ 에서 **<span style="color:#179CFF">weight $c_1, \dots, + c_p$ 중 하나라도 nonzero면 linearly dependent</span>**라고 한다.
- nontrivial solution을 갖고 있으면 최소 1개가 nonzero, 여러개가 nonzero 일 수 있으므로 linear combination으로 표현되지 않을 수 있다.


<br>
<br>

## Linearly Independent or Linearly Dependent 판단 예시

- trivial solution (free varialble 이 없음) 만 확인하면 linear independent 하므로 augmented matrix 로 변환 후 row reduction을 통해 검출해야한다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_02.png){: : width="600" .normal }

- **<span style="color:#179CFF">변수는 $x_1,x_2,x_3$ 3개인데, pivot position이 2개 이므로 free variable 이 존재함을 의미한다.</span>**
- 따라서, **<span style="color:#179CFF">free variable 이 존재 -> nontrivial solution -> linearly dependent </span>**하다.
- 마지막에 나오는 vector set을 보면, $ 10v_1 - 5v_2 + 5v_3 = 0 $ 임을 확인할 수 있는데 여기서 한 벡터를 우변으로 넘기면
- $ 10v_1 + 5v_3 = 5v_2 $ 어떤 2개의 벡터의 합으로 다른 벡터를 표현이 되는 것을 볼 수 있다. 우리는 이것을 linearly dependent 이라고 한다.

<br>
<br>

## Linear Independence of Matrix Columns - 행렬의 열의 선형 독립

<br>

> The columns of a matrix $\mathbf{A}$ are linearly independent if and only if the equation $ \mathbf{A}\mathsf{x} = 0 $ has $only$ the trivial solution.   
>     
> $ \mathbf{A}\mathsf{x} = 0 $ (homogeneous equation)가 trivial solution만을 갖고 있다면 A의 열들은 linearly independent 하다.
> 즉, A가 linearly independent 하면 $ \mathbf{A}\mathsf{x} = 0 $ 는 trivial solution만을 갖고 있다.
{: .prompt-warning}

<br>

- 예시 문제
- $ \mathbf{A}\mathsf{x} = 0 $ 에서 A는 coefficient matrix 를 의미한다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_03.png){: : width="600" .normal }

- **모든 row 에 pivot position이 존재한다.**
- free varialbe 이 없으므로 trivial solution 밖에 없음.
- trivial solution 이므로 linearly independent하다.

<br>
<br>

## Sets of One Vector - 하나의 벡터 집합

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_04.png){: : width="600" .normal }

- **<span style="color:#179CFF">집합이 하나의 벡터 v 만을 갖고 있고 v 가 0이 아닐 때 linearly independent 하다.</span>**
- **<span style="color:#179CFF">v = 0</span>**이면, $x_1v = x_10 = 0$ 에서 $x_1$은 임의의 값을 갖게 된다. 이는 $x_1$이 free variable 임을 의미한다. 따라서 nontrivial solution이 존재하게 되어 linearly dependent 하게 된다.
- **<span style="color:#179CFF">v \ne 0</span>**이면, $x_1v = 0$ 에서 0을 만족하려면 $x_1$은 무조건 0이 되어야한다. 따라서 이는 trivial solution 이므로 linearly independent 하다.

<br>
<br>

## Sets of Two Vectors - 두 개의 벡터 집합

<br>

> **A set of tow vectors {$v_1, v_2$} is linearly dependent if at least one of the vectors is a multiple of the other. The set is linearly independent if and only if neither of the vectors is a multiple of the other**    
{: .prompt-warning}

<br>

- 예시 문제

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_07.png){: : width="600" .normal }

   - a. 는 scalar multiplation 형태로 표현이 가능하므로 linearly dependent 하다.
   - b. 는 scalar multiplation 으로 표현을 못하므로 linearly independent 하다.

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_05.png){: : width="400" .normal }

- **두 vector의 집합에서 하나의 vector 가 다른 vector 의 scalar multiplation 형태로 표현되면 linearly dependent 하다.**

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_06.png){: : width="400" .normal }

- **두 vector의 집합에서 하나의 vector 가 다른 vector 의 scalar multiplation 형태로 표현되지 않는다면 linearly independent 하다.**

<br>
<br>


> ***<span style="color:#179CFF">Theorem7.  </span>*** **<span style="color:#179CFF">Characterization of Linearly Dependent Sets </span>**   
> An indexed set $ \mathbf{S} = $ { $ v_1, \dots, v_p $ } of two or more vectors is linearly dependent if and only if at leat one of the vectors in $\mathbf{S}$ is a linear combination of the others. In fact, if $\mathbf{S}$ is linearly dependent and $v_1 \ne \mathbf{0}$, then some $v_j$ (with $j$ > 1) is a linear combination of the preceding vectors $ v_1, \dots, v_{j-1} $.   
{: .prompt-tip}

- 집합 $ \mathbf{S} = $ { $ v_1, \dots, v_p $ } 의 **<span style="color:#179CFF">두 개 이상의 vector가 linearly dependent 하다면 $\mathbf{S}$ 에 있는 vector들 중 적어도 하나는 다른 vector들의 linear combination으로 표현할 수 있다.</span>**
- **<span style="color:#179CFF">즉, 최소한 하나의 vector가 다른 vector의 linear combination으로 표현가능하면 2개 이상의 vector는 linearly dependent 하다.</span>**

<br>

- $c_1v_1 + \dots + c_pv_p = 0$ 에서 두 개 이상의 vector가 linearly dependent라고 가정해보자.
- linearly dependent 하므로 하나의 벡터는 다른 벡터의 scalar multiplation 형태로 표현이 가능하다. 따라서 하나의 벡터는 다른 벡터의 linear combination 으로 표현될 수 있다.
- $v_1 = (-c_2 / c_1)v_2 + \dots + (-c_p / c_1)v_p$
- $-v_1 + c_2v_2 + \dots + c_pv_p = 0$ 에서 $c_2v_2 + \dots + c_pv_p = 0$ 이여도 $v_1$은 nonzero이다. $\because$ **linearly dependent**

<br>
<br>

## $ \mathbb{R}^{3} $ 공간에서의 {u,v,w}

- **<span style="color:#179CFF">u와 v가 linearly independent 할 때, set{u,v,w}가 linearly dependent 하다면 w is in Span{u.v}이다.</span>**
- w is in Span{u.v}는 **<span style="color:#179CFF">Span{u,v}에 w가 존재</span>**한다는 의미이다. 즉, **<span style="color:#179CFF">u와 v의 linear combination으로 w를 표현</span>**할 수 있다.

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_08.png){: : width="600" .normal }

- 일반화 하자면, S = {u,v,w}가 dependent 하면 $v_j$는 $v_{j-1}$의 linear combination으로 표현 가능하다 -> w는 u와 v의 linear combination으로 표현 가능하다 -> w is in Span{u,v}이다.

<br>
<br>

> ***<span style="color:#179CFF">Theorem8. </span>***    
> **If a set contains more vectors than there are entries in each vector. then the set is linearly dependent. That is, any set {$v_1, \dots, v_p$} in $ \mathbb{R}^{n} $ is linearly dependent if $ p > n$.**
{: .prompt-tip}

<br>

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_09.png){: : width="400" .normal }

<br>

- 예제, $ \begin{bmatrix} 2 \\\ 1 \end{bmatrix}, \begin{bmatrix} \phantom{-}4 \\\ -1 \end{bmatrix}, \begin{bmatrix} -2 \\\ \phantom{-}2 \end{bmatrix} $ 가 linearly dependent 한지 풀어보자.
- 위 set 은 n = 2, p = 3 이므로 1개 이상의 free variable을 갖게 된다. 따라서 nontrivial solution을 갖게 되므로 linearly dependent 하다.
- 정리하자면,**<span style="color:#179CFF"> free variable의 의미는 infinitely many solution을 의미하고 nontrivial solution을 갖게 되며 linearly dependent를 의미한다.</span>**

<br>
<br>

> ***<span style="color:#179CFF">Theorem9. </span>***    
> **If a set $\mathbf{S} = $ {$ v_1, \dots, v_p $} in $\mathbb{R}^{n}$ contains the zero vector, then the set is linearly dependent.**
{: .prompt-tip}

<br>

- zero vector 를 포함하는 set은 linearly dependent 하다.

$$ 1v_1 + 0v_2 + \dots + 0v_p = \mathbf{0} $$

- $v_1$을 zero vector로 가정했을 때 $v_2 ~ v/p$에 해당하는 coefficient가 0이어도 $v_1$에 해당하는 coefficient는 nonzero 가 될 수 있다.
- **<span style="color:#179CFF">$v_1$은 0이므로 $c_1$은 어떤 값을 곱해도 0이 성립하기 때문이다. nontrivial solution을 갖게되므로 linearly dependent를 의미한다.</span>**

<br>
<br>

## row reduction 없이 linearly dependent 판단 예제

   ![Desktop View](/assets/img/post/mathematics/linearalgebra6_10.png){: : width="600" .normal }

- a. linearly dependent하다. theorem 8 의 $ n < p $
- b. linearly dependent하다. 0 벡터가 존재하므로..
- c. linearly independent하다. scalar multiplation으로 표현되지 않고, $ n > p $ 이기 때문