---
title: 1.1 Systems of Linear Equations
date: 2023-11-27 00:00:00 +/-TTTT
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
> * 선형 방정식 - linear equation   
> * 선형 방정식 계 - system of linear equation   
> * 해의 집합 - solution set   
> * consistent - exactly one solution, infinitely many solutions   
> * inconsistent - no solution   
> * 행령 표기법 - matrix notation   
> * 소거법 - elimination   
> * 행 연산 - row operation (replacement, interchange, scaling)   
> * 상등 - equivalent   
> * 행 상등 - row equivalent   
{: .prompt-info}


<br>

## 선형 방정식 - linear equation

$ x_1,...,x_n$ 변수로 이루어진 선형 방정식은 다음과 같이 쓸 수 있다.


A linear equations in the variables $ x_1, x_2, \dots, x_n $

<br>

$$ a_1x_1 + a_2x_2 + \dots + a_nx_n = b $$

<br>

- 우리는 위와 같은 식을 선형 방정식이라고 부른다.
- 변수 앞에 붙은 $ a_1, a_2, \dots, a_n $ 을 우리는 **Coefficients** 라고 부른다.
- 여기서 $ b $ 와 $ a_1, \dots, a_n $ 은 실수(real number) 혹은 허수(complex numbers)인 상수(coefficient)이다.

<br>

- 문제. 그렇다면 다음 두 식은 Linear Equation 인가?   
   $$ 4x_1 - 5x_2 = x_1x_2 $$   
   $$ x_2 = \sqrt x_1 - 6 $$   
   정답 : 아니다.

<br>
<br>

## 선형 방정식 계 - A system of linear equations (줄여서 linear system)

- a collection of one or more linear equations (같은 변수들을 포함한 선형 방정식이 1개 또는 그 이상의 집합을 의미)
- 선형 방정식이 한 개여도 상관없음
- 선형 방정식의 예시   
- 아래 두 개의 선형 방정식은 선형 방정식 계라고 할 수 있다.

   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 3x_2 = 3 $   
     
   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_01.png){: : width="300" .normal }


<br>
<br>

## 해의 집합 - Solution Set
- The set of all possible solutions of the linear system.
- 선형 시스템에서 모든 가능한 해의 집합을 의미한다.

<br>
<br>

## 상등 - equivalent

- Two linear systems are called **<span style="color:#FFD412">equivalent</span>** if they have the **same solution set**.
- 두 선형 방정식이 상등(**<span style="color:#FFD412">equivalent</span>**) 하다라는 뜻은 같은 **solution set** 을 지녔다는 것을 의미한다.

<br>
<br>

## 해가 있다 (**consistent**), 해가 없다(**inconsistent**)

#### 해가 없다 - inconsistent

- **<span style="color:#FE6800">no solution</span>** 해가 없는 상태 -> **<span style="color:#FFD412">inconsistent</span>**      
   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 2x_2 = 3 $   
      
   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_02.png){: : width="300" .normal }

   - 이 처럼 두 직선이 평행하게 되면 교차점이 없다. 이 경우에 no solution 이며, 두 방정식은 inconsistent 하다.

<br>

#### 해가 있다 - consistent

- (i)**<span style="color:#FE6800">exactly one solution</span>** or (ii)**<span style="color:#FE6800">infinitely many solutions</span>** 해가 하나이거나 무한히 많을 때 -> **<span style="color:#FFD412">consistent</span>**    

   #1. 해가 하나인 경우

   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 2x_2 = 3 $

   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_01.png){: : width="300" .normal }

   <br>

   #2. 해가 무수히 많은 경우
   
   $ x_1 - 2x_2 = -1 $   
   $ -x_1 + 2x_2 = 1 $

   ![Desktop View](/assets/img/post/mathematics/linearalgebra1_03.png){: : width="300" .normal }

