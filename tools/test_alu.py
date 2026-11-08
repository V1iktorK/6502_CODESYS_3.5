# -*- coding: utf-8 -*-
"""
test_alu.py -- izolirovannaya proverka FB_ALU6502 v RANTAME.

Vopros: pochemu ALU_R = 0, hotya WDATA = 0x42 i vybor operandov dolzhen dat'
0x42. Provеryaem sam POU: podaem konstanty, chitaem GVL_CPU.ALU_R.

Ozhidaem 0x42 dlya rezhima zagruzki (ALU_A=0, ALU_B=0, F_SUB=F_CMP=FALSE).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_alu.log")
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
log(u"=== TEST_ALU START ===")

# программа: подаём константы на входы АЛУ
s = Sheet(u"PLC_PRG: проверка АЛУ")
pins = [(u"A", s.const(u"BYTE#0", 0)),
        (u"X", s.const(u"BYTE#0", 0)),
        (u"P", s.const(u"BYTE#0", 0)),
        (u"WDATA", s.const(u"BYTE#16#42", 0)),
        (u"ALU_A", s.const(u"BYTE#0", 0)),
        (u"ALU_B", s.const(u"BYTE#0", 0)),
        (u"F_SUB", s.const(u"FALSE", 0)),
        (u"F_CMP", s.const(u"FALSE", 0)),
        (u"USE_CARRY", s.const(u"FALSE", 0))]
bid = s.blk(u"FB_ALU6502", pins, 2, width=150, inst=u"Alu")
# Читаем контактный выход: без этого CODESYS не исполняет тело ПОУ.
s.assign(u"GVL_CPU.Chain1", bid, 4)
prg = pou_xml(u"PLC_PRG", u"program",
              interface(locals_=[(u"Alu", u"FB_ALU6502")]), [s], u"проверка АЛУ")
p = wr(u"PRG_ALU", prg)
log(u"PRG_ALU: %d байт" % os.path.getsize(p))

import scriptengine

BASE = os.path.join(BUILD, u"alu.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"alu.project"):
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

gvl = (u"VAR_GLOBAL\n"
       u"\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n\tSP : BYTE;\n\tPC : WORD;\n"
       u"\tWDATA : BYTE;\n\tALU_A : BYTE;\n\tALU_B : BYTE;\n"
       u"\tF_SUB : BOOL;\n\tF_CMP : BOOL;\n\tUSE_CARRY : BOOL;\n\tF_ADD : BOOL;\n"
       u"\tALU_R : BYTE;\n\tCARRY : BOOL;\n\tV_ADD : BOOL;\n\tV_SUB : BOOL;\n"
       u"\tN_F : BOOL;\n\tZ_F : BOOL;\n\tISUB : BOOL;\n\tChain1 : BOOL;\n"
       u"END_VAR\n")
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(gvl)
    log(u"GVL создан")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    for dep in (u"FB_ALU6502",):
        app.import_xml(os.path.join(PLCOPEN, u"%s.xml" % dep), False)
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(p, False)
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
    for expr in (u"GVL_CPU.ALU_R", u"GVL_CPU.ALU_AX", u"GVL_CPU.ALU_BX",
                 u"GVL_CPU.CARRY", u"GVL_CPU.N_F"):
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

log(u"=== TEST_ALU END ===")
try:
    system.exit()
except Exception:
    pass
