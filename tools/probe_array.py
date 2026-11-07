# -*- coding: utf-8 -*-
"""
probe_array.py -- gipoteza: LOKALNYY MASSIV v deklaracii POU lovit import.

Edinstvennoe strukturnoe otlichie yadra ot rabochego deshifratora --
objavleniya
    UNP, PKD, PUNP : ARRAY[0..7] OF BOOL
(v deklaracii POU). Nichego podobnogo v rabotayushchih shemah net.

Proveryaem 5 massivnyh variantov v krohotnyh shemah.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_array.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def write(path, text):
    f = io.open(path, "wb")
    f.write(text.encode("utf-8"))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_ARRAY START ===")
import scriptengine

CASES = []


def case(name, builder, locs):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    CASES.append((name, fbd.pou_xml(name, u"program", fbd.interface(locals_=locs), [s],
                                   comment=u"probe"), locs))


def b_none(s):
    s.assign(u"B1", s.ref(u"B2", 0), 1)


def b_arr_read(s):
    s.assign(u"B1", s.ref(u"AR1[3]", 0), 1)


def b_arr_write(s):
    s.assign(u"AR1[3]", s.ref(u"B1", 0), 1)


def b_arr_byte_read(s):
    s.assign(u"B1", s.ref(u"ARB[3]", 0), 1)


def b_arr_2d(s):
    s.assign(u"B1", s.ref(u"AR2[1, 2]", 0), 1)


case(u"A_DECL_ONLY", b_none, [(u"B1", u"BYTE"), (u"B2", u"BYTE"), (u"AR1", u"ARRAY[0..7] OF BOOL")])
case(u"A_READ", b_arr_read, [(u"B1", u"BYTE"), (u"AR1", u"ARRAY[0..7] OF BOOL")])
case(u"A_WRITE", b_arr_write, [(u"B1", u"BYTE"), (u"AR1", u"ARRAY[0..7] OF BOOL")])
case(u"A_BYTE_READ", b_arr_byte_read, [(u"B1", u"BYTE"), (u"ARB", u"ARRAY[0..7] OF BYTE")])
case(u"A_2D_READ", b_arr_2d, [(u"B1", u"BYTE"), (u"AR2", u"ARRAY[0..7, 0..7] OF BOOL")])

for name, xml, _l in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))
log(u"")
log(u"как выглядит объявление массива в XML:")
for name in (u"A_DECL_ONLY",):
    t = io.open(os.path.join(PLCOPEN, u"%s.xml" % name), "rb").read().decode("utf-8")
    k = t.find(u"AR1")
    log(u"  %s" % t[k - 40:k + 200].replace(u"\n", u" "))

BASE = os.path.join(BUILD, u"arr_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"arr_bs.project"):
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


def names():
    out = set()
    try:
        for ch in app.get_children():
            try:
                out.add(ch.get_name())
            except Exception:
                s = str(ch)
                if u"Name=" in s:
                    out.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        pass
    return out


log(u"")
log(u"%-14s %s" % (u"СЛУЧАЙ", u"результат"))
log(u"-" * 34)
bad = []
for name, _xml, _l in CASES:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"%-14s %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                         (u"  (искл: %s)" % exc) if exc else u""))
    if not ok:
        bad.append(name)

log(u"")
if bad:
    log(u"НЕ ПРИНИМАЮТСЯ: %s" % u", ".join(bad))
    log(u"ВЫВОД: локальный массив в объявлении POU ломает импорт.")
else:
    log(u"ВСЕ приняты -> массив не виноват.")
log(u"=== PROBE_ARRAY END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
