// Bento 1.6.1 targeted architecture trace (read-only).
// Use with bento1.bin imported as ARM:LE:32:Cortex at 0x08040000.
// This script writes a text report only. It does NOT modify Ghidra's program or firmware.
//@category Bento

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.Map;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class Bento_16_Deep_Dive extends GhidraScript {
    private PrintWriter out;
    private DecompInterface dec;

    private Address at(long n) { return toAddr(n); }
    private String hx(long n) { return String.format("0x%08X", n); }
    private void p(String s) { out.println(s); }

    private long littleWord(long address) {
        long result = 0;
        try {
            for (int i=0; i<4; i++) {
                result |= ((long)currentProgram.getMemory().getByte(at(address+i)) & 0xffL) << (8*i);
            }
        } catch (Exception e) {
            p("Memory read failed at "+hx(address)+": "+e.toString());
        }
        return result;
    }

    private void vectors(long base) {
        p("\n== Vector table at "+hx(base)+" ==");
        p("Initial SP: "+hx(littleWord(base)));
        long reset=littleWord(base+4);
        p("Reset word (Thumb bit included): "+hx(reset));
        p("Reset instruction address (Thumb bit cleared): "+hx(reset & ~1L));
        for (int i=2; i<16; i++) {
            p("vector["+i+"] = "+hx(littleWord(base+4L*i)));
        }
        Function f=currentProgram.getFunctionManager().getFunctionContaining(at(reset & ~1L));
        p("Ghidra function at reset: "+(f==null?"NOT FOUND (analysis may be incomplete)":f.getName()));
    }

    private void xrefs(long address, int max) {
        ReferenceIterator it=currentProgram.getReferenceManager().getReferencesTo(at(address));
        int n=0;
        while (it.hasNext() && n<max && !monitor.isCancelled()) {
            Reference r=it.next();
            Function caller=currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            p("  "+r.getFromAddress()+" "+r.getReferenceType()+"  function="+
              (caller==null?"[unidentified]":caller.getName()+" @ "+caller.getEntryPoint()));
            n++;
        }
        if (n==0) p("  [No automatic cross-references identified]");
        if (n==max) p("  [Reference display capped at "+max+"]");
    }

    private void hexWindow(String label,long center,int before,int after) {
        p("\n== Bytes around "+label+" @ "+hx(center)+" ==");
        for (long line=(center-before)&~15L; line<center+after; line+=16L) {
            StringBuilder sb=new StringBuilder(hx(line)+" ");
            for (int k=0; k<16; k++) {
                try {
                    sb.append(String.format("%02X ", currentProgram.getMemory().getByte(at(line+k)) & 255));
                } catch (Exception e) { sb.append("?? "); }
            }
            p(sb.toString());
        }
        p("Ghidra references to address:");
        xrefs(center,12);
    }

    private void function(String description,long address,int maxChars,int maxSeconds) {
        if (monitor.isCancelled()) return;
        p("\n==========================================================");
        p(description+" @ "+hx(address));
        p("==========================================================");
        Function f=currentProgram.getFunctionManager().getFunctionContaining(at(address));
        if (f==null) { p("No Ghidra function discovered at this address."); return; }
        p("Function: "+f.getName()+" entry="+f.getEntryPoint()+" body="+f.getBody().getNumAddresses());
        p("References to function:"); xrefs(f.getEntryPoint().getOffset(),24);
        try {
            DecompileResults result=dec.decompileFunction(f,maxSeconds,monitor);
            if (result!=null && result.decompileCompleted() && result.getDecompiledFunction()!=null) {
                String c=result.getDecompiledFunction().getC();
                p(c.length()>maxChars?c.substring(0,maxChars)+"\n[TRUNCATED: "+c.length()+" chars]":c);
            } else {
                p("Decompilation not completed: "+(result==null?"no result":result.getErrorMessage()));
            }
        } catch (Exception e) { p("Decompiler exception: "+e.toString()); }
        out.flush();
    }

    @Override
    protected void run() throws Exception {
        if (currentProgram==null || !currentProgram.getMemory().contains(at(0x081639A8L))) {
            println("Open the analyzed bento1.bin program with base 0x08040000 first.");
            return;
        }
        File target=askFile("Save Bento Deep Dive report", "Save");
        if (target==null) return;
        out=new PrintWriter(new BufferedWriter(new FileWriter(target)));
        dec=new DecompInterface();
        try {
            p("BENTO 1.6.1 ARCHITECTURE DEEP DIVE — READ ONLY");
            p("Program: "+currentProgram.getName());
            p("Language: "+currentProgram.getLanguage().getLanguageID());
            vectors(0x08040000L);
            vectors(0x080E0000L);
            vectors(0x08100000L);
            hexWindow("region-1 evtcond parameter registration",0x0806C334L,48,48);
            hexWindow("region-3 evtcond parameter registration",0x08165D38L,48,48);
            hexWindow("region-1 FX3 Send registration",0x08068CFEL,48,48);
            hexWindow("region-3 FX3 Send registration",0x08163E9AL,48,48);
            hexWindow("region-3 Pad Bright registration",0x081659CEL,48,48);
            if (!dec.openProgram(currentProgram)) {
                p("Decompiler unable to open program.");
                return;
            }
            function("Full parameter registration schema (avoid previous output truncation)",0x081639A8L,120000,60);
            function("Object-listener event dispatch",0x0816FC52L,12000,25);
            function("Alternative notification dispatch",0x0816FC34L,12000,25);
            function("Track action-message construction",0x081605B0L,20000,25);
            function("Session layer mismatch and resend detection",0x081372ECL,20000,25);
            function("Resend initiation candidate",0x08136928L,20000,25);
            function("Generic parameter getter",0x08133614L,20000,25);
            function("Property resolution helper",0x0812DC74L,20000,25);
            function("Property fallback path",0x0812DCA2L,20000,25);
            function("Selection UI widget redraw flag",0x08173574L,12000,25);
            function("UI track selection updater",0x0814B630L,12000,25);
            function("SF2 RIFF/sample/zone parser",0x0810389CL,22000,25);
            function("MIDI message helper in region 1",0x080A1F00L,12000,25);
            p("\nEND OF REPORT: No Ghidra program bytes or firmware bytes modified.");
        } finally {
            try { dec.dispose(); } catch (Exception ignored) {}
            try { out.close(); } catch (Exception ignored) {}
        }
        println("Saved Bento architecture deep dive to "+target.getAbsolutePath());
    }
}
