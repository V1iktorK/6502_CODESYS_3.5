# -*- coding: utf-8 -*-
"""
probe_constructs.py -- KAKAYA KONSTRUKCIYA v yadre lovit import?

Opornye fakty (vse provereno):
  * ob"em/blokи/razmer  -- OPROVERGNUTO (4000 blokov, 3.7 MB -- sozdaetsya);
  * FB_Decoder6502 (OR/SEL/EQ po BYTE) -- sozdaetsya;
  * yadro (SEL/EQ/OR + ADD/SHR/WORD_TO_BYTE, rabota s Mem i GVL) -- net;
  * import molchit: ni isklyucheniya, ni soobshcheniya.

Znachit delo v otdelnoj konstrukcii. Proveryaem 11 shtuk, kazhdaya v
krohotnoj sheme -- tak vidno tochno, chto imenno ne prinimaetsya.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_constructs.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def write(path, text):
    f = io.open(path, "wb")
    f.write(text.encode("utf-8"))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_CONSTRUCTS START ===")
import scriptengine

CASES = []


def case(name, builder, locs):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    CASES.append((name, fbd.pou_xml(name, u"program", fbd.interface(locals_=locs), [s],
                                   comment=u"probe"), locs))


def b_mem_iw_write(s):
    s.assign(u"Mem[W1]", s.ref(u"B1", 0), 1)


def b_mem_iw_read(s):
    s.assign(u"B1", s.ref(u"Mem[W1]", 0), 1)


def b_mem_ib_read(s):
    s.assign(u"B1", s.ref(u"Mem[SPV]", 0), 1)


def b_mem_ib_write(s):
    s.assign(u"Mem[SPV]", s.ref(u"B1", 0), 1)


def b_mem_expr(s):
    s.assign(u"B1", s.ref(u"Mem[W1 + 1]", 0), 1)


def b_shr_w2b(s):
    b = s.blk(u"SHR", [(u"", s.ref(u"W1", 0)), (u"", s.const(u"8", 0))], 1)
    w = s.blk(u"WORD_TO_BYTE", [(u"", b)], 2)
    s.assign(u"B1", w, 3)


def b_gvl_ref(s):
    s.assign(u"GVL_MEM.Mem[0]", s.ref(u"B1", 0), 1)


def b_gvl_local(s):
    s.assign(u"GVL_CPU.A", s.ref(u"B1", 0), 1)


def b_wordlit(s):
    s.assign(u"W1", s.const(u"WORD#16#FFFC", 0), 1)


def b_mem_wr_from_mem(s):
    s.assign(u"Mem[W1]", s.ref(u"Mem[W2]", 0), 1)


def b_add_sel(s):
    a = s.blk(u"ADD", [(u"", s.ref(u"W1", 0)), (u"", s.ref(u"W2", 0))], 1)
    s.assign(u"W3", a, 2)
    g = s.blk(u"GT", [(u"", s.ref(u"W3", 0)), (u"", s.const(u"WORD#16#0100", 0))], 1)
    sel = s.blk(u"SEL", [(u"G", g), (u"IN0", s.ref(u"W3", 0)), (u"IN1", s.ref(u"W1", 0))], 2)
    s.assign(u"W4", sel, 3)


V_W = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD"), (u"W4", u"WORD")]
V_WB = V_W + [(u"B1", u"BYTE")]
V_SP = V_WB + [(u"SPV", u"BYTE")]

case(u"C_MEM_IW_WRITE", b_mem_iw_write, V_WB)
case(u"C_MEM_IW_READ", b_mem_iw_read, V_WB)
case(u"C_MEM_IB_READ", b_mem_ib_read, V_SP)
case(u"C_MEM_IB_WRITE", b_mem_ib_write, V_SP)
case(u"C_MEM_EXPR", b_mem_expr, V_WB)
case(u"C_SHR_W2B", b_shr_w2b, V_WB)
case(u"C_GVL_REF", b_gvl_ref, V_WB)
case(u"C_GVL_LOCAL", b_gvl_local, V_WB)
case(u"C_WORDLIT", b_wordlit, V_W)
case(u"C_MEM_WR_FROM_MEM", b_mem_wr_from_mem, V_W)
case(u"C_ADD_SEL", b_add_sel, V_W)

for name, xml, _l in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"con_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"con_bs.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(TPL, "rb")
_d = _s.read()
_s.close()
_o = io.open(BASE, "wb")
_o.write(_d)
_o.close()

proj = app = None
try:
    proj = projects.open(BASE)
    app = proj.active_application
    log(u"проект открыт")
except Exception:
    log(traceback.format_exc())

try:
    g2 = app.create_gvl(u"GVL_MEM")
    g2.textual_declaration.replace(u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
    log(u"GVL созданы")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])


def names():
    out = set()
    try:
        for ch in app.get_children():
            try:
                out.add(ch.get_name())
            except Exception:
                s = str(ch)
                if u"Name=" in s:
                    out.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        pass
    return out


log(u"")
log(u"%-18s %s" % (u"КОНСТРУКЦИЯ", u"результат"))
log(u"-" * 40)
bad = []
for name, _xml, _l in CASES:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"%-18s %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                         (u"  (искл: %s)" % exc) if exc else u""))
    if not ok:
        bad.append(name)

log(u"")
if bad:
    log(u"НЕ ПРИНИМАЮТСЯ: %s" % u", ".join(bad))
else:
    log(u"ВСЕ 11 конструкций принимаются -> ни одна не виновата сама по себе.")
log(u"=== PROBE_CONSTRUCTS END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
