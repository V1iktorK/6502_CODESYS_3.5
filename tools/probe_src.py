# -*- coding: utf-8 -*-
"""
probe_src.py -- differencialnyy opyt: KAKOY istochnik nelzya potreblyat.

Fakty:
  prefix47 FB_AddrMode                        -> СОЗДАН
  prefix47 + ADD(2509, 2515)                  -> зависание
  prefix47 + ADD(W7, W8)   (postoronnie)      -> СОЗДАН
  prefix47 + outVariable ABT <- 2509          -> зависание

Znachit delo v tom, CHTO potreblyaetsya, a ne v forme potrebitelya.
2509 = AB = ADD(2508, 2505);  2508 = MUL(2506, 2507);  2506 = BYTE_TO_WORD(OP2);
2505 = BYTE_TO_WORD(OP1);  2507 = WORD#256.

Opyty (ot naimenee podozritelnogo k naibolee):
  R1  WM <- 2506 (BYTE_TO_WORD от входа OP2)
  R2  WM <- 2505 (BYTE_TO_WORD от входа OP1)
  R3  WM <- 2508 (MUL)
  R4  WM <- 2509 (AB)          <-- ожидаемое зависание, поэтому последний
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_src.log")
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
log(u"=== PROBE_SRC START ===")


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
log(u"префикс: %d элементов" % len(prefix))


def take(src_id, lid, y):
    return (u'<outVariable localId="%d" height="20" width="70">'
            u'<position x="21000" y="%d" />'
            u'<connectionPointIn><relPosition x="0" y="10" />'
            u'<connection refLocalId="%d" /></connectionPointIn>'
            u'<expression>WM</expression></outVariable>' % (lid, y, src_id))


def make(name, extra):
    t = head + u"".join(prefix) + extra + tail
    t = re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)
    if u"<localVars>" in t:
        t = t.replace(u"</localVars>",
                      u'<variable name="WM"><type><WORD /></type></variable></localVars>', 1)
    else:
        t = t.replace(u"</interface>",
                      u'<localVars><variable name="WM"><type><WORD /></type></variable>'
                      u'</localVars></interface>', 1)
    return t


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"src_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"src_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"src_bs.project"):
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


CASES = [(u"R1 2506 B2W(OP2)", 2506, 21000),
         (u"R2 2505 B2W(OP1)", 2505, 21040),
         (u"R3 2508 MUL", 2508, 21080),
         (u"R4 2509 AB", 2509, 21120)]

log(u"")
for i, (label, src, y) in enumerate(CASES):
    name = u"SRC_%d" % (i + 1)
    log(u"  ПЕРЕД ИМПОРТОМ %s" % label)
    try:
        write(make(name, take(src, 900100 + i, y)))
        app.import_xml(os.path.join(PLCOPEN, u"src_tmp.xml"), False)
    except Exception:
        log(u"  %-18s ИСКЛЮЧЕНИЕ: %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        continue
    ok = name in names()
    log(u"  %-18s -> %s" % (label, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))

log(u"=== PROBE_SRC END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
