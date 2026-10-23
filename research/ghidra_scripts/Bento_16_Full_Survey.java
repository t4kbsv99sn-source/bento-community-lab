// Bento 1.6.1 broad firmware survey. Read-only: does NOT modify the program or firmware.
// Import bento1.bin (raw ARM little-endian) at 0x08040000, analyze, then run.
// Save as exactly Bento_16_Full_Survey.java (Java class name must match file name).
// Optionally run headlessly with the report path as a script argument.
//@category Bento

import java.io.*;
import java.util.*;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class Bento_16_Full_Survey extends GhidraScript {
    private PrintWriter out;
    private DecompInterface dec;
    private LinkedHashSet<Function> focus = new LinkedHashSet<Function>();
    private ArrayList<Function> all = new ArrayList<Function>();
    private LinkedHashMap<String, Long> strings = new LinkedHashMap<String, Long>();
    private int decompCount = 0;
    private static final int MAX_DECOMPILES = 75;
    private static final int MAX_DECOMPILE_CHARS = 10000;
    private static final long FW_BASE = 0x08040000L;
    private static final int FW_SIZE = 1523516;

    private void line(String s) { out.println(s); }
    private Address at(long x) { return toAddr(x); }
    private String hx(long x) { return String.format("0x%08X", x); }

    private String safeAscii(long address, int max) {
        StringBuilder s = new StringBuilder();
        for (int i=0; i<max; i++) {
            try {
                int b = currentProgram.getMemory().getByte(at(address+i)) & 0xff;
                if (b == 0) break;
                if (b < 32 || b > 126) return s.toString() + " [non-ASCII]";
                s.append((char)b);
            } catch (Exception e) { return s.toString() + " [unmapped]"; }
        }
        return s.toString();
    }

    private Function containing(long a) {
        if (!currentProgram.getMemory().contains(at(a))) return null;
        return currentProgram.getFunctionManager().getFunctionContaining(at(a));
    }

    private void addFocus(Function f) { if (f!=null) focus.add(f); }

    private void populateStrings() {
        strings.put("SessionMgr UI/engine mismatch", 0x0818BC24L);
        strings.put("SessionMgr load bank", 0x0818BC9CL);
        strings.put("UITrackPane diagnostic", 0x0818C530L);
        strings.put("Config Track label", 0x0818BDE4L);
        strings.put("Menu record Config Track", 0x081980A8L);
        strings.put("Change Patch menu record", 0x08198080L);
        strings.put("Selected Pad label", 0x0818E274L);
        strings.put("FX3 Send (first parameter bank)", 0x080A7D38L);
        strings.put("FX4 Send (first parameter bank)", 0x080A7D4CL);
        strings.put("FX3 Send (second parameter bank)", 0x0818D148L);
        strings.put("evtcond (first parameter bank)", 0x080A8EDCL);
        strings.put("evtcond (second parameter bank)", 0x0818E23CL);
        strings.put("seqquant (second parameter bank)", 0x0818D6D8L);
        strings.put("chorusamount (second parameter bank)", 0x0818DE38L);
        strings.put("Pad Bright (second parameter bank)", 0x0818E114L);
        strings.put("Pad brightness parameter (second parameter bank)", 0x0818E120L);
        strings.put("SF2 sample parser", 0x08189598L);
        strings.put("PowerMgr first core", 0x080F6218L);
    }

    private byte[] readOriginalFirmware() {
        byte[] data = new byte[FW_SIZE];
        try {
            int n = currentProgram.getMemory().getBytes(at(FW_BASE), data);
            if (n != data.length) {
                line("WARN: read " + n + " firmware bytes, expected " + data.length);
                return null;
            }
            return data;
        } catch (Exception e) {
            line("WARN: firmware bytes unavailable: " + e.getMessage());
            return null;
        }
    }

    private ArrayList<Long> rawPointerSites(byte[] bytes, long value, int limit) {
        ArrayList<Long> sites = new ArrayList<Long>();
        if (bytes == null) return sites;
        for (int i=0; i+4<=bytes.length; i+=4) {
            long v = ((long)bytes[i] & 255) | (((long)bytes[i+1] & 255)<<8) |
                     (((long)bytes[i+2] & 255)<<16) | (((long)bytes[i+3] & 255)<<24);
            if (v == value) {
                sites.add(FW_BASE+i);
                if (sites.size() == limit) break;
            }
        }
        return sites;
    }

    private void refsTo(long address, int max) {
        int num=0;
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(at(address));
        while (refs.hasNext() && num<max && !monitor.isCancelled()) {
            Reference r = refs.next();
            Function f = containing(r.getFromAddress().getOffset());
            line("    Ghidra xref " + r.getFromAddress() + " " + r.getReferenceType() +
                 " function=" + (f==null ? "none" : f.getName() + " @ " + f.getEntryPoint()));
            addFocus(f);
            num++;
        }
        if (num == 0) line("    No automatically recognized xrefs");
        if (num == max) line("    ... xrefs truncated");
    }

    private void stringCatalog(byte[] raw) {
        line("\n=== STRING/RAW POINTER REFERENCES ===");
        for (Map.Entry<String,Long> entry : strings.entrySet()) {
            if (monitor.isCancelled()) break;
            long addr = entry.getValue();
            line("\n" + entry.getKey() + " @ " + hx(addr) +
                    ": " + safeAscii(addr, 100));
            refsTo(addr, 12);
            ArrayList<Long> ptrs = rawPointerSites(raw, addr, 24);
            for (Long ptr : ptrs) {
                line("    LE32 pointer at " + hx(ptr));
                refsTo(ptr, 3);
            }
            if (ptrs.isEmpty()) line("    No aligned, literal LE32 pointers found");
        }
    }

    private void inventory() {
        line("\n=== FULL FUNCTION INVENTORY ===");
        int[] regionCounts = new int[4];
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f=it.next();
            all.add(f);
            long adr=f.getEntryPoint().getOffset();
            if (adr < 0x080E0000L) regionCounts[0]++;
            else if (adr < 0x08100000L) regionCounts[1]++;
            else if (adr < 0x081B3F3CL) regionCounts[2]++;
            else regionCounts[3]++;
            line(f.getEntryPoint() + "  " + f.getName() + "  body=" + f.getBody().getNumAddresses() +
                    "  thunk=" + f.isThunk());
        }
        line("FUNCTION TOTAL " + all.size());
        line("FUNCTION COUNT by region <080E=" + regionCounts[0] + " 080E-0810=" + regionCounts[1] +
                " >=0810=" + regionCounts[2] + " other=" + regionCounts[3]);
    }

    private void sampleAcrossRegions() {
        line("\n=== CROSS-REGION REPRESENTATIVE FUNCTIONS (auto-sampled) ===");
        long[][] ranges = {{0x08040000L,0x080E0000L},{0x080E0000L,0x08100000L},
                            {0x08100000L,0x081B3F3CL}};
        for (long[] range : ranges) {
            ArrayList<Function> inRegion = new ArrayList<Function>();
            for (Function f: all) {
                long x=f.getEntryPoint().getOffset();
                if (x>=range[0] && x<range[1] && f.getBody().getNumAddresses()>16) inRegion.add(f);
            }
            line("Region " + hx(range[0]) + " to " + hx(range[1]) +
                    " discovered functions with body>16B: " + inRegion.size());
            if (inRegion.isEmpty()) continue;
            // 8 evenly distributed examples per region; not necessarily subsystem entry points.
            for (int i=0;i<8;i++) {
                Function f=inRegion.get(Math.min(inRegion.size()-1,(int)((long)i*inRegion.size()/8)));
                line("    sample: " + f.getName() + " @ " + f.getEntryPoint());
                addFocus(f);
            }
        }
    }

    private void knownAnchors() {
        line("\n=== PRIOR GHIDRA LEADS / KNOWN FUNCTIONS ===");
        long[] anchors={
            0x0814B3B4L, 0x0814B630L, 0x081605B0L, 0x08160338L, 0x081639A8L,
            0x08133614L, 0x081736B4L, 0x08138164L, 0x0816FC52L, 0x0816FABCL,
            0x08133960L, 0x08133F7CL, 0x081361B4L, 0x081734EAL,
            0x080403CCL, 0x080E03C2L, 0x081003CCL,
            0x08134F20L, 0x08147480L
        };
        for (long addr: anchors) {
            Function f=containing(addr);
            line(hx(addr)+" : "+(f==null?"unidentified":f.getName()+" @ "+f.getEntryPoint()));
            addFocus(f);
        }
    }

    private void decompileFocus() {
        line("\n=== FOCUSED DECOMPILATION, up to " + MAX_DECOMPILES + " functions ===");
        dec=new DecompInterface();
        if (!dec.openProgram(currentProgram)) {
            line("ERROR: Ghidra decompiler could not open the program");
            dec.dispose();
            return;
        }
        try {
            for (Function f: new ArrayList<Function>(focus)) {
                if (monitor.isCancelled() || decompCount>=MAX_DECOMPILES) break;
                line("\n--- FUNCTION "+f.getName()+" @ "+f.getEntryPoint()+" ---");
                refsTo(f.getEntryPoint().getOffset(), 7);
                try {
                    DecompileResults result=dec.decompileFunction(f, 10, monitor);
                    if (result!=null && result.decompileCompleted() && result.getDecompiledFunction()!=null) {
                        String code=result.getDecompiledFunction().getC();
                        line(code.length()>MAX_DECOMPILE_CHARS?
                             code.substring(0,MAX_DECOMPILE_CHARS)+"\n[TRUNCATED; original characters: "+code.length()+"]":code);
                    } else line("[Decompiler failed/timed out] "+(result==null?"null":result.getErrorMessage()));
                } catch (Exception e) { line("[Decompiler error] "+e.toString()); }
                decompCount++;
            }
        } finally { dec.dispose(); }
        line("\nFocused decompilation count: "+decompCount);
    }

    @Override
    protected void run() throws Exception {
        if (currentProgram==null) { println("Open the analyzed bento1.bin first"); return; }
        if (!currentProgram.getMemory().contains(at(FW_BASE)) ||
            !"Config Track".equals(safeAscii(0x0818BDE4L, 20))) {
            println("Not the expected Bento 1.6.1 firmware/mapping. Aborting without modifying anything.");
            return;
        }
        File file;
        String[] arguments=getScriptArgs();
        if (arguments!=null && arguments.length>0 && !arguments[0].trim().isEmpty()) {
            file=new File(arguments[0]);
        } else {
            file=askFile("Save Bento firmware broad-survey report", "Save");
        }
        if (file==null) return;
        populateStrings();
        out=new PrintWriter(new BufferedWriter(new FileWriter(file)));
        try {
            line("BENTO 1.6.1 GLOBAL FIRMWARE SURVEY — READ ONLY");
            line("Program: "+currentProgram.getName());
            line("Language: "+currentProgram.getLanguage().getLanguageID());
            line("Compiler: "+currentProgram.getCompilerSpec().getCompilerSpecID());
            line("NOTE: Decompiled code is inferred by Ghidra and can be wrong. Auto-discovery is incomplete.");
            line("NOTE: Ghidra has not necessarily separated embedded ARM images or identified reset functions.");
            line("\n=== MEMORY BLOCKS ===");
            for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
                line(block.getName() + " " + block.getStart() + " to " + block.getEnd() +
                     " R="+block.isRead()+" W="+block.isWrite()+" X="+block.isExecute());
            }
            byte[] raw=readOriginalFirmware();
            inventory();
            knownAnchors();
            stringCatalog(raw);
            sampleAcrossRegions();
            decompileFocus();
            line("\nEND — NO BYTES, FUNCTIONS OR FIRMWARE MODIFIED BY THIS SCRIPT");
        } finally { out.close(); }
        println("Bento broad survey saved: "+file.getAbsolutePath());
    }
}
