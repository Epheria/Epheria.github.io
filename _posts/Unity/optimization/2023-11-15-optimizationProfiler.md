---
title: Unity Profiler 최적화
date: 2023-11-15 12:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [Unity, Optimization, Profiler]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

<br>
<br>

## 유니티 프로파일러

- 에디터 환경에서 or 빌드를 통해서 간편하게 최적화를 진행할 수 있는 툴이다.

<br>

#### 프로파일러의 구성

![Desktop View](/assets/img/post/unity/profiler01.png){: : width="1200" .normal }

<br>
<br>

#### Development Build 옵션을 체크하자.
- 추가 옵션은 대부분 불필요하다. 추가옵션은 프로파일러 자동연결, 딥 프로파일링 등을 지원한다.
- 다만 여기서 자동연결은 해당 컴퓨터의 ip를 베이크하기 때문에 빌드한 컴퓨터에서만 자동연결이 가능하다.

![Desktop View](/assets/img/post/unity/profiler02.png){: : width="400" .normal }
![Desktop View](/assets/img/post/unity/profiler03.png){: : width="400" .normal }

<br>
<br>

#### 프로파일러 - CPU 모듈
- 샘플 단위로 볼 수 있음.
- 각 처리가 CPU 시간을 얼마나 소비했는지 확인 가능.

![Desktop View](/assets/img/post/unity/profiler04.png){: : width="1200" .normal }

<br>
<br>

#### 프로파일러 - 차트 창
- 평균적으로 프로젝트에서 설정한 타겟 FPS보다 빠르게 처리하는지 확인! -> 60fps 의 경우 대부분 16ms 내에 모든 처리가 끝나야한다. 30fps 는 33ms
- 그래프 과부하(스파이크)가 발생하는지 확인하자.
- vsync가 켜져있을 경우 모든 차트가 강제로 60fps 16ms로 세팅된다. 따라서 프로파일링 할 때는 vsync를 끄고 돌리자.

![Desktop View](/assets/img/post/unity/profiler05.png){: : width="500" .normal }

<br>
<br>

#### 프로파일러 - 상세 창, 타임라인 뷰
- CPU 사용시간을 직관적으로 파악이 가능하다.
- 모든 스레드를 한 눈에 파악
- 함수들의 타이밍과 실행 순서 관계를 선형적으로 파악가능하다.

![Desktop View](/assets/img/post/unity/profiler06.png){: : width="1600" .normal }

<br>
<br>

#### 프로파일러 - 상세창, 계층 뷰
- 부모<->자식 호출 관계 파악
- 원하는 지표를 기준으로 정렬이 가능

![Desktop View](/assets/img/post/unity/profiler07.png){: : width="1600" .normal }

<br>
<br>

- 가장 실행시간이 긴 샘플들 부터 해결하면 된다.

![Desktop View](/assets/img/post/unity/profiler08.png){: : width="1600" .normal }

<br>
<br>

#### 프로파일러 - 스레드들

- 메인 스레드
> 1. 유니티 Player Loop (Awake, Start..) 가 일어남   
> 2. MonoBehaviour 스크립트들이 일차적으로 동작한다

<br>

- 렌더 스레드
> 1. GPU에게 전달할 명령어를 조립하는 스레드
> 실질적인 GPU에게 전달할 그래픽스 명령어를 조립하고 메인 스레드에서 드로우콜이 발생 -> 렌더 스레드에서 실행

<br>

- 워커 스레드 (잡 스레드)
> 1. 잡 시스템 등으로 비동기 병렬 실행한 처리들
> 2. 애니메이션 / 물리 등 연산 집약 처리들이 이곳에서 실행
> 메인 스레드에서 잡을 예약 -> 워커 스레드에서 처리

<br>

![Desktop View](/assets/img/post/unity/profiler09.png){: : width="400" .normal }

<br>
<br>

- 서로 다른 스레드에서, 서로 직접 호출하지 않는 메소드 실행 사이에 인과관계가 있을 수 있다.
> ex1. 잡 예약  >  워커 스레드에서 처리   
> ex2. 메인 스레드의 메시 렌더러가 Draw() 실행 > 렌더 스레드에서 그래픽스 명령어 조합   
> 메인스레드의 처리들이 지연되면 렌더 스레드가 놀 수 있다.

<br>
<br>

- Show Flow Events 설정 활성화 : 실행 순서, 인과 관계 확인 가능.

