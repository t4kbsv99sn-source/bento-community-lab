// Bento 1.6.1: read-only investigation of track selection and UI event routing.
// Requires bento1.bin imported as ARM:LE:32:Cortex Raw Binary at 0x08040000.
// Does NOT modify, patch, export, or flash firmware.
//@category Bento

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class Bento_16_Track_Trace extends GhidraScript {

    private PrintWriter out;
    private DecompInterface dec;
    private int successful = 0;

    private void p(String s) {
        out.println(s);
    }

    private Address a(long value) {
        return toAddr(value);
    }

    private void describeReferencesTo(Address destination, int limit) {
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(destination);
        int seen = 0;
        while (refs.hasNext() && seen < limit && !monitor.isCancelled()) {
            Reference r = refs.next();
            Function containing = currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            p("    " + r.getFromAddress() + " type=" + r.getReferenceType() +
                " within=" + (containing == null ? "[unidentified]" : containing.getName() + " @ " + containing.getEntryPoint()));
            seen++;
        }
        if (seen == 0) p("    [No automatic references resolved — this can reflect incomplete analysis]");
        if (seen == limit) p("    [Reference display capped at " + limit + "]");
    }

    private String decompile(Function f, int maxChars) {
        try {
            DecompileResults result = dec.decompileFunction(f, 30, monitor);
            if (result == null || !result.decompileCompleted() || result.getDecompiledFunction() == null) {
                return "[Decompiler failure: " + (result == null ? "no result" : result.getErrorMessage()) + "]";
            }
            String c = result.getDecompiledFunction().getC();
            successful++;
            return c.length() > maxChars ? c.substring(0, maxChars) + "\n[TRUNCATED: " + c.length() + " chars total]" : c;
        } catch (Exception e) {
            return "[Decompiler error: " + e.toString() + "]";
        }
    }

    private Function dumpFunction(String heading, long raw, int maxChars) {
        p("\n======================================================");
        p(heading + " 0x" + Long.toHexString(raw));
        p("======================================================");
        Address destination = a(raw);
        Function f = currentProgram.getFunctionManager().getFunctionContaining(destination);
        if (f == null) {
            p("[No function identified at this address. Don't infer absence of code.]");
        } else {
            p("Function: " + f.getName() + " entry=" + f.getEntryPoint() +
                " bodyBytes=" + f.getBody().getNumAddresses());
            p("\n-- References to entry --");
            describeReferencesTo(f.getEntryPoint(), 35);
            p("\n-- Decompilation --");
            p(decompile(f, maxChars));
        }
        return f;
    }

    private void dumpCallingFunctions(String header, Function target, int maxCallers) {
        p("\n-- Callers of " + header + " --");
        if (target == null) return;
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target.getEntryPoint());
        Set<String> seen = new LinkedHashSet<String>();
        int n = 0;
        while (refs.hasNext() && n < maxCallers && !monitor.isCancelled()) {
            Reference r = refs.next();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            if (caller == null) continue;
            String key = caller.getEntryPoint().toString();
            if (seen.add(key)) {
                p("\nCaller " + caller.getName() + " @ " + key + " (ref from " + r.getFromAddress() + ")");
                p(decompile(caller, 6000));
                n++;
            }
        }
        if (n == 0) p("No callers identified automatically.");
    }

    @Override
    protected void run() throws Exception {
        if (currentProgram == null) {
            println("Open Bento bento1.bin in CodeBrowser first.");
            return;
        }
        if (!currentProgram.getMemory().contains(a(0x0814b630L)) ||
            !currentProgram.getMemory().contains(a(0x081605b0L))) {
            println("Expected addresses not mapped. Check base 0x08040000 and bento1.bin.");
            return;
        }
        File target = askFile("Save Bento track trace report", "Save");
        if (target == null) return;
        out = new PrintWriter(new BufferedWriter(new FileWriter(target)));
        dec = new DecompInterface();
        try {
            p("BENTO 1.6.1 TRACK SELECTION / MENU TRACE (READ ONLY)");
            p("Program: " + currentProgram.getName());
            p("Language: " + currentProgram.getLanguage().getLanguageID());
            p("Compiler: " + currentProgram.getCompilerSpec().getCompilerSpecID());
            p("Original import base should be 0x08040000");
            if (!dec.openProgram(currentProgram)) {
                p("ERROR: could not open program in Ghidra decompiler.");
                return;
            }
            Map<String, Long> important = new LinkedHashMap<String, Long>();
            important.put("Track selection/highlight widget updater", 0x0814b630L);
            important.put("Getter for possible selected-track state (ID 0x131)", 0x08133614L);
            important.put("Update/highlight one of eight track widgets", 0x081736b4L);
            important.put("Construct track context menu", 0x081605b0L);
            important.put("Append menu entry", 0x0816fc52L);
            important.put("Track pane function near OpenInstrument diagnostic", 0x0814b3b4L);
            important.put("Other track pane function near OpenInstrument diagnostic", 0x08160338L);
            important.put("Selected Pad label handling", 0x081639a8L);
            important.put("Track pane per-cell state check", 0x08138164L);
            important.put("Base track pane update", 0x0816fabcL);
            Map<String, Function> found = new LinkedHashMap<String, Function>();
            for (Map.Entry<String, Long> e : important.entrySet()) {
                if (monitor.isCancelled()) break;
                Function f = dumpFunction(e.getKey(), e.getValue(), 11500);
                found.put(e.getKey(), f);
            }
            // Include a bounded amount of calling code to follow the event/data flow.
            dumpCallingFunctions("track selection/highlight widget updater", found.get("Track selection/highlight widget updater"), 8);
            dumpCallingFunctions("getter for selected-track state", found.get("Getter for possible selected-track state (ID 0x131)"), 10);
            dumpCallingFunctions("construct track context menu", found.get("Construct track context menu"), 8);
            dumpCallingFunctions("update/highlight track widget", found.get("Update/highlight one of eight track widgets"), 8);
            p("\nEND OF REPORT. Successfully decompiled " + successful + " functions. NO FIRMWARE MODIFIED.");
        } finally {
            try { dec.dispose(); } catch (Exception ignored) {}
            try { out.close(); } catch (Exception ignored) {}
        }
        println("Saved Bento track trace: " + target.getAbsolutePath());
    }
}
