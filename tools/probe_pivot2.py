# -*- coding: utf-8 -*-
"""
probe_pivot2.py -- chto imenno delaet element #2225 zapreshchennym V KONTEKSTE.

Uzhe izvestno:
  prefiks 2224                -> СОЗДАН
  prefiks 2224 + chuzhoy MOVE -> СОЗДАН   (znachit eto NE kolichestvennyy porog)
  prefiks 2224 + element #2225 -> НЕ СОЗДАН
  minimalnaya shema iz zavisimostey #2225 -> СОЗДАН

Razlichaem tri vozmozhnye prichiny:
  D1: tot zhe element, no sdvinutaya POZICIYA
  D2: tot zhe element, no NOVYY localId
  D3: novyy localId + sdvinutaya poziciya
  D4: kontrol -- kopiya bolee rannego bloka s novym localId
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_pivot2.log")
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
log(u"=== PROBE_PIVOT2 START ===")


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
byid = {}
for e in els:
    m = re.search(u'localId="(\\d+)"', e[:200])
    if m:
        byid[int(m.group(1))] = e

prefix = els[:PIVOT - 1]
pivot = els[PIVOT - 1]
log(u"элементов: %d, префикс: %d" % (len(els), len(prefix)))

# chto uzhe est v prefikse na tochechnoy pozicii pivota
pm = re.search(u'<position x="(\\d+)" y="(\\d+)"', pivot)
px, py = pm.group(1), pm.group(2)
same = [e[:80] for e in prefix if (u'<position x="%s" y="%s"' % (px, py)) in e]
log(u"позиция опорного элемента: x=%s y=%s" % (px, py))
log(u"элементов префикса на ТОЙ ЖЕ позиции: %d" % len(same))
for s in same[:5]:
    log(u"   %s" % s)

log(u"")
log(u"--- зависимости опорного элемента ---")
need = set()
stack = [pivot]
while stack:
    e = stack.pop()
    m = re.search(u'localId="(\\d+)"', e[:200])
    if not m:
        continue
    eid = int(m.group(1))
    if eid in need:
        continue
    need.add(eid)
    for r in re.findall(u'refLocalId="(\\d+)"', e):
        rid = int(r)
        if rid in byid and rid not in need:
            stack.append(byid[rid])
for e in els:
    m = re.search(u'localId="(\\d+)"', e[:200])
    if m and int(m.group(1)) in need:
        t = re.search(u'typeName="([^"]+)"', e)
        ex = re.search(u'<expression>([^<]*)</expression>', e)
        log(u"   id=%-6s %-16s %s" % (m.group(1), (t.group(1) if t else u'(переменная)'),
                                      (u"expr=" + ex.group(1)) if ex else u""))


def v_pos(el):
    return el.replace(u'<position x="%s" y="%s"' % (px, py),
                      u'<position x="31000" y="31000"')


def v_id(el, newid):
    return el.replace(u'localId="%d"' % int(re.search(u'localId="(\\d+)"', el[:200]).group(1)),
                      u'localId="%d"' % newid, 1)


VARIANTS = [
    (u"D1 сдвинутая позиция", prefix + [v_pos(pivot)]),
    (u"D2 новый localId", prefix + [v_id(pivot, 999002)]),
    (u"D3 новый id + позиция", prefix + [v_id(v_pos(pivot), 999003)]),
    (u"D4 копия раннего блока", prefix + [v_id(els[2222], 999004)]),
]


def make(name, elements):
    t = head + u"".join(elements) + tail
    return re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"piv2_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"piv2_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"piv2_bs.project"):
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


log(u"")
log(u"--- ОПЫТЫ ---")
res = []
for i, (label, elements) in enumerate(VARIANTS):
    name = u"PV2_%d" % i
    try:
        write(make(name, elements))
        app.import_xml(os.path.join(PLCOPEN, u"piv2_tmp.xml"), False)
    except Exception:
        log(u"  %-26s ИСКЛЮЧЕНИЕ: %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        res.append((label, None))
        continue
    ok = name in names()
    log(u"  %-26s -> %s" % (label, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))
    res.append((label, ok))

log(u"")
log(u"ИТОГ:")
for label, ok in res:
    log(u"  %-26s %s" % (label, u"СОЗДАН" if ok else (u"НЕ СОЗДАН" if ok is False else u"?")))
log(u"=== PROBE_PIVOT2 END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
