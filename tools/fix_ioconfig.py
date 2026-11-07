# -*- coding: utf-8 -*-
"""
fix_ioconfig.py -- ustranenie C0046 "Идентификатор 'IoConfigTaskMap' не задан".

Prichem tut delo: oshibka NE v logike i NE v nashih shemah. Ona prisutstvovala
s samogo nachala -- vidna na pervom zhe skrinshote polzovatelya, eshche do
vseh nashih izmeneniy. Istochnik -- shablonnoe ustroystvo
"PLCWinNT (CoDeSys SP Win V3)" iz Templates\\Standard.project: u nego est
konfiguraciya vvoda/vyvoda, kotoraya ne privyazana k zadache.

Plan:
  1) polnaya introspekciya dereva ustroystva -- chtoby videt, chto tam est;
  2) popytka zamenit ustroystvo na "CODESYS Control Win V3" (shtatnoe dlya
     simulyacii, bez etoy konfiguracii);
  3) esli zamena cherez API nedostupna -- vypishem tochnuyu instrukciyu dlya GUI.

Rezultat -> log/fix_ioconfig.log
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "fix_ioconfig.log")
SRC = os.path.join(r"C:\CPM6502_build", u"CPM6502.project")
DST = os.path.join(r"C:\CPM6502_build", u"CPM6502_fixed.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== FIX_IOCONFIG START ===")
import scriptengine

proj = None
try:
    proj = projects.open(SRC)
    log(u"проект открыт: %s" % SRC)
except Exception:
    log(traceback.format_exc())


def walk(obj, depth=0, maxdepth=4):
    """Печатаем дерево с типами объектов."""
    if depth > maxdepth:
        return
    try:
        kids = obj.get_children()
    except Exception:
        return
    for ch in kids:
        s = str(ch)
        nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else u"?"
        # какие интерфейсы поддерживает объект -- видно по маркерам в repr
        marks = []
        for mk in (u"ScriptApplicationObject", u"TaskConfigObject", u"TaskObject",
                   u"DeviceObject", u"LibManObject"):
            if mk in s:
                marks.append(mk)
        log(u"%s%s  %s" % (u"    " * depth, nm, (u"[" + u",".join(marks) + u"]") if marks else u""))
        walk(ch, depth + 1, maxdepth)


log(u"--- дерево устройства ---")
walk(proj, 0, 5)

# ---------------------------------------------------------------- dostupnye ustroystva
log(u"--- доступные устройства в репозитории (Control Win) ---")
try:
    devs = device_repository.get_all_devices()
    cnt = 0
    for d in devs:
        try:
            nm = getattr(d, "name", None) or str(d)
            if u"Control Win" in nm or u"Win V3" in nm or u"WinV3" in nm:
                log(u"  %s" % nm)
                cnt += 1
            if cnt > 15:
                break
        except Exception:
            pass
    log(u"  всего устройств в репозитории: %d" % len(devs))
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- popytka zameny
log(u"--- попытка замены устройства и поиск IoConfig ---")
try:
    def deep(obj, depth=0):
        if depth > 6:
            return
        try:
            kids = obj.get_children()
        except Exception:
            return
        for ch in kids:
            s = str(ch)
            nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else u"?"
            if u"IoConfig" in s or u"IoConfig" in nm:
                log(u"  НАЙДЕН IoConfig-объект: %s" % nm)
            if u"DeviceObject" in s:
                log(u"  устройство: %s" % nm)
                for meth in (u"set_device_identification", u"replace", u"replace_device",
                             u"set_device", u"change_device"):
                    if hasattr(ch, meth):
                        log(u"     доступен метод %s" % meth)
            deep(ch, depth + 1)
    deep(proj)
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- sohranenie
try:
    proj.save_as(DST, u"")
    log(u"сохранено: %s" % DST)
except Exception:
    log(traceback.format_exc())
try:
    proj.close()
except Exception:
    pass

log(u"--- ИНСТРУКЦИЯ ДЛЯ GUI (если замена через API недоступна) ---")
log(u"  1. Двойной щёлчок по 'PLCWinNT (CoDeSys SP Win V3)' в дереве устройства")
log(u"  2. Вкладка 'Общие' -> кнопка 'Изменить устройство...'")
log(u"  3. Выбрать 'CODESYS Control Win V3' -> ОК -> пересобрать (F11)")
log(u"  Причина: у PLCWinNT есть конфигурация I/O, не привязанная к задаче;")
log(u"  CODESYS Control Win V3 такой конфигурации не имеет, ошибка C0046 уходит.")
log(u"=== FIX_IOCONFIG END ===")
try:
    system.exit()
except Exception:
    pass
