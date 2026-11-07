# -*- coding: utf-8 -*-
"""test_open.py -- proverka: otkryvaetsya li MALENKIY proekt (create -> save -> open)."""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_open.log")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_OPEN START ===")
import scriptengine
log(u"scriptengine ok")

p = os.path.join(BUILD, u"tiny.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"tiny.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass

t0 = time.time()
try:
    proj = projects.create(p)
    log(u"create: %.1f с" % (time.time() - t0))
    t0 = time.time()
    proj.save()
    log(u"save: %.1f с" % (time.time() - t0))
    proj.close()
    log(u"close ок")
except Exception:
    log(u"create/save: %s" % traceback.format_exc().strip().splitlines()[-1])

t0 = time.time()
try:
    proj2 = projects.open(p)
    log(u"open маленького: %.1f с -> %s" % (time.time() - t0, proj2))
    proj2.close()
    log(u"закрыт")
except Exception:
    log(u"open: %s" % traceback.format_exc().strip().splitlines()[-1])

# --- теперь большой проект
BIG = os.path.join(BUILD, u"tiny_big.project")
SRC = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"tiny_big.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
try:
    _s = io.open(SRC, "rb")
    _d = _s.read()
    _s.close()
    _o = io.open(BIG, "wb")
    _o.write(_d)
    _o.close()
    t0 = time.time()
    proj3 = projects.open(BIG)
    log(u"open БОЛЬШОГО: %.1f с -> %s" % (time.time() - t0, proj3))
    proj3.close()
    log(u"большой закрыт")
except Exception:
    log(u"большой: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== TEST_OPEN END ===")
try:
    system.exit()
except Exception:
    pass
