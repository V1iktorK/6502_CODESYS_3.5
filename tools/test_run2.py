# -*- coding: utf-8 -*-
"""
test_run2.py -- zapusk yadra v simulyacii i pervaya komanda.

Shagi:
  1) otkryt build/CPM6502_CPU.project;
  2) vklyuchit rezhim simulyacii (perebor kandidatov: app, app.parent, ...);
  3) onlajn: login -> zapis programmy v pamyat -> start;
  4) prochitat sostoyanie posle neskolkih skanov.

Test T-LDA-1: LDA #$42.
  Mem[$0200]=$A9, Mem[$0201]=$42, PC=$0200, SP=$FF, A=0
  Ozhidaem: A=$42, PC продвинулся.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_run2.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_RUN2 START ===")
import scriptengine

WORK = os.path.join(BUILD, u"run2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"run2.project"):
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

# ---------------------------------------------------------- режим симуляции
log(u"")
log(u"--- поиск режима симуляции ---")
cands = []
node = app
for i in range(6):
    cands.append((u"глубина %d" % i, node))
    try:
        node = node.parent
    except Exception:
        break
    if node is None:
        break
cands.append((u"project", proj))

sim_ok = False
for label, obj in cands:
    if obj is None:
        continue
    for meth in (u"set_simulation_mode", u"set_simulation"):
        try:
            getattr(obj, meth)(True)
            log(u"  %s: %s(True) — принят" % (label, meth))
            sim_ok = True
            break
        except Exception:
            continue
    if sim_ok:
        break
if not sim_ok:
    log(u"  метод не найден ни на одном уровне")

# ---------------------------------------------------------- онлайн
log(u"")
log(u"--- сборка ---")
try:
    app.build()
except Exception:
    pass
errs = 0
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                t = u"%s" % (m,)
            except Exception:
                continue
            if u"ошибк" in t.lower() and u"0 ошибки" not in t:
                errs += 1
                log(u"  %s" % t)
    except Exception:
        pass
log(u"  ошибок компиляции: %d" % errs)

log(u"")
log(u"--- онлайн ---")
oa = None
try:
    oa = scriptengine.online.create_online_application(app)
    log(u"  объект создан")
    for how in ((u"login(Try,False)", lambda: oa.login(scriptengine.OnlineChangeOption.Try, False)),
                (u"login()", lambda: oa.login()),
                (u"login(Try,True)", lambda: oa.login(scriptengine.OnlineChangeOption.Try, True))):
        try:
            how[1]()
            log(u"  %s — ок, is_logged_in=%s" % (how[0], oa.is_logged_in))
            break
        except Exception:
            log(u"  %s — не вышло: %s" % (how[0], (u"%s" % traceback.format_exc()).splitlines()[-1][:160]))
except Exception:
    log(u"  ОШИБКА создания: %s" % traceback.format_exc().strip().splitlines()[-1])
    oa = None

if oa is not None and oa.is_logged_in:
    # ------------------------------------------------ загрузка программы
    log(u"")
    log(u"--- загрузка программы LDA #$42 ---")
    written = False
    try:
        oa.set_prepared_value(u"GVL_MEM.Mem[512]", u"16#A9")
        oa.set_prepared_value(u"GVL_MEM.Mem[513]", u"16#42")
        oa.set_prepared_value(u"GVL_CPU.PC", u"16#0200")
        oa.set_prepared_value(u"GVL_CPU.SP", u"16#FF")
        oa.set_prepared_value(u"GVL_CPU.A", u"16#00")
        oa.write_prepared_values()
        written = True
        log(u"  записано")
    except Exception:
        log(u"  ОШИБКА записи: %s" % (u"%s" % traceback.format_exc()).splitlines()[-1][:200])

    log(u"")
    log(u"--- запуск ---")
    try:
        oa.start()
        log(u"  start ок, состояние=%s" % (oa.application_state,))
    except Exception:
        log(u"  ОШИБКА start: %s" % (u"%s" % traceback.format_exc()).splitlines()[-1][:200])

    try:
        import time
        time.sleep(0.5)
    except Exception:
        for _ in range(300000):
            pass

    log(u"")
    log(u"--- чтение ---")
    for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.P",
                 u"GVL_CPU.OPs", u"GVL_CPU.OP1", u"GVL_CPU.OP2", u"GVL_CPU.PC2",
                 u"GVL_CPU.ADDR_MODE", u"GVL_CPU.PC_MODE", u"GVL_CPU.LEN",
                 u"GVL_CPU.SRC", u"GVL_CPU.ADV", u"GVL_CPU.P_ADV", u"GVL_CPU.PC_NEW",
                 u"GVL_CPU.EFF", u"GVL_CPU.C_IMM", u"GVL_CPU.WDATA",
                 u"GVL_CPU.REG_WR", u"GVL_CPU.LD_A_E", u"GVL_CPU.Enable",
                 u"GVL_CPU.Done", u"GVL_MEM.Mem[512]"):
        try:
            log(u"  %-18s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-18s ошибка чтения" % expr)

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.close()
except Exception:
    pass

log(u"=== TEST_RUN2 END ===")
try:
    system.exit()
except Exception:
    pass
