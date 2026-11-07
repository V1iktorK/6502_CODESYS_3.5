# -*- coding: utf-8 -*-
"""test_open2.py -- kakie kopii proektov voobshche otkryvayutsya (s trassirovkoy)."""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_open2.log")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_OPEN2 START ===")
import scriptengine
log(u"scriptengine ok")

for name in (u"wrk_a.project", u"bat.project", u"lda2.project", u"final.project"):
    p = os.path.join(BUILD, name)
    if not os.path.exists(p):
        log(u"%s: файла нет" % name)
        continue
    log(u"открываю %s (%d байт)..." % (name, os.path.getsize(p)))
    t0 = time.time()
    try:
        pr = projects.open(p)
        log(u"  OK за %.1f с -> %s" % (time.time() - t0, pr))
        try:
            pr.close()
            log(u"  закрыт")
        except Exception:
            log(u"  не закрылся")
    except Exception:
        log(u"  ИСКЛЮЧЕНИЕ: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== TEST_OPEN2 END ===")
try:
    system.exit()
except Exception:
    pass
