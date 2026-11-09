# -*- coding: utf-8 -*-
"""test_memw.py -- gde propadaet zapis' v GVL_MEM.Mem po peremennomu adresu.

Stroim tri POU:
  FB_MW    -- ADR/DAT/EN -> Mem[ADR] := EN ? DAT : Mem[ADR]
  FB_L1    -- vyzyvaet FB_MW (vlozhennost' 1 uroven')
  PLC_PRG  -- vyzyvaet FB_L1 (vlozhennost' 2 urovnya)
Pishem po adresu iz vhodnogo pina i smotrim, chto leglo v pamyat'.
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_memw.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_MEMW START ===")


def wr_xml(name, xml):
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    with io.open(p, "wb") as fh:
        fh.write(xml.encode("utf-8"))
    return p


# --- FB_MW
s = Sheet(u"FB_MW: запись в память")
addr = u"GVL_MEM.Mem[ADR]"
s.assign(addr, s.blk(u"SEL", [(u"G", s.ref(u"EN", 0)), (u"IN0", s.ref(addr, 0)),
                              (u"IN1", s.ref(u"DAT", 0))], 1), 2)
s.assign(u"OUT", s.ref(u"EN", 3), 4)
p_mw = wr_xml(u"FB_MW", pou_xml(u"FB_MW", u"functionBlock",
                                interface(inputs=[(u"ADR", u"WORD"), (u"DAT", u"BYTE"),
                                                  (u"EN", u"BOOL")],
                                          outputs=[(u"OUT", u"BOOL")]),
                                [s], u"запись"))

# --- FB_L1 (один уровень вложенности)
s = Sheet(u"FB_L1: обёртка")
b = s.blk(u"FB_MW", [(u"ADR", s.ref(u"ADR", 0)), (u"DAT", s.ref(u"DAT", 0)),
                     (u"EN", s.ref(u"EN", 0))], 1, inst=u"Mw")
s.assign(u"OUT", b, 3)
p_l1 = wr_xml(u"FB_L1", pou_xml(u"FB_L1", u"functionBlock",
                                interface(inputs=[(u"ADR", u"WORD"), (u"DAT", u"BYTE"),
                                                  (u"EN", u"BOOL")],
                                          outputs=[(u"OUT", u"BOOL")],
                                          locals_=[(u"Mw", u"FB_MW")]),
                                [s], u"обёртка"))

# --- PLC_PRG: вызов FB_MW напрямую и через FB_L1
s = Sheet(u"PLC_PRG: проверка записи")
a0 = s.blk(u"FB_MW", [(u"ADR", s.ref(u"GVL_CPU.A0", 0)), (u"DAT", s.ref(u"GVL_CPU.D0", 0)),
                      (u"EN", s.const(u"TRUE", 0))], 1, inst=u"M0")
s.assign(u"GVL_CPU.C0", a0, 3)
a1 = s.blk(u"FB_L1", [(u"ADR", s.ref(u"GVL_CPU.A1", 0)), (u"DAT", s.ref(u"GVL_CPU.D1", 0)),
                      (u"EN", s.const(u"TRUE", 0))], 4, inst=u"L1")
s.assign(u"GVL_CPU.C1", a1, 6)
# и запись прямо из программы (для контроля)
mem = u"GVL_MEM.Mem[GVL_CPU.A2]"
s.assign(mem, s.blk(u"SEL", [(u"G", s.const(u"TRUE", 0)), (u"IN0", s.ref(mem, 0)),
                             (u"IN1", s.ref(u"GVL_CPU.D2", 0))], 7), 8)
p_prg = wr_xml(u"PRG_MEMW", pou_xml(u"PLC_PRG", u"program",
                                    interface(locals_=[(u"M0", u"FB_MW"), (u"L1", u"FB_L1")]),
                                    [s], u"проверка записи"))

import scriptengine

BASE = os.path.join(BUILD, u"memw.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"memw.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
src = io.open(TPL, "rb")
data = src.read()
src.close()
dst = io.open(BASE, "wb")
dst.write(data)
dst.close()

proj = projects.open(BASE)
app = proj.active_application
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA0 : WORD;\n\tD0 : BYTE;\n\tC0 : BOOL;\n"
        u"\tA1 : WORD;\n\tD1 : BYTE;\n\tC1 : BOOL;\n"
        u"\tA2 : WORD;\n\tD2 : BYTE;\nEND_VAR\n")
    m = app.create_gvl(u"GVL_MEM")
    m.textual_declaration.replace(u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    for nm, pth in ((u"FB_MW", p_mw), (u"FB_L1", p_l1)):
        app.import_xml(pth, False)
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(p_prg, False)
except Exception:
    log(u"импорт: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.build()
except Exception:
    pass

try:
    node = app
    for i in range(6):
        node = node.parent
        if node is None:
            break
        try:
            node.set_simulation_mode(True)
            break
        except Exception:
            continue
    oa = scriptengine.online.create_online_application(app)
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    oa.start()

    def wr(e, v):
        oa.set_prepared_value(e, v)
        oa.write_prepared_values()

    def rd(e):
        try:
            v = u"%s" % oa.read_value(e)
        except Exception:
            return -1
        try:
            if u"16#" in v:
                return int(v.split(u"16#")[-1], 16)
            if u"#" in v:
                return int(v.split(u"#")[-1])
            return int(v)
        except Exception:
            return -1

    # три записи по разным адресам: напрямую, через 1 уровень, из программы
    wr(u"GVL_CPU.A0", u"16#0300"); wr(u"GVL_CPU.D0", u"16#A0")
    wr(u"GVL_CPU.A1", u"16#0301"); wr(u"GVL_CPU.D1", u"16#A1")
    wr(u"GVL_CPU.A2", u"16#0302"); wr(u"GVL_CPU.D2", u"16#A2")
    time.sleep(0.4)
    log(u"  Mem[0300] (FB напрямую) = %02X  (ожид A0)" % (rd(u"GVL_MEM.Mem[768]") & 0xFF))
    log(u"  Mem[0301] (через обёртку) = %02X (ожид A1)" % (rd(u"GVL_MEM.Mem[769]") & 0xFF))
    log(u"  Mem[0302] (из программы)  = %02X (ожид A2)" % (rd(u"GVL_MEM.Mem[770]") & 0xFF))
    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"онлайн: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== TEST_MEMW END ===")
try:
    system.exit()
except Exception:
    pass
