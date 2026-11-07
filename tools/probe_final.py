# -*- coding: utf-8 -*-
"""
probe_final.py -- PEREVERKA "blokera".

Pochti uveren, chto istinnaya prichina "yadro ne sozdaetsya" -- oshibka MOEY
proverki: vse PRG_CORE_L*.xml vnutri ob"yavlyayut imya PRG_CPU_CORE, a ya
iskal sovpadenie s imenem FAYLA (PRG_CORE_L2 i t.p.). Poetomu zdes:
  1) importiruem zavisimosti + dekoder;
  2) importiruem PRG_CORE_L10 (polnoe yadro);
  3) vygruzhaem POLNYY spisok detey (rekursivno);
  4) sobiraem proekt i chitaem SOOBSHCHENIYA s podrobnym razborom atributov.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_final.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_FINAL START ===")
import scriptengine

BASE = os.path.join(BUILD, u"fin_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fin_bs.project"):
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

try:
    g2 = app.create_gvl(u"GVL_MEM")
    g2.textual_declaration.replace(u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
    log(u"GVL созданы")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])


def all_names():
    """Rekursivno: vse imena ob"ektov v prilozhenii."""
    out = []

    def walk(node, depth):
        try:
            kids = node.get_children()
        except Exception:
            return
        for k in kids:
            nm = None
            try:
                nm = k.get_name()
            except Exception:
                nm = None
            if nm is None:
                try:
                    s = str(k)
                    nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else s
                except Exception:
                    nm = u"<??>"
            out.append((depth, nm))
            walk(k, depth + 1)

    walk(app, 0)
    return out


for dep in (u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16"):
    p = os.path.join(PLCOPEN, u"%s.xml" % dep)
    if os.path.exists(p):
        try:
            app.import_xml(p, False)
        except Exception:
            pass
try:
    app.import_xml(os.path.join(PLCOPEN, u"FB_Decoder6502.xml"), False)
except Exception:
    log(u"декодер: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"")
log(u"--- дети ДО импорта ядра ---")
before = all_names()
for d, n in before:
    log(u"  %s%s" % (u"  " * d, n))

log(u"")
exc = None
try:
    app.import_xml(os.path.join(PLCOPEN, u"PRG_CORE_L10.xml"), False)
except Exception:
    exc = traceback.format_exc().strip().splitlines()[-1]
log(u"импорт PRG_CORE_L10: %s" % (u"исключение: %s" % exc if exc else u"без исключения"))

after = all_names()
log(u"")
log(u"--- дети ПОСЛЕ импорта ядра ---")
for d, n in after:
    log(u"  %s%s" % (u"  " * d, n))
new = [n for d, n in after if n not in [x for _, x in before]]
log(u"")
log(u"НОВЫЕ объекты: %s" % (u", ".join(new) if new else u"нет"))
log(u"PRG_CPU_CORE присутствует: %s" % (u"ДА" if u"PRG_CPU_CORE" in [n for _, n in after] else u"НЕТ"))


def dump_msgs(where):
    log(u"  --- сообщения: %s ---" % where)
    total = 0
    try:
        cats = system.get_message_categories()
    except Exception:
        log(u"    нет get_message_categories")
        return 0
    for c in cats:
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        if not msgs:
            continue
        for m in msgs:
            total += 1
            parts = []
            for attr in (u"severity", u"text", u"pou", u"object", u"position",
                         u"category", u"number", u"project", u"filename", u"line"):
                try:
                    parts.append(u"%s=%s" % (attr, getattr(m, attr)))
                except Exception:
                    parts.append(u"%s=?" % attr)
            log(u"    [%s] %s" % (c, u" | ".join(parts)))
            try:
                log(u"           str: %s" % (m,))
            except Exception:
                pass
            try:
                system.delete_message(m)
            except Exception:
                pass
    if total == 0:
        log(u"    (сообщений нет)")
    return total


log(u"")
try:
    app.build()
    log(u"сборка: выполнена")
except Exception:
    log(u"сборка: исключение %s" % traceback.format_exc().strip().splitlines()[-1])
dump_msgs(u"после сборки")

# poprobuyte poluchit dostup k POU po imeni
for nm in (u"PRG_CPU_CORE", u"FB_CPU_Core", u"FB_Decoder6502"):
    try:
        pou = app.find(nm, True)
        log(u"find(%s) -> %s" % (nm, u"НАЙДЕН" if pou is not None else u"нет"))
    except Exception:
        log(u"find(%s) -> исключение %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))

log(u"=== PROBE_FINAL END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
