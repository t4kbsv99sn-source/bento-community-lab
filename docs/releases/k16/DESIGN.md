# K16 implementation record

Based on K15 / 5d304f4, preserving K14's hardware-confirmed kick/snare and K13 drawing cleanup. K15 was not yet installed by the maintainer. K16 is software-tested only until an maintainer report arrives.

## Sample UI restoration
The native per-slot text override lives at slot+0x2C8. Native 08170656(bar,index,NULL) clears it. Merely restoring the row key tables at +703C left the last synth string visible. On synth->sample transition K16 clears all 24 text overrides, reads native property values and forces native 08171C1C configuration for each restored key. Native 08171108 then restores labels/ranges/types. Normal refresh and sampler drawing follow unchanged. Tests execute the actual native configuration and override functions with drawing substituted.

## Velocity
The accepted note 0x12 handler at 0808FA90 takes record+16 velocity, runs native 08050F20 normalization, then calls 08094760. Native 08094BBE..08094BE8 converts the velocity to float /127 and writes voice+0xB8. This happens AFTER our existing voice-creation hook, so gain is read in kick_render, not captured prematurely at kick_voice. Direct trigger mode sets +B8 to 1. K16 multiplies the final bounded synth signal by the clamped 0..1 source before native postprocessing. No Daisy accent or other timbre parameter is velocity-modulated. Explicit user mod-matrix routing can still add its own modulation. Native zero/default incoming-velocity handling is retained.

## Two locks, no additional automation lanes
Existing target kinds 1..11 and every old pair code retain their exact meaning. New model-specific kinds: kick 12..19 (Tune,Decay,Tone,Impact,Sweep,Sweep Dec,Dirt,Click), snare 20..24 (Tune,Decay,FM,Impact,Snappy), hat 25..29 (Tune,Decay,Tone,Impact,Noise). Kick Tune stores 25..180Hz; all other synth controls retain their existing 0..100 UI values. Synth pairs append after the old 1,290,761,893 pair combinations, total 1,519,176,901, within the 31-bit space. Complete rows are skipped arithmetically when decoding. XML attributes and native event size remain unchanged.

Encoder 5/6 pickers list only the selected engine's targets plus existing native targets. The model helper resolves the pad's adjacent native file object, matching the instrument editor. Private descriptor ownership checks remain in place. Legacy note locks are regression-tested unchanged. Stored incompatible model locks are ignored by DSP; they remain clearable, preserving a project if a user switches back to that engine.

M7 snapshots the two decoded lock words per synth voice at creation, applies matching values before trigger and subsequent audio blocks, and does not modify pad background settings. It does not decode the pair in every audio block. Unlocked next hits clear both snapshots. Model-specific locks cannot accidentally enter the native send path, which now explicitly admits only kinds 10/11.

## Bounds
No new heap, MPU, stack reservation, original bootloader or controller changes. M7 snapshots occupy the existing unused reserved gap 24047E80..24047F00, after model IDs and before UI state at 24048000. UI picker pointers occupy 24048480..240484D0, after the UI state ending 24048438. Lock UI constant strings now follow the existing LED helper at 081B9000; linker/build guards keep them below the installer at 081BA000. Existing fixed call entry addresses remain intact. Application patches are guarded against exact stock bytes; patch reversal must reproduce stock exactly. Version-specific runtime magic resets stale state.
