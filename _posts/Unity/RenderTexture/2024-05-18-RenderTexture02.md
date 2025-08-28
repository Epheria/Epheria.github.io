---
title: Unity RenderTexture - 스크린 캡쳐시 PostProcessing 효과 적용안되는 버그 수정
date: 2024-05-18 10:00:00 +/-TTTT
categories: [Unity, RenderTexture]
tags: [Unity, RenderTexture, PostProcessing, ScreenCapture, ScreenShot, RenderTextureFormat, TextureFormat, ARGB32, RGBAHalf, ARGBHalf]     # TAG names should always be lowercase

toc: true
toc_sticky: true
---
[![Hits](https://hits.sh/epheria.github.io.svg?view=today-total&label=visitors)](https://hits.sh/epheria.github.io/)

---

<br>
<br>

## 주요 에러 현상 분석

- 에러 발생 플랫폼 : aos, ios, 유니티 에디터(Mac, Windows) 전부
- 렌더 파이프라인 : URP
- 코루틴으로 yield return new WaitForEndofFrame() 을 기다린 뒤, RenderTexture 를 동적 생성하고 현재 카메라의 Output Texture 에 할당 후 1회 렌더하여 Texture2D에 카메라가 렌더하는 텍스처를 ReadPixels 를 실행하여 픽센 단위로 새로 만들어서 저장하는 코드이다.

<br>

- 처음에는 렌더링 파이프라인의 렌더 순서 때문에 발생한 문제인 줄 알았다. 특히 빌트인 렌더파이프라인에서는 크게 놓고 보면 OnPreRender -> OnPostRender -> OnRenderImage 순서로 렌더링이 이루어지는데, 여기서 OnPostRender 에서 카메라가 씬 렌더링을 마치고 OnRenderImage 에서 포스트 프로세싱을 진행한다. 하지만 프로젝트는 URP 였기 때문에, ScriptableRenderPass 쉐이더나 렌더패스로 처리를 하려고 했으나 생각대로 잘 되지 않았다. 정리하자면 코루틴의 WaitForEndofFrame 보다 더 늦게 포스트 프로세싱 렌더가 적용되어서 안되는 줄 알았다.

<br>
<br>

#### 에러 현상

![Desktop View](/assets/img/post/unity/rendertex01.png){: : width="500" .normal }     
_스크린 캡쳐를 실행하기 전 카메라 렌더_

<br>

![Desktop View](/assets/img/post/unity/rendertex02.png){: : width="500" .normal }     
_스크린 캡쳐 후 저장한 이미지를 로드하여 이미지에 렌더_

<br>

- 위 사진 두장을 확인해보면 확실히 포스트 프로세싱만 빠져있다는 것을 확인할 수 있다.

<br>
<br>

#### 기존 RenderTexture 스크린샷 코드

```csharp
private RenderTexture rt;

rt = new RenderTexture(pixelWidth, pixelHeight, 24, RenderTextureFormat.ARGB32);
var prev = _camera.targetTexture;

_camera.targetTexture = rt;
_camera.Render();

screenTex = new Texture2D(pixelWidth, pixelHeight, TextureFormat.ARGB32, false);

RenderTexture.active = rt;

Rect area = new Rect(0f, 0f, pixelWidth, pixelHeight);

screenTex.ReadPixels(area, 0, 0);
screenTex.Apply();

_camera.targetTexture = prev;
```

<br>
<br>

## 해결방법

- 일단, 위에서 언급한 렌더파이프라인의 렌더링 순서가 원인이 아니였다. 원인은 바로 **'RenderTextureFormat', 'TextureFormat'** 에 있었다..

<br>

#### TextureFormat 과 RenderTextureFormat 에 대해

- **Texture Format**
- 유니티 텍스처 포맷은 텍스처 데이터를 저장하는 방법을 정의한다. 텍스처 포맷은 주로 이미지 품질, 메모리 사용량, 압축 여부 및 성능에 영향을 준다. [Texture Format](https://docs.unity3d.com/ScriptReference/TextureFormat.html)

<br>

- **RenderTexture Format**
- 렌더 텍스처 포맷은 렌더링 결과를 저장할 때 사용하는 포맷이다. 주로 포스트 프로세싱, 쉐이더 연산, 동적 텍스쳐 생성등에 사용된다. [RenderTexture Format](https://docs.unity3d.com/ScriptReference/RenderTextureFormat.html)

<br>

- 즉, 이 현상의 원인은 RenderTexture Format, Texture Format 과 색상 범위 및 정밀도에 대한 문제였던 것이다.
- 특히 기존 코드에서 사용중인 **'ARGB32'** 이녀석이 문제였다.

<br>
<br>

#### 수정된 코드

- 포스트 프로세싱 효과를 렌더 텍스쳐에 제대로 반영하려면 HDR 처리가 가능한 포맷을 적용해야한다.
- 하지만 기존 코드의 ARGB32 는 HDR 처리가 불가능한 범위(8비트)를 지녔기 때문에 포스트 프로세싱 효과가 반영이 안되었던 것이다.

```csharp
private RenderTexture rt;

rt = new RenderTexture(pixelWidth, pixelHeight, 24, RenderTextureFormat.ARGBHalf);
var prev = _camera.targetTexture;

_camera.targetTexture = rt;
_camera.Render();

screenTex = new Texture2D(pixelWidth, pixelHeight, TextureFormat.RGBAHalf, false);

RenderTexture.active = rt;

Rect area = new Rect(0f, 0f, pixelWidth, pixelHeight);

screenTex.ReadPixels(area, 0, 0);
screenTex.Apply();

_camera.targetTexture = prev;
```

> **ARGB32**      
>      
> - ARGB32 는 8비트 정수로 각 채널을 저장하므로, 0-255 범위의 값을 갖는다. 이는 LDR(Low Dynamic Range) 이미지를 저장하는데 적합하다.     
> - 따라서, 포스트 프로세싱 효과(블룸, 톤 매핑 등)는 종종 높은 동적 범위와 정밀도를 필요로 하기 때문에 ARGB32 포맷은 이러한 높은 범위를 저장할 수 없기 때문에 RenderTexture 에 포스트 프로세싱 효과가 제대로 적용되지 않았던 것이다.
{: .prompt-info}

<br>

> **ARGBHalf,RGBAHalf**      
>     
> - 16비트 부동 소수점으로 각 채널을 저장하므로, ARGB32 에 비해 훨씬 넓은 범위의 값을 저장할 수 있다. 즉 HDR 처리를 지원한다.     
> - 포스트 프로세싱 효과는 일반적으로 HDR 처리를 필요로 함.
{: .prompt-info}

<br>
<br>

#### 해결된 사진

![Desktop View](/assets/img/post/unity/rendertex03.png){: : width="500" .normal }     
_RenderTextureFormat 을 ARGBHalf 로 변경 후 스크린샷_

<br>

> **참고**      
> TextureFormat 도 Half 로 꼭 변경해야하는지는 의문이다. 테스트 결과 TextureFormat 을 ARGB32 로 놓아도 RenderTexture 만 ARGBHalf 로 해놓으면 제대로 포스트 프로세싱이 반영되었다.     
> 즉, 이미 RenderTexture 에 포스트 프로세싱 효과가 적용된 상태에서의 데이터를 가지고 TextureFormat 에 읽어들여서 저장하기 때문에 그대로 적용된게 아닐까 추측한다.
{: .prompt-warning}
