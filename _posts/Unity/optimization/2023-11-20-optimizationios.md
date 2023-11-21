---
title: 유니티 & iOS 메모리 구조에 대해
date: 2023-11-20 19:12:00 +/-TTTT
categories: [Unity, Optimization]
tags: [iOS, Optimization, Unity, Memory Structure]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

<br>
<br>

## **iOS 메모리 구조**

#### **물리 메모리** (RAM)

![Desktop View](/assets/img/post/unity/profilerios01.png){: : width="500" .normal }

- 물리적으로 더 추가 불가능
- 이것보다 더 할당하지 말자
- ***물리 메모리 사용량 != 앱의 VM 할당량***
> 앱은 물리 메모리에 대해 알 수 없고, 직접 사용하지 않는다.   
> 앱의 메모리 할당은 VM 즉 Virtual Memory 에서 할당한다.

<br>

#### **가상 메모리** (VM - Virtual Memory)
- 앱은 물리 메모리를 직접 사용하지 않는다.
- 할당은 VM에서 이루어진다.

<br>

![Desktop View](/assets/img/post/unity/profilerios02.png){: : width="500" .normal }

- 페이지 단위로 나뉜다. (4kb or 16kb)
- 페이지들은 물리 메모리에 매핑된다.
- 보통 Clean 하거나 Dirty 하다.

<br>

![Desktop View](/assets/img/post/unity/profilerios03.png){: : width="500" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios04.png){: : width="500" .normal }

- 엔진이 새 페이지들을 예약(Reserve) -> OS 에게 이들을 PM 에 **커밋**하도록 요청한다.
- 유니티 할당 메모리를 Total **Committed** Memory 라고 부른다.
- 커밋을 요청한 예약 페이지들을 사용하지 않으면 실제로 PM에 커밋되지 않는다.

<br>

![Desktop View](/assets/img/post/unity/profilerios05.png){: : width="500" .normal }

- ***물리 메모리 사용량 != VM 사용량***
- 상주 메모리 : 318.0 MB, 총 할당량 : 1.76 GB
> 1.78기가 할당 -> 실제 사용량 380mb 정도

<br>
<br>

#### **VM의 이점**

![Desktop View](/assets/img/post/unity/profilerios06.png){: : width="500" .normal }

- 최적화 : PM과 VM사이에서 최적화
- 간결함 : 앱은 물리 메모리 단계의 최적화를 모른다.
- VM 사용량이 커도 물리 메모리 사용량은 적을 수 있다. 
- 정말 중요한 것은 -> **물리 메모리를 얼마나 사용하는가?**이다.

<br>
<br>

#### **메모리 풋프린트** (Memory Footprint)

- 메모리 풋프린트란 앱이 실질적으로 차지하는 크기를 의미
> 상주 메모리 비율이 높은 할당 영역들의 합산
- **상주 메모리**(Resident Memory) : 메모리 할당 중 실제 물리 메모리에 상주하는 부분을 의미
- ex. 가상 메모리 할당에 500MB 에서 상주 메모리 비율 10%
> 물리 메모리에 상주하는 것들 50MB + 가상 메모리에만 할당된 것 450MB

<br>
<br>

![Desktop View](/assets/img/post/unity/profilerios07.png){: : width="600" .normal }

- 일반적으로 앱 메모리 프로파일은 Dirty, Compressed, Clean 메모리 세그먼트로 구성된다.
- **Dirty** : 힙의 메모리 할당, 심볼 등이 수정된 프레임워크, 사용중인 Graphics API 리소스들 (Metal)
> 앱에 의해 쓰여진 메모리를 의미, Decode 된 이미지 버퍼 일 수도 있다.
- **Dirty Compressed** : 거의 접근 안한 Dirty 페이지들
> 디스크 스왑이 가능. 아직 엑세스 되지 않은 페이지를 압축하여 실제로 더 많은 공간을 만들 수 있다. 메모리 엑세스시 압축 해제함   
```
디스크 스왑?
물리적 메모리의 용량이 가득 차게 될 경우 하드 디스크 공간을 메모리 공간처럼 교환(Swap)하여 사용하는것
```
- **Clean** : 맵핑된 파일들, 읽기 전용 프레임워크, 앱의 바이너리들(정적 코드) 언제든지 물리 메모리 영역에서 뺄 수 있는 것들, 상주 메모리 비율이 낮다.

