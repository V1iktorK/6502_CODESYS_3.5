# -*- coding: utf-8 -*-
"""test_io.py -- T-IO-1: vyvod simvolov v okno $F000 (konsol CP/M)."""
import io, os, sys, time, traceback
ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm6502

LOG = os.path.join(ROOT, "log", "test_io.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8"); f.write(u"%s\n" % (m,)); f.close()


f = io.open(LOG, "w", encoding="utf-8"); f.write(u""); f.close()
log(u"=== TEST_IO START ===")

SRC = """
ORG $0200
        LDA #$43
        STA $F000
        LDA #$50
        STA $F000
        LDA #$2F
        STA $F000
        LDA #$4D
        STA $F000
        LDA #$20
        STA $F000
        LDA #$4F
        STA $F000
        LDA #$4B
        STA $F000
        HLT
"""
mem, labels = asm6502.assemble(SRC)
log(u"образ: %d байт, метки %s" % (len(mem), labels))
for line in asm6502.to_hex(mem):
    log(u"  " + line)

import scriptengine
WORK = os.path.join(BUILD, u"io.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"io.project"):
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
    # Snachala STOP: inache yadro ispolnyaet musor vo vremya zagruzki obraza
    wr(u"GVL_CPU.Run", u"FALSE")
    # Svobodnyy progon (bez poshagovyh impulsov): odna komanda za skan,
    # ostanavlivaet programma komandoy HLT.
    wr(u"GVL_CPU.Step_On", u"FALSE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    # грузим образ через канал ПЛК
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
    wr(u"GVL_CPU.Run", u"TRUE")
    log(u"перед прогоном: PC=%s Ops=%s Run=%s" % (rd(u"GVL_CPU.PC"), rd(u"GVL_CPU.Ops"), rd(u"GVL_CPU.Run")))
    trace = []
    for _ in range(40):
        trace.append(u"%s/%s" % (rd(u"GVL_CPU.PC"), rd(u"GVL_CPU.Ops")))
        time.sleep(0.02)
    log(u"PC/OPs: %s" % u" ".join(trace))
    log(u"после прогона: PC=%s Ops=%s Enable=%s" % (rd(u"GVL_CPU.PC"), rd(u"GVL_CPU.Ops"), rd(u"GVL_CPU.Enable")))
    n = rd(u"GVL_IO.ConPtr")
    log(u"ConPtr = %s" % n)
    out = []
    for i in range(max(0, min(16, n))):
        wr(u"GVL_CPU.RD_ADR", u"16#F1%02X" % i)
        time.sleep(0.02)
        out.append(rd(u"GVL_CPU.RD_VAL") & 0xFF)
    txt = u"".join(chr(c) if 32 <= c < 127 else u"." for c in out)
    log(u"консоль: [%s]" % txt)
    log(u"T-IO-1: %s (ожидалось CP/M OK)" % (u"PASS" if txt.startswith(u"CP/M OK") else u"FAIL"))
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
log(u"=== TEST_IO END ===")
try:
    system.exit()
except Exception:
    pass
