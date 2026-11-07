# -*- coding: utf-8 -*-
"""
probe_sim2.py -- dva voprosa odnim progonом.

1) Rezhim simulyacii: probuem set_simulation_mode na vseh predkah prilozheniya.
2) Tochka vhoda: probuem udalit PLC_PRG (remove) i zatem importirovat FBD-versiyu;
   esli ne poluchitsya -- propisyvaem v PLC_PRG odnu stroku-vyzov (vsya logika
   ostaetsya v FBD-bloke FB_CPU_Core).

V konce -- sborka, login, start, chtenie A/PC.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_sim2.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
PLCOPEN = os.path.join(ROOT, "plcopen")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_SIM2 START ===")
import scriptengine

WORK = os.path.join(BUILD, u"sim2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"sim2.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(PROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()

proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")

# ---------------------------------------------------------------- 1. симуляция
log(u"")
log(u"--- set_simulation_mode по предкам ---")
try:
    online_app = scriptengine.online.create_online_application(app)
    node = app
    for depth in range(6):
        try:
            node = node.parent
        except Exception:
            break
        if node is None:
            break
        try:
            nm = node.get_name()
        except Exception:
            nm = u"?"
        try:
            node.set_simulation_mode(True)
            log(u"  глубина %d (%s): set_simulation_mode(True) — выполнено" % (depth + 1, nm))
            break
        except Exception as e:
            log(u"  глубина %d (%s): нет метода (%s)" % (depth + 1, nm,
                                                         u"%s" % e).splitlines()[0][:80])
except Exception:
    log(u"  create_online_application: %s" % traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------- 2. точка входа
log(u"")
log(u"--- точка входа: PLC_PRG ---")
prg = None
try:
    res = app.find(u"PLC_PRG", True)
    for o in (res or []):
        try:
            t = o.textual_declaration
            if t is not None and t.text:
                prg = o
                break
        except Exception:
            continue
    log(u"  текстовый PLC_PRG найден: %s" % (prg is not None))
except Exception:
    log(u"  find: %s" % traceback.format_exc().strip().splitlines()[-1])

removed = False
if prg is not None:
    try:
        prg.remove()
        removed = True
        log(u"  PLC_PRG удалён")
    except Exception:
        log(u"  remove() недоступен: %s" % traceback.format_exc().strip().splitlines()[-1])

if removed:
    try:
        app.import_xml(os.path.join(PLCOPEN, u"PRG_PLC.xml"), False)
        res = app.find(u"PLC_PRG", True)
        ok = False
        for o in (res or []):
            try:
                if o.textual_declaration is None:
                    ok = True
            except Exception:
                ok = True
        log(u"  FBD-версия PLC_PRG импортирована: %s" % ok)
    except Exception:
        log(u"  импорт после удаления: %s" % traceback.format_exc().strip().splitlines()[-1])
else:
    if prg is not None:
        try:
            prg.textual_declaration.replace(
                u"PROGRAM PLC_PRG\nVAR\n\tCore : FB_CPU_Core;\nEND_VAR\n")
            prg.textual_implementation.replace(u"Core(Enable := TRUE);\n")
            log(u"  в PLC_PRG прописан вызов FBD-блока (одна строка)")
        except Exception:
            log(u"  запись в PLC_PRG: %s" % traceback.format_exc().strip().splitlines()[-1])

# ---------------------------------------------------------------- 3. сборка и прогон
log(u"")
log(u"--- сборка ---")
try:
    app.build()
except Exception:
    pass
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                log(u"  %s" % (m,))
            except Exception:
                pass
    except Exception:
        pass

log(u"")
log(u"--- онлайн ---")
try:
    online_app = scriptengine.online.create_online_application(app)
    online_app.login(scriptengine.OnlineChangeOption.Try, False)
    log(u"  login ок, is_logged_in=%s" % online_app.is_logged_in)
    online_app.start()
    log(u"  start ок")
    for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.OP",
                 u"GVL_CPU.Done"):
        try:
            log(u"  %s = %s" % (expr, online_app.read_value(expr)))
        except Exception:
            log(u"  %s: ошибка чтения" % expr)
    online_app.stop()
    online_app.logout()
except Exception:
    log(u"  ОШИБКА онлайн: %s" % traceback.format_exc())

try:
    proj.save()
except Exception:
    pass
try:
    proj.close()
except Exception:
    pass

log(u"=== PROBE_SIM2 END ===")
try:
    system.exit()
except Exception:
    pass