![Desktop View](/assets/img/post/unity/profiler10.png){: : width="1600" .normal }

<br>
<br>

#### 샘플 스택과 콜 스택 차이

![Desktop View](/assets/img/post/unity/profiler11.png){: : width="1600" .normal }

- 샘플 스택과 콜 스택의 차이가 존재한다. 샘플 스택은 청크 단위로 정리되고 마크된 C# 메서드, 코드 블록만 실행한다.
- 이 이유 때문에 크게 하나로 묶여서 샘플링이 처리가 된다. -> 모든 C# 메서드 호출을 샘플링 하지 않음. 마크된 C# 메서드와 코드 블록만 샘플링.(유니티에서 미리 주요 실행들에 대해 마크해 둠.)

<br>

##### 딥 프로파일링 시 주의 사항
> 딥 프로파일링 시 -> 모든 C# 호출 (생성자, 프로퍼티 포함) 마크   
> 프로파일링 그 자체의 과도한 오버헤드가 발생 -> 부정확한 데이터

- 따라서 딥 프로파일링 시 아주 제한적인 스코프 내에서 한정된 시간내에서만 사용하는 것을 권장한다.

<br>
<br>

#### 콜 스택 설정 하는 방법

![Desktop View](/assets/img/post/unity/profiler12.png){: : width="400" .normal }

- 콜 스택 버튼을 눌러서 활성화 시켜야함!! (음영 생김)
- 콜 스택 드롭다운 -> 원하는 마커 선택하여 클릭

![Desktop View](/assets/img/post/unity/profiler13.png){: : width="2400" .normal }

- 특정 샘플에 대해서는 콜스택 전체를 기록 할 수 있다.
> 1. GC.Alloc : 동적 할당이 일어나는 경우   
> 2. UnsafeUtility.Malloc : 관리되지 않는 할당 - 메모리를 직접 해제해야하는 할당을 했을 때   
> 3. Jobhandle.Complete : 잡 동기 완료, 메인 스레드에서 잡 스레드를 강제로 동기완료 했을 때

- 권장하지 않고 제한적으로 사용 가능.

<br>
<br>

#### 마커에 대해 알아보자

<br>

#### 1. 메인 루프 마커

- PlayerLoop : 플레이어 루프에 맞춰 실행되는 샘플들의 루트

- BeahvourUpdate : Update() 샘플들의 홀더

- FixedBehaviourUpdate : FixedUpdate() 샘플들의 홀더

- EditorLoop : 에디터 전용, 에디터 루프

<br>

#### 2. 그래픽스 마커 (메인 스레드)

- WaitForTargetFPS
> Vsync, 목표 프레임 레이트를 기다리는 시간

- Gfx.WaitForPresentOnGfxThread
> 렌더 스레드가 GPU를 기다리고 있어서 생기는 마커  렌더 스레드가 바빠서 메인 스레드도 같이 대기해야하는 경우

- Gfx.PresnetFrame 
> GPU가 현재 프레임을 렌더하는 시간을 기다림   
> 이것이 길면 GPU 처리가 늦어짐

- GPU.WaitForCommands
> 렌더 스래드는 새로운 커맨드 받을 준비 완료. 메인 스레드에서 렌더 스레드에게 못 넘겨주고 있는 상황 메인 스레드가 대기중

<br>
<br>

#### 병목 지점 찾기
- 그래픽스 마커는 GPU / CPU 바운드 판단에 유용하다.
- 메인 스레드에서 렌더 스레드를 기다리는 중일 때 -> 메인 스레드에서 병목현상이 발생하고 LateUpdate 단에서 렌더 스레드에서 명령어를 생성
- 즉 gpu cpu 병목을 파악하는게 아닌 스레드간의 병목을 파악해야한다.

<br>

![Desktop View](/assets/img/post/unity/profiler14.png){: : width="2400" .normal }

- CPU 메인스레드 바운드
> 메인스레드 처리가 늦어서 렏더 스레드를 대기

<br>

![Desktop View](/assets/img/post/unity/profiler15.png){: : width="2400" .normal }

- 렌더스레드 바운드
> 직전 프레임을 그리기 위한 드로우콜 명령어를 아직도 보내는 중

<br>

![Desktop View](/assets/img/post/unity/profiler16.png){: : width="2400" .normal }

- 워커스레드 바운드
> 잡 완료를 동기로 대기중

<br>