<br>

![Desktop View](/assets/img/post/unity/profilerios08.png){: : width="600" .normal }

- Dirty 와 Dirty Compressed 는 메모리 풋프린트이고 상주 메모리 비율이 높다.
- Clean은 상주 메모리 비율이 낮다.

#### **정리**

- 현재 쓰고 있는 전체 물리 메모리양(상주 메모리)이 메모리 풋프린트가 아닌 이유?
> Clean 의 상주 메모리는 언제든지 해제가 가능하기 때문   
> Dirty 의 상주 메모리는 해제하기 힘듦

- Dirty는 반드시 써야 할 최소 물리 메모리임을 의미한다.
> 실질적인 물리 메모리 제약은 Dirty 기준이므로 Dirty가 곧 메모리 풋프린트이다.

- **Dirty 메모리가 가장 집중해야할 최적화 대상이다**
> ex. 동적 할당들   
> **단 클린 메모리가 너무 큰 경우도 스왑이 너무 자주 일어나서 오버헤드가 발생하므로 성능에 좋지 않다.**

더티 메모리가 가장 집중해야할 최적화 대상이다. -> 동적할당들
클린 메모리 자주 발생하면 -> 오버헤드 발생

<br>

#### **iOS의 메모리 제한**

![Desktop View](/assets/img/post/unity/profilerios09.png){: : width="1600" .normal }

- Xcode 디버거에서 출력되는 메모리 샤용량 = Dirty 메모리 사용량
- 예시 그림의 경우 가상 메모리 할당량은 2GB 이상

<br>

![Desktop View](/assets/img/post/unity/profilerios10.png){: : width="1600" .normal }

- 어떤 앱의 Dirty 가 늘어난다?
> 앱의 Clean의 상주 메모리를 해제 -> Dirty를 위한 물리 메모리 공간 확보   
> 다른 백그라운드 프로세스의 메모리 사용량을 줄인다.

<br>

![Desktop View](/assets/img/post/unity/profilerios11.png){: : width="1600" .normal }

- **앱이 최대한 사용할 수 있는 메모리 샤용량은 Dirty 기준으로 계산된다.

<br>
<br>

#### **유니티에서는 무엇이 메모리 풋프린트를 남기는가?**

![Desktop View](/assets/img/post/unity/profilerios12.png){: : width="1600" .normal }

- **<span style="color:#FFC26A">유니티 네이티브 메모리</span>**
> 유니티의 C++ 레이어 : C#으로 Texture2D 에셋 로드 -> C++ Texture2D 객체와 함께 로드   
> 대부분 Dirty 메모리   
```
어째서 C# 소스코드를 사용하는데 C++ 일까에 대한 설명
유니티는 .NET 가상머신을 쓰는 C++ 엔진이다. 유니티의 네이티브 코어는 C++ 이고 이것을 관리하는 스크립트가 .NET, C# 이다.
```

- **<span style="color:#FFC26A">그래픽스</span>**
> 모바일은 GPU/CPU가 메모리를 공유한다. -> 통합 메모리 (Unified Memrory)   
> 텍스쳐, 셰이더 등의 그래픽 리소스 (Metal 리소스)   
> 그래픽스 드라이버   
> 대부분 Dirty 메모리

- **<span style="color:#75B8FF">네이티브 플러그인</span>**
> 코드 바이너리는 Clean 메모리이다.   
> 네이티브 플러그인의 **런타임 할당**은 **Dirty** 메모리이다.

