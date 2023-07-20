---
title: C# LINQ 퍼포먼스 관련
date: 2023-07-19 11:06:00 +/-TTTT
categories: [C#, C# Study]
tags: [Csharp, LINQ]     # TAG names should always be lowercase

toc: true
toc_sticky: true
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
#### 따라서 LINQ를 쓰기 전 아래의 규칙을 생각해야한다..
<br>
## 사용시 규칙
> 1. 빠르게 구현해야만 하는 상황인지?(프로토타입 개발, TDD) - <span style="color:green">LINQ 사용</span>
> 2. 성능에 민감하지 않은 코드인지? - <span style="color:green">LINQ 사용</span>
> 3. LINQ의 편의성 또는 가독성이 꼭 필요한가? - <span style="color:green">LINQ 사용</span>
> 4. 매 프레임 호출되거나, 성능에 민감한 부분인가? - <span style="color:red">LINQ 사용 불가</span>

<br>
<br>
## LINQ 퍼포먼스 벤치마크
> * 벤치마크 라이브러리 : [BenchMark](https://github.com/dotnet/BenchmarkDotNet)
> * 테스트 코드 : [TestCode](https://github.com/jamesvickers19/dotnet-linq-benchmarks)
> * 원문 링크 : [LinqPerformance](https://medium.com/swlh/is-using-linq-in-c-bad-for-performance-318a1e71a732)

<br>
<br>

## 벤치마크 : 반복문
> 연령이 18세 미만인 Customer 수를 반환

1. For / Foreach 문
<img src="/assets/img/post/linq/linq01.png" width="1920px" height="1080px" title="256" alt="linq1">

2. LINQ Count / Predicate Count
<img src="/assets/img/post/linq/linq02.png" width="1920px" height="1080px" title="256" alt="linq2">
<br>

<img src="/assets/img/post/linq/linq03.png" width="1920px" height="1080px" title="256" alt="linq3">

for/foreach 문에 비해 LINQ는 약간의 오버헤드(특정 기능을 수행하는데 드는 간접적인 시간, 메모리, 자원을 의미) 페넡티가 존재한다.
필터링 후 카운트는 그나마 for문과 비슷하지만 단순하게 시퀀스의 요소 수를 반환하는 Count는 상당한 퍼포먼스 저하가 있음.

<br>
<br>

## 벤치마크 : 필터링
> 연령이 18세 이상인 고객 배열의 하위 집합인 고객 목록을 반환

1. For/Foreach 문
<img src="/assets/img/post/linq/linq04.png" width="1920px" height="1080px" title="256" alt="linq4">

2. LINQ 문
<img src="/assets/img/post/linq/linq05.png" width="1920px" height="1080px" title="256" alt="linq5">

<img src="/assets/img/post/linq/linq06.png" width="1920px" height="1080px" title="256" alt="linq6">
for/foreach 사용한 구현과 매우 유사한 성능을 발휘함. for/foreach 보다 4ms 더 걸림

<br>
<br>

##### 실제로 RaycastAll 에서 필터링 후 tag 체크할 때 사용했던 코드
<img src="/assets/img/post/linq/linq07.png" width="1920px" height="1080px" title="256" alt="linq7">
필터링 같은 경우는 일반적인 for/foreach 보다 훨씬 간결하고 가독성이 좋은 코드를 만들 수 있었다..

<br>

## 벤치마크 : 변환
> 연령이 연도가 아닌 월로 표시되는 고객 목록 반환

1. For/Foreach 문
<img src="/assets/img/post/linq/linq08.png" width="1920px" height="1080px" title="256" alt="linq8">

2. LINQ 문
<img src="/assets/img/post/linq/linq09.png" width="1920px" height="1080px" title="256" alt="linq9">

<img src="/assets/img/post/linq/linq10.png" width="1920px" height="1080px" title="256" alt="linq10">

<br>
<br>

## LINQ는 얼마나 많은 GC를 생성할까?
> 테스트 조건은 아래 링크 참조
* 원문 링크 : [Just How Much Garbage Does LINQ Create?](https://www.jacksondunstan.com/articles/4840)

#### 결과
1. GC Alloc Count
<img src="/assets/img/post/linq/linq11.png" width="1920px" height="1080px" title="256" alt="linq11">
<img src="/assets/img/post/linq/linq12.png" width="1920px" height="1080px" title="256" alt="linq12">
<br>
<br>

## Microsoft Documents Unity 에 대한 성능 "추천" 사항
[Unity에 대한 성능 추천 사항](https://learn.microsoft.com/ko-kr/windows/mixed-reality/develop/unity/performance-recommendations-for-unity?tabs=openxr)

<img src="/assets/img/post/linq/linq13.png" width="1920px" height="1080px" title="256" alt="linq13">

<br>
<br>

## 결론
1. LINQ의 성능은 Count가 상당히 느리다
2. 이외의 필터링 Where, 변환 Select는 성능측면으로는 for문과 비슷하다.
3. 한 줄 또는 두 줄의 매우 간결한 코드를 작성할 수 있다.
4. 디버깅이 힘들다..
5. GC 발생이 존재한다.. 너무 남발하면 감당 못함
6. 매 프레임 호출, 퍼포먼스에 영향을 미칠 수 있는 곳에서는 사용하지 말기!!