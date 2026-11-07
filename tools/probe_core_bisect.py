# -*- coding: utf-8 -*-
"""
probe_core_bisect.py -- chto imenno otvergaet FB_CPU_Core.

Posle ustraneniya neobyavlennyh imen yadro (233 bloka) vse ravno NE sozdaetsya.
Ostalis dve konstrukcii, kotoryh net ni v odnoy uspeshno importirovannoy sheme:

  1) sem KONKRETNOGO vyhodnogo pina ekzemplyara FB -- svyaz s
     formalParameter="IMYA" na vhode outVariable (29 signalov dekodera);
  2) zapis v pamyat po adresu-LOKALNOY peremennoy: Mem[W0], gde W0 : WORD.

Stroim po krossochichnomu POU na kazhduyu konstrukciyu i smotrim, kakie poyavyatsya.

Rezultat -> log/probe_core_bisect.log
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_core_bisect.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\Standard.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_CORE_BISECT START ===")
import scriptengine
from fbd import Sheet, interface, pou_xml


def callee_xml():
    """FB с двумя выходами: Q (IN + 1) и R (IN)."""
    s = Sheet(u"тело CALLEE2")
    v = s.var(u"IN", 0)
    s.assign(u"Q", v, 2)
    s.assign(u"R", v, 2)
    return pou_xml(u"CALLEE2", u"functionBlock",
                   interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"Q", u"BYTE"), (u"R", u"BYTE")]),
                   [s], None)


def v_inst_pin():
    """Подозреваемое 1: съём КОНКРЕТНОГО выхода экземпляра через formalParameter."""
    s = Sheet(u"съём конкретного выхода экземпляра")
    src = s.var(u"IN", 0)
    inst = s.blk(u"CALLEE2", [(u"IN", src)], 1)
    s.assign(u"OUT", inst, 3, src_pin=u"R")     # именно R, а не первый выход Q
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")],
                      locals_=[(u"Inst", u"CALLEE2")])
    xml = pou_xml(u"B_INST_PIN", u"functionBlock", iface, [s], None)
    xml = xml.replace(u"<type><CALLEE2 /></type>", u'<type><derived name="CALLEE2" /></type>')
    xml = xml.replace(u'typeName="CALLEE2"', u'typeName="CALLEE2" instanceName="Inst"')
    return xml


def v_inst_plain():
    """Контроль: экземпляр без formalParameter (первый выход)."""
    s = Sheet(u"съём первого выхода экземпляра")
    src = s.var(u"IN", 0)
    inst = s.blk(u"CALLEE2", [(u"IN", src)], 1)
    s.assign(u"OUT", inst, 3)
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")],
                      locals_=[(u"Inst", u"CALLEE2")])
    xml = pou_xml(u"B_INST_PLAIN", u"functionBlock", iface, [s], None)
    xml = xml.replace(u"<type><CALLEE2 /></type>", u'<type><derived name="CALLEE2" /></type>')
    xml = xml.replace(u'typeName="CALLEE2"', u'typeName="CALLEE2" instanceName="Inst"')
    return xml


def v_mem_write_local():
    """Подозреваемое 2: запись в память по адресу — ЛОКАЛЬНОЙ переменной."""
    s = Sheet(u"запись Mem[W0], где W0 локальная")
    v = s.var(u"IN", 0)
    w = s.blk(u"BYTE_TO_WORD", [(u"IN", v)], 1)
    s.assign(u"W0", w, 2)
    s.assign(u"Mem[W0]", s.blk(u"SEL", [(u"G", s.var(u"IN", 2)),
                                        (u"IN0", s.var(u"Mem[W0]", 2)),
                                        (u"IN1", s.var(u"IN", 2))], 3), 4)
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")],
                      locals_=[(u"W0", u"WORD")])
    return pou_xml(u"B_MEMW_LOCAL", u"functionBlock", iface, [s], None)


def v_mem_read_local():
    """Контроль: чтение Mem[W0] по локальной переменной-адресу."""
    s = Sheet(u"чтение Mem[W0]")
    v = s.var(u"IN", 0)
    w = s.blk(u"BYTE_TO_WORD", [(u"IN", v)], 1)
    s.assign(u"W0", w, 2)
    s.assign(u"OUT", s.var(u"Mem[W0]", 3), 4)
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")],
                      locals_=[(u"W0", u"WORD")])
    return pou_xml(u"B_MEMR_LOCAL", u"functionBlock", iface, [s], None)


def v_mem_write_expr():
    """Контроль: запись Mem[GVL_CPU.PC] — индекс-выражение, как в рабочем PRG_6502."""
    s = Sheet(u"запись Mem[GVL_CPU.PC]")
    v = s.var(u"IN", 0)
    s.assign(u"Mem[GVL_CPU.PC]", s.blk(u"SEL", [(u"G", s.var(u"IN", 2)),
                                                 (u"IN0", s.var(u"Mem[GVL_CPU.PC]", 2)),
                                                 (u"IN1", s.var(u"IN", 2))], 3), 4)
    iface = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")], locals_=[])
    return pou_xml(u"B_MEMW_EXPR", u"functionBlock", iface, [s], None)


VARIANTS = [(u"CALLEE2", callee_xml),
            (u"B_INST_PLAIN", v_inst_plain),
            (u"B_INST_PIN", v_inst_pin),
            (u"B_MEMW_LOCAL", v_mem_write_local),
            (u"B_MEMR_LOCAL", v_mem_read_local),
            (u"B_MEMW_EXPR", v_mem_write_expr)]

# ------------------------------------------------------------------ проект
BASE = os.path.join(os.getcwd(), u"base_bisect.project")
for junk in os.listdir(os.getcwd()):
    if junk.startswith(u"base_bisect.project"):
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


ok, bad = [], []
for name, fn in VARIANTS:
    xp = os.path.join(PLCOPEN, u"bis_%s.xml" % name)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(fn())
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"  %-16s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(name)
        continue
    got = name in children()
    log(u"  %-16s -> %s" % (name, u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(name)

log(u"")
log(u"СОЗДАНЫ   : %s" % (u", ".join(ok) or u"(нет)"))
log(u"НЕ СОЗДАНЫ: %s" % (u", ".join(bad) or u"(нет)"))
log(u"")
log(u"Толкование:")
log(u"  если НЕ СОЗДАН только B_INST_PIN  -> виноват съём конкретного выхода экземпляра")
log(u"  если НЕ СОЗДАН только B_MEMW_LOCAL -> виновата запись Mem[локальная_переменная]")
log(u"  если НЕ СОЗДАНы оба контрольных   -> дело в чём-то ещё")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_CORE_BISECT END ===")
try:
    system.exit()
except Exception:
    pass
