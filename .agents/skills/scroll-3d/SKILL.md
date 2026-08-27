---
name: scroll-3d
description: >
  Turns a one-line brief into a deployed, scroll-driven 3D website using Three.js (pinned r160)
  and Canvas frame scrubbing. Supports 7 rendering techniques (video-scroll-effect, 3d-scene-effect,
  pointer-follow-effect, click-navigate, physics-play, hybrid-2d3d, cursor-trail) and shared choreography.
argument-hint: "[site brief or reference URL]"
license: MIT
metadata:
  version: "1.0.0"
  tags: ["threejs", "webgl", "scroll-driven", "3d", "canvas", "frontend"]
---

# Scroll-3D

Generates production-grade, scroll-driven 3D web experiences from a single brief or reference structure.

## Quick Architecture

```
User Brief → site-planner (Intake & Plan JSON)
                ↓ [Approval Checkpoint]
Technique Builders (video-scroll | 3d-scene | pointer-follow | click-navigate | physics | hybrid | cursor-trail)
                ↓
shared-scroll-engine (Scaffold: index.html + styles.css + choreography.js + <engine>.js)
                ↓
build-reviewer & DESIGN.md (Pre-deploy QA & plan deviation validation)
```

---

## 1. Site Planning & Intake (`site-planner`)

The `site-planner` is the structural decision-maker:
1. Analyzes product brief or reference site.
2. Generates a JSON site plan containing:
   - Color palette (`bg`, `primary`, `accent`, `text`)
   - Section sequence with designated technique per section
   - Per-section asset requirements
   - Estimated resource requirements
3. Outputs an **Approval Checkpoint** before generating code.

### Canonical Scaffold

Every generated project uses this shared layout:
- `index.html`: Unified shell loading Three.js r160, base stylesheets, and engine scripts.
- `styles.css`: Base layout, sticky viewports, section spacers, typography, responsive rules.
- `choreography.js`: Shared scroll position calculation, lerp/smoothing math, pointer tracking, and color interpolation.
- `<technique>.js`: Modular engine script for each active technique in the plan.
- `frames/`: (Optional) sequential JPG/WebP assets for video-scroll sections.

> **Important**: Three.js is pinned to **r160** (`https://cdnjs.cloudflare.com/ajax/libs/three.js/r160/three.min.js`) for stable UMD build compatibility.

---

## 2. Seven Technique Modules

### 1. `video-scroll-effect` (Canvas Frame Scrub)
- Canvas element fixed in viewport with sticky positioning (`position: sticky; top: 0; height: 100vh;`).
- Preloads image sequence into an array of `Image` objects.
- Draws image matching current section normalized progress:
  $$\text{frameIndex} = \lfloor \text{progress} \times (\text{totalFrames} - 1) \rfloor$$
- Renders to `<canvas>` using `ctx.drawImage` maintaining aspect ratio (`cover` / `contain`).

### 2. `3d-scene-effect` (Scroll-Driven Three.js)
- Pinned Three.js r160 WebGLRenderer with alpha transparency and tone mapping.
- Camera position, rotation, and mesh morphs/transforms lerped based on section scroll progress:
  ```javascript
  camera.position.z = THREE.MathUtils.lerp(zStart, zEnd, progress);
  model.rotation.y = THREE.MathUtils.lerp(rotStart, rotEnd, progress);
  ```
- **Fallback**: Zero-cost `image-plane` (3D billboard with texture plane) if complex 3D models are unavailable.

### 3. `pointer-follow-effect` (Cursor Parallax)
- Tracks normalized mouse coordinates $(-1.0 \text{ to } +1.0)$.
- Smooths motion with damping factor ($\alpha \approx 0.05$).
- Degrades gracefully to static pose on touch / mobile devices (`@media (pointer: coarse)`).

### 4. `click-navigate` (Waypoint Camera Navigation)
- Interactive 3D hotspots using Three.js `Raycaster`.
- On click / tap, slerps camera quaternion and lerps position to designated target waypoint.
- Fully compatible with both touch and desktop inputs.

### 5. `physics-play` (Three.js + Cannon-es)
- Integrates physical world simulation with rigid bodies and colliders.
- Syncs Three.js meshes with Cannon physics bodies inside the render loop.
- **Rule**: Heaviest technique; limit to at most one section per site.

### 6. `hybrid-2d3d` (Editorial Layout + Embedded WebGL)
- Clean responsive HTML/CSS editorial typography with embedded 3D canvas viewport.
- Non-pinned floating 3D objects that react to scroll triggers and section entry/exit.

### 7. `cursor-trail` (2D Canvas Particle Trail)
- Lightweight 2D canvas overlay.
- Emits fading particle trails following pointer coordinates.
- Non-load-bearing, atmospheric effect.

---

## 3. Shared Choreography (`choreography.js`)

Central math engine for scroll calculation and lerping:

```javascript
export const Choreography = {
  getSectionProgress(element) {
    const rect = element.getBoundingClientRect();
    const total = element.offsetHeight - window.innerHeight;
    if (total <= 0) return 0;
    const current = -rect.top;
    return Math.min(Math.max(current / total, 0), 1);
  },
  lerp(start, end, factor) {
    return start + (end - start) * factor;
  },
  damp(current, target, lambda, dt) {
    return THREE.MathUtils.damp(current, target, lambda, dt);
  }
};
```

---

## 4. Honesty Guarantees & Quality Gates

Every build must follow these rules:
1. **No Silent Fallbacks**: If a video or asset is missing, return explicit failure rather than silently altering technique without logging.
2. **Plan Deviations**: Any deviation from the approved site plan must be recorded in `DESIGN.md`.
3. **`DESIGN.md` Generation**: Every project must output a `DESIGN.md` documenting:
   - Planned vs Built Technique Table
   - Asset Manifest & Resolutions
   - Frame counts and performance benchmarks
   - Accessibility & motion preferences (`prefers-reduced-motion`)
