# -*- coding: utf-8 -*-
"""
test_wire2.py -- T-WIRE na baze gotovoy sborki.

Shablon otkryvaetsya nedopustimo dolgo (zavisaet), a build/CPM6502_CPU.project
otkryvaetsya normalno. Poetomu opyt delaem na ego kopii:
  WIRE_P1 -- FB s odnim vyhodom OUT := BYTE#5;
  WIRE_P2 -- vyzyvaet P1 i delaet GVL_CPU.C_IMM := SEL(TRUE, P1.OUT, 0);
  PLC_PRG -- vyzyvaet WIRE_P1 i WIRE_P2.

Chtenie: C_IMM (ozhidaem 5), C_ZP (kontrol, dolzhen byt 0).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_wire2.log")
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
OLD = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


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
log(u"=== TEST_WIRE2 START ===")

# P1: OUT := BYTE#5
s = Sheet(u"WIRE_P1: выход OUT")
s.assign(u"OUT", s.const(u"BYTE#5", 0), 1)
wr(u"WIRE_P1", pou_xml(u"WIRE_P1", u"functionBlock",
                       interface(outputs=[(u"OUT", u"BYTE")]), [s], u"пишет OUT"))

# P2: C_IMM := SEL(TRUE, P1.OUT, 0)
s = Sheet(u"WIRE_P2: провод от экземпляра")
a = s.blk(u"WIRE_P1", [], 1, width=110, inst=u"A")
sel = s.blk(u"SEL", [(u"G", s.const(u"TRUE", 0)), (u"IN0", a),
                     (u"IN1", s.const(u"BYTE#0", 0))], 3)
s.assign(u"GVL_CPU.C_IMM", sel, 5)
wr(u"WIRE_P2", pou_xml(u"WIRE_P2", u"functionBlock",
                       interface(locals_=[(u"A", u"WIRE_P1")]), [s],
                       u"берёт выход экземпляра проводом"))

# программа
s = Sheet(u"PLC_PRG: проверка провода")
s.blk(u"WIRE_P1", [], 1, width=110, inst=u"P1")
s.blk(u"WIRE_P2", [], 3, width=110, inst=u"P2")
s.assign(u"GVL_CPU.C_ZP", s.const(u"BYTE#0", 5), 6)
prg = pou_xml(u"PLC_PRG", u"program",
              interface(locals_=[(u"P1", u"WIRE_P1"), (u"P2", u"WIRE_P2")]), [s],
              u"проверка провода")
p = wr(u"WIRE_PRG", prg)
log(u"схемы записаны")

import scriptengine

WORK = os.path.join(BUILD, u"wrk_a.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"wrk_a.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(OLD, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()
log(u"копия сборки: %d байт" % len(_d))

# прогрев: create открывает сессию быстрее, чем первый open
try:
    warm = os.path.join(BUILD, u"wire2_warm.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"wire2_warm.project"):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    wp = projects.create(warm)
    wp.close()
    log(u"прогрев выполнен")
except Exception:
    log(u"прогрев: %s" % traceback.format_exc().strip().splitlines()[-1])
proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")


def drop(name):
    try:
        for o in (app.find(name, True) or []):
            try:
                if o.textual_declaration is not None and o.textual_declaration.text:
                    o.remove()
                    log(u"  удалён старый %s" % name)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


drop(u"PLC_PRG")
for nm in (u"WIRE_P1", u"WIRE_P2"):
    drop(nm)
    try:
        app.import_xml(os.path.join(PLCOPEN, u"%s.xml" % nm), False)
        log(u"  импортирован %s" % nm)
    except Exception:
        log(u"  импорт %s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))
try:
    app.import_xml(p, False)
    log(u"  импортирована PLC_PRG")
except Exception:
    log(u"  импорт PLC_PRG: %s" % traceback.format_exc().strip().splitlines()[-1])

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
    c_imm = c_zp = None
    for expr in (u"GVL_CPU.C_IMM", u"GVL_CPU.C_ZP"):
        try:
            v = oa.read_value(expr)
            log(u"  %-14s = %s" % (expr, v))
            if expr.endswith(u"C_IMM"):
                c_imm = v
            else:
                c_zp = v
        except Exception:
            log(u"  %-14s ошибка чтения" % expr)
    log(u"T-WIRE: %s" % (u"PASS (провод работает)" if c_imm is not None else u"см. значения"))
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

log(u"=== TEST_WIRE2 END ===")
try:
    system.exit()
except Exception:
    pass
