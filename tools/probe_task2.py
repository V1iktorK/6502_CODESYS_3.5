# -*- coding: utf-8 -*-
"""
probe_task2.py -- metody ob#ekta zadachi i onlajn-API.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_task2.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_TASK2 START ===")
import scriptengine

COPY = os.path.join(BUILD, u"task2_probe.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"task2_probe.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(PROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(COPY, "wb")
_o.write(_d)
_o.close()

proj = projects.open(COPY)
app = proj.active_application
log(u"проект открыт")

log(u"")
log(u"--- модули scriptengine ---")
for name in dir(scriptengine):
    if not name.startswith(u"_"):
        log(u"  %s" % name)
try:
    import scriptengine.online as on
    log(u"  scriptengine.online доступен")
except Exception:
    log(u"  scriptengine.online: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"")
log(u"--- методы задачи ---")
try:
    res = app.find(u"MainTask", True)
    task = res[0]
    for a in dir(task):
        if not a.startswith(u"_"):
            log(u"  %s" % a)
except Exception:
    log(traceback.format_exc())

log(u"")
log(u"--- методы конфигурации задач ---")
try:
    res = app.find(u"Taskkonfiguration", True)
    tc = res[0]
    for a in dir(tc):
        if not a.startswith(u"_"):
            log(u"  %s" % a)
except Exception:
    log(traceback.format_exc())

log(u"")
log(u"--- декларация PLC_PRG ---")
try:
    res = app.find(u"PLC_PRG", True)
    for o in res:
        log(u"  объект: %s" % o)
        try:
            log(u"   decl: %s" % o.textual_declaration.text[:200])
        except Exception:
            log(u"   decl: недоступно")
except Exception:
    log(traceback.format_exc())

log(u"")
log(u"--- online API ---")
try:
    log(u"  online.%s" % [a for a in dir(scriptengine) if u"online" in a.lower()])
except Exception:
    pass
try:
    oa = scriptengine.online.create_online_application(app)
    log(u"  create_online_application -> %s" % oa)
    for a in (u"login", u"start", u"stop", u"read_value", u"set_prepared_value",
              u"write_prepared_values", u"logout", u"is_logged_in", u"set_default_credentials",
              u"application_state"):
        try:
            log(u"    %s -> %s" % (a, getattr(oa, a)))
        except Exception:
            pass
except Exception:
    log(u"  create_online_application: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== PROBE_TASK2 END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
