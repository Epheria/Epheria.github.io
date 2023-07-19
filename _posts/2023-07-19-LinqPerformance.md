---
title: C# LINQ 퍼포먼스 관련
date: 2023-07-19 11:06:00 +/-TTTT
categories: [C#, C# Study]
tags: [Csharp, LINQ]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---


#<center> C# LINQ 퍼포먼스 관련 </center>
---
<br>
<br>
## LINQ 의 장점
> * LINQ(Language Integrated Query)는 간결하고 편리한 코드를 위한 C#의 기능 집합이다.   
    개발자는 쿼리를 사용하게 되는데 쿼리 구문을 사용하면 최소한의 코드로 데이터 소스에 대해   
    필터링, 정렬 및 그룹화 작업을 수행할 수 있다.

<br>
## LINQ 사용 시 주의사항
> * LINQ의 대부분의 연산자는 중간 버퍼(일종의 배열)를 생성하고 이는 모조리 가비지가 된다. 👉 <span style="color:red">GC 발생!!</span>   
> * LINQ 연산자 한 두개쯤 사용할 수 있는 것을 가독성 문제로 여러번 나누어 사용하게 되면 성능 저하의 원인이 될 수 있음.
> * Average, Count, orderBy, Reverse 등과 같은 연산자들은 원본 시퀀스를 반복하기 때문에 퍼포먼스 면에서 효율이 떨어짐.

<br>
#### <span style='background-color: #dcffe4'> 따라서 LINQ를 쓰기 전 아래의 규칙을 생각해야한다..</span>
<br>
## 사용시 규칙
> 1. 빠르게 구현해야만 하는 상황인지?(프로토타입 개발, TDD) - <span style='background-color: #dcffe4'>LINQ 사용</span>
> 2. 성능에 민감하지 않은 코드인지? - <span style='background-color: #dcffe4'>LINQ 사용</span>
> 3. LINQ의 편의성 또는 가독성이 꼭 필요한가? - <span style='background-color: #dcffe4'>LINQ 사용</span>
> 4. 매 프레임 호출되거나, 성능에 민감한 부분인가? - <span style='background-color: #ffdce0'>LINQ 사용 불가</span>

<br>
<br>
## LINQ 퍼포먼스 벤치마크
> * 벤치마크 라이브러리 : 

Alternatively, for H1 and H2, an underline-ish style:

Alt-H1
======

Alt-H2
------