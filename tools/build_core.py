# -*- coding: utf-8 -*-
"""
build_core.py -- sozdaet GVL, importiruet PRG_CPU_CORE, kompiliruet.

Proverka: primet li CODESYS samuyu bolshuyu shemu proekta (2716 elementov,
777 blokov) i razreshitsya li vnutri neyo vyzovy funkciy
F_UnpackByte / F_PackByte.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
PLCOPEN_ALT = r"C:\CPM6502_build\plcopen"
LOG = os.path.join(ROOT, "log", "build_core.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
PROJECT = os.path.join(os.getcwd(), u"CPM6502_Core3.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== BUILD_CORE START ===")
log(u"cwd: %s" % os.getcwd())
import scriptengine

BASE = os.path.join(os.getcwd(), u"base_core3.project")
for junk in os.listdir(os.getcwd()):
    if junk.startswith(u"base_core3.project") or junk.startswith(u"CPM6502_Core3.project"):
        try:
            os.remove(os.path.join(os.getcwd(), junk))
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


def xp(name):
    p = os.path.join(PLCOPEN, name)
    return p if os.path.exists(p) else os.path.join(PLCOPEN_ALT, name)


for gname, dfile in ((u"GVL_CPU", u"GVL_decl.txt"), (u"GVL_MEM", u"GVL_mem_decl.txt")):
    try:
        txt = io.open(xp(dfile), "r", encoding="utf-8").read()
        gvl = app.create_gvl(gname)
        gvl.textual_declaration.replace(txt)
        log(u"GVL %s создана" % gname)
    except Exception:
        log(u"!!! GVL %s:" % gname)
        log(traceback.format_exc())

for helper in (u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16"):
    p = xp(u"%s.xml" % helper)
    if not os.path.exists(p):
        log(u"нет файла %s" % helper)
        continue
    try:
        app.import_xml(p, False)
        log(u"%s -> %s" % (helper, u"создан" if helper in children() else u"НЕ СОЗДАН"))
    except Exception:
        log(u"!!! %s: %s" % (helper, traceback.format_exc().strip().splitlines()[-1]))

# ВАЖНО: тип экземпляра обязан существовать в проекте ДО импорта того POU,
# который его использует. PRG_CPU_CORE объявляет Dec : FB_Decoder6502, поэтому
# декодер грузится ПЕРВЫМ. Без этого CODESYS молча отбрасывает ядро:
# неразрешённый тип экземпляра -- ошибка того же класса, что и необъявленная
# переменная, то есть ссылка на то, чего нет в объявлении.
for dep in (u"FB_Decoder6502",):
    p = xp(u"%s.xml" % dep)
    if not os.path.exists(p):
        log(u"нет файла зависимости %s" % dep)
        continue
    try:
        app.import_xml(p, False)
        log(u"зависимость %s -> %s" % (dep, u"создан" if dep in children() else u"НЕ СОЗДАН"))
    except Exception:
        log(u"!!! %s: %s" % (dep, traceback.format_exc().strip().splitlines()[-1]))

p = xp(u"PRG_CPU_CORE.xml")
log(u"импорт %s (%d байт)" % (p, os.path.getsize(p) if os.path.exists(p) else -1))
try:
    app.import_xml(p, False)
    log(u"PRG_CPU_CORE -> %s" % (u"СОЗДАН" if u"PRG_CPU_CORE" in children() else u"НЕ СОЗДАН"))
except Exception:
    log(u"!!! импорт ядра:")
    log(traceback.format_exc())

log(u"--- сохранение (ДО компиляции) ---")
# Сохраняем ДО сборки: app.build() на этом проекте иногда роняет процесс CODESYS,
# и тогда сохранение после сборки не выполняется -- результат теряется.
log(u"состав: %s" % u", ".join(sorted(children())))
try:
    proj.save_as(PROJECT, u"")
    log(u"сохранено: %s" % PROJECT)
except Exception:
    log(traceback.format_exc())

log(u"--- компиляция ---")
try:
    app.build()
    log(u"app.build() -- без исключения")
except Exception:
    log(u"app.build() -- ИСКЛЮЧЕНИЕ:")
    log(traceback.format_exc())
try:
    msgs = system.get_messages()
    log(u"сообщений: %d" % len(msgs))
    for m in msgs[:60]:
        try:
            log(u"  [%s] %s" % (getattr(m, "severity", u"?"), getattr(m, "text", m)))
        except Exception:
            log(u"  %r" % (m,))
except Exception:
    log(traceback.format_exc())

try:
    proj.close()
except Exception:
    pass
log(u"=== BUILD_CORE END ===")
try:
    system.exit()
except Exception:
    pass
