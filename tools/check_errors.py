# -*- coding: utf-8 -*-
"""check_errors.py -- sobrat' proekt i vyvesti soobshcheniya ob oshibkah."""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "check_errors.log")
DIR = r"C:\p"
SRC = os.path.join(DIR, u"CPM6502_CPU.project")
WORK = os.path.join(DIR, u"c.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== CHECK_ERRORS START ===")

for junk in os.listdir(DIR):
    if junk.startswith(u"c.project"):
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

log(u"сборка...")
try:
    app.build()
    log(u"сборка вернулась")
except Exception:
    log(u"сборка: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    cats = system.get_message_categories()
    log(u"категорий: %d" % len(cats))
    total = 0
    shown = 0
    for c in cats:
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        for m in msgs:
            total += 1
            try:
                t = u"%s" % (m,)
            except Exception:
                continue
            low = t.lower()
            if (u"ошибк" in low or u"error" in low or u"неизвестн" in low
                    or u"не задан" in low) and u"0 ошибки" not in t:
                if shown < 15:
                    log(u"  !! %s" % t[:200])
                    shown += 1
    log(u"всего сообщений: %d, показано: %d" % (total, shown))
except Exception:
    log(u"перебор: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== CHECK_ERRORS END ===")
try:
    system.exit()
except Exception:
    pass
