import sys,struct;sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import emu,render
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
MODEL=0x30024b00; U=0x24048000; VIEW=0xC0400000; DEV=0xC0600000
OFF=dict(magic=0,view=4,select_mode=1088,chord_state=1128)
class World:
    def __init__(s,image,kind):
        e=s.e=emu.Emu(image); render.boot_gfx(e); s.kind=kind
        e.call(0x08180198,render.ROOT)
        def ret(v):
            def h(u,a,n,d):
                u.reg_write(UC_ARM_REG_R0,v); u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return h
        e.u.hook_add(UC_HOOK_CODE,ret(14 if kind=='drum' else 15),begin=0x08133F7C,end=0x08133F7C)
        def owner(u,a,n,d):
            s.e.w(u.reg_read(UC_ARM_REG_R1),0x1234); u.reg_write(UC_ARM_REG_R0,1); u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        e.u.hook_add(UC_HOOK_CODE,owner,begin=0x08133CFC,end=0x08133CFC)
        # model: display active, page 27, sequence id
        e.u.mem_write(MODEL+0x14c,b'\x01'); e.w(MODEL+0xb19c,1); e.w(MODEL+0x3c60,1); e.w(MODEL+0x144,0x5e9)
        # view fields so supported(view) holds (drum)
        e.w(VIEW+0x113e4,1); e.w(VIEW+0x113dc,1); e.w(VIEW+0x11400,0)
        e.w(U+OFF['magic'],0x47555042); e.w(U+OFF['view'],0); e.w(U+OFF['select_mode'],0)
        # chord device state
        e.w(U+OFF['chord_state'],DEV); e.w(DEV,0x31484342); e.w(DEV+20,0x5e9); e.w(DEV+24,0x1234)
    def navigate(s,page_tpl,page):
        render.page_reset(s.e)
        s.e.u.mem_write(MODEL+0x3a00,render.tpl(s.e,page_tpl)); s.e.u.mem_write(MODEL+0x12c,bytes([page]))
    def ready(s):
        if s.kind=='drum': s.e.w(U+OFF['view'],VIEW)
        else: s.e.w(DEV+8,VIEW)   # s->piano captured by the piano header hook
    def tick(s):
        flags=0x2001f000; s.e.u.mem_write(flags,bytes(8))
        s.e.call(0x08180088,render.ROOT,flags)
    def shot(s,path):
        render.clear(s.e); render.paint(s.e,render.ROOT)
        render.save(s.e,path,crop=(0,424,1280,480))
    def buttons(s):
        out=[]
        for k in range(6):
            b=render.ROOT+0x54c+k*0xd0
            out.append((s.e.text(b+0x3c+0x31) or '-', 'hidden' if s.e.u.mem_read(b+0x30,1)[0] else 'shown'))
        return out
