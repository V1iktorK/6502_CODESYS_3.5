# -*- coding: utf-8 -*-
"""
test_run1.py -- pervaya integracionnaya proverka: zapustit yadro v simulyacii.

Shagi:
  1) kopiya build/CPM6502_CPU.project;
  2) import FBD-programmy PLC_PRG (zamena pustoy ST-programmy shablona);
  3) sborka;
  4) onlajn: login -> start;
  5) zapis v pamyat programmy LDA #$42 (A9 42) po adresu $0200, PC=$0200, SP=$FF;
  6) neskolko skanov, chtenie A, X, PC, SP, P.

Rezultaty pishem v log.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_run1.log")
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
log(u"=== TEST_RUN1 START ===")
import scriptengine

WORK = os.path.join(BUILD, u"run1.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"run1.project"):
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
log(u"проект скопирован")

proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")

# ---------------- 1. замена PLC_PRG на FBD-программу
log(u"")
log(u"--- импорт FBD-программы вместо PLC_PRG ---")
try:
    app.import_xml(os.path.join(PLCOPEN, u"PRG_PLC.xml"), False)
    log(u"  импорт выполнен")
except Exception:
    log(u"  исключение: %s" % traceback.format_exc().strip().splitlines()[-1])

def names():
    out = []
    try:
        for ch in app.get_children():
            try:
                out.append(ch.get_name())
            except Exception:
                pass
    except Exception:
        pass
    return out

log(u"  дети приложения: PLC_PRG встречается %d раз" % names().count(u"PLC_PRG"))
try:
    res = app.find(u"PLC_PRG", True)
    log(u"  find(PLC_PRG): %d объектов" % (len(res) if res is not None else -1))
    for o in (res or []):
        try:
            d = o.textual_declaration
            log(u"    decl: %s" % d.text.replace(u"\n", u" | ")[:160])
        except Exception:
            log(u"    decl: недоступно (не текстовый объект)")
except Exception:
    log(u"  find: %s" % traceback.format_exc().strip().splitlines()[-1])

# ---------------- 2. сборка
log(u"")
log(u"--- сборка ---")
try:
    app.build()
except Exception:
    log(u"  исключение сборки: %s" % traceback.format_exc().strip().splitlines()[-1])
msgs = []
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                msgs.append(u"%s" % (m,))
            except Exception:
                pass
    except Exception:
        pass
for m in msgs:
    log(u"  %s" % m)

# ---------------- 3. онлайн
log(u"")
log(u"--- онлайн ---")
online_app = None
try:
    online_app = scriptengine.online.create_online_application(app)
    log(u"  объект онлайн создан")
    try:
        online_app.set_default_credentials(u"", u"")
    except Exception:
        pass
    online_app.login(scriptengine.OnlineChangeOption.Try, False)
    log(u"  login ок, is_logged_in=%s" % online_app.is_logged_in)
    online_app.start()
    log(u"  start ок")
except Exception:
    log(u"  ОШИБКА онлайн: %s" % traceback.format_exc())
    online_app = None

if online_app is not None:
    # ---------------- 4. загрузка тестовой программы
    log(u"")
    log(u"--- загрузка программы LDA #$42 ---")
    try:
        online_app.set_prepared_value(u"GVL_MEM.Mem[512]", u"16#A9")
        online_app.set_prepared_value(u"GVL_MEM.Mem[513]", u"16#42")
        online_app.set_prepared_value(u"GVL_CPU.PC", u"16#0200")
        online_app.set_prepared_value(u"GVL_CPU.SP", u"16#FF")
        online_app.set_prepared_value(u"GVL_CPU.A", u"16#00")
        online_app.write_prepared_values()
        log(u"  значения записаны")
    except Exception:
        log(u"  ОШИБКА записи: %s" % traceback.format_exc())

    # ---------------- 5. прогон
    log(u"")
    log(u"--- чтение состояния ---")
    for tag in (u"до", u"после"):
        try:
            a = online_app.read_value(u"GVL_CPU.A")
            pc = online_app.read_value(u"GVL_CPU.PC")
            sp = online_app.read_value(u"GVL_CPU.SP")
            p = online_app.read_value(u"GVL_CPU.P")
            op = online_app.read_value(u"GVL_CPU.OP")
            log(u"  %-6s A=%s PC=%s SP=%s P=%s OP=%s" % (tag, a, pc, sp, p, op))
        except Exception:
            log(u"  %-6s ОШИБКА чтения: %s" % (tag, traceback.format_exc().strip().splitlines()[-1]))
        if tag == u"до":
            try:
                online_app.stop()   # дать прогону выполниться
                online_app.start()
            except Exception:
                pass

    try:
        online_app.stop()
        online_app.logout()
    except Exception:
        pass

if proj is not None:
    try:
        proj.save()
    except Exception:
        pass
    try:
        proj.close()
    except Exception:
        pass

log(u"=== TEST_RUN1 END ===")
try:
    system.exit()
except Exception:
    pass