- Xcode Frame Debugger, 2023 프로파일러는 GPU CPU바운드 표기 해줌


<br>
<br>

#### 병목에는 크게 4가지 병목이 존재한다.

1. CPU 메인 스레드 바운드
2. CPU 워커 스레드 바운드 (물리, 애니메이션, 잡 시스템)
3. CPU 렌더 스레드 바운드 (그래픽카드의 병목이 아닌 CPU에서 그래픽카드로 작업 즉 명령어 조립 넘기는것에 대한 병목)
4. GPU 바운드

<br>

- 병목을 찾는 흐름
> 메인 스레드 병목 ? 플레이어 루프 최적화   
> 아닐경우 물리, 애니메이션, 잡 시스템 집중   
> 이거도 아니면 렌더 스레드 병목  GPuU 인지 CPU인지 또 파악

<br>

- 렌더 스레드 CPU 병목인 경우
- CPU그래픽스 최적화
> 카메라, 컬링 최적화   
> Setpass call 줄이기 (batching)
> 가능한 그래픽스 배칭 - SRP 배칭, Dynamic 배칭, Static 배칭, GPU 인스턴싱

<br>
<br>

#### 범용적인 사실
- 배칭에 대해 설명하기 전 짚고 넘어가기.
- 그래픽스 처리 지연들
> 요즘 그래픽카드가 좋아졌기 때문에 GPU성능에 문제가 있다라기 보단, CPU가 명령어를 구성하는데에서 지연 -> GPU성능을 제대로 활용을 못하고 있다.   
> CPU->GPU로 명령어, 리소스를 업로드하는 데에서의 지연   
> GPU 내에서의 처리 지연이 있을 수 있다.

- 드로우콜 CPU -> GPU에게 렌더 실행 명령을 내림
> 드로우콜 보단 렌더 상태 변경에서 발생하는 CPU 성능 소모/업로드 지연이 크다.

- 그리라는 명령 보단 그리라는 명령하기 직전 
- GPU는 다수의 작은 메시보다 대량의 정점을 가직 메시를 빠르게 그린다.
- GPU의 계산 성능이 떨어지는 것보단 GPU를 효율적으로 사용하지 못해서 발생
> GPU는 다수의 작은 메시보다 한번에 대량의 정점을 가진 메시를 더 빠르게 그린다   
> 대부분의 랜더링 문제는 GPU의 계산 성능이 떨어지는 것 보다   
> GPU를 효율적으로 못쓰는데서 많이 발생한다   
> 정점수가 작은 메시를 전달 > GPU의 처리 단위(Wavefront/Warp)를 낭비   
> 예시로는 256개의 버텍스를 한 프레임당 처리하는데, 128개 버텍스를 요청하면 낭비가 발생

<br>
<br>

#### 그래픽스 배칭

#### 1. SRP 배칭 (URP, HDRP)

<span style=`background-color: #ffdce0`>드로우 명령어보다, 이에 앞서 매번 서로 다른 렌더 상태를 셋업하는게 비용이 더 크다</span>

정적 배칭
동적 배칭
GPU Instancing


SRP 배칭 - URP HDRP

드로우 명령어보다, 명령어 직전에 서로 다른 렌더 스테이트( 서로 다른 쉐이더 )를 셋업하는게 비용이 더 크다

같은 쉐이더를 사용하는 애들 끼리 모아서 셋업을 실행한다.

하나의 SetPass Call (동일한 셰이더 베리언트) 아래에 다수의 드로우콜을 묶는다.

프로젝트에서 사용하는 쉐이더 수를 줄이면 최적화가 가능하다.





정적 배칭 

GPU는 한번에 큰 메시를 그리는 것을 좋아한다. 적은 데이터 전송 이라는 컨셉

움직이지 않는 메시들을 미리 합쳐서 베이크함 -> gpu에게 미리 전달함 -> 각 렌더러에서 DrawIndexed()호출

유니티 에디터가 앱을 빌드할 때 만 베이크

단점, 기존 메시들을 합쳐서 메모리 사용량이 증가한다.



다이나믹 배칭
-> 별로 권장하지 않음.
GPU는 한번에 큰 메시를 그리는 것을 좋아한다. 적은 데이터 전송 이라는 컨셉

GPU측에서는 최적화
CPU에서는 매프레임 메시를 합쳐줘야한다.

매 프레임 베이크




GPU 인스턴싱

CPU에서 GPU로 명령 전달을 아끼자.

