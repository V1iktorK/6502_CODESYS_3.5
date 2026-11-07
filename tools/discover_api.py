# -*- coding: utf-8 -*-
"""
discover_api.py -- chto umeet API: repo ustroystv, dobavlenie device, add().

Cel: sozdat' proekt C NULYA (projects.create rabotaet) i dobavit' ustroystvo
programmno, chtoby ne otkryvat' sushchestvuyushchie proekty (ikh otkrytie
seychas avanit CODESYS).
"""
import io
import os

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "discover_api.log")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DISCOVER START ===")

import scriptengine
log(u"scriptengine ok")

# 1) modul repository
for nm in (u"device_repository", u"DeviceRepository", u"devices"):
    try:
        mod = getattr(scriptengine, nm)
        log(u"scriptengine.%s -> %s" % (nm, mod))
    except Exception as e:
        log(u"scriptengine.%s -> нет (%s)" % (nm, type(e).__name__))

# 2) sozdanie proekta
p = os.path.join(BUILD, u"disc.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"disc.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
proj = projects.create(p)
log(u"projects.create OK")

# 3) chto est' u proekta
for attr in (u"add", u"active_application", u"children", u"devices", u"find"):
    try:
        v = getattr(proj, attr)
        log(u"proj.%s -> %s" % (attr, v if not callable(v) else u"callable"))
    except Exception as e:
        log(u"proj.%s -> нет (%s)" % (attr, type(e).__name__))

# 4) poprobovat' poluchit' spisok ustroystv iz repo
try:
    rep = scriptengine.device_repository
    devs = rep.get_all_devices()
    log(u"устройств в репозитории: %d" % len(devs))
    shown = 0
    for d in devs:
        try:
            nm = u"%s" % d
        except Exception:
            nm = u"?"
        if u"Control" in nm or u"PLK" in nm or u"210" in nm or u"Win" in nm:
            log(u"  %s" % nm)
            shown += 1
            if shown > 25:
                break
except Exception:
    log(u"repo: %s" % traceback.format_exc().strip().splitlines()[-1]
        if False else u"repo недоступен")

try:
    proj.close()
except Exception:
    pass
log(u"=== DISCOVER END ===")
try:
    system.exit()
except Exception:
    pass
