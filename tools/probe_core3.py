# -*- coding: utf-8 -*-
"""
probe_core3.py -- proverka BLOKERA B2 (shag B2.1 plana ostatka).

Gipoteza: FB_CPU_Core otvergaetsya potomu, chto eto EDINSTVENNAYA shema proekta,
kotoraya ODOVREMENNO vyzyvaet i ekzemplyar FB (FB_Decoder6502), i funkcii
(F_UnpackByte / F_PackByte).

Stroim tri odinakovyh krossochichnyh POU:
  C_FB_ONLY   -- tolko ekzemplyar FB
  C_FUN_ONLY  -- tolko funkciya
  C_BOTH      -- I ekzemplyar, I funkciya   <-- klyuchevoy sluchay

Esli C_FB_ONLY i C_FUN_ONLY sozdayutsya, a C_BOTH net -- gipoteza podtverzhdena,
i yadro lechitsya udaleniem vyzovov funkciy (vstroit raspakovku bitov P).

Rezultat -> log/probe_core3.log
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_core3.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_CORE3 START ===")
import scriptengine
from fbd import Sheet, interface, pou_xml


def callee():
    """Крошечный FB с двумя выходами."""
    s = Sheet(u"тело CALLEE3")
    v = s.var(u"IN", 0)
    s.assign(u"Q", v, 2)
    s.assign(u"R", v, 2)
    return pou_xml(u"CALLEE3", u"functionBlock",
                   interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"Q", u"BYTE"), (u"R", u"BYTE")]),
                   [s], None)


def caller(variant):
    """Три варианта вызова в теле одного POU."""
    s = Sheet(u"вариант %s" % variant)
    src = s.var(u"IN", 0)
    parts = []

    if variant in (u"FB_ONLY", u"BOTH"):
        inst = s.blk(u"CALLEE3", [(u"IN", src)], 1)
        parts.append(inst)
    if variant in (u"FUN_ONLY", u"BOTH"):
        # вызов ФУНКЦИИ из уже сгенерированных схем (F_PackByte: ARRAY -> BYTE)
        arr = s.var(u"ARR", 1)
        fn = s.blk(u"F_PackByte", [(u"B", arr)], 2)
        parts.append(fn)

    s.assign(u"OUT", parts[0], 4)
    if len(parts) > 1:
        s.assign(u"OUT2", parts[1], 4)

    outs = [(u"OUT", u"BYTE")]
    if len(parts) > 1:
        outs.append((u"OUT2", u"BYTE"))
    locals_ = []
    if variant in (u"FB_ONLY", u"BOTH"):
        locals_.append((u"Inst", u"CALLEE3"))
    if variant in (u"FUN_ONLY", u"BOTH"):
        locals_.append((u"ARR", u"ARRAY[0..7] OF BOOL"))
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=outs, locals_=locals_)
    xml = pou_xml(u"C_%s" % variant, u"functionBlock", iface, [s], None)
    # производный тип -> <derived>, как требует CODESYS
    xml = xml.replace(u"<type><CALLEE3 /></type>", u'<type><derived name="CALLEE3" /></type>')
    xml = xml.replace(u'typeName="CALLEE3"', u'typeName="CALLEE3" instanceName="Inst"')
    return xml


def children(app):
    names = []
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.append(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        log(traceback.format_exc())
    return names


BUILD = r"C:\CPM6502_build"
BASE = os.path.join(BUILD, u"base_probe3.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"base_probe3.project"):
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

# зависимости: функция F_PackByte и FB CALLEE3
for name, xml in ((u"F_PackByte", None), (u"CALLEE3", callee())):
    xp = os.path.join(PLCOPEN, u"%s.xml" % name)
    if xml is not None:
        xp = os.path.join(PLCOPEN, u"p3_%s.xml" % name)
        ff = io.open(xp, "w", encoding="utf-8")
        ff.write(xml)
        ff.close()
    if not os.path.exists(xp):
        log(u"нет файла %s" % name)
        continue
    try:
        app.import_xml(xp, False)
        log(u"%s -> %s" % (name, u"создан" if name in children(app) else u"НЕ СОЗДАН"))
    except Exception:
        log(u"%s: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))

ok, bad = [], []
for variant in (u"FB_ONLY", u"FUN_ONLY", u"BOTH"):
    xp = os.path.join(PLCOPEN, u"p3_C_%s.xml" % variant)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(caller(variant))
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"  %-10s ИСКЛЮЧЕНИЕ: %s" % (variant, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(variant)
        continue
    got = (u"C_%s" % variant) in children(app)
    log(u"  %-10s -> %s" % (variant, u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(variant)

log(u"")
log(u"СОЗДАНЫ   : %s" % (u", ".join(ok) or u"(нет)"))
log(u"НЕ СОЗДАНЫ: %s" % (u", ".join(bad) or u"(нет)"))
log(u"")
log(u"Толкование:")
log(u"  C_BOTH не создан, а FB_ONLY и FUN_ONLY созданы")
log(u"     -> гипотеза B2 ПОДТВЕРЖДЕНА: лечим ядро удалением вызовов функций")
log(u"  C_BOTH создан -> гипотеза ОПРОВЕРГНУТА, причина в другом")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_CORE3 END ===")
try:
    system.exit()
except Exception:
    pass
