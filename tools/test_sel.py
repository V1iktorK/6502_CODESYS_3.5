# -*- coding: utf-8 -*-
"""test_sel.py -- kakie piny u SEL: G? IN0? IN1? Proveryaem napryamую.

Stroim PLC_PRG s odnim blokom SEL(G:=TRUE, IN0:=BYTE#11, IN1:=BYTE#22)
i chitaem rezultat. Zatem to zhe s G=FALSE. Eto reshaet vopros o poryadke
pinov (pravilo 2.8: piny ekzemplyarov sopostavlyayutsya POZICIONNO).
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_sel.log")
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
log(u"=== TEST_SEL START ===")

s = Sheet(u"PLC_PRG: проверка порядка пинов SEL")
# G берём из GVL, чтобы проверить оба случая в одном прогоне
sel = s.blk(u"SEL", [(u"G", s.ref(u"GVL_CPU.TG", 0)),
                     (u"IN0", s.const(u"BYTE#16#11", 0)),
                     (u"IN1", s.const(u"BYTE#16#22", 0))], 2)
s.assign(u"GVL_CPU.RS", sel, 4)
prg = pou_xml(u"PLC_PRG", u"program", interface(), [s], u"порядок пинов SEL")
p = os.path.join(PLCOPEN, u"PRG_SEL.xml")
with io.open(p, "wb") as fh:
    fh.write(prg.encode("utf-8"))

import scriptengine

BASE = os.path.join(BUILD, u"sel.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"sel.project"):
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
    g.textual_declaration.replace(u"VAR_GLOBAL\n\tTG : BOOL;\n\tRS : BYTE;\nEND_VAR\n")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(p, False)
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

    for gval, label in ((u"FALSE", u"G=FALSE"), (u"TRUE", u"G=TRUE")):
        wr(u"GVL_CPU.TG", gval)
        time.sleep(0.3)
        log(u"  %s -> RS=%02X" % (label, rd(u"GVL_CPU.RS") & 0xFF))
    log(u"  ожидание по документации: G=FALSE -> 11, G=TRUE -> 22")
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
log(u"=== TEST_SEL END ===")
try:
    system.exit()
except Exception:
    pass
