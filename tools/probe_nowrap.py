# -*- coding: utf-8 -*-
"""
probe_nowrap.py -- yadro BEZ sinteticheskih peremennyh G<id>.

Chto izvestno:
  * prefiks 2224 sozdaetsya, a dobavlenie bloka OR 2681, vhodyashchego v
    SEL 2670, -- lomaet import;
  * u etogo SEL vhod G pitayetsya ot sinteticheskoy peremennoy G2671,
    sozdannoy rezhimom razryva svyazey (USE_WRAP_CMP);
  * v minimalnoy sheme tot zhe fragment sozdaetsya, v polnom kontekste -- net.

Proverka: preobrazuem list tak, chtoby NIKAKIH sinteticheskih G-peremennyh
ne bylo -- potrebiteli podklyuchayutsya NAPRYAMUYU k istochniku. Zagotovki
(outVariable G<id> / inVariable G<id>) udalyayutsya.

  W1: polnyy list bez G-peremennyh
  W2: kontrol -- polnyy list kak est (dolzhen NE sozdatysya)
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_nowrap.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
SRC = os.path.join(PLCOPEN, u"PRG_CORE_L10.xml")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_NOWRAP START ===")


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
log(u"элементов: %d" % len(els))

GNAME = re.compile(u'^G(\\d+)$')


def eid(e):
    m = re.search(u'localId="(\\d+)"', e[:200])
    return int(m.group(1)) if m else None


def expr(e):
    m = re.search(u'<expression>([^<]*)</expression>', e)
    return m.group(1) if m else None


# 1) zagotovki: outVariable G<id> <- P
produced = {}
for e in els:
    if e.startswith(u"<outVariable"):
        x = expr(e)
        if x and GNAME.match(x):
            m = re.search(u'refLocalId="(\\d+)"', e)
            if m:
                produced[x] = int(m.group(1))
log(u"синтетических G-переменных произведено: %d" % len(produced))

# 2) potrebiteli: inVariable G<id>
consumed = {}
for e in els:
    if e.startswith(u"<inVariable"):
        x = expr(e)
        if x and GNAME.match(x) and x in produced:
            i = eid(e)
            if i is not None:
                consumed[i] = produced[x]
log(u"G-переменных читается: %d" % len(consumed))

drop = set()
for e in els:
    i = eid(e)
    if i is None:
        continue
    x = expr(e)
    if x and GNAME.match(x) and (((e.startswith(u"<inVariable")) and i in consumed)
                                 or (e.startswith(u"<outVariable") and x in produced)):
        drop.add(i)
log(u"удаляем заглушек: %d" % len(drop))

newels = []
for e in els:
    i = eid(e)
    if i in drop:
        continue
    def repl(m):
        r = int(m.group(1))
        if r in consumed:
            return u'refLocalId="%d"' % consumed[r]
        return m.group(0)
    newels.append(re.sub(u'refLocalId="(\\d+)"', repl, e))
log(u"элементов после преобразования: %d" % len(newels))


def make(name, elements):
    t = head + u"".join(elements) + tail
    return re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"wr_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"wr_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"wr_bs.project"):
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


def trial(label, name, elements):
    try:
        write(make(name, elements))
        rv = app.import_xml(os.path.join(PLCOPEN, u"wr_tmp.xml"), False)
    except Exception:
        log(u"  %-26s ИСКЛЮЧЕНИЕ: %s" % (label, traceback.format_exc().strip().splitlines()[-1]))
        return None
    ok = name in names()
    log(u"  %-26s -> %s   (import_xml вернул: %s)" % (label, u"СОЗДАН" if ok else u"НЕ СОЗДАН", rv))
    return ok


log(u"")
log(u"--- ОПЫТЫ ---")
trial(u"W2 контроль (как есть)", u"NW_CTRL", els)
trial(u"W1 без G-переменных", u"NW_1", newels)

log(u"=== PROBE_NOWRAP END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
