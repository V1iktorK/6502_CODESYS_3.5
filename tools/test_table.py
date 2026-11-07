# -*- coding: utf-8 -*-
"""
test_table.py -- proverka idei: tablica dekodirovaniya kak DANNYE.

Pochemu: offlajn-interpretator (fbd_sim.py) dokazyvaet, chto shema deshifratora
logicheski vernа (ADDR_MODE=1 dlya LDA #), a v CODESYS vse BYTE-signaly ravny 0.
Bulevy signaly toy zhe shemy rabotayut. Znachit problemа v konstrukcii
SEL-po-konstantam + derevo OR vnutri bolshogo lista.

Obhod: hranit tablicu "kod operacii -> signal" kak massiv v GVL (eto dannye,
inicыализируемые pri starte), a v sheme delat obychnoe chtenie elementa.
Zdes proveryaem, chto takoe chtenie rabotaet: massiv inicializiruetsya
v deklaracii GVL, programma chitaet dva elementa i pishet v GVL_CPU.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml
from opcodes import build_effects, BYTE_SIGNALS

LOG = os.path.join(ROOT, "log", "test_table.log")
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
log(u"=== TEST_TABLE START ===")

EFF = build_effects()


def table_decl(sig):
    vals = []
    for opc in range(256):
        vals.append(int(EFF.get(opc, {}).get(sig, 0)))
    return u"\t%s : ARRAY[0..255] OF BYTE := [%s];" % (
        sig, u", ".join(u"%d" % v for v in vals))


decl = [u"VAR_GLOBAL", u"\t(* таблицы декодирования: код операции -> сигнал *)"]
for sig in BYTE_SIGNALS:
    decl.append(table_decl(sig))
decl.append(u"END_VAR")
decl_text = u"\n".join(decl) + u"\n"
log(u"объявление GVL_TABLE: %d байт" % len(decl_text))

# программа: читаем элементы по индексу 169 ($A9)
s = Sheet(u"PLC_PRG: чтение таблицы декодирования")
s.assign(u"GVL_CPU.C_IMM",
         s.ref(u"GVL_TABLE.ADDR_MODE[169]", 1), 3)
s.assign(u"GVL_CPU.C_ZP",
         s.ref(u"GVL_TABLE.LEN[169]", 2), 4)
s.assign(u"GVL_CPU.C_ZPX",
         s.ref(u"GVL_TABLE.SRC[169]", 3), 5)
s.assign(u"GVL_CPU.C_ZPY",
         s.ref(u"GVL_TABLE.ADDR_MODE[141]", 4), 6)
xml = pou_xml(u"PLC_PRG", u"program", interface(locals_=[]), [s], u"чтение таблицы")
p = os.path.join(PLCOPEN, u"PRG_TABLE.xml")
fo = io.open(p, "wb")
fo.write(xml.encode("utf-8"))
fo.close()
log(u"PRG_TABLE: %d байт" % os.path.getsize(p))

import scriptengine

BASE = os.path.join(BUILD, u"table.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"table.project"):
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

proj = projects.open(BASE)
app = proj.active_application
log(u"проект открыт")

try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tC_IMM : BYTE;\n\tC_ZP : BYTE;\n\tC_ZPX : BYTE;\n\tC_ZPY : BYTE;\nEND_VAR\n")
    t = app.create_gvl(u"GVL_TABLE")
    t.textual_declaration.replace(decl_text)
    log(u"GVL созданы")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    prg = None
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                prg = o
                break
        except Exception:
            continue
    if prg is not None:
        prg.remove()
    app.import_xml(p, False)
    log(u"PRG_TABLE импортирована")
except Exception:
    log(u"замена: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.build()
except Exception:
    pass
errs = []
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                tt = u"%s" % (m,)
            except Exception:
                continue
            low = tt.lower()
            if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) and u"0 ошибки" not in tt:
                errs.append(tt)
    except Exception:
        pass
log(u"ошибок компиляции: %d" % len(errs))
for tt in errs[:8]:
    log(u"  %s" % tt)

try:
    node = app
    for i in range(6):
        node = node.parent
        if node is None:
            break
        try:
            node.set_simulation_mode(True)
            break
        except Exception:
            continue
    oa = scriptengine.online.create_online_application(app)
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    oa.start()
    log(u"симуляция запущена")
    try:
        import time
        time.sleep(0.5)
    except Exception:
        pass
    for expr in (u"GVL_CPU.C_IMM", u"GVL_CPU.C_ZP", u"GVL_CPU.C_ZPX", u"GVL_CPU.C_ZPY"):
        try:
            log(u"  %-16s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-16s ошибка чтения" % expr)
    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"онлайн: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass

log(u"=== TEST_TABLE END ===")
try:
    system.exit()
except Exception:
    pass
