# -*- coding: utf-8 -*-
"""
probe_sim.py -- kak vklyuchit rezhim simulyacii i vojti v onlajn.

Oshibka logina: "Некорректная конфигурация Gateway" -- dlya simulyacii nuzhno
pereklyuchit ustroystvo v rezhim эмуляции. Ischem metod u ob#ekta ustroystva.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_sim.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_SIM START ===")
import scriptengine

WORK = os.path.join(BUILD, u"sim_probe.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"sim_probe.project"):
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

log(u"")
log(u"--- объект устройства ---")
dev = None
try:
    dev = app.parent
    log(u"  app.parent -> %s" % dev)
except Exception:
    log(u"  app.parent: %s" % traceback.format_exc().strip().splitlines()[-1])

for obj, label in ((dev, u"устройство"), (app, u"приложение")):
    if obj is None:
        continue
    log(u"")
    log(u"--- методы %s ---" % label)
    names = []
    try:
        names = [a for a in dir(obj) if not a.startswith(u"_")]
    except Exception:
        log(u"  dir(): %s" % traceback.format_exc().strip().splitlines()[-1])
    for a in names:
        low = a.lower()
        if any(k in low for k in (u"sim", u"gateway", u"address", u"online", u"mode",
                                  u"login", u"connect", u"credential", u"device")):
            try:
                log(u"  %s = %s" % (a, getattr(obj, a)))
            except Exception:
                log(u"  %s (не читается)" % a)

log(u"")
log(u"--- probuem set_simulation_mode ---")
for obj, label in ((dev, u"устройство"), (app, u"приложение")):
    if obj is None:
        continue
    for meth in (u"set_simulation_mode", u"set_simulation", u"set_gateway_and_address"):
        try:
            m = getattr(obj, meth)
            log(u"  %s.%s существует -> %s" % (label, meth, m))
        except Exception:
            pass

log(u"")
log(u"--- probuem vklyuchit simulyaciyu i login ---")
online_app = None
try:
    for target in (dev, app):
        if target is None:
            continue
        try:
            target.set_simulation_mode(True)
            log(u"  set_simulation_mode(True) выполнен на %s" % target)
            break
        except Exception:
            continue
    online_app = scriptengine.online.create_online_application(app)
    online_app.set_default_credentials(u"", u"")
    online_app.login(scriptengine.OnlineChangeOption.Try, False)
    log(u"  login ок, is_logged_in=%s" % online_app.is_logged_in)
    online_app.start()
    log(u"  start ок")
    log(u"  A=%s PC=%s" % (online_app.read_value(u"GVL_CPU.A"),
                           online_app.read_value(u"GVL_CPU.PC")))
    online_app.stop()
    online_app.logout()
except Exception:
    log(u"  ОШИБКА: %s" % traceback.format_exc())

if proj is not None:
    try:
        proj.close()
    except Exception:
        pass

log(u"=== PROBE_SIM END ===")
try:
    system.exit()
except Exception:
    pass
