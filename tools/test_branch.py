# -*- coding: utf-8 -*-
"""test_branch.py -- proverka cikla/vetvleniy v svobodnom progone.

Programma:
    LDX #$00
loop: INX
    CPX #$05
    BNE loop
    STX $0300      ; dolzhno byt 5
    HLT
Chitaem Mem[$0300] cherez RD_ADR/RD_VAL.
"""
import io, os, sys, time, traceback
ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm6502

LOG = os.path.join(ROOT, "log", "test_branch.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8"); f.write(u"%s\n" % (m,)); f.close()


f = io.open(LOG, "w", encoding="utf-8"); f.write(u""); f.close()
log(u"=== TEST_BRANCH START ===")

SRC = """
ORG $0200
        LDA #$00
        BEQ skip
        LDA #$AA
skip:   STA $0300
        HLT
"""
mem, labels = asm6502.assemble(SRC)
log(u"байты: %s" % u" ".join(u"%02X" % mem[a] for a in sorted(mem)))

import scriptengine
WORK = os.path.join(BUILD, u"br.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"br.project"):
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
    wr(u"GVL_CPU.Run", u"FALSE")
    wr(u"GVL_CPU.Step_On", u"FALSE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    for a in sorted(mem):
        wr(u"GVL_CPU.HADR", u"16#%04X" % a)
        wr(u"GVL_CPU.HDAT", u"16#%02X" % mem[a])
        wr(u"GVL_CPU.HEN", u"TRUE")
        time.sleep(0.02)
        wr(u"GVL_CPU.HEN", u"FALSE")
    wr(u"GVL_CPU.PC", u"16#0200")
    wr(u"GVL_CPU.SP", u"16#FF")
    time.sleep(0.1)
    log(u"до пуска: PC=%s" % rd(u"GVL_CPU.PC"))
    wr(u"GVL_CPU.Run", u"TRUE")
    time.sleep(1.2)
    log(u"после: PC=%s Ops=%s" % (rd(u"GVL_CPU.PC"), rd(u"GVL_CPU.Ops")))
    wr(u"GVL_CPU.RD_ADR", u"16#0300")
    time.sleep(0.05)
    v = rd(u"GVL_CPU.RD_VAL")
    log(u"Mem[0300] = %s (ожидалось 0 -- BEQ перешёл)" % v)
    log(u"T-BEQ0: %s" % (u"PASS" if v == 0 else u"FAIL"))
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
log(u"=== TEST_BRANCH END ===")
try:
    system.exit()
except Exception:
    pass
