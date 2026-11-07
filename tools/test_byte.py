# -*- coding: utf-8 -*-
"""
test_byte.py -- minimalnyy opyt: rabotayut li v CODESYS SEL i OR po BYTE.

Logika shemy dokazana offlajn (fbd_sim.py): deshifrator daet ADDR_MODE=1.
Znachit vopros v povedenii SEL/OR po BYTE v samom CODESYS.

Chistyy proekt: GVL_CPU (C_IMM, C_ZP), programma PLC_PRG s dvumya vyrazheniyami:
  C_IMM := OR(BYTE#1, BYTE#2)          -- ozhidaem 3
  C_ZP  := SEL(G=TRUE, IN0=BYTE#0, IN1=BYTE#7)  -- ozhidaem 7
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_byte.log")
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
log(u"=== TEST_BYTE START ===")

# ---------- генерация маленькой программы
s = Sheet(u"PLC_PRG: проверка байтовых операций")
s.assign(u"GVL_CPU.C_IMM",
         s.blk(u"OR", [(u"IN1", s.const(u"BYTE#1", 0)),
                       (u"IN2", s.const(u"BYTE#2", 0))], 1), 3)
s.assign(u"GVL_CPU.C_ZP",
         s.blk(u"SEL", [(u"G", s.const(u"TRUE", 0)),
                        (u"IN0", s.const(u"BYTE#0", 1)),
                        (u"IN1", s.const(u"BYTE#7", 1))], 2), 4)
xml = pou_xml(u"PLC_PRG", u"program", interface(locals_=[]), [s], u"проверка BYTE")
p = os.path.join(PLCOPEN, u"PRG_BYTE.xml")
fo = io.open(p, "wb")
fo.write(xml.encode("utf-8"))
fo.close()
log(u"PRG_BYTE: %d байт" % os.path.getsize(p))

import scriptengine

BASE = os.path.join(BUILD, u"byte.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"byte.project"):
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

try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tC_IMM : BYTE;\n\tC_ZP : BYTE;\nEND_VAR\n")
    log(u"GVL создан")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

# заменить PLC_PRG
try:
    prg = None
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                prg = o
                break
        except Exception:
            continue
    if prg is not None:
        prg.remove()
        log(u"пустая PLC_PRG удалена")
    app.import_xml(p, False)
    log(u"PRG_BYTE импортирована")
except Exception:
    log(u"замена: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.build()
except Exception:
    pass
errs = []
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                t = u"%s" % (m,)
            except Exception:
                continue
            low = t.lower()
            if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) and u"0 ошибки" not in t:
                errs.append(t)
    except Exception:
        pass
log(u"ошибок компиляции: %d" % len(errs))
for t in errs[:8]:
    log(u"  %s" % t)

# симуляция
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
    log(u"симуляция запущена")
    try:
        import time
        time.sleep(0.5)
    except Exception:
        pass
    for expr in (u"GVL_CPU.C_IMM", u"GVL_CPU.C_ZP"):
        try:
            log(u"  %-16s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-16s ошибка чтения" % expr)
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

log(u"=== TEST_BYTE END ===")
try:
    system.exit()
except Exception:
    pass
