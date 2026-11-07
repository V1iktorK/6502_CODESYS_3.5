# -*- coding: utf-8 -*-
"""probe_device2.py -- atributy opisaniya ustroystva BEZ prevrashcheniya v stroku."""
import io
import os

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_device2.log")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_DEVICE2 START ===")
import scriptengine

rep = scriptengine.device_repository
devs = rep.get_all_devices()
log(u"устройств: %d" % len(devs))
d0 = devs[0]

NAMES = [u"name", u"device_id", u"id", u"version", u"device_version", u"vendor",
         u"vendor_id", u"type", u"guid", u"description", u"display_name",
         u"category", u"device_name", u"title", u"vendor_name"]
ok = []
for n in NAMES:
    try:
        v = getattr(d0, n)
        try:
            s = u"%s" % v
        except Exception:
            s = u"<не строковый>"
        log(u"  .%s = %s" % (n, s[:80]))
        ok.append(n)
    except Exception as e:
        log(u"  .%s -> %s" % (n, type(e).__name__))

log(u"доступные атрибуты: %s" % u", ".join(ok))

# poisk po imeni: perebiraem i sravnivaem atribut name, esli on est'
if u"name" in ok:
    found = 0
    for i in range(len(devs)):
        try:
            nm = u"%s" % devs[i].name
        except Exception:
            continue
        if u"Control Win" in nm or u"210" in nm:
            try:
                did = u"%s" % devs[i].device_id
            except Exception:
                did = u"?"
            try:
                ver = u"%s" % devs[i].version
            except Exception:
                ver = u"?"
            log(u"  НАЙДЕНО: name=%s device_id=%s version=%s" % (nm, did, ver))
            found += 1
            if found >= 8:
                break
    log(u"найдено кандидатов: %d" % found)

log(u"=== PROBE_DEVICE2 END ===")
try:
    system.exit()
except Exception:
    pass
