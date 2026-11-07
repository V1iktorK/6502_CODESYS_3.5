# -*- coding: utf-8 -*-
"""test_smoke2.py -- chto imenno visnet: create / open shablona / open sborki."""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_smoke2.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
OLD = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== SMOKE2 START ===")
import scriptengine
log(u"scriptengine ok")

NEW = os.path.join(BUILD, u"sm2_new.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"sm2_new.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass

log(u"--- projects.create ---")
try:
    p = projects.create(NEW)
    log(u"  create вернул: %s" % p)
    try:
        p.close()
    except Exception:
        pass
except Exception:
    log(u"  create: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"--- open sborki (build/CPM6502_CPU.project) ---")
COPY = os.path.join(BUILD, u"sm2_old.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"sm2_old.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
try:
    _s = io.open(OLD, "rb")
    _d = _s.read()
    _s.close()
    o = io.open(COPY, "wb")
    o.write(_d)
    o.close()
    log(u"  копия %d байт" % len(_d))
    log(u"  вызываю open...")
    p = projects.open(COPY)
    log(u"  open вернул: %s" % p)
    try:
        p.close()
    except Exception:
        pass
except Exception:
    log(u"  open: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== SMOKE2 END ===")
try:
    system.exit()
except Exception:
    pass
