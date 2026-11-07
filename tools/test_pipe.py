# -*- coding: utf-8 -*-
"""
test_pipe.py -- klyuchevoy zamer arhitektury.

Vopros: vidny li zapisi v GVL_CPU iz ODNOY POU drugoy POU V TOM ZHE skane?
Ot etogo zavisit vsya kompoziciya:
  * esli vidny -- mezhstupennye svyazi mozhno derzhat v GVL (kak seychas);
  * esli net   -- nuzhno vse vesti PROVODAMI v odnom liste.

Opy t: dve kroshechnye POU i programma:
  P1: GVL_CPU.MID := 5           (zapis)
  P2: GVL_CPU.OUT2 := GVL_CPU.MID (chtenie v drugoy POU)
  PLC_PRG: P1() ; P2()
Chtenie OUT2 posle starta: esli 0 -- znachit zapisi vidny tolko so sleduyushchego
skana (i togda vsya kompoziciya peredelyvaetsya na provoda).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_pipe.log")
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
log(u"=== TEST_PIPE START ===")

# P1: пишет MID := 5
s = Sheet(u"P1: запись MID")
s.assign(u"GVL_CPU.MID", s.const(u"BYTE#5", 0), 1)
wr(u"PIPE_P1", pou_xml(u"PIPE_P1", u"functionBlock", interface(locals_=[]), [s],
                       u"пишет MID"))

# P2: OUT2 := MID
s = Sheet(u"P2: чтение MID")
s.assign(u"GVL_CPU.OUT2", s.ref(u"GVL_CPU.MID", 0), 1)
wr(u"PIPE_P2", pou_xml(u"PIPE_P2", u"functionBlock", interface(locals_=[]), [s],
                       u"читает MID"))

# программa: P1(); P2();
s = Sheet(u"PLC_PRG: конвейер")
s.blk(u"PIPE_P1", [], 1, width=110, inst=u"A")
s.blk(u"PIPE_P2", [], 3, width=110, inst=u"B")
prg = pou_xml(u"PLC_PRG", u"program",
              interface(locals_=[(u"A", u"PIPE_P1"), (u"B", u"PIPE_P2")]), [s],
              u"проверка порядка")
p = wr(u"PIPE_PRG", prg)
log(u"схемы записаны")

import scriptengine

BASE = os.path.join(BUILD, u"pipe.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"pipe.project"):
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
    for nm in (u"PIPE_P1", u"PIPE_P2"):
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
    if errs == 0:
        try:
            oa.set_prepared_value(u"GVL_CPU.OUT2", u"16#00")
            oa.write_prepared_values()
        except Exception:
            pass
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

log(u"=== TEST_PIPE END ===")
try:
    system.exit()
except Exception:
    pass
