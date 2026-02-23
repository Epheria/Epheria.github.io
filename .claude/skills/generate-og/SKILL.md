---
name: generate-og
description: 블로그 포스트용 OG(Open Graph) 미리보기 이미지를 생성한다. 배경 이미지 위에 카테고리명, 작성자, URL을 오버레이하여 1200x630 크기의 OG 이미지를 만든다. 카테고리별 OG 이미지가 필요하거나, 포스트 미리보기 이미지를 만들 때 사용한다.
argument-hint: <source-image> <category-name> [options]
allowed-tools: Bash(python3 *), Read, Edit, Glob, Grep
---

# OG 이미지 생성기

블로그 포스트의 OG(Open Graph) 미리보기 이미지를 생성하는 스킬이다.

## 사용법

### 기본 사용

```bash
python3 .claude/skills/generate-og/scripts/generate_og.py <source-image> <category-name>
```

`<source-image>`는 배경으로 사용할 이미지 경로, `<category-name>`은 이미지에 표시할 카테고리명이다.

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-o`, `--output` | 출력 경로 | `assets/img/og/{category}.png` |
| `-c`, `--color` | 악센트 색상 (R,G,B) | 카테고리별 자동 |
| `--alpha` | 오버레이 어둡기 0-255 | 140 |
| `--subtitle` | 부제 텍스트 | `Sehyup  \|  Game Programmer` |

### 예시

```bash
# Security 카테고리 OG 생성
python3 .claude/skills/generate-og/scripts/generate_og.py ~/Downloads/hacker.png Security

# 커스텀 색상과 출력 경로
python3 .claude/skills/generate-og/scripts/generate_og.py ~/Downloads/bg.png Unity -c "100,200,100" -o assets/img/og/unity.png

# 오버레이 밝기 조절
python3 .claude/skills/generate-og/scripts/generate_og.py ~/Downloads/bg.png ML --alpha 160
```

## 생성 결과

- 크기: 1200x630 (OG 표준)
- 구성: 배경 이미지 + 어두운 오버레이 + 왼쪽 그라디언트 + 텍스트
- 텍스트 요소: 카테고리명, 부제(작성자), 악센트 라인, epheria.github.io

## 포스트에 적용하기

생성된 OG 이미지를 포스트에 적용하려면 front matter에 `image:` 추가:

```yaml
image: /assets/img/og/{category}.png
```

## 카테고리별 기본 악센트 색상

| 카테고리 | 색상 (R,G,B) |
|---------|-------------|
| Security | 100, 180, 160 (teal) |
| Network | 60, 180, 220 (cyan) |
| Unity | 100, 200, 100 (green) |
| Unreal | 80, 120, 220 (blue) |
| Csharp | 150, 100, 220 (purple) |
| Cpp | 60, 120, 200 (blue) |
| ML | 220, 140, 60 (orange) |
| Mathematics | 180, 100, 180 (magenta) |
| Python | 60, 160, 200 (sky blue) |
| Common | 140, 160, 180 (gray) |
| ETC | 140, 160, 180 (gray) |

## 의존성

- Python 3
- Pillow (`pip3 install Pillow`)
- 폰트: Roboto (macOS: `/Library/Fonts/Roboto-*.ttf`, Linux: `/usr/share/fonts/truetype/roboto/`)
