/**
 * 3Blue1Brown / Manim visual language.
 * Near-black stage, thin bright strokes, LaTeX in white, the signature blue,
 * and a warm yellow reserved for the thing you're meant to look at.
 *
 * Palette values are Manim's own constants (manim_colors.py) so the piece
 * reads as authentically "that style".
 */
export const theme = {
  // stage
  bg: '#0d0f14', // near-black with a faint cool cast (Manim renders on black)

  // ink
  white: '#ffffff',
  grey: '#888c94', // secondary text
  gridLine: '#2a2f38', // faint axes / dot grid

  // the blues (BLUE_E..A)
  blueDark: '#1c758a',
  blue: '#58c4dd', // BLUE_C — the signature stroke
  blueLight: '#9cdceb',
  bluePale: '#c7e9f1',

  // supporting accents
  teal: '#5cd0b3',
  green: '#83c167',
  yellow: '#ffd866', // highlight / heading — the "look here" color
  red: '#fc6255', // weapon / impact / error
  maroon: '#c55f73',
};

export const fonts = {
  // 3b1b uses a serif for body and Computer Modern for math.
  // Placeholder stacks — swap for licensed faces before final render.
  body: 'Georgia, "Times New Roman", serif',
  sans: 'Inter, sans-serif',
  math: 'Latin Modern Math, "Computer Modern", serif',
};

export const sizes = {
  title: 96,
  heading: 64,
  body: 40,
  label: 32,
  caption: 26,
};