- **<span style="color:#FFC26A">Unity Managed Memory</span>**
> .NET 가상머신이 제어하는 메모리   
> 유니티의 C# 스크립트 레이어의 메모리   
> 동적 할당 대부분은 Dirty 메모리

<br>
- <span style="color:#75B8FF">바이너리, 네이티브 플러그인 </span> -> Clean 메모리
- 나머지는 Dirty 메모리

<br>
<br>

#### **유니티 메모리 구조**

#### **네이티브와 관리되는 스크립트**

- 유니티는 .NET 가상 머신을 쓰는 C++ 엔진이다.
- 두 개의 레이어 존재
> 네이티브 코드 C++   
> 관리되는 스크립트 .NET, C#
- 어떤 에셋을 로드하게 되면 -> C# 버전과 C++ 버전 메모리 두 가지를 합해서 보여주게된다.

<br>

#### **게임 오브젝트의 바인딩에 대해**

![Desktop View](/assets/img/post/unity/profilerios13.png){: : width="400" .normal }

- UnityEngine.Object 를 상속한 .NET 오브젝트
- C++ 네이티브 인스턴스와 링크됨

<br>

#### **메모리 영역**

- **관리되는 메모리**(Managed Memory) : 자동으로 관리되는 영역
- **네이티브 메모리**(Native Memory) : 엔진의 C++ 레이어에서 사용하는 영역
- **C# 관리되지 않는 메모리**(Unmanaged Memory) : GC로 관리하지 않는 C# 코드 메모리 -> JobSystem, BurstCompiler 등에 사용

- 예시 : 폰트 에셋의 경우

![Desktop View](/assets/img/post/unity/profilerios14.png){: : width="400" .normal }

- 342.5 KB 네이티브 코드
- 32 B 관리되는 스크립트

<br>

#### **관리되는 메모리**

- 스크립팅 백엔드 가상머신(VM)에 의해 할당/제어 되는 곳
- 관리되는 힙 : 모든 C# 할당 - 동적 할당들
- C# 스크립팅 스택 : 지역변수들
- 네이티브 VM 메모리 : 가상머신을 위한 메모리 공간, 스크립팅 그 자체를 위한 할당, 메타 스크립팅(리플렉션, 제네릭 지원을 위한 메타 데이터들)
- GC(Garbage Collection)에 의해 할당들이 관리(정리)된다.
- 관리 대상인 할당들은 GC Allocation 또는 GC.Alloc 으로 표기된다.

<br>

#### **관리되는 메모리 : 실제 동작 방식**

![Desktop View](/assets/img/post/unity/profilerios15.png){: : width="600" .normal }

- 메모리 풀 확보 -> 메모리 리전 내에 유사한 크기의 오브젝트들을 담는 블록들이 나누어짐
> 사이즈별로 비슷한 애들끼리 모아서 블록 형성
- 새 객체는 블록 내부에 할당된다.

<br>

![Desktop View](/assets/img/post/unity/profilerios16.png){: : width="600" .normal }

- 객체가 파괴되면 블록에서 제거된다.
- 메모리 파편화 발생 가능

<br>

![Desktop View](/assets/img/post/unity/profilerios17.png){: : width="600" .normal }

- 완전히 빈 블록들은 OS에게 반환 가능하다
- **<span style="color:#FF0BB1">완전히 빈 블록은 커밋해제(decommitted)</span>**
- **<span style="color:#FF0BB1">VM 상으로는 여전히 예약되어 있지만 물리 메모리에 매핑되지 않음</span>**

<br>

![Desktop View](/assets/img/post/unity/profilerios18.png){: : width="600" .normal }

- 만약 기존 블록에 새로운 할당이 맞지 않는다면 새 메모리 리전을 예약한다.
- 기본 블록 크기보다 더 큰 할당은 커스텀 블록을 생성한다.
- 리전에서 블록이 할당되지 않은 공간 -> 물리 메모리에 매핑되지 않는다.

