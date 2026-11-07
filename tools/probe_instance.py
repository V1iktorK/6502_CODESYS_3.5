# -*- coding: utf-8 -*-
"""
probe_instance.py -- SHAG 0: kak zapisat VYZOV EKZEMPLYARA FB v PLCopen XML.

Ot etogo zavisit vsya arhitektura: dogovorennost predusmatrivaet "N ekzemplyarov
FB_CPU_Core, aktivnye vklyuchayutsya multipleksorom". Esli CODESYS ne prinimaet
takuyu zapis, shemu pridetsya stroit inache (vstraivaniem kopiy v odin list).

Proveryaem tri varianta na odinakovyh krossochichnyh POU:
  A: <block typeName="CALLEE" instanceName="Inst">  + lokalnaya peremennaya
     proizvodnogo tipa Inst : CALLEE
  B: <block typeName="Inst"> -- v typeName stoit IMYA EKZEMPLYARA
  C: kontrol -- ni ekzemplyara, ni atributa (tak delat nelzya, no nado uvidet)

Rezultat -> log/probe_instance.log
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
LOG = os.path.join(ROOT, "log", "probe_instance.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\Standard.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_INSTANCE START ===")
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
    xml = xml.replace(u"<type><CALLEE /></type>",
                      u'<type><derived name="CALLEE" /></type>')
    if variant == u"A":
        xml = xml.replace(u'typeName="CALLEE"', u'typeName="CALLEE" instanceName="Inst"')
    else:
        xml = xml.replace(u'typeName="CALLEE"', u'typeName="Inst"')
    return xml


BASE = os.path.join(os.getcwd(), u"base_inst.project")
for junk in os.listdir(os.getcwd()):
    if junk.startswith(u"base_inst.project"):
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

proj = None
app = None
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


# вызываемый FB
cp = os.path.join(PLCOPEN, u"inst_CALLEE.xml")
ff = io.open(cp, "w", encoding="utf-8")
ff.write(callee_xml())
ff.close()
try:
    app.import_xml(cp, False)
    log(u"CALLEE -> %s" % (u"создан" if u"CALLEE" in children() else u"НЕ СОЗДАН"))
except Exception:
    log(u"CALLEE ИСКЛЮЧЕНИЕ: %s" % traceback.format_exc().strip().splitlines()[-1])

for v in (u"A", u"B", u"C"):
    xp = os.path.join(PLCOPEN, u"inst_CALL_%s.xml" % v)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(caller_xml(u"CALL_%s" % v, v))
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"  вариант %s: ИСКЛЮЧЕНИЕ %s" % (v, traceback.format_exc().strip().splitlines()[-1]))
        continue
    log(u"  вариант %-3s -> %s" % (v, u"СОЗДАН" if (u"CALL_%s" % v) in children() else u"НЕ СОЗДАН"))

log(u"--- компиляция (проверяет, разрешился ли вызов) ---")
try:
    app.build()
    log(u"app.build() -- без исключения")
except Exception:
    log(u"app.build() -- ИСКЛЮЧЕНИЕ")
    log(traceback.format_exc())
try:
    msgs = system.get_messages()
    log(u"сообщений: %d" % len(msgs))
    for m in msgs[:40]:
        try:
            log(u"  [%s] %s" % (getattr(m, "severity", u"?"), getattr(m, "text", m)))
        except Exception:
            log(u"  %r" % (m,))
except Exception:
    log(traceback.format_exc())

log(u"состав: %s" % u", ".join(sorted(children())))
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_INSTANCE END ===")
try:
    system.exit()
except Exception:
    pass
