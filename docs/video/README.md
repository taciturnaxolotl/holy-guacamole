# Holy Guacamole — explainer video

A 3Blue1Brown–style explainer on how meltybrain combat robots work, built in
Motion Canvas. Voiceover-driven, so timing is intentionally loose.

## Run it

```bash
bun install
bun start      # Motion Canvas editor at http://localhost:9000
```

Scrub the timeline in the editor; render from there. `./render.sh [out.mp4]`
then stitches the rendered frames in `output/project/` into an MP4 with ffmpeg
(default `output/project.mp4`).

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
- `src/beats/*.tsx` — the eleven beats, in order.

## The arc (`src/beats/`)

1. `intro`: the melty pops onto the stage
2. `problem`: a body-fixed heading vector; "forward" turns with the robot
3. `translation`: kick a motor at the same heading each spin; kicks → a glide
4. `gyroRedline`: a gyro's reading flatlines at its ceiling (about 660 rpm)
   while the true spin races on, so we use accelerometers
5. `centrifugal`: camera glides to a rim sensor; a = ω²r → ω = √(a/r)
6. `gForce`: g against rpm; the curve climbs out of the noise floor as rpm²
7. `integration`: heading is the area under spin rate, θ = ∫ω dt
8. `drift`: a naive integrator's estimate lags; live error readout climbs
9. `sensorShove`: three sensors; subtracting one from another cancels a shove
10. `measurements`: six measurements, four unknowns, so the readings can
    check each other
11. `solution`: an EKF's belief (bell curve) predicts, then sharpens on the
    sensors until the estimate locks onto the true heading

Reorder or trim beats in `main.tsx`. To add one, drop a
`function* name(s: Stage)` in `src/beats/` and slot it into the sequence.