<br>

![Desktop View](/assets/img/post/unity/profilerios19.png){: : width="600" .normal }

- 기존 블록을 비슷한 크기의 오브젝트 할당에 재사용 할 수 있다.
- 만약 메모리 리전이 통째로 해제되면 -> 가상 메모리에는 확보 했지만 물리 메모리상에서는 디커밋 반환 해버리는 경우가 발생한다. (물리 메모리에 래핑이 안됨)
- 새로운 할당이 기존 블록에 못들어가면 -> 커스텀 블록 생성 및 할당

<br>
<br>

#### **유니티 메모리 프로파일러 분석**

![Desktop View](/assets/img/post/unity/profilerios20.png){: : width="1600" .normal }

<br>

#### **Summaries 탭**

![Desktop View](/assets/img/post/unity/profilerios21.png){: : width="600" .normal }

- Memory Usage On Devices : 실기기 메모리 사용량
- Allocated Memory Distribution : VM 할당 분포
- Managed Heap Utilization : 힙 활용도
- Top Unity Objects : 메모리 많이 쓰는 유니티 오브젝트

<br>

- **Memory Usage On Devices**

![Desktop View](/assets/img/post/unity/profilerios22.png){: : width="400" .normal }

- Total Resident : 상주 메모리
- Total Allocated : 할당량

<br>

- **Allocated Memory Distribution**

![Desktop View](/assets/img/post/unity/profilerios23.png){: : width="400" .normal }

- 카테고리 별 VM 할당량 분포
- **Native** : Natice C++, 네이티브 코드
- **Graphics** : metal에 의해 GPU 할당 메모리
- **Managed** : C#
- **Executable & Mapped** : Clean 메모리들, 바이너리, dll
- **Untracked** : symbol을 모를 때, 카테고리가 모호할 때 -> 카테고리 기능은 완벽하지않다. ex. 오디오 클립

- **카테고리는 완벽하지 않다!**
> 종류가 애매한 경우   
> 분류할 수 없는 경우   
> 버전에 따라 분류 기조가 다른 경우
- Unknown, Others, Untracked 는 유니티가 모르거나 카테고리로 분류할 수 없는 할당을 의미한다.
> ex. 플러그인의 할당(안드로이드 플러그인으로 로그인 기능 만들때 라던가..), 유니티 앱에서 발생한 할당

![Desktop View](/assets/img/post/unity/profilerios25.png){: : width="400" .normal }

- 상주 메모리 비율도 보여준다.

![Desktop View](/assets/img/post/unity/profilerios27.png){: : width="400" .normal }

- Untracked 가 크다고 문제가 있다! 라고는 볼 수 없다.
- ex. MALLOC_NANO
> **미리 확보한 힙공간을 의미한다.**
> 할당 크기 : 502.1 MB
> 상주 메모리 : 3.3 MB

<br>
<br>

-**Managed Heap Utilization**

![Desktop View](/assets/img/post/unity/profilerios28.png){: : width="400" .normal }

- 힙의 활용도를 보여줌
> 우리가 직접 제어하기는 힘든 영역이다.
- Virtrual Machine
- Empty Heap Space
- Objects

<br>

- **Virtual Machine**
   - VM 머신, 스크립팅 그 자체를 위한 할당
   - 제네릭, 타입 메타 데이터, 리플렉션
   - **런타임 동안 계속 커지는 경향이 있다.**
   - **줄이는 방법**
   > 1. **코드 스트립**   
   ```
   - 엔진 코드 스트립 - 유니티 엔진 모듈 내에서 앱 빌드 시 쓰이지 않는 코드를 찾아서 스트립
   - Managed Code Strip Level
   둘 다 사용하자, 리플렉션을 사용하면 에러가 터질 수 있으니 link.xml 에서 특정 클래스는 사용하도록 명시할 수 있다.
   ```
   > 2. **리플렉션 안쓰기**   
   > 3. **제네릭 쉐어링(유니티 2022 이상)**

