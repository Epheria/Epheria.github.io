---
title: Render Pipeline Lecture
date: 2023-09-04 18:00:00 +/-TTTT
categories: [ETC, RenderPipeline]
tags: [renderpipeline, game-engine]

difficulty: intermediate
lang: en
toc: true
---

11/25 Sat

Core Analysis of Game Engines - Prof. Seongwan Kim

g-Matrix3d neo -> GitHub open source

https://github.com/idgmatrix?tab=repositories

1. Game Engines and Rendering

DirectX 12, Metal, Vulkan:
- APIs are completely different from DirectX 11.

Framebuffer:
- Component that draws to the screen.

GPU chip internal memory is important:
- Setting internal memory is expensive (state changes, texture changes).
- Internal cache often needs to be flushed and refilled.

Rasterizer:
- Process that pixelizes vertices.
- Triangle polygons are converted to pixels.

Anti-aliasing:
- Pixel correction/smoothing.

Why textures are packed as atlases, and why frequent texture switching is bad:
- GPU cache often stores in tiled or zigzag patterns.
- If address locality is poor or processing is not contiguous, performance drops.

Z-buffering:
- Compares depth value `z` per pixel.
- Uses a depth buffer.
- `z-fighting` can happen when surfaces are too close.

Chris Hecker - Texture Mapping:
- Hyperbolic interpolation.
- Texture mapping.

Types of rendering methods:
- Forward rendering
  - Oldest basic approach.
  - Draws what is in front as it goes.
  - Used again widely due to VR.
  - After per-object work (vertex, shading, etc.), pixels can be overdrawn heavily, so waste is large.

- Deferred rendering
  - Means delayed rendering.
  - Good for complex lighting, shadows, reflections.
  - Stores only data needed for lighting into buffers, then computes visible parts at the end.
  - Faster because it shades only visible final pixels.
  - Uses G-buffer (Geometric Buffer).
  - Drawback: transparent materials need separate handling.
  - At high resolutions (4K+), G-buffer memory cost is high and not suitable for mobile.

- Forward+ rendering
  - Uses light heat maps and clustered light data.
  - Pre-computes where lighting calculations are needed.
  - One of the latest practical approaches.

- TBDR: Tile Based Deferred Rendering
  - Happens at hardware level; mobile devices execute this internally, so we cannot control it directly.
  - Common on mobile.
  - Renders in tiles to reduce memory consumption.

Rendering pipeline by engine:

Unity

URP
- Supports Forward, Deferred, and Forward+.

HDRP
- Designed for high-quality real-time rendering.

Unreal Engine 5
- Deferred by default.
- Forward can be enabled when needed.

VR must render two images (left and right),
so Forward is generally preferred over Deferred.

Godot Engine
- Forward+
- Tile-based on mobile
- Compatible with GLES-based rendering

Chapter 2. Structure of the Rendering Pipeline

* Coordinate system transformations

Transform pipeline (OpenGL):
- Fundamental backbone.

Types of coordinate systems:
- Left-handed (DirectX) vs right-handed (OpenGL).
- Axis rotation direction conventions are opposite.
- Right-handed: clockwise is `+`, left-handed: counterclockwise is `+` (as taught in this note).
- Cross-product result direction flips depending on handedness.
- Normal vector direction also flips depending on coordinate system.
- You cannot distinguish handedness from formula alone; the cross-product formula itself is the same.

Also used:
- Spherical coordinates (astronomical viewpoint)
- BRDF (Bidirectional Reflectance Distribution Function): incident and reflected light, etc.
- Spherical harmonics (used in quantum mechanics and lighting)
- Cylindrical coordinates

Texture coordinate system (UV origin and direction):
- Some systems use bottom-left origin, others top-left.
- This is why textures sometimes look flipped.
- Unity uses bottom-left origin.

Mathematical properties of matrix transforms:
- Why represent 2D transforms with `3x3`?
- Translation: addition
- Scale and rotation: multiplication
- We need one unified multiplication-based framework.

Mixed matrix operations:
- Rotation is multiplication, translation is addition.
- If all transforms are expressed with multiplication -> affine transform.
- Achieved by adding one extra coordinate.

Extend to homogeneous coordinates:
- All 2D transforms can be represented as multiplication by `3x3` matrices.
- Translation, rotation, scale, and shear are all supported.

Rigid / Euclidean transform:
- Preserves length and angle.
- Identity, translation, and rotation.

Rigid body:
- Shape never changes; only position and rotation change.

Rotation transform matrix:
- Orthogonal matrix.
- Inverse matrix, transpose matrix, and angle negation are closely related (equivalent for pure rotation).

Similarity transform (scaling):
- Isotropic scaling.
- Angles are preserved.

Linear transform:
- Multiplication by constants.
- Representable by matrix multiplication.

Affine Transformation:
- Parallel lines are preserved.
- Algebraically, adds constant terms to linear equations.
x' = ax + by + c
y' = dx + ey + f
- The set of affine transforms can be represented as first-order polynomials.
- Orthographic projection is closely related.

Projective Transformation:
- Straight lines stay straight, but parallel lines are not preserved.
- Perspective projection.
- Cannot be fully expressed by only affine matrix multiplication.
- Perspective.

