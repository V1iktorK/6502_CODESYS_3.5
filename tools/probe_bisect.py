# -*- coding: utf-8 -*-
"""
probe_bisect.py -- BISEKCIYA PO ELEMENTAM XML. Reshayushchij metod.

Pochva:
  * vse 11 konstrukcij yadra po otdelnosti prinimayutsya;
  * ob"em/razmer oprovergnuty (4000 blokov, 3.7 MB -- sozdaetsya);
  * yadro molcha ne sozdaetsya, ni isklyucheniya, ni soobshcheniya.

Klyuchevoy fakt: fbd.py vytavlyaet elementy v poryadke sozdaniya, i
KAZHDAYA svyaz ssylaetsya na B O L E E  R A N N I Y localId. Znachit lyuboy
PREFIKS spiska elementov -- validnaya (chastichnaya) shema bez visit
ssylok. Pereborom po K nahodim pervyy element, iz-za kotorogo import
perestaet sozdavat POU, i pechataem ego.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))

LOG = os.path.join(ROOT, "log", "probe_bisect.log")
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
log(u"=== PROBE_BISECT START ===")


# ------------------------------------------------------------ razbor XML
def split_fbd(text):
    """Vernut (head, elements, tail): head vklyuchaet '<FBD>', tail '</FBD>...'."""
    i = text.find(u"<FBD")
    if i < 0:
        i = text.find(u"<FBD>")
    if i < 0:
        raise RuntimeError(u"нет <FBD>")
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
            self_close = (body[e - 1] == u"/")
            if self_close:
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
log(u"элементов верхнего уровня в листе: %d" % N)
if N == 0:
    log(u"ОШИБКА РАЗБОРА: элементов не найдено")
    log(u"=== PROBE_BISECT END ===")
    try:
        system.exit()
    except Exception:
        pass
    sys.exit(0)
log(u"  первый: %s" % els[0][:100])
log(u"  последний: %s" % els[-1][:100])

# imya POU berem iz fajla, dalee podstavlyaem svoe
import re
m = re.search(u'<pou name="([^"]+)"', text)
BASE_NAME = m.group(1) if m else u"PRG_CPU_CORE"
log(u"имя POU в файле: %s" % BASE_NAME)


def make_xml(k, name):
    body = u"".join(els[:k])
    t = head + body + tail
    t = re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)
    # ubiraem kommentariy-sheet? net, ostavlyaem kak est
    return t


def write(path, s):
    o = io.open(path, "wb")
    o.write(s.encode("utf-8"))
    o.close()


# ------------------------------------------------------------ proekt
BASE = os.path.join(BUILD, u"bis_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"bis_bs.project"):
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


_try = [0]


def trial(k):
    """True, esli shema iz pervyh k elementov SOZDAETSYA."""
    _try[0] += 1
    name = u"BIS_%d_%d" % (k, _try[0])
    p = os.path.join(PLCOPEN, u"bis_tmp.xml")
    try:
        write(p, make_xml(k, name))
        app.import_xml(p, False)
    except Exception:
        log(u"  K=%-5d исключение: %s" % (k, traceback.format_exc().strip().splitlines()[-1]))
        return None
    ok = name in names()
    return ok


log(u"")
log(u"--- грубая проверка ---")
okN = trial(N)
log(u"  K=%-5d -> %s" % (N, u"СОЗДАН" if okN else u"НЕ СОЗДАН"))
if okN:
    log(u"ВНИМАНИЕ: полный префикс (= весь лист) создался! Значит проблема не в листе.")
    log(u"=== PROBE_BISECT END ===")
    try:
        proj.close()
    except Exception:
        pass
    try:
        system.exit()
    except Exception:
        pass
    sys.exit(0)

ok1 = trial(1)
log(u"  K=%-5d -> %s" % (1, u"СОЗДАН" if ok1 else u"НЕ СОЗДАН"))

if not ok1:
    log(u"ДАЖЕ 1 элемент не создаётся -- дело в шапке файла (декларация/POU).")
    log(u"=== PROBE_BISECT END ===")
    try:
        proj.close()
    except Exception:
        pass
    try:
        system.exit()
    except Exception:
        pass
    sys.exit(0)

# ------------------------------------------------------------ bisekciya
lo = 1      # sozdaetsya
hi = N      # ne sozdaetsya
log(u"")
log(u"--- бисекция: lo=%d (ok), hi=%d (fail) ---" % (lo, hi))
steps = 0
while hi - lo > 1 and steps < 24:
    steps += 1
    mid = (lo + hi) // 2
    ok = trial(mid)
    if ok is None:
        ok = False
    log(u"  K=%-5d -> %s" % (mid, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))
    if ok:
        lo = mid
    else:
        hi = mid

log(u"")
log(u"ПОРОГ: К=%d создаётся, К=%d НЕ создаётся" % (lo, hi))
log(u"")
log(u"--- последний принятый элемент (K=%d) ---" % lo)
log(els[lo - 1][:1200])
log(u"")
log(u"--- ПЕРВЫЙ ОТВЕРГАЕМЫЙ элемент (K=%d) ---" % hi)
log(els[hi - 1][:1600])

log(u"=== PROBE_BISECT END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
