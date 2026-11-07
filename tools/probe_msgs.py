# -*- coding: utf-8 -*-
"""
probe_msgs.py -- import padaet MOLCHA. Nado uvidet SOOBSHCHENIYA.

Chto delaem:
  1) importiruem FB_Decoder6502 (zavisimost yadra!) -- v probe_base ya ee
     ZABYL, poetomu tot rezultat nedostoveren;
  2) importiruem PRG_CORE_L2 i POSLE importa vygruzhaem VSE soobshcheniya
     po kategoryam (system.get_messages(cat));
  3) otdelno proveryaem tri podozritelnyh bloka v krohotnyh shemah:
     SHR po WORD, WORD_TO_BYTE, ADD po WORD.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_msgs.log")
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
log(u"=== PROBE_MSGS START ===")
import scriptengine

# --------------------------------------------------- tri malenkie shemy
SMALL = []
# S: SHR po WORD
s = fbd.Sheet(u"", order_start=1)
src = s.ref(u"W1", 0)
b = s.blk(u"SHR", [(u"", src), (u"", s.const(u"8", 0))], 1)
s.assign(u"B1", b, 2)
SMALL.append((u"T_SHR_WORD", fbd.pou_xml(u"T_SHR_WORD", u"program",
             fbd.interface(locals_=[(u"W1", u"WORD"), (u"B1", u"BYTE")]), [s], comment=u"probe")))
# WORD_TO_BYTE
s = fbd.Sheet(u"", order_start=1)
src = s.ref(u"W1", 0)
b = s.blk(u"WORD_TO_BYTE", [(u"", src)], 1)
s.assign(u"B1", b, 2)
SMALL.append((u"T_W2B", fbd.pou_xml(u"T_W2B", u"program",
             fbd.interface(locals_=[(u"W1", u"WORD"), (u"B1", u"BYTE")]), [s], comment=u"probe")))
# ADD po WORD
s = fbd.Sheet(u"", order_start=1)
b = s.blk(u"ADD", [(u"", s.ref(u"W1", 0)), (u"", s.ref(u"W2", 0))], 1)
s.assign(u"W3", b, 2)
SMALL.append((u"T_ADD_WORD", fbd.pou_xml(u"T_ADD_WORD", u"program",
             fbd.interface(locals_=[(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD")]), [s], comment=u"probe")))

for name, xml in SMALL:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"малых схем сгенерировано: %d" % len(SMALL))

# --------------------------------------------------- proekt
BASE = os.path.join(BUILD, u"msg_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"msg_bs.project"):
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


def children():
    names = set()
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        pass
    return names


def dump_msgs(where):
    log(u"  --- сообщения: %s ---" % where)
    total = 0
    try:
        cats = system.get_message_categories()
    except Exception:
        log(u"    get_message_categories: %s" % traceback.format_exc().strip().splitlines()[-1])
        return 0
    for c in cats:
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        for m in msgs:
            try:
                total += 1
                log(u"    [%s] %s | %s" % (c, m.severity, m.text))
                try:
                    o = m.object
                    log(u"           объект: %s" % (o,))
                except Exception:
                    pass
                try:
                    log(u"           позиция: %s" % (m.position,))
                except Exception:
                    pass
                try:
                    system.delete_message(m)
                except Exception:
                    pass
            except Exception:
                log(u"    <нечитаемое сообщение>")
    if total == 0:
        log(u"    (сообщений нет)")
    return total


# 1) zavisimosti
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
dec_ok = u"FB_Decoder6502" in children()
log(u"декодер (зависимость): %s" % (u"СОЗДАН" if dec_ok else u"НЕ СОЗДАН"))
dump_msgs(u"после декодера")

# 2) malye shemy
log(u"")
for name, _xml in SMALL:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in children()
    log(u"%-12s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                            (u"  (искл: %s)" % exc) if exc else u""))
    dump_msgs(name)

# 3) yadro L2
log(u"")
p = os.path.join(PLCOPEN, u"PRG_CORE_L2.xml")
exc = None
try:
    app.import_xml(p, False)
except Exception:
    exc = traceback.format_exc().strip().splitlines()[-1]
ok = u"PRG_CORE_L2" in children()
log(u"PRG_CORE_L2 -> %s%s" % (u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))
dump_msgs(u"PRG_CORE_L2")

# 4) polnyy build -- pokazhet oshibki kompilyacii, esli POU vse-taki est
log(u"")
try:
    app.build()
    ok_b = True
except Exception:
    ok_b = False
    log(u"build: %s" % traceback.format_exc().strip().splitlines()[-1])
log(u"сборка: %s" % (u"выполнена" if ok_b else u"исключение"))
dump_msgs(u"после сборки")

log(u"=== PROBE_MSGS END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
