# -*- coding: utf-8 -*-
"""
test_memwr.py -- proverka pravila 2.4 konspekta: zapis' v massiv po
VYCHISLYAEMOMU indeksu.

Konspekt govorit: "Log[i] := ch ne pishetsya" -- zapis' po indeksu-vyrazheniyu
teryaetsya. Nam eto kriticheski vazhno: bez nee ne rabotayut STA, JSR, BRK.

Opyty v odnom POU (vse - otdelnye prisvoeniya):
  Mem[ADDR]      := DATA          -- indeks-vhod (kak u nas v FB_CPU_Store)
  Mem[WORD#16#0300] := DATA       -- indeks-konstanta (kontrol')
Chtenie: Mem[512] dolzhno stat' $55, Mem[768] -- $55.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_memwr.log")
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
log(u"=== TEST_MEMWR START ===")

s = Sheet(u"WR: запись в память")
addr = s.ref(u"ADDR", 0)
data = s.ref(u"DATA", 1)
s.assign(u"GVL_MEM.Mem[ADDR]", data, 2)
s.assign(u"GVL_MEM.Mem[WORD#16#0300]", s.ref(u"DATA", 1), 4)
wr(u"MEMWR", pou_xml(u"MEMWR", u"functionBlock",
                     interface(inputs=[(u"ADDR", u"WORD"), (u"DATA", u"BYTE")]),
                     [s], u"запись в память"))

s2 = Sheet(u"PLC_PRG: подача адреса и данных")
s2.blk(u"MEMWR", [(u"ADDR", s2.const(u"WORD#16#0200", 0)),
                  (u"DATA", s2.const(u"BYTE#16#55", 0))], 1, width=110, inst=u"W")
wr(u"MEMWR_PRG", pou_xml(u"PLC_PRG", u"program",
                         interface(locals_=[(u"W", u"MEMWR")]), [s2], u"подача"))
log(u"схемы записаны")

import scriptengine

BASE = os.path.join(BUILD, u"memwr.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"memwr.project"):
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
try:
    g = app.create_gvl(u"GVL_MEM")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.import_xml(os.path.join(PLCOPEN, u"MEMWR.xml"), False)
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(os.path.join(PLCOPEN, u"MEMWR_PRG.xml"), False)
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
        time.sleep(0.5)
    except Exception:
        pass
    log(u"")
    log(u"  ожидание: Mem[512]=$55 (индекс-вход), Mem[768]=$55 (индекс-константа)")
    for expr in (u"GVL_MEM.Mem[512]", u"GVL_MEM.Mem[768]", u"GVL_MEM.Mem[513]"):
        try:
            log(u"  %-22s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-22s ошибка чтения" % expr)
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

log(u"=== TEST_MEMWR END ===")
try:
    system.exit()
except Exception:
    pass