- **Empty Heap Space**
- 빈 힙공간
- 새 할당이 들어갈 수 있다.
- 다음 GC때 수집될 버려진 오브젝트가 있을 수도 있다.
- PM에서 언맵된 페이지는 제외
- Empty Heap Size 가 크면 메모리 파편화가 심하다고 볼 수 있다. -> 동적할당 과정에서 CPU 오버헤드가 발생, 불필요하게 점유한 메모리가 크다는 의미

- 구 버전   

   ![Desktop View](/assets/img/post/unity/profilerios29.png){: : width="400" .normal }

   ![Desktop View](/assets/img/post/unity/profilerios30.png){: : width="400" .normal }

- 구버전 에서는 Active, Fragmented 두 종류로 분리되어있음
- Active Empty Heap Space : 연속 힙 메모리 블록에서 빈 공간(우선순위 높음)
- Fragmented Empty Heap Space : 파편화된 힙 메모리 블록에서 빈 공간
- Fragmentation 에 대해 사용자가 직접 할 수있는건 없다.

<br>

- **GC 실행 구조**
- 빈블록 형성은 알고리즘이 있음.
1. 새 할당 발생
2. 우선 연속 힙 공간의 빈공간(=Active Empty Heap Space)에서 할당 시도 (빠름)
3. 그 다음에는 전체 빈 블록 목록, 이외에 힙의 남은 공간을 스캔해서 할당 시도 (느림)
4. 그래도 공간이 없으면 GC Collection 트리거
- Incremental GC 를 사용한다면 GC Collection 과 동시에 힙을 확장한다.
> **gc_call_with_alloc 이라는 symbol 로 표기된다.**
- Incremental GC 를 사용하지 않는다면 GC Collection 이후에도 공간이 여전히 없다면 힙을 확장한다.
> gc_expand_hp_inner

- **Incremental GC 설정을 권장함.**

<br>

#### **Unity Objects 탭**

![Desktop View](/assets/img/post/unity/profilerios31.png){: : width="800" .normal }

