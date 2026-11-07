# -*- coding: utf-8 -*-
"""test_smoke.py -- minimalnaya proverka: CODESYS zhiv i otkryvaet proekt."""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_smoke.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== SMOKE START ===")
try:
    log(u"шаблон существует: %s" % os.path.exists(TPL))
    BASE = os.path.join(BUILD, u"smoke.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"smoke.project"):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    _s = io.open(TPL, "rb")
    _d = _s.read()
    _s.close()
    o = io.open(BASE, "wb")
    o.write(_d)
    o.close()
    log(u"копия создана: %d байт" % len(_d))

    import scriptengine
    log(u"scriptengine импортирован")
    proj = projects.open(BASE)
    log(u"проект открыт: %s" % proj)
    app = proj.active_application
    log(u"приложение: %s" % app)
    proj.close()
    log(u"проект закрыт")
except Exception:
    log(u"ОШИБКА: %s" % traceback.format_exc())
log(u"=== SMOKE END ===")
try:
    system.exit()
except Exception:
    pass
