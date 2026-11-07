# -*- coding: utf-8 -*-
"""
probe_instance2.py -- SHAG 0b: strogiy test vyzova ekzemplyara FB.

Pervaya proverka ("POU sozdan") ne razlichila varianty: vse tri poyavilis v
proekte, a kompilyator soobshcheniy ne vydal. Znachit nuzhen bolee strogiy kriteriy.

Kriteriy: EKSPORT OBRATNO. Esli CODESYS PONYAL vyzov, on zapishet ego v svoey
kanonicheskoy forme. Sravnivaya iskhodnyy XML i eksport, vidno:
  * raspoznal li on blok kak ekzemplyar FB (poyavilsya li instanceName
    ili imya ekzemplyara v typeName);
  * ne prevratil li on blok v neizvestnyy/neprazvuchennyy element.

Dopolnitelno: chitaem textual_declaration -- esli CODESYS ponel vyzov,
on dobalyaet obyavlenie ekzemplyara.

Rezultat -> log/probe_instance2.log
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\Emu6502\tools")

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_instance2.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\Standard.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_INSTANCE2 START ===")
import scriptengine
from fbd import Sheet, interface, pou_xml


def callee_xml():
    s = Sheet(u"тело CALLEE: Q := IN")
    v = s.var(u"IN", 0)
    s.assign(u"Q", v, 1)
    return pou_xml(u"CALLEE", u"functionBlock",
                   interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"Q", u"BYTE")]),
                   [s], None)


def caller_xml(pou_name, variant):
    s = Sheet(u"вызов экземпляра, вариант %s" % variant)
    src = s.var(u"IN", 0)
    bid = s.blk(u"CALLEE", [(u"IN", src)], 1)
    s.assign(u"OUT", bid, 2)
    if variant == u"C":
        return pou_xml(pou_name, u"functionBlock",
                       interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")]),
                       [s], None)
    ifc = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")],
                    locals_=[(u"Inst", u"CALLEE")])
    xml = pou_xml(pou_name, u"functionBlock", ifc, [s], None)
    xml = xml.replace(u"<type><CALLEE /></type>", u'<type><derived name="CALLEE" /></type>')
    if variant == u"A":
        xml = xml.replace(u'typeName="CALLEE"', u'typeName="CALLEE" instanceName="Inst"')
    else:
        xml = xml.replace(u'typeName="CALLEE"', u'typeName="Inst"')
    return xml


BASE = os.path.join(os.getcwd(), u"base_inst2.project")
for junk in os.listdir(os.getcwd()):
    if junk.startswith(u"base_inst2.project"):
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

cp = os.path.join(PLCOPEN, u"inst_CALLEE.xml")
ff = io.open(cp, "w", encoding="utf-8")
ff.write(callee_xml())
ff.close()
try:
    app.import_xml(cp, False)
except Exception:
    log(u"CALLEE: %s" % traceback.format_exc().strip().splitlines()[-1])

for v in (u"A", u"B", u"C"):
    xp = os.path.join(PLCOPEN, u"inst2_CALL_%s.xml" % v)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(caller_xml(u"CALL2_%s" % v, v))
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"вариант %s: ИСКЛЮЧЕНИЕ %s" % (v, traceback.format_exc().strip().splitlines()[-1]))
        continue

    # --- строгая проверка 1: объявление POU ---
    pou = None
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=CALL2_%s," % v in s:
                pou = ch
                break
    except Exception:
        log(traceback.format_exc())
    if pou is None:
        log(u"вариант %s: POU не найден" % v)
        continue
    try:
        decl = pou.textual_declaration
        try:
            txt = decl.text
        except Exception:
            txt = unicode(decl)
        log(u"--- вариант %s: объявление ---" % v)
        log(txt)
    except Exception:
        log(u"вариант %s: объявление недоступно: %s" % (v, traceback.format_exc().strip().splitlines()[-1]))

    # --- строгая проверка 2: экспорт обратно ---
    out = os.path.join(PLCOPEN, u"inst2_rt_%s.xml" % v)
    try:
        pou.export_xml(out, False, False, False)
        d = io.open(out, "r", encoding="utf-8").read()
        body = d.split(u"<FBD>", 1)
        frag = body[1][:1200] if len(body) > 1 else d[:1200]
        log(u"--- вариант %s: экспорт обратно ---" % v)
        log(frag)
    except Exception:
        log(u"вариант %s: экспорт не удался: %s" % (v, traceback.format_exc().strip().splitlines()[-1]))

try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_INSTANCE2 END ===")
try:
    system.exit()
except Exception:
    pass
