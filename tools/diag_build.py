# -*- coding: utf-8 -*-
"""
diag_build.py -- CHESTNOE chtenie oshibok kompilyatora + ispravlenie F_Add16.

Uroki so skrinshota polzovatelya:
  * system.get_messages() vernul 0 soobshcheniy PRI 4 realnyh oshibkah.
    Znachit chitat nado po KATEGORIYAM (get_message_categories), a ne podryad;
  * realnye oshibki v F_Add16:
        C0032 "Обнаружен неоднозначный элемент (Недопустимое количество входов)"
        C0032 "Для '<' требуется ровно 2 операндов"  (dvazhdy)
    to est blok LT poluchil ne 2 operanda, a drugoy blok -- nedopustimoe chislo vhodov.

Gipoteza: lishniy operand daet PUSTOY element <inOutVariables />, kotoryy ya
dobavlyal radi XSD. Proveryaem dva varianta emissii bloka:
  A) kak seychas: <inOutVariables /> pered <outputVariables>
  B) bez <inOutVariables /> voobshche
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "diag_build.log")
SRC = r"C:\CPM6502_build\CPM6502.project"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DIAG_BUILD START ===")
import scriptengine

proj = app = None
try:
    proj = projects.open(SRC)
    app = proj.active_application
    log(u"проект открыт: %s" % SRC)
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- категории сообщений
log(u"--- категории сообщений ---")
cats = []
try:
    cats = system.get_message_categories()
    for c in cats:
        try:
            log(u"  %r  (%s)" % (c, system.get_message_category_description(c)))
        except Exception:
            log(u"  %r" % (c,))
except Exception:
    log(traceback.format_exc())

# ---------------------------------------------------------------- сборка
log(u"--- сборка ---")
try:
    app.build()
    log(u"app.build() без исключения")
except Exception:
    log(u"app.build() ИСКЛЮЧЕНИЕ:")
    log(traceback.format_exc())

# ---------------------------------------------------------------- сообщения
log(u"--- сообщения: подряд ---")
try:
    msgs = system.get_messages()
    log(u"всего: %d" % len(msgs))
    for m in msgs:
        log(u"  %r" % (m,))
except Exception:
    log(traceback.format_exc())

for c in cats:
    try:
        msgs = system.get_messages(c)
        log(u"--- сообщения категории %r: %d ---" % (c, len(msgs)))
        for m in msgs:
            try:
                log(u"  [%s] %s" % (getattr(m, "severity", u"?"), getattr(m, "text", m)))
            except Exception:
                log(u"  %r" % (m,))
    except Exception:
        log(u"  категория %r недоступна: %s" % (c, traceback.format_exc().strip().splitlines()[-1]))

# ---------------------------------------------------------------- объекты проекта
log(u"--- объекты уровня Application ---")
try:
    for ch in app.get_children():
        s = str(ch)
        nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else repr(ch)[:60]
        log(u"  %s" % nm)
except Exception:
    log(traceback.format_exc())

try:
    proj.close()
except Exception:
    pass
log(u"=== DIAG_BUILD END ===")
try:
    system.exit()
except Exception:
    pass
