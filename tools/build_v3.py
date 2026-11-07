# -*- coding: utf-8 -*-
"""
build_v3.py -- sozdaem proekt srazu na "CODESYS Control Win V3".

Zachem: oshibka C0046 "Идентификатор 'IoConfigTaskMap' не задан" idet ot
shablonnogo ustroystva PLCWinNT (CoDeSys SP Win V3) iz Templates\\Standard.project.
U nego est konfiguraciya I/O, ne privyazannaya k zadache. U CODESYS Control Win V3
takoy konfiguracii net -- oshibka ischezaet, i eto shtatnoe ustroystvo dlya
simulyacii (i ono zhe potom menyaetsya na Control for Raspberry Pi).

Probuyem neskolko variantov vyzova add_device i, esli hot odin rabotaet,
sobirayem polnyy proekt na nem.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
BUILD = r"C:\CPM6502_build"
LOG = os.path.join(ROOT, "log", "build_v3.log")
DST = os.path.join(BUILD, u"CPM6502_v3.project")

ORDER = [u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
         u"FB_Decoder6502"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== BUILD_V3 START ===")
import scriptengine

# ---------------------------------------------------------------- kandidaty ustroystv
log(u"--- поиск устройства в репозитории ---")
cands = []
try:
    for d in device_repository.get_all_devices():
        try:
            nm = u""
            for attr in (u"name", u"device_name", u"Name"):
                try:
                    v = getattr(d, attr)
                    if v:
                        nm = v
                        break
                except Exception:
                    pass
            if not nm:
                nm = str(d)
            if u"Control Win" in nm:
                cands.append((nm, d))
        except Exception:
            pass
    log(u"найдено кандидатов: %d" % len(cands))
    for nm, d in cands[:10]:
        log(u"  %s" % nm)
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- proba add_device
log(u"--- попытки создать проект с нужным устройством ---")
dev = None
app = None
proj = None
if cands:
    nm = cands[0][0]
    attempts = [
        (u"create + add_device(name, type, id)",
         lambda: projects.create("v3probe").add_device(nm, 4096, u"1")),
        (u"create + add_device(name=, type=, id=)",
         lambda: projects.create("v3probe2").add_device(name=nm, type=4096, id=u"1")),
        (u"create + add_device(name)",
         lambda: projects.create("v3probe3").add_device(nm)),
    ]
    for title, fn in attempts:
        try:
            r = fn()
            log(u">>> РАБОТАЕТ: %s -> %r" % (title, r))
            dev = r
            break
        except Exception:
            log(u">>> не подошёл: %s -- %s" % (title, traceback.format_exc().strip().splitlines()[-1]))

if dev is not None:
    try:
        app = dev.create_application() if hasattr(dev, "create_application") else None
        log(u"create_application -> %r" % (app,))
    except Exception:
        log(traceback.format_exc())

# ---------------------------------------------------------------- sborka na ustroystve
if app is not None:
    log(u"--- сборка на CODESYS Control Win V3 ---")
    for gname, dfile in ((u"GVL_CPU", u"GVL_decl.txt"), (u"GVL_MEM", u"GVL_mem_decl.txt")):
        try:
            txt = io.open(os.path.join(PLCOPEN, dfile), "r", encoding="utf-8").read()
            gvl = app.create_gvl(gname)
            gvl.textual_declaration.replace(txt)
            log(u"GVL %s создана" % gname)
        except Exception:
            log(u"!!! GVL %s: %s" % (gname, traceback.format_exc().strip().splitlines()[-1]))
    for name in ORDER:
        p = os.path.join(PLCOPEN, u"%s.xml" % name)
        try:
            app.import_xml(p, False)
            log(u"  %s импортирован" % name)
        except Exception:
            log(u"  %s ОШИБКА: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
    try:
        names = []
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.append(s.split(u"Name=")[1].split(u",")[0])
        log(u"состав: %s" % u", ".join(sorted(names)))
    except Exception:
        log(traceback.format_exc())
    # сохраняем ДО компиляции
    try:
        for p in projects.all:
            p.save_as(DST, u"")
        log(u"сохранено: %s" % DST)
    except Exception:
        log(traceback.format_exc())
    log(u"--- компиляция ---")
    try:
        app.build()
        log(u"app.build() -- без исключения")
    except Exception:
        log(u"app.build() -- ИСКЛЮЧЕНИЕ:")
        log(traceback.format_exc())
else:
    log(u"!!! автоматически создать проект на CODESYS Control Win V3 не удалось")
    log(u"--- ИНСТРУКЦИЯ ДЛЯ GUI ---")
    log(u"  1. Открыть CPM6502.project")
    log(u"  2. Двойной щёлчок по 'PLCWinNT (CoDeSys SP Win V3)'")
    log(u"  3. Вкладка 'Общие' -> кнопка 'Изменить устройство...'")
    log(u"  4. Выбрать 'CODESYS Control Win V3' -> ОК")
    log(u"  5. F11 (пересборка) -- ошибка C0046 уходит")

log(u"=== BUILD_V3 END ===")
try:
    system.exit()
except Exception:
    pass
