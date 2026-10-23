# EU10 software validation — 23 October 2026

249 firmware tests passed across 14 suites. Six new tests cover engine-specific target lists, original sample ADSR, send mappings, first/last synth target encoding, sample restoration and preservation of saved legacy ADSR locks. All inherited UI, native note/lock, Euclidean, condition, Track FX and DSP regressions passed.

Independent fresh-source rebuild is byte-identical. All 288 isolated source inputs match the repository. Exact stock/K16 reversal, application bounds, four-byte alignment, unchanged controller and unchanged EU9 synth cave are checked. Original bootloader, vectors/recovery, MPU, heap/stack reservations and audio DSP are unchanged. No device flash performed.

Main SHA256: 4ed81f1604459f338624fcfd4a22e40b29b992f4e9df4303de1a0564b8b32a37
Size: 1,601,924 bytes. Label: 1.6EA.

Native model/SD and parent services are substituted in targeted fixtures. Physical startup, display, SD round-trip and real-time CPU behavior remain device checks. The existing EU9 offline patcher was not changed and cannot produce EU10.

The first full run's visual suite silently ended without a summary inside Unicorn callback cleanup despite exit 0. The completion gate correctly rejected it. Retaining probe instances until process exit fixes the harness; the complete 10-test visual recheck passes. Production firmware bytes were unaffected. Other suites completed normally; no failing assertion was waived.
