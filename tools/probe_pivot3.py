# -*- coding: utf-8 -*-
"""
probe_pivot3.py -- kakaya SVYAZ delaet element #2225 nedopustimym v kontekste.

Izvestno:
  prefiks 2224                          -> СОЗДАН
  prefiks 2224 + chuzhoy MOVE           -> СОЗДАН
  prefiks 2224 + element #2225 (kak est)-> НЕ СОЗДАН
  smeshchenie pozicii / novyy localId   -> NE pomogaet (delo v soderzhimom)

Element #2225 -- OR, vhody: 2678 (OR) i 2670 (SEL).
Probуem po ocheredi ubirat svyazi i podklyuchat ikh zanovo:
  E1: bez vhodov
  E2: tolko IN1 (2678)
  E3: tolko IN2 (2670)
  E4: oba vhoda, no kazhdyy -- na SOBSTVENNUYU kopiyu peremennoy
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_pivot3.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
SRC = os.path.join(PLCOPEN, u"PRG_CORE_L10.xml")
PIVOT = 2225


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_PIVOT3 START ===")


def split_fbd(text):
    i = text.find(u"<FBD")
    j = text.find(u">", i)
    head = text[:j + 1]
    k = text.find(u"</FBD>", j)
    body = text[j + 1:k]
    tail = text[k:]
    els = []
    depth = 0
    start = None
    q = False
    p = 0
    n = len(body)
    while p < n:
        c = body[p]
        if q:
            if c == u'"':
                q = False
            p += 1
            continue
        if c == u'"':
            q = True
            p += 1
            continue
        if c == u"<":
            if body.startswith(u"<!--", p):
                e = body.find(u"-->", p)
                if depth == 0:
                    els.append(body[p:e + 3])
                p = e + 3
                continue
            if body.startswith(u"</", p):
                e = body.find(u">", p)
                depth -= 1
                if depth == 0 and start is not None:
                    els.append(body[start:e + 1])
                    start = None
                p = e + 1
                continue
            if depth == 0:
                start = p
            e = body.find(u">", p)
            if body[e - 1] == u"/":
                if depth == 0 and start is not None:
                    els.append(body[start:e + 1])
                    start = None
            else:
                depth += 1
            p = e + 1
            continue
        p += 1
    return head, els, tail


text = io.open(SRC, "rb").read().decode("utf-8")
head, els, tail = split_fbd(text)
prefix = els[:PIVOT - 1]
pivot = els[PIVOT - 1]
log(u"префикс: %d" % len(prefix))
log(u"опорный элемент: %s" % pivot[:400])


def strip_inputs(el, keep=None):
    """Ubrat vhody, krome perechislennyh v keep (IN1/IN2)."""
    def repl(m):
        name = m.group(1)
        if keep is not None and name in keep:
            return m.group(0)
        return (u'<variable formalParameter="%s"><connectionPointIn>'
                u'<relPosition x="0" y="10" /></connectionPointIn></variable>' % name)
    return re.sub(u'<variable formalParameter="(IN\\d+)">.*?</variable>', repl, el, flags=re.S)


E1 = strip_inputs(pivot, keep=())
E2 = strip_inputs(pivot, keep=(u"IN1",))
E3 = strip_inputs(pivot, keep=(u"IN2",))

# E4: oba vhoda, no kazhdyy na svoyu kopiyu peremennoy
E4_el = pivot
dupA = u'<inVariable localId="998001" height="20" width="80"><position x="31500" y="31500" />' \
       u'<connectionPointOut><relPosition x="80" y="10" /></connectionPointOut>' \
       u'<expression>OP1</expression></inVariable>'
dupB = u'<inVariable localId="998002" height="20" width="80"><position x="31500" y="31560" />' \
       u'<connectionPointOut><relPosition x="80" y="10" /></connectionPointOut>' \
       u'<expression>OP2</expression></inVariable>'
E4_el = re.sub(u'(<variable formalParameter="IN1">.*?refLocalId=")(\\d+)(")',
               u'\\g<1>998001\\g<3>', E4_el, count=1, flags=re.S)
E4_el = re.sub(u'(<variable formalParameter="IN2">.*?refLocalId=")(\\d+)(")',
               u'\\g<1>998002\\g<3>', E4_el, count=1, flags=re.S)


def make(name, elements):
    t = head + u"".join(elements) + tail
    return re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"piv3_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"piv3_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"piv3_bs.project"):
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

import scriptengine
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
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

for dep in (u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
            u"FB_Decoder6502"):
    p = os.path.join(PLCOPEN, u"%s.xml" % dep)
    if os.path.exists(p):
        try:
            app.import_xml(p, False)
        except Exception:
            pass
log(u"зависимости импортированы")


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


VARIANTS = [
    (u"E1 без входов", prefix + [E1]),
    (u"E2 только IN1 (=OR 2678)", prefix + [E2]),
    (u"E3 только IN2 (=SEL 2670)", prefix + [E3]),
    (u"E4 копии переменных", prefix + [dupA, dupB, E4_el]),
]

log(u"")
log(u"--- ОПЫТЫ ---")
for i, (label, elements) in enumerate(VARIANTS):
    name = u"PV3_%d" % i
    try:
        write(make(name, elements))
        app.import_xml(os.path.join(PLCOPEN, u"piv3_tmp.xml"), False)
    except Exception:
        log(u"  %-28s ИСКЛЮЧЕНИЕ: %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        continue
    ok = name in names()
    log(u"  %-28s -> %s" % (label, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))

log(u"=== PROBE_PIVOT3 END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
