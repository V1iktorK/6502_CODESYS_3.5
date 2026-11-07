# -*- coding: utf-8 -*-
"""
test_wire.py -- T-WIRE: rabotaet li provod "vyhod OUT ekzemplyara -> vhod SEL".

Eto klyuchevoy opyt dlya varianta A:
  P1 -- funkciya/ FB s ODNIM vyhodom OUT = BYTE#5 (konstanta);
  P2 -- vyzyvaet P1 i delaet GVL_CPU.OUT2 := SEL(G=TRUE, IN0=P1.OUT, IN1=BYTE#0);
  PLC_PRG -- A() ; B().

Ozhidaem OUT2 = 5. Esli 0 -- provod ne rabotaet, i vsya kompoziciya trebuet
inogo reshenia (naprimer, peredachi cherez pamyat).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_wire.log")
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
log(u"=== TEST_WIRE START ===")

# --- P1: OU T := BYTE#5
s = Sheet(u"W_P1: выход OUT")
s.assign(u"OUT", s.const(u"BYTE#5", 0), 1)
wr(u"WIRE_P1", pou_xml(u"WIRE_P1", u"functionBlock",
                       interface(outputs=[(u"OUT", u"BYTE")]), [s], u"пишет OUT"))

# --- P2: OUT2 := SEL(TRUE, A.OUT, BYTE#0)
s = Sheet(u"W_P2: провод от экземпляра")
a = s.blk(u"WIRE_P1", [], 1, width=110, inst=u"A")
sel = s.blk(u"SEL", [(u"G", s.const(u"TRUE", 0)), (u"IN0", a),
                     (u"IN1", s.const(u"BYTE#0", 0))], 3)
s.assign(u"GVL_CPU.OUT2", sel, 5)
wr(u"WIRE_P2", pou_xml(u"WIRE_P2", u"functionBlock",
                       interface(locals_=[(u"A", u"WIRE_P1")]), [s],
                       u"берёт выход экземпляра проводом"))

# --- программа
s = Sheet(u"PLC_PRG: проверка провода")
s.blk(u"WIRE_P1", [], 1, width=110, inst=u"P1")
s.assign(u"GVL_CPU.MID", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 0)),
                                        (u"IN0", s.blk(u"WIRE_P1", [], 2, width=110, inst=u"P1b")),
                                        (u"IN1", s.const(u"BYTE#0", 0))], 3), 5)
s.blk(u"WIRE_P2", [], 6, width=110, inst=u"P2")
prg = pou_xml(u"PLC_PRG", u"program",
              interface(locals_=[(u"P1", u"WIRE_P1"), (u"P1b", u"WIRE_P1"),
                                 (u"P2", u"WIRE_P2")]), [s], u"проверка провода")
p = wr(u"WIRE_PRG", prg)
log(u"схемы записаны")

import scriptengine

BASE = os.path.join(BUILD, u"wire.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"wire.project"):
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
        u"VAR_GLOBAL\n\tMID : BYTE;\n\tOUT2 : BYTE;\nEND_VAR\n")
    log(u"GVL создан")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    prgobj = None
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                prgobj = o
                break
        except Exception:
            continue
    if prgobj is not None:
        prgobj.remove()
    for nm in (u"WIRE_P1", u"WIRE_P2"):
        app.import_xml(os.path.join(PLCOPEN, u"%s.xml" % nm), False)
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
    for expr in (u"GVL_CPU.MID", u"GVL_CPU.OUT2"):
        try:
            log(u"  %-14s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-14s ошибка чтения" % expr)
    log(u"T-WIRE: %s (ожидание MID=5, OUT2=5)"
        % (u"PASS" if os.environ.get(u"__never__") else u"см. значения выше"))
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

log(u"=== TEST_WIRE END ===")
try:
    system.exit()
except Exception:
    pass
