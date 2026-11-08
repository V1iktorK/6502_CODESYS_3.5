# -*- coding: utf-8 -*-
"""
test_prim.py -- chto iz primitivov realno rabotaet V RANTAME.

Odin malenkiy POU chitaet vhod WDATA i pishet 8 nezavisimyh rezultatov.
Cel: ponyat, kakaya KONSTRUKCIYA lomaetsya (podozrenie -- vlozhennye SEL,
poskolku i deshifrator, i ALU dayut 0 imenno na cepochkah SEL).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_prim.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def wr(name, xml):
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    return p


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_PRIM START ===")

# ---------------- POU с примитивами
s = Sheet(u"PRIM: проверка примитивов")
wd = s.ref(u"WDATA", 0)
s.assign(u"GVL_CPU.T1", s.blk(u"ADD", [(u"IN1", s.const(u"BYTE#0", 1)),
                                       (u"IN2", wd)], 1), 2)
s.assign(u"GVL_CPU.T2", s.blk(u"SEL", [(u"G", s.const(u"FALSE", 1)),
                                       (u"IN0", s.const(u"BYTE#9", 1)),
                                       (u"IN1", s.ref(u"WDATA", 1))], 3), 4)
s.assign(u"GVL_CPU.T3", s.blk(u"XOR", [(u"IN1", s.ref(u"WDATA", 1)),
                                       (u"IN2", s.const(u"BYTE#16#FF", 1))], 5), 6)
inner = s.blk(u"SEL", [(u"G", s.const(u"FALSE", 1)),
                       (u"IN0", s.const(u"BYTE#9", 1)),
                       (u"IN1", s.const(u"BYTE#7", 1))], 7)
s.assign(u"GVL_CPU.T4", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 1)),
                                       (u"IN0", inner),
                                       (u"IN1", s.const(u"BYTE#3", 1))], 8), 9)
prim = pou_xml(u"PRIM", u"functionBlock",
               interface(inputs=[(u"WDATA", u"BYTE")]), [s], u"примитивы")
p1 = wr(u"PRIM", prim)

# ---------------- программа: PRIM(WDATA := $42)
s2 = Sheet(u"PLC_PRG: подача $42")
s2.blk(u"PRIM", [(u"WDATA", s2.const(u"BYTE#16#42", 0))], 1, width=110, inst=u"P")
prg = pou_xml(u"PLC_PRG", u"program", interface(locals_=[(u"P", u"PRIM")]), [s2],
              u"подача")
p2 = wr(u"PRIM_PRG", prg)
log(u"схемы записаны")

import scriptengine

BASE = os.path.join(BUILD, u"prim.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"prim.project"):
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

proj = projects.open(BASE)
app = proj.active_application
log(u"проект открыт")

gvl = (u"VAR_GLOBAL\n\tT1 : BYTE;\n\tT2 : BYTE;\n\tT3 : BYTE;\n\tT4 : BYTE;\n"
       u"\tWDATA : BYTE;\nEND_VAR\n")
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(gvl)
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.import_xml(p1, False)
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(p2, False)
    log(u"импорт выполнен")
except Exception:
    log(u"импорт: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.build()
except Exception:
    pass
errs = 0
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                t = u"%s" % (m,)
            except Exception:
                continue
            low = t.lower()
            if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) and u"0 ошибки" not in t:
                errs += 1
                log(u"  !! %s" % t)
    except Exception:
        pass
log(u"ошибок компиляции: %d" % errs)

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
    try:
        import time
        time.sleep(0.4)
    except Exception:
        pass
    log(u"")
    log(u"  ожидание: T1=66 (ADD 0+$42), T2=66 (SEL FALSE), T3=189 (XOR $FF), T4=7 (вложенный SEL)")
    for expr in (u"GVL_CPU.T1", u"GVL_CPU.T2", u"GVL_CPU.T3", u"GVL_CPU.T4"):
        try:
            log(u"  %-12s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-12s ошибка чтения" % expr)
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

log(u"=== TEST_PRIM END ===")
try:
    system.exit()
except Exception:
    pass
