---
title: Unity 어드레서블 최적화 방법
date: 2023-11-15 11:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [Addressable, Optimization, Unity]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

<br>
<br>

## 어드레서블 최적화

#### 어드레서블의 중복 종속성(Dependency) 문제
- 어드레서블 리포트를 통해 중복 종속성을 체크할 수 있다. -> 난 개인적으로 Analyze를 통해 처리

<br>

#### 중복 종속성이란?

- 어드레서블은 Assets 폴더 내부 어디에 있든 어드레서블에 등록이 가능하다. 에셋의 메모리 주소에 접근해서 처리하기에 가능.
- 하지만 이렇게 편리함과 동시에 주의해야할 점은 에셋의 중복 종속성 문제이다.

![Desktop View](/assets/img/post/unity/profileraddr02.png){: : width="700" .normal }

- 에셋 그룹 A, B 가 있다.
- 각 에셋 그룹에 속한 에셋 a,b가 에셋 c 를 참조한다고 가정하자.

<br>

![Desktop View](/assets/img/post/unity/profileraddr03.png){: : width="700" .normal }

- 이렇게 되면, 생성되는 에셋 번들 A, B 에는 에셋 c 가 모두 포함되버린다!
- 즉, 메모리에 에셋 c가 두 개 로드된다.

<br>

![Desktop View](/assets/img/post/unity/profileraddr04.png){: : width="700" .normal }

- 해결 방법은
- 에셋 c를 에셋 그룹 C를 만들어서 포함시켜 해결할 수 있다.
- 이렇게되면 에셋 번들 A, B는 에셋 번들 C를 참조하게 되고 에셋c 가 두 개 로드 되지않는다.

<br>

#### 정리

- 대표적으로 쉐이더가 이런 문제가 많이 발생한다. 온갖 머테리얼에서 그 쉐이더를 다 참조하고 있으므로..
- 따라서 쉐이더는 쉐이더 그룹을 만들어서 따로 묶어주자. (이는 아래 쉐이더 베리언트를 설명하면서도 나옴)
- 에셋에 직접 어드레스를 부여해서 쓰진 않지만 다른 에셋 그룹에 참조되는 에셋들 -> 명시적으로 종속성 전용 에셋 그룹을 만들어서 해결할 수 있다.
- 어드레스를 카탈로그에 포함 시키지 않음으로 카탈로그 사이즈를 줄일 수도있다.
> Include Addresses in Catalog 옵션 체크 해제.

<br>

![Desktop View](/assets/img/post/unity/profileraddr01.png){: : width="1800" .normal }

- 어드레서블 Analyze 라는 툴이 존재하는데, 여기서 Fixable Ruels 를 클릭해서 -> 상단 툴바의 Analyze Selected Rules를 돌리면 자동으로 중복 종속성을 가지고 있는 에셋들을 
- Duplicate Isolation 이라는 에셋 그룹을 만들어 집어 넣어준다.

<br>
<br>

#### 어드레서블 최적화 팁

- AssetReference를 상요하지 않고 있으면 GUID를 카탈로그에서 뺄 수 있다.
> Include GUIDs in Catalog 옵션 체크 해제.

![Desktop View](/assets/img/post/unity/profileraddr05.png){: : width="500" .normal }

<br>

- JSON 카탈로그 말고 바이너리를 쓰자 -> 요즘 어드레서블 카탈로그를 뜯어서 업데이트 내용을 해킹하는 방법도 있어서 바이너리로 1차 보안을 챙길 수도 있을듯.

<br>

- 모바일의 경우 동시 처리 가능한 웹리퀘스트 수에 한계가 있다.
> Max Concurrent Web Request 옵션 값이 기본으로 500으로 설정되어있는데 낮은값으로 적당히 낮춰주자.

![Desktop View](/assets/img/post/unity/profileraddr06.png){: : width="500" .normal }

<br>
<br>


#### 셰이더 베리언트 최적화

#### Project Auditor

![Desktop View](/assets/img/post/unity/profileraddr07.png){: : width="1800" .normal }

