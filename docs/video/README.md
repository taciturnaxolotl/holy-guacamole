# Holy Guacamole — explainer video

A 3Blue1Brown–style explainer on how meltybrain combat robots work, built in
Motion Canvas. Voiceover-driven, so timing is intentionally loose.

## Run it

```bash
bun install
bun start      # Motion Canvas editor at http://localhost:9000
```

Scrub the timeline in the editor; render from there.

## How it's built

The whole video is **one continuous scene** (`src/scenes/main.tsx`). There are
no cuts. A single persistent robot and a camera-able `world` are handed from
beat to beat, and each beat *transforms* what's on screen rather than replacing
it. That continuity is the 3b1b feel.

- `src/theme.ts` — Manim palette (near-black stage, signature blue, warm
  yellow for "look here"). Fonts are placeholder stacks — swap before final render.
- `src/lib.tsx` — the `Stage` (view + world + robot + a `shared` handoff bag),
  camera helpers (`zoomTo`, `resetCamera`), and builders (`tex`, `label`, `vector`).
- `src/components/MeltyRobot.tsx` — the robot as a minimal stroked diagram.
- `src/beats/*.tsx` — the seven beats, in order.

## The arc (`src/beats/`)

1. `intro` — the melty pops in and starts spinning; "this is a melty"
2. `weapon` — the whole body is the weapon; no constant forward
3. `problem` — a body-fixed heading vector; "forward" turns with the robot
4. `translation` — kick a motor at the same heading each spin; kicks → a glide
5. `centrifugal` — camera glides to a rim sensor; a = ω²r → ω → θ = ∫ω dt
6. `drift` — a naive integrator's estimate lags; live error readout climbs
7. `solution` — an EKF's belief (bell curve) predicts, then sharpens on the
   sensors until the estimate locks onto the true heading

Reorder or trim beats in `main.tsx`. To add one, drop a
`function* name(s: Stage)` in `src/beats/` and slot it into the sequence.