메시 데이터를 GPU에 한번만 업로드

GPU는 거대한 메시를 그리는 것이 성능이 더 좋다. 버텍스가 256 이하인 메시는 효율이 떨어진다.




SRP 배칭, 정적 배칭을 자주 쓰자.

드로우콜 보다 직전의 렌더 상태 셋업이 더 큰 CPU비용을 발생한다.

드로우콜보단 SetPass 콜을 줄이는데 집중하는게 좋다 (SRP배칭)    -> 물론 드로우콜도 중요하다.
SRP 배칭 켜고 쉐이더 종류를 줄이는게 가장 효과적이다. 쉐이더 종류를 줄여야한다..


Frame Debugger로 Setpass call 합쳐지지 않는 이유를 볼 수가 있다.


SetPass Call 을 300 미만으로 목표 설정.




GPU렌더 병목인 경우

Xcode GPU프레임 캡쳐

명령어들이 쭉 나열되어있음. 각각의 렌더 단계에서 시간 소모 확인

비정사적으로 시간 소모하는 드로우를 찾을 수 있음 -> 해당 드로우 명령어가 사용하는 셰이더, 메시를 찾아 최적화




어드레서블 ,에셋 번들 최적화

어드레서블 리포트 -> 중복 종속성(디펜던시) 체크

중복 종속성을 가진 에셋을 서로 다른 에셋 두개가 보유하고 있을 시 메모리에 중복 종속성을 가진 에셋이 두 개 사용됨

중복 종속성이 되는 에셋을 다른 에셋 그룹으로 묶어서 해결할 수 있음. -> Analyze

대표적으로 쉐이더!! 온갖 머테리얼에서 다 쓰고있어서 

쉐이더를 따로 묶어주자.


Asset Reference를 사용하지 않고 있으면 GUID를 카탈로그에서 뺄 수 있다. Include GUids in Catalog 체크 해제

Json 카탈로그 말고 바이너리를 쓰자!! -> 보안 이슈도 1차적으로 해결이 가능 해보임

모바일의 경우 동시 처리 가능한 웹리퀘스트 수에 한계가 있음 - 기본값 500보다 낮은 값으로 적당히 낮추기





에셋 번들 최적화 팁

에셋 번들이 너무 작은 경우
- 에셋 번들은 일부만 메모리에 로드 될 수 있음 (lz4압축) - 해당 장점을 희석
- 에셋 번들도 객체이므로 메모리 샤용량 증가
- 웹리퀘스트,  file io 가 증가 ^> cpu 처리 시간 증가, 발열

에셋 번들이 너무 큰 경우
- 언로드가 잘 안됨
- 일부만 로드할 수 없는 조견들이 존재. 에셋 번들 전체가 로드 되어버림..ㄷㄷ




쉐이더 베리언트 최적화

open gl, vulkan 여러개의 키워드를 사용하면 빌드할 때 배수의 쉐이더 베리언트가 발생

Project Auditor 
정적 분석 도구
- 유니티 에셋, 프로젝트 설정, 스크립트 분석
- 쉐이더 베리언트를 줄이는데 잘 사용됨.


쉐이더 베리언트 하나하나가 SetPass Call을 발생시킨다.


키워드를 쓰는 버전, 안쓰는 버전의 베리언트 각각 생성


기본 : 불필요한 셰이더 키워드를 쓰지 않기. 비슷한 역할을 하는 셰이더들을 병합하기

어드레서블에서 쉐이더 그룹을 따로 안묶어 놓으면 -> 중복된 쉐이더 베리언트가 각 에셋에 포함되어버려서 중복종속성이 발생하고 메모리에 로드가 되어버림

라이트 설정 -> 쓰지 않는 라이트맵 모드 해제하기 -> 해당 쉐이더 키워드가 명시적으로 제거됨

Lightmap Modes


사용하지 않는 그래픽스 API비활성화 - 쉐이더 1개당 각 그래픽스 API에 해당되는 쉐이더 베리언트 발생 -> 에셋 메모리 증가



빌드에 포함되지 않는 머티리얼 주의!!!!!

세이더의 shader_feature로 선언된 키워드 -> 머티리얼들이 사용하지 않으면 스트립됨 (제거)


URP 설정에서 strip 설정 활성화

Shader Stripping


Project Autior 를 통해 소거법으로 정리하는 방법

