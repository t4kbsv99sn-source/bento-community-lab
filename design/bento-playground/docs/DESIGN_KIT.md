# Measure / visual specification

## Color semantics

| Token | Preview value | Meaning |
|---|---|---|
| Background | #191B1C | Main canvas |
| Surface | #202324 | Active event area, very shallow depth |
| Raised | #292D2E | Selected lane/button |
| Rule | #3B4142 | Grid and passive bounds, not essential text |
| Secondary text | #A0AAA9 | Labels and context |
| Primary text | #E9EEEA | Values and focus |
| Quiet | #626C6C | Empty event numbering; never critical status |
| Track | #E9AA73 example only | Musical ownership, event measures and parameter traces |
| Record | #F27979 | Recording, always accompanied by REC/Recording text |

**Do not replace Bento's track palette.** The integration adapter resolves the native track/cell palette index at draw time. Examples use amber, blue, violet and green to test behavior. Native CLUT RGB values have not been fully traced; the proposal colors need quantization and hardware checking. Never use a global palette edit to recolor unrelated screens. A selected drum cell inherits its existing ownership color; these 32 grid cells are steps of one drum, not 32 differently colored instruments.

Inactive, selected, automated, modulated and recording must differ by shape or text as well as color. Muted active notes should retain a subdued event body plus a mute slash; they must not look empty. A disabled control keeps its label but removes its active measure. No pulsing color or glow is needed.

## Type and spacing

Prototype type is DejaVu Sans via a system fallback; no font binary is bundled. It is an approximation, not a replacement for Bento's mcufont renderer. Retain native fonts in the first integration pass. If a new font is later approved, Inter is an OFL candidate, subject to bitmap conversion, glyph coverage and memory measurement.

| Role | Native-size proposal |
|---|---|
| Encoder value | 25 px regular, stable numeral width |
| Action label | 20 px |
| Main context / macro name | 20–22 px |
| Encoder label | 16 px |
| Secondary value / subdivision | 14–17 px |
| Nonessential rail annotation | 12 px, never the sole cue |

Use 4px spacing increments for new artwork and 8/12/16px insets. Do not snap native 159px column pitch to a new global grid. Preserve source geometry before aesthetic regularity. Flat surfaces establish hierarchy; no shadows, gradients, bevels or corner-heavy panels. Rounded corners are reserved for existing action-button affordances, 3px maximum in this study.

## Geometry contract

All rectangles are upright browser coordinates unless noted.

- Canvas 1280×480.
- Encoder strip y0–72, columns x6+159i, width157.
- Step hit areas x6+159c, y74+89r, 157×87; c0–7, r0–3.
- Step inset drawing box x+5,y+5,147×77. Leave the full native hitbox in place.
- Bottom shell begins at y428. Six native action slots x163+159i,width157. Native tab/button visual heights differ; preserve original event geometry in firmware.
- Automation body x92–1250,y171–363 is proposed, not traced native geometry. Curve-node hit radius15 is browser-only; on device retain native selection and encoder editing before introducing direct touch-drag gestures.
- Macro future concept: four columns by two rows, each approximately310×194, no small icon-only targets. Encoder-to-macro assignment must be explicitly approved; eight physical encoders do not by themselves authorize a new mapping.

## Step component

1. Empty: quiet number, no bright fill.
2. Active: surface body with a track-color velocity measure; height is monotonic with velocity1–127.
3. Selected: white corner brackets around the full inset; selection does not imply playback.
4. Playing: white top rule and small white position dot, independently composited above active/empty states. The dot is redundant, not the only signal.
5. Locks: small original lock symbol plus a fine normalized rail beneath the velocity. The rail is the displayed lock target, never velocity. Target name/value stays in the encoder readout. A future per-lock switch must follow existing lock selection, not create a new gesture.
6. Probability: percentage only below100%; suppress the default to reduce noise.
7. Trigger condition: compact literal such as2:4 in the lower-right detail position, replacing the redundant per-cell velocity numeral. Velocity remains visible in the top selected-step readout. Probability and condition can coexist without overlapping.

Do not equate trigger conditions and the current `Locks when` condition in the model. Use separate data fields even if both share the text grammar. The selected readout must describe the actual condition kind. The sample condition demonstrates the visual slot; the integration adapter must distinguish note-trigger gating from lock-application gating.

Two treatments are supplied: **Measured bar** and **Quiet line**. Both use identical coordinates, values and semantics. Prefer the first for performance readability; keep the line version as a deliberate lower-color alternative.

## Automation and modulation

One track-color curve for the selected lane. Neutral grid, strong motion-loop bracket, separate segmented clip rail. These share a time scale but not a length. Label the owner (`Clip 01`) and both periods. Shrinking a loop clips the view, not the stored events; never squeeze all points to fit. Re-expansion reveals the tail. Do not imply clip changes preserve a global motion bank.

Linear interpolation must draw straight segments; stepped data must draw sample-and-hold segments. Do not smooth corners for visual beauty when playback is linear. Values are normalized in the prototype; a firmware target adapter supplies units and range mapping. The current vertical line is a playhead, not a node. Recording uses red plus a word; armed and recording are distinct. Empty recording should not show fabricated motion.

