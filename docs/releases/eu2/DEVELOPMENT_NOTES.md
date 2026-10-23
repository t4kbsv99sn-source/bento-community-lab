# Preserved EU2 development corrections

- Initial M7 linker garbage collection omitted externally called live_* symbols.
  The builder failed with a missing-symbol KeyError; clang's retain attribute
  now keeps these exports. Zig did not accept a tried --undefined linker option.
- Native timing tests established that 960 playback-clock ticks equal one
  quarter note, not one displayed sixteenth. The renderer now follows the
  native step-size table: default sixteenths are 240 playback ticks.
- Native route construction emits both sound and special MIDI/notification
  routes; the fixture initially counted the special route as a second sound.
  It now distinguishes destinations while running actual native packet code.
- The 48-step fixture initially included an extra hit from its final audio
  block extending beyond the requested interval. It now bounds that block.
- No failed candidate from these iterations was delivered or flashed. Final
  compiled entry/gate, timing and routing tests pass; device results are pending.