- [Project Auditor Github](https://github.com/Unity-Technologies/ProjectAuditor.git)
- 정적 분석 도구
> 유니티 에셋, 프로젝트 설정, 스크립트 분석   
> 셰이더 베리언트를 줄이는데 잘 사용된다.

<br>

#### 셰이더 베리언트란?

![Desktop View](/assets/img/post/unity/profileraddr08.png){: : width="500" .normal }

- 키워드의 조합 등에 따라 **파생된 버전의 셰이더**
> open gl, vulkan 여러개의 키워드를 사용하면 빌드할 때 배수의 쉐이더 베리언트가 발생

<br>

![Desktop View](/assets/img/post/unity/profileraddr09.png){: : width="500" .normal }

- 또한, 베리언트 수가 지나치게 많으면
- ***Setpass Call 증가***
- ***키워드 당 메모리 사용량 2배씩 증가***

<br>

#### 셰이더 베리언트 정리하기

- 기본적으로 불필요한 셰이더 키워드를 쓰지않아야 한다. 비슷한 역할을 하는 셰이더(베리언트)들을 병합해야한다.
- 가장 흔한 케이스
> ***어드레서블에서 셰이더 그룹을 따로 안묶어 놓으면*** -> 중복된 쉐이더 베리언트가 각 에셋 번들에 포함되어버려서 중복 종속성이 발생하고 메모리에 로드가 되어버림
> 셰이더만 모으는 에셋 그룹 만들어주기

<br>

- 라이트 설정 -> 쓰지 않는 라이트맵 모드 해제하기 -> 해당 셰이더 키워드가 명시적으로 제거됨.

![Desktop View](/assets/img/post/unity/profileraddr10.png){: : width="600" .normal }

<br>

- 사용하지 않는 그래픽스 API 비활성화하기 -> 각 종류별 그래픽스 API에 맞춰 각각의 셰이더 베리언트가 만들어짐
> 솔직히 개인적으로 안드로이드 모바일에선 vulkan 보단 opengl es3를 사용하는게 더 안정적인거같다. -> 파티클 시스템 깜빡거리는 이슈가 있음..   
> 애플 그래픽스 API는 Metal

![Desktop View](/assets/img/post/unity/profileraddr11.png){: : width="400" .normal }

<br>

- **빌드에 포함되지 않는 머테리얼 주의**
> 셰이더의 shader_feature로 선언된 키워드 > 머티리얼들이 사용하지 않으면 스트립(제거)됨   
> 빌드시 프로젝트 전체 머티리얼을 기준으로 키워드를 스트립 > 빌드에 포함되지 않는 머티리얼이 키워드를 살릴 수 있음

![Desktop View](/assets/img/post/unity/profileraddr12.png){: : width="500" .normal }

<br>

- URP 설정에서 strip 설정 활성화
> 디버그용 키워드
> 사용되지 않는 포스트 프로세스 베리언트 키워드
> 사용되지 않는 URP 피쳐 베리언트

![Desktop View](/assets/img/post/unity/profileraddr13.png){: : width="300" .normal }

<br>

#### Project Auditor 를 통해 소거법으로 정리하기

- ***우선 직전 빌드 캐시를 날려야한다!!***
- **빌드에 포함된 전체 베리언트 수집**
- **로그를 통해 플레이 도중에 실제로 쓰이는 베리언트 수집**
- **사용안되는 베리언트를 제거하기**
> 셰이더 코드에서 직접 키워드 제거   
> 머티리얼에서 체크 해제   
> IPreprocessSahders로 필터링

<br>

![Desktop View](/assets/img/post/unity/profileraddr14.png){: : width="900" .normal }

- 프로젝트 설정에서 셰이더 컴필리에이션 로그 활성화
> 프로젝트 설정 > Graphics > Log Shader Compilation 체크
- Development Build 활성화
- 어드레서블 빌드와 플레이어 빌드 실행
> 어드레서블 빌드 실행시 직전 어드레서블 빌드 캐시 제거해야함
- 프로젝트 오디터의 셰이더 베리언트 창에 빌드에 포함된 셰이더들이 표시됨

<br>

![Desktop View](/assets/img/post/unity/profileraddr15.png){: : width="900" .normal }

- 게임 플레이하며 전체 콘텐츠를 순회
- 로드되어 GPU에 의해 컴파일된 셰이더 베리언트 이름이 로그에 남음
- 해당 로그를 프로젝트 오디터 창에 드래그&드롭
> GPU가 컴파일한(=사용한) 셰이더 베리언트가 Compiled로 체크됨
- 사용되지 않는 베리언트들을 알았으니 -> 정리가능

<br>
<br>

#### 여담 : 어드레서블 패치 시스템 구현 시 CRC체크에 대해서

![Desktop View](/assets/img/post/unity/profileraddr16.png){: : width="500" .normal }

- 어드레서블 그룹 세팅을 보면 CRC를 활성화 할지 비활성화 할지 여부를 체크하는 옵션이 있다.
- CRC 체크는 간단하게 무결성 검사를 뜻하며, 에셋 번들이 변조되었는지를 체크한다.
- 하지만 난 라벨 전체를 가져와서 다운로드 받는 형식이 아니라, ResourceLocators 전체를 순회하며 어드레서블 패치 시스템을 구현했다.
- 그러나, 이 과정에서 리소스 다운로드 로딩에서 이상현상이 발생했다. (각 리소스 로케이터의 키 값들 각각을 더해서 만든 로딩)
- 예를들어, 200MB를 다운받는다고 쳤을 때 98% - 99% 정도 되면 실제로 90% 정도를 다운받는 시간보다 나머지 1% - 2% 를 다운 받는 시간이 더 오래걸렸다.
- 이부분이 CRC 체크를 해두어서 무결성 검사를 실행하는 부분이여서 로딩이 오래 걸린다는 이제민 강사님의 조언이 있었다. -> 시도 해볼 것
- 또는, CRC를 해제해도 똑같다면 웹 리퀘스트가 경쟁상태에 돌입해서 오래 걸리는 경우일 수도 있으므로.. Max Web Request 값을 줄여보자.