- 정리하자면 선형 방정식 계는 1. no solution, 2. exactly one solution, 3. infinitely many solution 세 가지 경우를 가지고 있다.
- inconsistent 는 no solution, consistent 는 exactly one solution or infinitely many solution을 의미한다.

<br>

## 행렬 표기법 - Matrix notation

- 행렬 표기법은 **선형 시스템을 행렬로 표현**한 것이다.

$ x_1 - 2x_2 + x_3 = 0 $   
$       2x_2 - 8x_3 = 8 $   
$ -4x_1 + 5x_2 + 9x_3 = -9 $

- 이 3개의 방정식을 행렬로 표기하면 다음과 같다.

<br>

### (1)  계수 행렬 - coefficient matrix (3x3)

- coefficient matrix 는 b를 제외하고 a만을 행렬로 나타낸 것이다.

$
\begin{bmatrix}
   \phantom{-}1 & -1 & \phantom{-}1 \\\ \phantom{-}0 & \phantom{-}2 & -8 \\\ -4 &  \phantom{-}5 &  \phantom{-}9 
\end{bmatrix}
$

<br>

### (2)  첨가 행렬 - augmented matrix (3x4)

- augmented matrix는 b까지 포함한 행렬이다.

$
\begin{bmatrix}
   \phantom{-}1 & -2 & \phantom{-}1 & \phantom{-}0 \\\ \phantom{-}0 & \phantom{-}2 & -8 & \phantom{-}8 \\\ -4 &  \phantom{-}5 &  \phantom{-}9 & -9
\end{bmatrix}
$

<br>

## 소거법 - elimination

- row operation을 통해 elimination을 진행하고 linear equation의 solution을 구할 수 있다.

- 예제 1. Solve the following system of linear equations   
    ![Desktop View](/assets/img/post/mathematics/linearalgebra1_04.png){: : width="500" .normal }   
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_05.png){: : width="500" .normal }   
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_06.png){: : width="500" .normal }    

	- 우리는 augmented matrix 만을 가지고도 solution을 구할 수 있다.
	![Desktop View](/assets/img/post/mathematics/linearalgebra1_07.png){: : width="500" .normal }

- $ x_1 = 1, x_2 = 0, x_3 = -1 $ 으로 one solution을 갖고 있으므로 세 방정식은 consistent 하다.
- 또한 같은 solution set을 갖고 있으므로 row equivalent 하다.

<br>

- 예제 2. Solve the following system of linear equations   
   	![Desktop View](/assets/img/post/mathematics/linearalgebra1_08.png){: : width="500" .normal }   
	- 행렬에서 좌측 상단을 pivot position 이라고 하는데, 이 pivot position 이 0이 되면 안되므로 interchange 를 실시해야한다.  
	- column 들 끼리는 자유롭게 interchange 할 수 있다.
	- 이 문제는 $ 0 = 5 / 2 $ 이기 때문에 incosistent 하므로 해가 없다.

<br>

## 행 연산 - Elementary row operations

1.  **<span style="color:#FFD412">replacement</span>**
2.  **<span style="color:#FFD412">interchange</span>** 
3.  **<span style="color:#FFD412">scaling</span>** 

- 위 3가지 row operation 을 통해 최종 계산한 결과 값이랑 최초의 행렬이랑 같다. ->  **<span style="color:#FFD412">row equivalent</span>**  하다.

- We say two matrices are  **<span style="color:#FFD412">row equivalent</span>**  if there is a sequence of elementary row operations that transforms one matrix into the other.
- If the augmented matrices of two linear systems are row equivalent, then the tow systems have the same solution set. (두 augmented matrices 가 row equivalent 하다라는 말은 같은 solution set을 가지고 있다라는 뜻.)

<br>

## 행 상등 - row equivalent

- row operation을 통해 하나의 matrix 를 다른 matrix로 변환된다면 두 matrix 는 row quivalent 하다고 할 수있다.
- 두 linear system 이 row equivalent 하다면 두 linear system은 have same solution set.