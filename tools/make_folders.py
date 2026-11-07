# -*- coding: utf-8 -*-
"""
make_folders.py -- struktura dereva POU, chtoby ona byla VIDNA i chitaema.

Zachem: POU, zagruzhennye cherez import_xml, lezhat ploskо vnutri uzla
Application, i derevo vyglyadit pustym: vidny tolko PLC_PRG i Task Configuration.
Sozdaem papki po planu proekta i perenosim tuda ob'ekty.

Papki (iz plana): 00_GVL, 10_CPU, 20_CPM, 30_IO, 40_Test, 50_Init, 60_Visu.
"""
import io
import os
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "make_folders.log")
SRC = os.path.join(r"C:\CPM6502_build", u"CPM6502_Core.project")
DST = os.path.join(r"C:\CPM6502_build", u"CPM6502.project")

FOLDERS = [u"00_GVL", u"10_CPU", u"20_CPM", u"30_IO", u"40_Test", u"50_Init", u"60_Visu"]

# какой объект в какую папку
PLACE = {
    u"GVL_CPU": u"00_GVL", u"GVL_MEM": u"00_GVL",
    u"FB_Decoder6502": u"10_CPU", u"FB_FlagsReg": u"10_CPU", u"FB_Memory64K": u"10_CPU",
    u"FB_PC_Update": u"10_CPU", u"FB_Reg8": u"10_CPU", u"FB_Reg16": u"10_CPU",
    u"F_Add16": u"10_CPU", u"F_Join16": u"10_CPU", u"F_PackByte": u"10_CPU",
    u"F_Split16": u"10_CPU", u"F_UnpackByte": u"10_CPU", u"FB_CPU_Core": u"10_CPU",
}


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== MAKE_FOLDERS START ===")
import scriptengine

if not os.path.exists(SRC):
    src = os.path.join(ROOT, "build", u"CPM6502_Core.project")
else:
    src = SRC
log(u"открываю %s" % src)
proj = app = None
try:
    proj = projects.open(src)
    app = proj.active_application
    log(u"проект открыт")
except Exception:
    log(traceback.format_exc())


def kids(obj):
    out = []
    try:
        for ch in obj.get_children():
            s = str(ch)
            nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else repr(ch)[:50]
            out.append((nm, ch))
    except Exception:
        log(traceback.format_exc())
    return out


log(u"состав до изменений: %s" % u", ".join(n for n, _ in kids(app)))

# ---- создаём папки ----
made = {}
for name in FOLDERS:
    try:
        folder = app.create_folder(name)
        made[name] = folder
        log(u"папка %s создана" % name)
    except Exception:
        log(u"!!! папка %s: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))

# ---- переносим объекты ----
log(u"--- перенос объектов ---")
for objname, obj in kids(app):
    target = PLACE.get(objname)
    if not target or target not in made:
        continue
    moved = False
    for meth in (u"move_to", u"move", u"set_parent", u"reparent"):
        if hasattr(obj, meth) and hasattr(made[target], u"get_children"):
            try:
                getattr(obj, meth)(made[target])
                log(u"  %-18s -> %s (через %s)" % (objname, target, meth))
                moved = True
                break
            except Exception:
                continue
    if not moved:
        log(u"  %-18s перенести не удалось (API перемещения недоступен)" % objname)

log(u"--- состав после ---")
for name in FOLDERS:
    if name in made:
        try:
            inner = u", ".join(n for n, _ in kids(made[name]))
        except Exception:
            inner = u"?"
        log(u"  %-9s : %s" % (name, inner or u"(пусто)"))
log(u"верхний уровень: %s" % u", ".join(n for n, _ in kids(app)))

try:
    proj.save_as(DST, u"")
    log(u"сохранено: %s" % DST)
except Exception:
    log(traceback.format_exc())
try:
    proj.close()
except Exception:
    pass
log(u"=== MAKE_FOLDERS END ===")
try:
    system.exit()
except Exception:
    pass
