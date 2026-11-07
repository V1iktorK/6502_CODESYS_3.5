# -*- coding: utf-8 -*-
"""
test_open3.py -- otkrytie proekta iz CHISTOY papki C:\p.

Gipoteza: v C:\CPM6502_build nakopilos' >200 fajlov .project; CODESYS pri
otkrytii mog padaт' iz-za etogo (watchdog kataloga / recent list).
"""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_open3.log")
SRC = r"C:\CPM6502_build\wrk_a.project"
DSTDIR = r"C:\p"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_OPEN3 START ===")
import scriptengine
log(u"scriptengine ok")

if not os.path.isdir(DSTDIR):
    os.makedirs(DSTDIR)
    log(u"создана папка %s" % DSTDIR)

dst = os.path.join(DSTDIR, u"a.project")
try:
    _s = io.open(SRC, "rb")
    _d = _s.read()
    _s.close()
    _o = io.open(dst, "wb")
    _o.write(_d)
    _o.close()
    log(u"копия %d байт -> %s" % (len(_d), dst))
except Exception:
    log(u"копия: %s" % traceback.format_exc().strip().splitlines()[-1])

t0 = time.time()
try:
    pr = projects.open(dst)
    log(u"open из C:\\p: OK за %.1f с" % (time.time() - t0))
    try:
        app = pr.active_application
        log(u"приложение получено")
    except Exception:
        log(u"приложение: %s" % traceback.format_exc().strip().splitlines()[-1])
    pr.close()
    log(u"закрыт")
except Exception:
    log(u"open: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== TEST_OPEN3 END ===")
try:
    system.exit()
except Exception:
    pass
