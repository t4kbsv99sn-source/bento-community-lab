# CH11 design: drum-synth destinations in the native Mod Matrix

The maintainer chose the native matrix over a custom page.

## How the native matrix works (traced in 1.6.1)
- View class vtable `0819DE14`. Rebuild `0814CC14` (event A8.., handle at
  event+4) fills per-row arrays in the view: `+8AC44` cell, `+8AC4C` cell
  type, `+8AC4D` row count, `+8AC50` keys (u16), `+8ACCC` row handles,
  `+8ADBC` row byte, `+8AE04` names (16 bytes). One-shot cells (type 1/2) get
  the ten keys of `0819E428` at `0814CD42`.
- Sources offered to one-shot cells (`0819E46C`): None, Velocity, Pressure,
  LFO 1, Mod Wheel, MIDI Vol, MIDI Pan, Auto A–D.
- An edit posts event D1 → model `08133388`, which stores the route under the
  cell (record +0C amount, +10 source, +12 key, +14 slot) and sends command
  0x3F via `0813325C`. Nothing on the M4 side filters keys.
- Save writes `<modsource dest=…>` with the registry token `081666F8(key)`;
  load maps it back with `08166720(token)`. Registry keys stop at 0x1F2 and
  only seven are free, too few for one key per engine parameter.
- M7: the sampler's command switch calls `080925E0(root, record)` at
  `0808F38E`. Per-voice sources are kept in the root's list `root+590`
  (12-byte records, count `+5FC`, nine max) and bound to each new voice by
  `08092F20`, which skips keys above 0x57.

## What CH11 adds
- `mod_rows` (UI, called at `0814CE80` via an adapter that replays
  `ldr r6,[sp,#0xc]; cmp r6,#0xf`): for a synth cell, list the engine's
  parameters (keys `1A0 1A1 1A2 1A4 1A5 1A6 1A9 1B0`, the existing synth knob
  keys), then the native rows minus Attack/Decay/Release.
- `mod_token` / `mod_key` replace the token calls at `0812F6A2` / `0812FE52`:
  `bento_synth_p1`…`p7`, `bento_synth_click`. Other keys go to the native
  lookups.
- `kick_route` (M7, at `0808F38E`): synth keys are stored in `root+590`
  (upsert by key and slot; source 0 removes); native keys take the original
  path. The native binder ignores these records.
- `kick_render` adds amount × source × range to each parameter every block,
  after knob and lock values, clamped to the range. Source values are read
  where the native sampler binds them: voice `+610` LFO 1, `+B4` velocity,
  `+C4` pressure; root `+650+8n` Auto A–D, `+108` mod wheel, `+110` MIDI vol,
  `+118` MIDI pan.
- The voice LFO 1 (`08064A80` on voice `+5D8`) is ticked in `kick_render`;
  the native render entry that normally does it is skipped for synth voices.

## Engine identity
The keys name parameter positions, not engine parameters. The engine the
routes belong to is kept in `KickKnob.reserved` bits 4–7 (0 = current engine)
and saved as `bento_mod_engine`. When a pad's engine changes, the old engine
is recorded; M7 applies routes only if that tag is 0 or equals the engine.
An edit of a synth route (`mod_edit`, at `08140924`) clears the mismatch.

## Not covered
- Hardware: none of this has been tried on the device yet.
- Sources the sampler does not bind (LFO 2–4, MOD 1–10, macros) are not
  offered for one-shot cells natively, and add nothing here.
- Synth parameter automation lanes are unchanged.
