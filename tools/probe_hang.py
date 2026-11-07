# -*- coding: utf-8 -*-
"""
probe_hang.py -- chto imenno VEASHAET import (modalnoe okno bez UI).

Fakt: FB_AddrMode (60 KB, ~120 blokov) privodit k zavisaniyu CODESYS, pri chem
ni isklyucheniya, ni soobshcheniya net; vse potoki zastyvayut v UserRequest
(nevidimoe modalnoe okno v rezhime --noUI). Eto NOVYY rezhim otkaza -- ranee
shema molcha NE sozdavalas, a teper import visnet.

Proveryaem po odnoy konstrukcii, prichyom stroka "перед импортом" pishetsya
DO importa: esli protsess zavisnet, v loge ostanetsya imenno vinovnaya
konstrukciya. Poryadok -- ot naimenee podozritelnoy k naibolee.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_hang.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def write(path, text):
    o = io.open(path, "wb")
    o.write(text.encode("utf-8"))
    o.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_HANG START ===")

CASES = []


def case(name, builder, locs):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    CASES.append((name, fbd.pou_xml(name, u"program",
                                   fbd.interface(locals_=locs), [s], comment=u"probe")))


def b_lit_idx(s):
    s.assign(u"B1", s.ref(u"Mem[WORD#16#FFFE]", 0), 1)


def b_local_idx(s):
    w = s.blk(u"ADD", [(u"IN1", s.ref(u"W2", 0)), (u"IN2", s.const(u"WORD#1", 0))], 0)
    s.assign(u"W1", w, 1)
    s.assign(u"B1", s.ref(u"Mem[W1]", 0), 2)


def b_mul256(s):
    m = s.blk(u"MUL", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"B2", 0))], 0)),
                       (u"IN2", s.const(u"WORD#256", 0))], 1)
    s.assign(u"W1", m, 2)


def b_ge_byte(s):
    s.assign(u"G1", s.blk(u"GE", [(u"IN1", s.ref(u"B2", 0)),
                                  (u"IN2", s.const(u"BYTE#16#80", 0))], 1), 2)


def b_ort11(s):
    parts = []
    for k in range(11):
        g = s.blk(u"EQ", [(u"IN1", s.ref(u"B2", 0)),
                          (u"IN2", s.const(u"BYTE#%d" % k, 0))], 1)
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(u"WORD#0", 0)),
                                    (u"IN1", s.const(u"WORD#%d" % (k + 1), 0))], 2))
    cur = s.blk(u"OR", [(u"IN1", parts[0]), (u"IN2", parts[1])], 4)
    for p in parts[2:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], 5)
    s.assign(u"W1", cur, 6)


V = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"B1", u"BYTE"), (u"B2", u"BYTE"),
     (u"G1", u"BOOL")]

case(u"H_GE_BYTE", b_ge_byte, V)
case(u"H_LOCAL_IDX", b_local_idx, V)
case(u"H_LIT_IDX", b_lit_idx, V)
case(u"H_MUL256", b_mul256, V)
case(u"H_ORT11", b_ort11, V)

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"hang_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"hang_bs.project"):
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

import scriptengine
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
    log(u"GVL_MEM создан")
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
for name, _x in CASES:
    log(u"  ПЕРЕД ИМПОРТОМ %s" % name)
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"  %s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                           (u"  (искл: %s)" % exc) if exc else u""))

log(u"конец (если последняя строка без результата -- виноват тот импорт)")
log(u"=== PROBE_HANG END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