- 유니티 오브젝트들의 할당량을 보여준다.
- Native Size(C++), Managed Size(C#), Graphics Size 세 가지 메모리 할당률로 보여준다.
- 상주 메모리 비율도 보여준다.

<br>

#### **All of Memory 탭**

![Desktop View](/assets/img/post/unity/profilerios32.png){: : width="800" .normal }

- VM 전체 할당 객체들을 보여준다.
- Untracked, Reserved 포함

<br>

#### **Memory Map**

![Desktop View](/assets/img/post/unity/profilerios33.png){: : width="800" .normal }

- 숨겨진 기능
- 페이지별 메모리 맵
- 어떤 주차게 해당 페이지를 점유했는지 파악 가능
> Device + IOACCELERATOR : GPU를 위한 할당   
> Native Allocation : 유니티 네이티브 코드에서 할당
- 구체적인 객체 이름이 안보임. 어떤 프레임워크나 바이너리가 점유했는지 파악이 가능

<br>

![Desktop View](/assets/img/post/unity/profilerios34.png){: : width="800" .normal }

- 512 * 512 텍스쳐의 할당량이 2.7 MB ?
- 네이티브 1.3MB + 그래픽스 1.3 MB ?
- 언제, 왜 이런 할당이 일어나는지 궁금한 경우 -> iOS 네이티브 프로파일러로 파악이 가능하다.
- 메모리 프로파일러는 스냅샷 이기 때문에 콜 스택을 파악하기 힘듦

<br>
<br>

## **네이티브 프로파일러 사용하기 : Xcode Instruments**

- [Xcode Instruments 사용 방법](https://epheria.github.io/posts/instruments/)
- **또는 Xcode 에서 Instruments 를 켜도 됨.**

![Desktop View](/assets/img/post/unity/profilerios35.png){: : width="600" .normal }

- **Xcode - Build Settings 내부에서 디버그 심볼을 반드시 포함해줘야한다.**

![Desktop View](/assets/img/post/unity/profilerios36.png){: : width="400" .normal }

- **Xcode - Open Developer Tools 선택**

![Desktop View](/assets/img/post/unity/profilerios37.png){: : width="600" .normal }

- **Instruments 템플릿 중에서 Allocation 선택**

<br>

#### **VM 트래커**

![Desktop View](/assets/img/post/unity/profilerios38.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/profilerios39.png){: : width="600" .normal }

- **앱의 모든 VM 할당을 살펴 볼 수 있다.**

![Desktop View](/assets/img/post/unity/profilerios40.png){: : width="800" .normal }

- **Binaries/Code (클린 메모리) : _LINKEDIT, _TEXT. _DATA, _DATA_CONST**
- **"GPU" : 유니티 GPU 처리를 의미한다. IOKit, IOSurface, IOAccelerate**
- **App Allocations : 유니티 CPU 처리를 의미한다. Malloc_* , VM_ALLOCATE**
- **Performance tool data**

![Desktop View](/assets/img/post/unity/profilerios41.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/profilerios42.png){: : width="800" .normal }

- **IOSurface 그래픽스 할당의 상주 메모리 비율이 100%이다. -> 물리 메모리에 100% 할당**
- **이 물리 메모리를 넘어서면 앱이 터짐**


![Desktop View](/assets/img/post/unity/profilerios43.png){: : width="800" .normal }

- **0x10da50000 오브젝트는 어디에 있을까?**

![Desktop View](/assets/img/post/unity/profilerios44.png){: : width="800" .normal }

![Desktop View](/assets/img/post/unity/profilerios45.png){: : width="800" .normal }

- **IL2CPP VM의 제네릭 메타 데이터 테이블 초기화 과정의 할당임을 확인할 수 있다.**

<br>

#### **콜스택 검색**

![Desktop View](/assets/img/post/unity/profilerios46.png){: : width="800" .normal }

- **하단의 검색창에서 검색 가능!**

<br>

![Desktop View](/assets/img/post/unity/profilerios47.png){: : width="800" .normal }

- **dirty size 가상 메모리 할당 내에서 dirty 인 애들 - 상주메모리에서 빼기 힘든애들**
- **swapped   스왑된 애들**
- **resident 상주 메모리**

![Desktop View](/assets/img/post/unity/profilerios48.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios49.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios50.png){: : width="800" .normal }

<br>

![Desktop View](/assets/img/post/unity/profilerios51.png){: : width="800" .normal }

- Allocations 에서 상주 메모리 비율도 볼 수 있음

<br>

- **추가 정보**
- Memory Graph : 네이티브 메모리 스냅샷 도구
- WWDC 2022 - Profile and optimize your game's memory

- **앱이 꺼지는 이유 파악 : 메모리 때문인지?**

- 앱이 안꺼지는 동안 메모리 프로파일러 스냅샷 찍어서  -  메모리를 과하게 쓰고있는지 파악

- ios xcode debugger 붙인 상태에서 게임플레이 -> 크래시 -> 크래시 잡을 수 있음

- 크래시가 메모리 때문인지? 에러 때문인지 파악가능

- **메모리 문제라면?**

- 메모리 프로파일러를 보면서 - Unity Objects, SUmmaries 탭에서 total commiteed 영역에서 가장 큰 메모리를 쓰는 영역을 순서대로 정리 후 파악

- **레이아웃에 대한 처리**
- 순환 레이아웃 문제 때문에
- dirty 여부 판단 - 프레임 마지막에 레이아웃을 갱신
- 항상 매프레임의 마지막으로 밀린다?  레이아웃을 강제로 갱신시키는 api 가 있을까?

- **기타 정보**
- 모바일 - Unified memory
- 윈도우 - VRAM
- 텍스쳐 read/write 설정 - cpu 메모리에도 올라감