General nonlinear transforms:
- Straight lines are not preserved.
- Pincushion distortion and barrel distortion.
- Used in VR (e.g., Oculus Rift barrel distortion). Historically a lens problem, now often compensated by rendering effects.

Fish-eye transform:
- Useful for underwater-like visual expression.

360-degree panorama transforms also exist.

Importance of transform order:

Same 90-degree rotation and same x-translation can produce different results:
1. Rotate 90 degrees -> translate along x
2. Translate along x -> rotate 90 degrees

Composition of transforms and matrix multiplication:
- Matrix multiplication is not commutative.
- Result changes by composition order.

Transform order vs matrix multiplication order:
- In D3D, transform order and matrix multiplication order match (position vector: row vector).
- In OGL, transform order and multiplication order are reversed (position vector: column vector).

This difference comes from row-major and column-major conventions.

World transform order:
- Standard convention
- SRT: Scale -> Rotation -> Translate

Unity Euler angle rotation order: `Z, X, Y`

X-axis rotation: Pitch
Y-axis rotation: Yaw
Z-axis rotation: Roll

This order helps avoid camera gimbal lock.

Model space -> world space

For rotation representation:
- In 2D, complex numbers can be used.
- In 3D, quaternions are used.

Camera transform matrix:
- View transform.
- Camera transform is the inverse of the camera rigid transform in world space.
- `(R * T)^-1 = T^-1 * R^-1`

Normal vector transform characteristics:
- Requires different treatment from point coordinates.
- Isotropic scaling is usually fine, but scaling only one axis can change normals.
- Even under anisotropic scaling, normals must still represent correct perpendicular directions.
- If two vectors have dot product `0`, they are perpendicular.

Perspective projection matrix:
- One of the hardest parts of pipeline transforms.
- Depth handling is tricky because values are remapped.
- `z` range must be suitable for z-buffering.
- FOV and view range should be easy to control.

After applying z-buffering and perspective projection:
- Coordinates become NDC (Normalized Device Coordinates).
- View frustum must be mapped to NDC.

Chapter 3. Ray Tracing Practice

GLSL

Light properties:
- Wave-particle duality.

Snell's law:
- Refraction angle can be computed from index of refraction.

Refractive index:
- Vacuum 1.0, air 1.003, water 1.33...

Wave refraction:
- Huygens' principle.

Light energy:
- Reflection, absorption, refraction (energy conservation).

Modern physically-based engines also consider light energy behavior:
- When light is incident, some is reflected and some is absorbed.

Principle of reflected color:
- Material and albedo/base color.

Reflective behavior: Fresnel effect
- Reflection is stronger at grazing angles.
- Reflection profile changes with incident angle.
- Fresnel equations describe polarization behavior.
- Reflectance differs for transverse and longitudinal components.
- Energy conservation is also handled through Fresnel terms.
- Fresnel reflectance differs between dielectrics and metals.
- During refraction, index also changes by wavelength -> rainbow.
- Wave interference exists: constructive and destructive.
- Example: soap-film interference (constructive), anti-reflection coating on glasses (destructive).
- Wave diffraction.
- Light scattering -> clouds, Rayleigh scattering, Mie scattering.
- Blue sky -> Rayleigh scattering in the atmosphere.

- Can be studied in detail in "Physics and Math of Shading".

Phong reflection model formula = Specular + Diffuse + Ambient
- Ignores strict energy conservation; values are summed directly.
- Represents older-style computer graphics (plastic look).

Specular:
- Mirror-like reflection on smooth surfaces.

Diffuse:
- Scattered reflection on rough micro-surfaces.

- Face normal, vertex normal, pixel normal (modern).
- Phong shading: interpolate vertex normals and compute lighting per pixel.

Normal map:
- Limitation: fake detail method; does not change geometry. Artifacts can be noticed on close inspection.

Today:
- More realistic reflection models such as PBR are common.
- Especially for realistic skin rendering.
- For metals, BRDF helps represent realistic material surfaces.

PBR: Physically Based Rendering

GI: Global Illumination
- Handles indirect lighting.
- Classical approach -> baked lighting.
- Modern approach -> real-time GI such as Lumen in Unreal Engine 5.
- Ray tracing: reflection, refraction.
- Radiosity: diffuse reflection only.

ShaderToy (WebGL based)

https://www.shadertoy.com/user/kaswan/sort=popular&from=0&num=8

WebGL < OpenGL ES < OpenGL

A next-generation WebGL path appeared this year: WebGPU.
- Heavily used in AI workloads.
- WebGL uses C-style GLSL syntax, somewhat similar in feel to Unity HLSL.

Fractal rendering:
- Uses formulas for the Mandelbrot set.
- Represented in complex number space.

Ray tracing:
- Uses the same law where incident angle equals reflection angle.
- Casting rays from the camera is equivalent to tracing light paths toward the camera.
- Can be implemented with relatively simple small ray setups.
- Shadows are easier to render.
- After hardware ray tracing became available,
- common hybrid approach: polygon rendering for most geometry, ray tracing for shadows and reflections.
- In ray tracing, spheres are among the easiest primitives to render.
- Sphere intersection is straightforward with quadratic equations.
- Conclusion: study math well.
