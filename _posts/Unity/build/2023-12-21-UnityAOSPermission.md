---
title: Unity AOS Permission 이 안빠지는 이슈 해결 방법
date: 2023-12-21 12:59:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Jenkins, 자동화]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fepheria.github.io&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=views&edge_flat=false)](https://hits.seeyoufarm.com)

---

- **Unity AOS Permission 이 안빠지는 이슈가 발생했다..**
- **사용하지도 않는 READ_EXTERNAL_STORAGE 외부 저장소 권한이 활성화가 계속 빌드에 포함이되었다.**

   ![Desktop View](/assets/img/post/unity/unityaosperm01.png){: : width="800" .normal }

<br>

## **원인 분석**

- 일단 AndoridMnaifest 파일안에 해당 권한을 사용하고 있는 곳은 없었다.
- 전체찾기로 사용하고 있는 곳을 찾아봤는데..

   ![Desktop View](/assets/img/post/unity/unityaosperm04.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/unityaosperm03.png){: : width="800" .normal }

- Unity.Notifications.Tests 의 internal class 인 PostprocessorTests 라는 유니티 패키지 캐시 파일이 존재했고
- 여기서 해당 권한을 사용하고 있었다.. 더 깊이 찾아보니 이게 유니티 패키지인 Mobile Notification 패키지안에 들어가있는 클래스였다.

   ![Desktop View](/assets/img/post/unity/unityaosperm05.png){: : width="800" .normal }

<br>

## **해결 방법**

1. AndroidManifest 파일에 지우고 싶은 권한이 있는지 확인하기. 나같은 경우는 READ_EXTERNAL_STORAGE
2. 컴파일러(라이더or비쥬얼스튜디오)에서 전체 찾기 모드로 빼고 싶은 권한을 검색해서 사용하고 있는 곳이 있는지 확인하기.

- 권한 예시
```
  <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
```

3. 만약 빼고싶은 권한이 있다면 과감하게 삭제를 해주자.
4. 하지만, 유니티 패키지, 플러그인 등에 포함되어 있을 경우가 있으니 확실하게 처리해줘야한다.

- **remove 를 명시해줌으로써 해결할 수 있었다.**
```
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" tools:node="remove" />
```

- 결과물
   ![Desktop View](/assets/img/post/unity/unityaosperm02.png){: : width="800" .normal }