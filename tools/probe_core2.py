# -*- coding: utf-8 -*-
"""
probe_core2.py -- ostavshiesya gipotezy po otkazu FB_CPU_Core.

Uzhe proverено i rabotaet: s'em konkretnogo vyhoda ekzemplyara cherez
formalParameter; zapis Mem[localnaya_peremennaya]. Ostalis:

  G1: ZAPIS v GVL-peremennuyu: outVariable s vyrazheniem "GVL_CPU.A"
      (v uspeshno importirovannyh shemah takoy zapisi ne bylo nikogda);
  G2: CHTENIE GVL-peremennoy i zapis' tuda zhe v odnoy sheme;
  G3: MNOGO vyhodov odnogo ekzemplyara (8 shtuk s raznymi formalParameter).

Rezultat -> log/probe_core2.log
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_core2.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\Standard.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_CORE2 START ===")
import scriptengine
from fbd import Sheet, interface, pou_xml

# --- вспомогательный FB с 8 выходами ---
def callee8():
    s = Sheet(u"тело CALLEE8: 8 выходов")
    v = s.var(u"IN", 0)
    for i in range(8):
        s.assign(u"Q%d" % i, v, 2)
    outs = [(u"Q%d" % i, u"BYTE") for i in range(8)]
    return pou_xml(u"CALLEE8", u"functionBlock",
                   interface(inputs=[(u"IN", u"BYTE")], outputs=outs), [s], None)


def v_gvl_write():
    """G1: запись значения в GVL-переменную."""
    s = Sheet(u"запись в GVL_CPU.A")
    v = s.var(u"IN", 0)
    s.assign(u"GVL_CPU.A", v, 2)
    ifc = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")])
    return pou_xml(u"C_GVL_WRITE", u"functionBlock", ifc, [s], None)


def v_gvl_rw():
    """G2: чтение GVL и запись в неё же."""
    s = Sheet(u"чтение и запись GVL_CPU.A")
    cur = s.var(u"GVL_CPU.A", 0)
    add = s.blk(u"ADD", [(u"IN1", cur), (u"IN2", s.const(u"BYTE#1", 0))], 1)
    s.assign(u"GVL_CPU.A", add, 2)
    ifc = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"BYTE")])
    return pou_xml(u"C_GVL_RW", u"functionBlock", ifc, [s], None)


def v_many_outs():
    """G3: 8 выходов одного экземпляра через formalParameter."""
    s = Sheet(u"8 выходов экземпляра")
    src = s.var(u"IN", 0)
    inst = s.blk(u"CALLEE8", [(u"IN", src)], 1)
    for i in range(8):
        s.assign(u"O%d" % i, inst, 4 + i, src_pin=u"Q%d" % i)
    ifc = interface(inputs=[(u"IN", u"BYTE")],
                    outputs=[(u"O%d" % i, u"BYTE") for i in range(8)],
                    locals_=[(u"Inst", u"CALLEE8")])
    xml = pou_xml(u"C_MANY_OUTS", u"functionBlock", ifc, [s], None)
    xml = xml.replace(u"<type><CALLEE8 /></type>", u'<type><derived name="CALLEE8" /></type>')
    xml = xml.replace(u'typeName="CALLEE8"', u'typeName="CALLEE8" instanceName="Inst"')
    return xml


def v_control():
    """Контроль: чтение GVL-переменной (работало и раньше)."""
    s = Sheet(u"чтение GVL_CPU.PC")
    v = s.var(u"GVL_CPU.PC", 0)
    w = s.blk(u"ADD", [(u"IN1", v), (u"IN2", s.const(u"WORD#1", 0))], 1)
    s.assign(u"OUT", w, 2)
    ifc = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"OUT", u"WORD")])
    return pou_xml(u"C_GVL_READ", u"functionBlock", ifc, [s], None)


VARIANTS = [(u"CALLEE8", callee8), (u"C_GVL_READ", v_control),
            (u"C_GVL_WRITE", v_gvl_write), (u"C_GVL_RW", v_gvl_rw),
            (u"C_MANY_OUTS", v_many_outs)]

BASE = os.path.join(os.getcwd(), u"base_probe2.project")
for junk in os.listdir(os.getcwd()):
    if junk.startswith(u"base_probe2.project"):
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

# GVL_CPU нужна: POU пишут в GVL_CPU.A / читают GVL_CPU.PC
try:
    gvl = app.create_gvl(u"GVL_CPU")
    gvl.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
    log(u"GVL_CPU создана")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])


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
    xp = os.path.join(PLCOPEN, u"p2_%s.xml" % name)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(fn())
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"  %-14s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(name)
        continue
    got = name in children()
    log(u"  %-14s -> %s" % (name, u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(name)

log(u"")
log(u"СОЗДАНЫ   : %s" % (u", ".join(ok) or u"(нет)"))
log(u"НЕ СОЗДАНЫ: %s" % (u", ".join(bad) or u"(нет)"))
log(u"Толкование:")
log(u"  C_GVL_READ не создан  -> GVL не видна вообще (не та GVL или порядок)")
log(u"  C_GVL_WRITE не создан -> ЗАПИСЬ в GVL-переменную не поддерживается")
log(u"  C_MANY_OUTS не создан -> проблема в числе выходов одного экземпляра")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_CORE2 END ===")
try:
    system.exit()
except Exception:
    pass
