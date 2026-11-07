# -*- coding: utf-8 -*-
"""
test_diag.py -- izoliruyushchiy opyt dlya deshifratora.

Berem gotovyy build/CPM6502_CPU.project, zamenyaem PLC_PRG na variant,
kotoryy podaet na FB_Decoder6502 konstantu $A9, zapuskaem simulyaciyu i
chitaem signaly deshifratora.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_diag.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
PLCOPEN = os.path.join(ROOT, "plcopen")
BUILD = r"C:\CPM6502_build"

READS = [u"GVL_CPU.C_IMM", u"GVL_CPU.C_STK", u"GVL_CPU.C_ABY", u"GVL_CPU.C_REL", u"GVL_CPU.ADDR_MODE", u"GVL_CPU.LEN", u"GVL_CPU.SRC",
         u"GVL_CPU.PC_MODE", u"GVL_CPU.SP_MODE", u"GVL_CPU.COND",
         u"GVL_CPU.LD_A", u"GVL_CPU.LD_X", u"GVL_CPU.WR_MEM",
         u"GVL_CPU.SET_NZ", u"GVL_CPU.F_ADD", u"GVL_CPU.OPs"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_DIAG START ===")
import scriptengine

WORK = os.path.join(BUILD, u"diag.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"diag.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(PROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()

proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")

# заменить PLC_PRG на диагностический
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
        log(u"PLC_PRG удалён")
    app.import_xml(os.path.join(PLCOPEN, u"PRG_DIAG.xml"), False)
    log(u"диагностическая PLC_PRG импортирована")
except Exception:
    log(u"ОШИБКА замены: %s" % traceback.format_exc().strip().splitlines()[-1])

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
log(u"ошибок: %d" % len(errs))
for t in errs[:10]:
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
    for expr in READS:
        try:
            log(u"  %-20s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-20s ошибка чтения" % expr)
    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"ОШИБКА онлайн: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass

log(u"=== TEST_DIAG END ===")
try:
    system.exit()
except Exception:
    pass