- 직전 빌드 캐시 날려버리기
- 프로젝트 설정 -> graphics -> log shader compliation체크

* development build 활성화

IPreprocessShaders 로 스크립트를 짜서 커스텀하게 스트립도 가능함.



CRC 체크 활성화 -> 무결성 검사

변조되어있는지 체크

웹리퀘스트가 경쟁상태에 돌입? Max Web Request를 줄여보기




유니티, ios 메모리 구조

ios 메모리 구조

물리 메모리 (RAM)
- 물리적으로 더 추가 불가
- 이것 보다 더 할당할 수 없음

앱은 물리 메모리에 대해 모르고 직접 사용하지 않는다.
앱의 메모리 할당은 VM virtual memory에서 할당

가상 메모리 VM
- 페이지 단위로 나뉨 4kb, 16kb 
- 페이지들은 물리 메모리에 매핑된다.

물리 메모리 사용량 != VM사용량
ex 1.78기가 할당 -> 실제 사용량 380mb 정도

VM의 이점
최적화  pm과 vm사이에서 최적화
간결함  앱은 물리 메모리 단계의 최적화를 모른다.

vm사용량이 커도 물리 메모리 샤용량은 적을 수 있음
중요한것 -> 물리 메로리를 얼마나 사용하는가?


메모리 풋프린트 - 앱이 실질적으로 차지하는 크기





ios 메모리의 구조

Dirty - 동적할당, 심볼 등이 수정된 프레임워크, 사용중인 메탈 g api 리소스들

Dirty Compressed - 거의 접근 안한 Dirty 페이지들

위 두놈들이 메모리 풋프린트

Clean - 맵핑된 파일들, 읽기 전용 프레임워크, 앱의 바이너리들(정적 코드)  언제든지 물리 메모리 영역에서 뺄 수 있는 것들, 상주 메모리 비율이 낮다.

메모리 풋프린트 - 상주 메모리 비율이 높다.


더티 메모리 -> 반드시 써야 할 최소 물리 메모리임을 의미

더티 메모리가 가장 집중해야할 최적화 대상이다. -> 동적할당들
클린 메모리 자주 발생하면 -> 오버헤드 발생



VM 
바이너리, 유니티 네이티브 메모리, 그래픽스, 네이티브 플러그인 (플러그인의 런타임은 더티임), Unity Managed Memory(.NET VM)

바이너리, 네이티브 플러그인 -> 클린 메모리

나머지 더티 






유니티 메모리 구조

유니티는 .NET 가상 머신을 쓰는 C++ 엔진 ,  코어는 CPP 제어는 C#


어떤 에셋을 로드하게 되면 
 C# 버전과 C++ 버전 메모리 두가지를 합해서 보여주게됨

스크립팅 백엔드 가상머신에 의해 할당/제어 되는 부분
- 관리되는 힙 모든 C# 할당  동적할당들
- C# 스크립팅 스택   지역변수들
- VM 메모리   가상머신을 위한 메모리 공간, 스크립팅 그 자체를 위한 할당,  메타 스크립팅 (리플렉션,제네릭)



Managed Memory 

GC Alloc

실제 동작 방식

메모리 풀 확보 -> 메모리 리전 내에 비슷한 크기를 모아서 블록들로 나눔
사이즈별로 비슷한 애들끼리 모아서 블록 형성

새 객체는 블록 내부에 할당


메모리 리전이 통째로 해제되면

가상 메모리에는 확보했는데
물리 메모리상에서는 디커밋 반환 해버리는 경우 발생 -> 물리 메모리에 래핑이 안된다.


새로운 할당이 기존 블럭에 못들어가면
커스텀 블럭 생성 및 할당



유니티 메모리 프로파일러 1.1v


allocated memory distribution

native C++ 네이티브 코드
graphics metal에의해 gpu 할당 메모리
managed C#
executalbe mapped  clean 메모리들  바이너리, dll
untracked  symbol을 모를때, 카테고리가 모호할 때 -> 카테고리는 완벽하지 않음. ex 오디오 클립?

유니티가 카테고리화를 못한 내용들이 들어감. 예  플러그인의 할당, 안드로이드 플러그인으로 로그인 만들때?

UnTrakced가 크다고 문제가 있는건 아니다.

ex   MALLOC_NANO   Allocated Size 500mb  resdient size  3,3mb
즉 미리 확보한 힙공간은 500mb 여도 실제 사용량은 3.3mb 밖에 되지 않는 경우가 있기 때문에 크다고 최적화가 필요한건 아니다.




