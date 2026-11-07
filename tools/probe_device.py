# -*- coding: utf-8 -*-
"""probe_device.py -- kakie atributy est' u opisanija ustroystva v repo."""
import io
import os

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_device.log")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_DEVICE START ===")
import scriptengine

rep = scriptengine.device_repository
devs = rep.get_all_devices()
log(u"устройств: %d" % len(devs))
d0 = devs[0]
log(u"объект: %s" % (u"%s" % d0)[:120])

NAMES = [u"name", u"device_id", u"id", u"version", u"device_version", u"vendor",
         u"vendor_id", u"type", u"guid", u"description", u"display_name",
         u"category", u"is_root", u"tree_devices", u"device_name", u"title"]
for n in NAMES:
    try:
        v = getattr(d0, n)
        log(u"  .%s = %s" % (n, v))
    except Exception as e:
        log(u"  .%s -> %s" % (n, type(e).__name__))

# metod: raspechatat' pervye 5 strok cherez str()
for i in range(3):
    log(u"устройство %d: %s" % (i, (u"%s" % devs[i])[:200]))

# poprobovat' poisк po imeni cherez metod repo
for meth in (u"get_device", u"find_device", u"get_all_devices", u"get_devices"):
    try:
        m = getattr(rep, meth)
        log(u"repo.%s -> callable" % meth)
    except Exception:
        log(u"repo.%s -> нет" % meth)

log(u"=== PROBE_DEVICE END ===")
try:
    system.exit()
except Exception:
    pass
