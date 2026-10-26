# P2 design notes (D1: drum synths without files to copy)

- Menus: the 20 native menu objects (0xE0 each) at 30030168: id +0, cells +4
  (20 bytes: code, label, 0, 0, enabled), count +CC; built by 081412EC from
  the flash tables at 08198068. The model event entry (081403EC hook,
  `drum_menu_event`) sees menu-open requests (F0..100, 100C..100E; see
  0813430C) and adds code 1056 "Drum Synth" to every menu offering Load WAV
  (1046) when the current track is one-shot (type 14), removing it otherwise.
- 1056: pad = current track's property 74 (selected pad, as the browser and
  recorder use), engine Kick.
- `drum_assign`: path = native join 08104648(out, 300010F4, "Projects", name)
  (as 08127D7C builds project paths); the marker is checked or written at
  "\\" + path (FatFS, mode 1 then 10 = create-always/write, as the hardware
  diagnostics report used); then 08139DE0(model, track index, &cell, pad,
  path, 0), the native file-onto-pad function the recorder uses, with the
  pad's existing cell (types 1/2, property 73 = pad) or 0 to create one. One-shot
  tracks only; an existing file that is not exactly our marker is left alone
  and nothing is assigned.
- Engine: key 1AD on the synth page's bottom row is now an enum (Kick..Tom)
  showing the current engine; a change reassigns the pad's own cell.
- Files are identical to tools/make_drum_carriers.py (test checks bytes).
- Unverified on hardware: that menu codes reach the model event entry, and
  the path form accepted by 08139DE0.
