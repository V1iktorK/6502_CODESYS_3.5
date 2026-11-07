# -*- coding: utf-8 -*-
"""
probe_bisect3.py -- uniwersalnaya bisekciya lyubogo POU s VOZMOZHNYM ZAVISANIEM.

Cel': BIS_TARGET=<imya bez .xml>, naprimer FB_PC_Update.
Osobennosti:
  * sostoyanie hranitsya v log/bis3_state_<target>.txt, poetomu posle zavisaniya
    (kogda protsess ubivaet run_quick.ps1) sleduyushchij zapusk PRODOLZHAET sushenie;
  * sostoyanie pishetsya PESSIMISTICHNO pered kazhdoy popytkoy: schitaem, chto
    ona provalitsya. Esli zavisnet -- posle perezapuska granica uzhe vernaya;
  * stroka "ПЕРЕД K=" pishetsya do importa, poetomu vsegda vidno, na chem zavisli.
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
TARGET = os.environ.get("BIS_TARGET", u"FB_PC_Update")
LOG = os.path.join(ROOT, "log", "probe_bisect3.log")
STATE = os.path.join(ROOT, "log", "bis3_state_%s.txt" % TARGET)
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
SRC = os.path.join(PLCOPEN, u"%s.xml" % TARGET)


def log(m, fresh=False):
    f = io.open(LOG, "w" if fresh else "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


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
N = len(els)
log(u"=== PROBE_BISECT3 START (%s) ===" % TARGET, fresh=True)
log(u"элементов в листе %s: %d" % (TARGET, N))

lo, hi = 1, N
if os.path.exists(STATE):
    try:
        st = io.open(STATE, "r", encoding="utf-8").read().split()
        lo, hi = int(st[0]), int(st[1])
    except Exception:
        pass
log(u"интервал: lo=%d (создаётся) hi=%d (нет)" % (lo, hi))


def make(k, name):
    t = head + u"".join(els[:k]) + tail
    return re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"bi3_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"bi3_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"bi3_bs.project"):
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


def trial(k):
    name = u"BI3_%d" % k
    log(u"ПЕРЕД K=%d" % k)
    try:
        write(make(k, name))
        app.import_xml(os.path.join(PLCOPEN, u"bi3_tmp.xml"), False)
    except Exception:
        log(u"  K=%-4d ИСКЛЮЧЕНИЕ: %s" % (k, traceback.format_exc().strip().splitlines()[-1]))
        return None
    ok = name in names()
    log(u"  K=%-4d -> %s" % (k, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))
    return ok


if hi - lo <= 1:
    log(u"интервал уже сужен")
else:
    ok1 = trial(1)
    if not ok1:
        log(u"K=1 НЕ создаётся -> виноват интерфейс POU")
        log(u"=== PROBE_BISECT3 END ===")
        try:
            system.exit()
        except Exception:
            pass
        sys.exit(0)
    steps = 0
    while hi - lo > 1 and steps < 20:
        steps += 1
        mid = (lo + hi) // 2
        io.open(STATE, "w", encoding="utf-8").write(u"%d %d" % (lo, mid))
        ok = trial(mid)
        if ok:
            lo = mid
            io.open(STATE, "w", encoding="utf-8").write(u"%d %d" % (lo, hi))
    log(u"")
    log(u"ПОРОГ: K=%d создаётся, K=%d нет" % (lo, hi))
    log(u"--- последний принятый (K=%d) ---" % lo)
    log(els[lo - 1][:800])
    log(u"--- ПЕРВЫЙ ОТВЕРГАЕМЫЙ (K=%d) ---" % hi)
    log(els[hi - 1][:1100])

log(u"=== PROBE_BISECT3 END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
