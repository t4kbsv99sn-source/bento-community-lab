// Bento 1.6.1 static analysis report, safe/read-only (does not patch or flash firmware).
// Import bento1.bin as Raw Binary at base 0x08040000, ARM:LE:32:Cortex, then run analysis.
//@category Bento

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class Bento_16_Ghidra_Report extends GhidraScript {

    private PrintWriter out;

    private void line(String message) {
        out.println(message);
        println(message);
    }

    private Address at(long address) {
        return toAddr(address);
    }

    private String ascii(long address, int count) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < count; i++) {
            Address a = at(address + i);
            if (!currentProgram.getMemory().contains(a)) {
                sb.append("[unmapped]");
                break;
            }
            int c;
            try {
                c = currentProgram.getMemory().getByte(a) & 0xff;
            } catch (ghidra.program.model.mem.MemoryAccessException e) {
                sb.append("[unreadable memory]");
                break;
            }
            if (c == 0) break;
            if (c < 32 || c > 126) {
                sb.append("[non-ASCII]");
                break;
            }
            sb.append((char)c);
        }
        return sb.toString();
    }

    private void location(String label, long address) {
        Address a = at(address);
        line("\n== " + label + " ==");
        line("Address: " + a);
        line("Mapped: " + currentProgram.getMemory().contains(a));
        if (!currentProgram.getMemory().contains(a)) return;
        line("ASCII preview: " + ascii(address, 50));
        ReferenceIterator it = currentProgram.getReferenceManager().getReferencesTo(a);
        int n = 0;
        while (it.hasNext() && n < 50) {
            Reference r = it.next();
            Function fn = currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            line("xref " + r.getFromAddress() + " [" + r.getReferenceType() + "] function=" + (fn == null ? "not identified" : fn.getName() + " @ " + fn.getEntryPoint()));
            n++;
        }
        if (n == 0) line("No Ghidra xrefs identified (not proof that none exist).");
    }

    private void decode(String label, long address, DecompInterface decompiler) {
        line("\n== CODE INVESTIGATION: " + label + " (" + at(address) + ") ==");
        Function f = currentProgram.getFunctionManager().getFunctionContaining(at(address));
        if (f == null) {
            line("No function identified here. Analysis may not have discovered this Thumb code yet.");
            return;
        }
        line("Function name: " + f.getName());
        line("Entry point: " + f.getEntryPoint());
        line("Function body size: " + f.getBody().getNumAddresses() + " bytes");
        try {
            DecompileResults res = decompiler.decompileFunction(f, 30, monitor);
            if (res != null && res.decompileCompleted() && res.getDecompiledFunction() != null) {
                String c = res.getDecompiledFunction().getC();
                if (c.length() > 20000) {
                    c = c.substring(0, 20000) + "\n[Decompilation truncated at 20,000 characters]";
                }
                line(c);
            } else {
                line("Decompiler not yet available here: " + (res == null ? "no result" : res.getErrorMessage()));
            }
        } catch (Exception e) {
            line("Decompiler exception: " + e.toString());
        }
    }

    @Override
    protected void run() throws Exception {
        if (currentProgram == null) {
            println("Open the Bento bento1.bin program first.");
            return;
        }
        File target = askFile("Save Bento Ghidra report", "Save");
        if (target == null) return;
        out = new PrintWriter(new BufferedWriter(new FileWriter(target)));
        try {
            line("BENTO 1.6.1 GHIDRA RECON - READ ONLY");
            line("Program: " + currentProgram.getName());
            line("Language: " + currentProgram.getLanguage().getLanguageID());
            line("Compiler: " + currentProgram.getCompilerSpec().getCompilerSpecID());
            line("Expected firmware image: bento1.bin, base 0x08040000");
            line("Expected first vector stack pointer @ 0x08040000: 0x2404CDA0");
            line("Expected first vector reset word @ 0x08040004: 0x080403CD (Thumb entry at 0x080403CC)");
            if (!currentProgram.getMemory().contains(at(0x08040000L)) ||
                !currentProgram.getMemory().contains(at(0x0818BDE4L))) {
                line("ERROR: expected addresses unmapped. Re-import Raw Binary at base 0x08040000.");
                return;
            }
            line("Config Track string: " + ascii(0x0818BDE4L, 20));
            if (!ascii(0x0818BDE4L, 20).equals("Config Track")) {
                line("ERROR: unexpected string. Check that this is the exact Bento 1.6.1 bento1.bin.");
                return;
            }
            line("Found matching version-specific string at expected address.");

            location("Config Track label", 0x0818BDE4L);
            location("Config Track menu entry (20-byte record)", 0x081980A8L);
            location("Change Patch menu record", 0x08198080L);
            location("UITrackPane diagnostic string", 0x0818C530L);
            location("UITrackPane string pointer in first code region", 0x0814B62CL);
            location("UITrackPane string pointer in second code region", 0x081605ACL);
            location("Track Config label", 0x0819A8C0L);
            location("Selected Pad label", 0x0818E274L);

            DecompInterface decompiler = new DecompInterface();
            try {
                if (!decompiler.openProgram(currentProgram)) {
                    line("Could not initialize Ghidra decompiler.");
                    return;
                }
                decode("first reset handler", 0x080403CCL, decompiler);
                decode("third-region reset handler", 0x081003CCL, decompiler);
                decode("near UITrackPane diagnostic pointer 1", 0x0814B630L, decompiler);
                decode("near UITrackPane diagnostic pointer 2", 0x081605B0L, decompiler);
                decode("source of Mod FX table ref 1", 0x08134F20L, decompiler);
                decode("source of Mod FX table ref 2", 0x08147480L, decompiler);
            } finally {
                decompiler.dispose();
            }
            line("\nEND OF REPORT. No firmware bytes were modified.");
        } finally {
            out.close();
        }
        println("Saved Bento report to: " + target.getAbsolutePath());
    }
}