Managed Heap Utilization -> 우리가 직접 제어하기는 힘든 영역


virutal machine  - 제네릭, 타입 메타 데이터, 리플렉션   -> 런타임 동안 계속 커지는 경향이 있다.

줄이는 방법 - 리플렉션 안쓰기, 코드 스트립, 2022 부터 제네릭 쉐어링 적용됨

엔진 코드 스트립 - 유니티 엔진 모듈 내에서 앱 빌드 시 ㅅ쓰이지 않는 코드 찾아서 스트립
매니지드 코드 스트립 레벨 

둘 다 사용

리플렉션을 사용하면 터질 수 있음 -> link.xml 에서 사용하도록 명시할 수도 있음




empty heap szie 가 크면 메모리 파편화가 심하다고 볼 수 있음. -> 동적할당 과정에서 CPU오버헤드가 발생, 불필요하게 점유한 메모리가 크다

빈블록 형성은 알고리즘이 있음.

엑세스 속도가 빠른 빈블록 찾아서 할당 -> 느린 빈블록 찾아서 할당 -> 이래도 없다? GC 트리거 -> Incremental GC 쓰면  GC Collection과 동시에 힙을 확장
안쓰면 GC Collection이후에도 공간이 여전히 없다라면 힙 확장 

Incremental GC 설정을 권장함.

gc call with alloc symbol 로 표기됨




Unity Objects 탭

Native Size, Managed Size, Graphics Size 세 가지 메모리 할당률로 보여줌
c++           c#    



Memory Map - 숨겨진 기능

구체적인 객체 이름이 안보임. 어떤 프레임워크나 바이너리가 점유했는지 파악이 가능


스냅샷 이기 때문에 콜 스택을 파악하기 힘듦

언제 왜 이런 할당이 발생했는가? 네이티브 프로파일러로 파악 가능



xcode instruments

xcode - build settings 내부
디버그 심볼을 반드시 포함해줘야함

resident 상주 메모리
dirty size 가상 메모리 할당 내에서 dirty 인 애들 - 상주메모리에서 빼기 힘든애들
swapped   스왑된 애들


클린메모리 binaries / code   

"GPU" - 유니티 GPU 처리
app allocations - 유니티 CPU 처리


IOSurface 상주메모리 비율이 100% -> 물리 메모리에 100% 할당
물리 메모리를 넘어서면 앱이 터짐

allocation 에서 상주 메모리 비율도 볼 수 있음

Memory Graph : 네이티브 메모리 스냅샷 도구




1. 앱이 꺼지는 이유 파악 ^ 메모리 때문인지?

안꺼지는 동안 메모리 프로파일러 스냅샷 찍어서  -  메로리 과하게 쓰고있는지 파악

ios xcode debugger 붙인 상태에서 게임플레이 -> 크래시 -> 크래시 잡을 수 있음

크래시가 메모리 때문인지? 에러 때문인지 파악가능

2. 메모리 문제라면?

메모리 프로파일러를 보면서 - Unity Objects, SUmmaries 탭에서 
total commiteed 영역에서 가장 큰 메모리를 쓰는 영역을 순서대로 정리 후 파악



레이아웃에 대한 처리는   순환 레이아웃 문제 때문에

dirty 여부 판단 - 프레임 마지막에 레이아웃을 갱신

항상 매프레임의 마지막으로 밀린다?  레이아웃을 강제로 갱신시키는 api 가 있을까?




모바일 - Unified memory
윈도우 - VRAM

텍스쳐 read/write 설정 - cpu 메모리에도 올라감








유니티 넷코드

데디케이트 서버 호스팅 서비스

핑 -> ICMP 프로토콜
클라 - 서버 전송 응답속도

핑이 있으면 라우팅이 있다.

ROUTING    HOP 들을 거쳐서 데이터센터에 연결을 위해 네트워크 연결을 위한 경로를 찾아내는 것

Tick Rate 클라 서버간 주고 받는 업데이트 빈도


네트워크 모델들

데디케이트 서버 - 서버에서 클라를 판단, 플레이어가 서버 연결하는데 시간이 걸림, 비용 높다

클라이언트 호스트 - 클라1이 호스팅, 방장이 나가면 끝

p2p peer to peer - 격투게임


Lag Compensation 핑 차이가 나면 서버가 지연 보상을 해줘야한다.

