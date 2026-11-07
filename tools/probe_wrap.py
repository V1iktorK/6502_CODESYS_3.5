# -*- coding: utf-8 -*-
"""
probe_wrap.py -- celеvой opyt: tot zhe element #48 iz FB_AddrMode, no svyaz
razorvana IMENOVANNOY peremennoy.

Izvestno: prefiks 47 elementov FB_AddrMode sozdaetsya, dobavlenie elementa #48
(ADD, IN1 <- 2509 "AB" -- vyhod bloka ADD, IN2 <- 2515 "xw" -- vyhod
BYTE_TO_WORD) privodit k zavisaniyu.

Varianty (poryadok: bezopasnye snachala):
  Q1 kontrol:  prefix47 + ADD ot dvuh svezhih inVariable
  Q2 RAZRYV:   AB snaruzhi vyveden v imya AB, potrebitel chitaet imya AB
  Q3 kak est:  prefix47 + element #48 bez izmeneniy  (ozhidaem zavisanie, poetomu posledniy)
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_wrap.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
SRC = os.path.join(PLCOPEN, u"FB_AddrMode.xml")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_WRAP START ===")


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
prefix = els[:47]
el48 = els[47]
log(u"элементов: %d, префикс: %d" % (len(els), len(prefix)))
log(u"элемент #48: %s" % el48[:300])

# ---------- Q1: контроль, два свежих inVariable
q1_extra = (
    u'<inVariable localId="900001" height="20" width="70"><position x="21000" y="21000" />'
    u'<connectionPointOut><relPosition x="70" y="10" /></connectionPointOut>'
    u'<expression>W7</expression></inVariable>'
    u'<inVariable localId="900002" height="20" width="70"><position x="21000" y="21040" />'
    u'<connectionPointOut><relPosition x="70" y="10" /></connectionPointOut>'
    u'<expression>W8</expression></inVariable>'
    u'<block localId="900003" typeName="ADD" height="40" width="80" executionOrderId="900">'
    u'<position x="21300" y="21000" />'
    u'<inputVariables>'
    u'<variable formalParameter="IN1"><connectionPointIn><relPosition x="0" y="10" />'
    u'<connection refLocalId="900001" /></connectionPointIn></variable>'
    u'<variable formalParameter="IN2"><connectionPointIn><relPosition x="0" y="30" />'
    u'<connection refLocalId="900002" /></connectionPointIn></variable>'
    u'</inputVariables><inOutVariables />'
    u'<outputVariables><variable formalParameter="OUT"><connectionPointOut>'
    u'<relPosition x="80" y="20" /></connectionPointOut></variable></outputVariables></block>')

# ---------- Q2: разрыв связи именованной переменной AB
q2_extra = (
    u'<outVariable localId="900011" height="20" width="70"><position x="21000" y="22000" />'
    u'<connectionPointIn><relPosition x="0" y="10" />'
    u'<connection refLocalId="2509" /></connectionPointIn>'
    u'<expression>ABT</expression></outVariable>'
    u'<inVariable localId="900012" height="20" width="70"><position x="21200" y="22000" />'
    u'<connectionPointOut><relPosition x="70" y="10" /></connectionPointOut>'
    u'<expression>ABT</expression></inVariable>'
    u'<inVariable localId="900013" height="20" width="70"><position x="21200" y="22040" />'
    u'<connectionPointOut><relPosition x="70" y="10" /></connectionPointOut>'
    u'<expression>XWT</expression></inVariable>'
    u'<block localId="900014" typeName="ADD" height="40" width="80" executionOrderId="901">'
    u'<position x="21400" y="22000" />'
    u'<inputVariables>'
    u'<variable formalParameter="IN1"><connectionPointIn><relPosition x="0" y="10" />'
    u'<connection refLocalId="900012" /></connectionPointIn></variable>'
    u'<variable formalParameter="IN2"><connectionPointIn><relPosition x="0" y="30" />'
    u'<connection refLocalId="900013" /></connectionPointIn></variable>'
    u'</inputVariables><inOutVariables />'
    u'<outputVariables><variable formalParameter="OUT"><connectionPointOut>'
    u'<relPosition x="80" y="20" /></connectionPointOut></variable></outputVariables></block>'
    u'<outVariable localId="900015" height="20" width="70"><position x="21600" y="22000" />'
    u'<connectionPointIn><relPosition x="0" y="10" />'
    u'<connection refLocalId="2515" /></connectionPointIn>'
    u'<expression>XWT</expression></outVariable>')


def add_locals(t, extra):
    """Добавить объявления в <localVars> (или создать секцию)."""
    decl = u"".join([u'<variable name="%s"><type><WORD /></type></variable>' % n
                     for n in extra])
    if u"<localVars>" in t:
        return t.replace(u"</localVars>", decl + u"</localVars>", 1)
    return t.replace(u"</interface>", u"<localVars>%s</localVars></interface>" % decl, 1)


def make(name, elements, decls):
    t = head + u"".join(elements) + tail
    t = re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)
    if decls:
        t = add_locals(t, decls)
    return t


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"wr2_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"wr2_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"wr2_bs.project"):
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
    log(u"GVL созданы")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])


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


CASES = [
    (u"Q1 контроль", prefix + [q1_extra], [u"W7", u"W8"]),
    (u"Q2 разрыв AB", prefix + [q2_extra], [u"ABT", u"XWT"]),
    (u"Q3 как есть", prefix + [el48], []),
]

log(u"")
for label, elements, decls in CASES:
    name = u"WR_%d" % (CASES.index((label, elements, decls)) + 1)
    log(u"  ПЕРЕД ИМПОРТОМ %s" % label)
    try:
        write(make(name, elements, decls))
        app.import_xml(os.path.join(PLCOPEN, u"wr2_tmp.xml"), False)
    except Exception:
        log(u"  %-16s ИСКЛЮЧЕНИЕ: %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        continue
    ok = name in names()
    log(u"  %-16s -> %s" % (label, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))

log(u"=== PROBE_WRAP END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
