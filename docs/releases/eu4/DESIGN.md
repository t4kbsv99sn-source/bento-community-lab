# EU4 implementation

Branches from EU3 be3e820c12dd992567e543ece3cedc340b02cafb. Independent eu4_work copies preserve earlier release source.

Snare and hi-hat PrepareBlock returns stack-owned coefficients, sets SVF coefficients once after current pitch, knobs and per-voice locks are applied. ProcessPrepared uses identical formulas and random order. Object sizes, 16 voice slots, fixed SRAM and three-second carrier lifetime are unchanged. Kick peak diagnostics accumulate locally then publish once per block. Compile DSP with -Os -flto, without fast-math.

Track FX skips settled wet/ceiling/makeup and coefficient updates; fault resets re-enable update paths. ProcessNormalized skips division by a0=1, guaranteed by the existing SetCoefficients API. No compressor decimation, envelope-rate change or new approximation. Native mix/sends path remains.

Native reset data at 081B3E38 offsets 48/4C initializes the M4 allocation end/start to C8000000/C6000000. EU3 allowed only below C6000000, so first allocation always failed on the device. EU4 permits the native range. M4 MPU region 4 maps this range; M7 privileged default map permits it under native PRIVDEFENA. No MPU/heap bounds change. Aligned word accesses/cache-line ownership are unchanged. Tests cover the actual 0815D4B4 event entry (event AE), native 08104C08 allocator, C6 bank playback and native MPU configuration.

Host/Unicorn checks do not establish real-time device deadlines or physical cache behavior. Instruction count comparisons install their hook before warming code, avoiding Unicorn's translated-block hook caching. Historical initial failed experiments are retained outside the release package.
