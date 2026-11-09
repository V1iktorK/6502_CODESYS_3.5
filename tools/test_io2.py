# -*- coding: utf-8 -*-
"""test_io2.py -- poshagovaya trassirovka konsolnoy programmy CP/M."""
import io, os, sys, time, traceback
ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm6502

LOG = os.path.join(ROOT, "log", "test_io2.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8"); f.write(u"%s\n" % (m,)); f.close()


f = io.open(LOG, "w", encoding="utf-8"); f.write(u""); f.close()
log(u"=== TEST_IO2 START ===")

SRC = """
ORG $0200
start:  LDX #$00
loop:   LDA msg,X
        BEQ done
        STA $F000
        INX
        JMP loop
done:   HLT
msg:    DB $43,$50,$2F,$4D,$00
"""
mem, labels = asm6502.assemble(SRC)
log(u"метки: %s" % {k: "%04X" % v for k, v in labels.items()})
log(u"байты: %s" % u" ".join(u"%02X" % mem[a] for a in sorted(mem)))

import scriptengine
WORK = os.path.join(BUILD, u"io2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"io2.project"):
        try: os.remove(os.path.join(BUILD, junk))
        except Exception: pass
s = io.open(PROJ, "rb"); d = s.read(); s.close()
o = io.open(WORK, "wb"); o.write(d); o.close()
proj = projects.open(WORK)
app = proj.active_application
node = app
for i in range(6):
    node = node.parent
    if node is None: break
    try:
        node.set_simulation_mode(True); break
    except Exception: continue
oa = scriptengine.online.create_online_application(app)
oa.login(scriptengine.OnlineChangeOption.Try, False)
oa.start()


def wr(e, v):
    oa.set_prepared_value(e, v); oa.write_prepared_values()


def rd(e):
    try:
        v = u"%s" % oa.read_value(e)
    except Exception:
        return -1
    try:
        if u"16#" in v: return int(v.split(u"16#")[-1], 16)
        if u"#" in v: return int(v.split(u"#")[-1])
        return int(v)
    except Exception:
        return -1


try:
    wr(u"GVL_CPU.Run", u"TRUE")
    wr(u"GVL_CPU.Step_On", u"TRUE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    for a in sorted(mem):
        wr(u"GVL_CPU.HADR", u"16#%04X" % a)
        wr(u"GVL_CPU.HDAT", u"16#%02X" % mem[a])
        wr(u"GVL_CPU.HEN", u"TRUE")
        time.sleep(0.02)
        wr(u"GVL_CPU.HEN", u"FALSE")
    wr(u"GVL_CPU.PC", u"16#0200")
    wr(u"GVL_CPU.SP", u"16#FF")
    wr(u"GVL_IO.ConPtr", u"16#00")
    time.sleep(0.2)
    for k in range(24):
        pc0 = rd(u"GVL_CPU.PC")
        op0 = rd(u"GVL_CPU.Ops")
        wr(u"GVL_CPU.Step_Pulse", u"TRUE"); time.sleep(0.10)
        wr(u"GVL_CPU.Step_Pulse", u"FALSE"); time.sleep(0.06)
        log(u"  такт %2d: PC=%04X OPs=%02X -> PC=%04X ConPtr=%s"
            % (k + 1, pc0, op0, rd(u"GVL_CPU.PC"), rd(u"GVL_IO.ConPtr")))
    n = rd(u"GVL_IO.ConPtr")
    out = []
    for i in range(max(0, min(10, n))):
        wr(u"GVL_CPU.RD_ADR", u"16#F1%02X" % i)
        time.sleep(0.02)
        out.append(rd(u"GVL_CPU.RD_VAL") & 0xFF)
    txt = u"".join(chr(c) if 32 <= c < 127 else u"." for c in out)
    log(u"консоль: [%s]  ConPtr=%s" % (txt, n))
    try:
        oa.stop(); oa.logout()
    except Exception:
        pass
except Exception:
    log(u"ошибка: %s" % traceback.format_exc().strip().splitlines()[-1])
try:
    proj.close()
except Exception:
    pass
log(u"=== TEST_IO2 END ===")
try:
    system.exit()
except Exception:
    pass
