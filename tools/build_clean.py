# -*- coding: utf-8 -*-
"""
build_clean.py -- chistaya sborka proekta s CHEStNOY proverkoy kompilyacii.

Pochemu otdelnyy skript: v proshlyh progah ya chital soobshcheniya cherez
system.get_messages() i poluchal 0 PRI 4 realnyh oshibkah (vyyasnilos po
skrinshotu polzovatelya). Zdes chitaem VSEMI dostupnymi sposobami:
get_messages(), get_message_objects(), get_messages(category_guid), a takzhe
lovim isklyuchenie ot app.build().

Poryadok: snachala SOHRANYAEM (build inogda ronyaet process), potom kompiliruem.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
BUILD = r"C:\CPM6502_build"
LOG = os.path.join(ROOT, "log", "build_clean.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BASE = os.path.join(BUILD, u"base_v3.project")
DST = os.path.join(BUILD, u"CPM6502.project")

# Порядок = порядок зависимостей. FB_CPU_Core исключён: он не создаётся,
# разбираться с ним отдельно, чтобы не мешать чистой сборке.
ORDER = [u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
         u"FB_Decoder6502", u"FB_IOBridge", u"FB_AnalogBridge", u"FB_DiskImage"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== BUILD_CLEAN START ===")
import scriptengine

for junk in os.listdir(BUILD):
    if junk.startswith(u"base_v3.project") or junk.startswith(u"CPM6502.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(TPL, "rb")
_d = _s.read()
_s.close()
_o = io.open(BASE, "wb")
_o.write(_d)
_o.close()

proj = app = None
try:
    proj = projects.open(BASE)
    app = proj.active_application
    log(u"проект открыт")
except Exception:
    log(traceback.format_exc())


def children():
    names = []
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.append(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        log(traceback.format_exc())
    return names


# ---------------------------------------------------------------- GVL
for gname, dfile in ((u"GVL_CPU", u"GVL_decl.txt"), (u"GVL_MEM", u"GVL_mem_decl.txt"),
                       (u"GVL_BUS", u"GVL_BUS.txt"), (u"GVL_IO", u"GVL_IO.txt"),
                       (u"GVL_MAP", u"GVL_MAP.txt")):
    p = os.path.join(PLCOPEN, dfile)
    try:
        txt = io.open(p, "r", encoding="utf-8").read()
        gvl = app.create_gvl(gname)
        gvl.textual_declaration.replace(txt)
        log(u"GVL %s создана" % gname)
    except Exception:
        log(u"!!! GVL %s: %s" % (gname, traceback.format_exc().strip().splitlines()[-1]))

# ---------------------------------------------------------------- импорт схем
log(u"--- импорт схем ---")
ok, bad = [], []
for name in ORDER:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(p):
        log(u"  %-16s НЕТ ФАЙЛА" % name)
        bad.append(name)
        continue
    try:
        app.import_xml(p, False)
    except Exception:
        log(u"  %-16s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(name)
        continue
    got = name in children()
    log(u"  %-16s -> %s" % (name, u"создан" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(name)
log(u"импортировано %d из %d; проблемные: %s" % (len(ok), len(ORDER), u", ".join(bad) or u"(нет)"))
log(u"состав: %s" % u", ".join(sorted(children())))

# ---------------------------------------------------------------- сохранение ДО сборки
log(u"--- сохранение до сборки ---")
saved = False
try:
    proj.save_as(DST, u"")
    saved = True
    log(u"сохранено: %s (%d байт)" % (DST, os.path.getsize(DST)))
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- компиляция
log(u"--- компиляция ---")
try:
    app.build()
    log(u"app.build() -- без исключения")
except Exception:
    log(u"app.build() -- ИСКЛЮЧЕНИЕ:")
    log(traceback.format_exc())

# ---------------------------------------------------------------- сообщения: все способы
log(u"--- сообщения: get_messages() ---")
try:
    msgs = system.get_messages()
    log(u"всего: %d" % len(msgs))
    for m in msgs:
        log(u"  %r" % (m,))
except Exception:
    log(traceback.format_exc())

log(u"--- сообщения: get_message_objects() ---")
try:
    objs = system.get_message_objects()
    log(u"всего: %d" % len(objs))
    for o in objs:
        parts = []
        for attr in (u"severity", u"text", u"message", u"position", u"object_name"):
            try:
                parts.append(u"%s=%s" % (attr, getattr(o, attr)))
            except Exception:
                pass
        log(u"  " + (u" | ".join(parts) if parts else repr(o)))
except Exception:
    log(traceback.format_exc())

log(u"--- сообщения по категориям ---")
try:
    for c in system.get_message_categories():
        try:
            msgs = system.get_messages(c)
            log(u"  категория %r: %d" % (c, len(msgs)))
            for m in msgs:
                log(u"     %r" % (m,))
        except Exception:
            pass
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- финальное сохранение
try:
    proj.save()
    log(u"повторное сохранение выполнено")
except Exception:
    log(traceback.format_exc())

log(u"ИТОГ: схем импортировано %d из %d" % (len(ok), len(ORDER)))
log(u"=== BUILD_CLEAN END ===")
try:
    system.exit()
except Exception:
    pass