Modulation primitive: a baseline marks the base value, a bracket marks the permitted excursion, and a small moving dot marks the current effective value. Automation gets an original miniature polyline mark; native modulated-value `*` remains until owner approves replacement. Neither moving dot nor automation marker may hide an existing p-lock indicator.

## Musical diagrams

- Cutoff: monotonic response-shaped curve, position tied to cutoff. It is a control illustration unless calculated from the actual engine response.
- Drive: transfer curve whose saturation increases with drive; label as schematic.
- Delay/reverb send: repeated decreasing taps, amplitude tied to send. Do not animate decay time unless decay is assigned too.
- Pan: bipolar rail with a central reference and current position dot.
- Envelope: attack/decay segments tied to the parameter; units remain explicit.
- Resonance: a peak grows at a fixed frequency as resonance rises. Moving a lowpass cutoff would misrepresent this control.
- Multiple destinations: show the second numeric output beneath the primary output. Never hide conflicting polarity mappings behind a decorative shape.

Each renderer consumes normalized values and fixed geometry, not audio buffers. The component sheet contains the original lock, condition, automation and modulation icons. Reuse the procedural functions instead of creating subtly different SVGs per screen.

## Feedback rules

No easing on musical time or actual parameter values. Redraw the latest state rather than queuing every encoder tick. UI-only value feedback may be throttled to20Hz initially; verify native cadence and latency on hardware. Stop animation when not visible. Respect reduced-motion preferences in the browser by disabling auto-start (the preview always starts stopped). Do not flash selection or animate navigation. No idle animation is needed.


## Revision 02 — Opal-informed one-shot (current)

The owner selected retaining Bento's layout and showing velocity plus lock values. This revision supersedes the earlier step styling and bar/line alternatives above. Each native hit area remains157×87. Inside it, the trigger is101×37 at x+14,y+29, with4px corner radius. Velocity fills upward inside the frame, never changing the on/off meaning. A separate101×5 rail at y+76 shows the selected lock target. Unlocked rails stay neutral. Playback uses the dot above the trigger plus a top rule. Selection adds an outer white outline. Probability and condition have separate text positions. Browser controls can compare Filter versus Send and edit the selected normalized lock value; these controls are outside the device display and do not authorize new firmware navigation. Example cutoff conversion is logarithmic20Hz–20kHz, illustrative only.

The actual eight-encoder row,32-step hit areas, bottom navigation, track color and hold-to-inspect behavior are retained. Engine symbols and Opal's split composition are not reproduced.


## Revision 03 — two p-locks and probability (current)

Both p-locks are now visible simultaneously. The upper101×3 rail at y+74 represents lock1 (Filter in the example); the lower rail at y+81 represents lock2 (Send). The browser's target selector selects which value to edit, never which strip to display. Actual target labels remain in encoder7/8. The velocity fill remains inside the trigger. Probability below100% appears as an exact percentage and a3×37 vertical gauge at x+124. Full probability is implicit. This keeps probability separate from both lock values and velocity. The probability gauge is informational, not a new touch target.


## Revision04 — square steps, eight colors and overview studies (current)

The32 native step hitboxes remain157×87. Each contains a56×56 square at x+48,y+17. Velocity fills inside it; two56×2 lock strips sit at y+78 and y+84. Each set lock retains at least2px of color at zero. Probability below100% is numerical only, with no duplicate gauge. Selection is a white outer frame; playback uses a dot and short rule.

Eight proposed track swatches, in order: Amber #E9AA73; Blue #8BBBD1; Violet #C5A4D0; Sage #9FC5A8; Rose #D58F9A; Ochre #D3C57E; Teal #87C4BC; Periwinkle #A9AFD8. The first four preserve the previous palette. These are proposals, not extracted native CLUT values. Eight tracks remain labeled by number and name, so color is never their sole identifier.

Tracks and Mixer are new information-informed mockups, not pixel-exact P19 reconstructions. Track overview preserves eight identities, type, selection, stereo activity and project/key/resource context. Mixer retains upper outputs, eight channels and Level/Mute/Delay/Reverb mode roles. P19's native mixer tests were inspected for mute/solo state and the project's post-FX meter behavior. Output labels/group roles and track context were checked against the official v1.3.17b manual (pages24–27 and365); the manual is older than P19. Full latest native geometry has not been traced. Meter samples, dB values and track names are illustrative. Source: https://1010music.com/wp-content/uploads/2026/01/bento_v1.3.17b_user_manual.pdf


## Revision05 — encoder-aligned macro columns (current)

The supplied owner screenshot supersedes the earlier abstract macro diagrams. Eight columns align with eight physical encoders. Each has a name and macro amount, followed by target rows. Rows show track ownership color, parameter name, current normalized value and a horizontal0–100 scale. Gray marks the assigned range; color shows travel from the start; a white tick shows the current value. Reversed ranges fill in the reverse direction. Macro8 is explicitly unassigned. Browser values are simulated. This is a visual structure, not approval to introduce the screenshot's Assign/Keep ON/navigation functions into firmware.
