# -*- coding: utf-8 -*-
"""test_online.py -- poshagovaya lokalizaciya onlajn-fazy (bez sborki)."""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_online.log")
DIR = r"C:\p"
WORK = os.path.join(DIR, u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_ONLINE START ===")
import scriptengine

proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")

node = app
found = False
for i in range(6):
    node = node.parent
    if node is None:
        break
    try:
        node.set_simulation_mode(True)
        log(u"set_simulation_mode ок на уровне %d" % (i + 1))
        found = True
        break
    except Exception as e:
        log(u"уровень %d: %s" % (i + 1, type(e).__name__))
log(u"симуляция включена: %s" % found)

log(u"create_online_application...")
oa = scriptengine.online.create_online_application(app)
log(u"создано: %s" % (u"%s" % oa)[:80])

log(u"login (Never)...")
oa.login(scriptengine.OnlineChangeOption.Never, False)
log(u"login ок")

log(u"start...")
oa.start()
log(u"start ок")

log(u"чтение A...")
try:
    log(u"  A = %s" % oa.read_value(u"GVL_CPU.A"))
except Exception:
    log(u"  чтение: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    oa.stop()
    oa.logout()
    log(u"остановлено")
except Exception:
    log(u"stop: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== TEST_ONLINE END ===")
try:
    system.exit()
except Exception:
    pass
