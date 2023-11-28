---
title: Linear Algebra - Systems of Linear Equations
date: 2023-11-27 00:00:00 +/-TTTT
categories: [Mathematics, Linear Algebra]
tags: [Mathematics,  Linear Algebra]     # TAG names should always be lowercase

toc: true
toc_sticky: true
math: true

---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

A linear equations in the variables $ x_1, x_2, \dots, x_n $

<br>

$$ a_1x_1 + a_2x_2 + \dots + a_nx_n = b $$

<br>

- 우리는 위와 같은 식을 선형 방정식이라고 부른다.
- 변수 앞에 붙은 $ a_1, a_2, \dots, a_n $ 을 우리는 **Coefficients** 라고 부른다.
- 그리고 이 Coefficients 와 오른쪽 항의 $ b $ 에는 real or complex numbers 실수혹은 허수가 와도 상관없다.

<br>

- 문제. 그렇다면 다음 두 식은 Linear Equation 인가?   
   $$ 4x_1 - 5x_2 = x_1x_2 $$   
   $$ x_2 = \sqrt x_1 - 6 $$   
   정답 : 아니다.

<br>

## A system of linear equations 줄여서 linear system

- a collection of one or more linear equations
- 선형 방정식이 한 개여도 상관없음
- 선형 방정식의 예시   
   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 3x_2 = 3 $   
     
   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_01.png){: : width="300" .normal }


<br>

## Solution Set 이란
- The set of all possible solutions of the linear system.
- 모든 가능한 해의 집합을 solution set 이라고 한다.

- Two linear systems are called **<span style="color:#FFD412">equivalent</span>** if they have the same solution set.
- 두 선형 방정식이 **equivalent** 하다라는 뜻은 같은 solution set 을 지녔다는 것을 의미한다.

<br>

- **<span style="color:#FE6800">no solution</span>** 해가 없는 상태 -> **<span style="color:#FFD412">inconsistent</span>**      
   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 2x_2 = 3 $   
      
   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_02.png){: : width="300" .normal }


- **<span style="color:#FE6800">exactly one solution</span>** or **<span style="color:#FE6800">infinitely many solutions</span>** 해가 하나이거나 무한히 많을 때 -> **<span style="color:#FFD412">consistent</span>**    
   $ x_1 - 2x_2 = 1 $   
   $ -x_1 + 2x_2 = 1 $
   
   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_03.png){: : width="300" .normal }

<br>

## Matrix notation

$ x_1 - 2x_2 + x_3 = 0 $   
$       2x_2 - 8x_3 = 8 $   
$ -4x_1 + 5x_2 + 9x_3 = -9 $

- 이 수식들을 행렬로 표시하자면

$ \begin{pmatrix}
1 & -2 & 1 \\\\  
0 & 2 & -8 \\\\ 
-4 & 5 & 9 \\\\
\end{pmatrix} $

- 이렇게 표시되며, 이를 coefficient matrix (3x3) 이라고 부른다.

<br>

$ \begin{pmatrix}
1 & -2 & 1 & 0 \\\\  
0 & 2 & -8 & 8 \\\\ 
-4 & 5 & 9 & -9 \\\\
\end{pmatrix} $

- 오른쪽 항도 추가를 해서 표시하자면
- augmented matrix (3x4) 라고 부른다.

<br>

- 예제 1. Solve the following system of linear equations   
    ![Desktop View](/assets/img/post/mathematics/linearalgebra1_04.png){: : width="500" .normal }   
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_05.png){: : width="500" .normal }   
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_06.png){: : width="500" .normal }    

	- 우리는 augumented matrix 만을 가지고도 풀 수 있다!
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_07.png){: : width="500" .normal }

<br>

- 예제 2. Solve the following system of linear equations   
   	![Desktop View](/assets/img/post/mathematics/linearalgebra1_08.png){: : width="500" .normal }   
	- 행렬에서 좌측 상단을 pivot position 이라고 하는데, 이 pivot position 이 0이 되면 안되므로 interchange 를 실시해야한다.  
	- column 들 끼리는 자유롭게 interchange 할 수 있다.
	- 이 문제는 $ 0 = 5 / 2 $ 이기 때문에 incosistent 하므로 해가 없다.

<br>

## Elementary row operations

1.  **<span style="color:#FFD412">replacement</span>**
2.  **<span style="color:#FFD412">interchange</span>** 
3.  **<span style="color:#FFD412">scaling</span>** 

- 위 3가지 row operation 을 통해 최종 계산한 결과 값이랑 최초의 행렬이랑 같다. ->  **<span style="color:#FFD412">row equivalent</span>**  하다.

- We say two matrices are  **<span style="color:#FFD412">row equivalent</span>**  if there is a sequence of elementary row operations that transforms one matrix into the other.
- If the augmented matrices of two linear systems are row equivalent, then the tow systems have the same solution set. (두 augumented matrices 가 row equivalent 하다라는 말은 같은 solution set을 가지고 있다라는 뜻.)