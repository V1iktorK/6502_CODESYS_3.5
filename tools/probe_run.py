# -*- coding: utf-8 -*-
"""probe_run.py -- ispolnyaetsya li programma i primenyayutsya li zapisi."""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_run.log")
DIR = r"C:\p"
SRC = os.path.join(DIR, u"CPM6502_CPU.project")
WORK = os.path.join(DIR, u"pr.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_RUN START ===")

for junk in os.listdir(DIR):
    if junk.startswith(u"pr.project"):
        try:
            os.remove(os.path.join(DIR, junk))
        except Exception:
            pass
_s = io.open(SRC, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()
log(u"копия %d байт" % len(_d))

import scriptengine

proj = projects.open(WORK)
app = proj.active_application
log(u"открыт")

# zadat' neskolko yacheek pamyati i vektor
oa = None
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
    log(u"онлайн создано")
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    log(u"login ок")
    oa.start()
    log(u"start ок")
except Exception:
    log(u"ОНЛАЙН: %s" % traceback.format_exc().strip().splitlines()[-1])

if oa is not None:
    try:
        oa.set_prepared_value(u"GVL_MEM.Mem[768]", u"16#AB")
        oa.set_prepared_value(u"GVL_MEM.Mem[65534]", u"16#00")
        oa.set_prepared_value(u"GVL_MEM.Mem[65535]", u"16#02")
        oa.write_prepared_values()
        log(u"записи подготовлены")
    except Exception:
        log(u"запись: %s" % traceback.format_exc().strip().splitlines()[-1])

    time.sleep(0.5)
    for expr in (u"GVL_CPU.PC", u"GVL_CPU.OPs", u"GVL_CPU.SP",
                 u"GVL_CPU.PC_MODE", u"GVL_CPU.SP_MODE", u"GVL_CPU.BRKV",
                 u"GVL_CPU.P_BRK", u"GVL_CPU.P_ADV", u"GVL_CPU.P_KEEP",
                 u"GVL_CPU.EFF", u"GVL_CPU.ADDR_MODE", u"GVL_CPU.LEN",
                 u"GVL_CPU.WDATA", u"GVL_CPU.REG_WR", u"GVL_CPU.ALU_R"):
        try:
            log(u"  %-22s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-22s ошибка чтения" % expr)

    # sostoyanie prilozheniya
    try:
        log(u"  состояние: %s" % oa.application_state)
    except Exception:
        log(u"  application_state: нет")
    try:
        log(u"  online: %s" % (u"%s" % oa.application_state)[:60])
    except Exception:
        pass

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_RUN END ===")
try:
    system.exit()
except Exception:
    pass
