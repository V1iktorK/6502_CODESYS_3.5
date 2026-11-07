# -*- coding: utf-8 -*-
"""
test_lda2.py -- T-LDA-1 na sohranennom proekte, s podrobnym logom.

Programma: $0200: A9 42 (LDA #$42) ; $0202: 4C 02 02 (JMP $0202) -- samopovtor.
Start: vektor BRK $FFFE/FFFF = $0200 (yadro v moment starta krutit BRK po adresu 0).
Ozhidaem: A=$42, PC=$0202.
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_lda2.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_LDA2 START ===")
import scriptengine

WORK = os.path.join(BUILD, u"lda2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"lda2.project"):
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
log(u"копия: %d байт" % len(_d))

try:
    _w = projects.create(os.path.join(BUILD, u"lda2_warm.project"))
    _w.close()
    log(u"прогрев ок")
except Exception:
    log(u"прогрев: %s" % traceback.format_exc().strip().splitlines()[-1])

t0 = time.time()
proj = projects.open(WORK)
app = proj.active_application
log(u"открыт за %.1f с" % (time.time() - t0))

log(u"сборка...")
try:
    app.build()
    log(u"сборка ок")
except Exception:
    log(u"сборка: %s" % traceback.format_exc().strip().splitlines()[-1])

oa = None
try:
    node = app
    for i in range(6):
        node = node.parent
        if node is None:
            break
        try:
            node.set_simulation_mode(True)
            log(u"режим симуляции включён (уровень %d)" % (i + 1))
            break
        except Exception:
            continue
    log(u"создаю онлайн-приложение...")
    oa = scriptengine.online.create_online_application(app)
    log(u"онлайн-приложение создано")
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    log(u"login ок")
    oa.start()
    log(u"start ок")
except Exception:
    log(u"ОНЛАЙН ОШИБКА: %s" % traceback.format_exc())

if oa is not None:
    try:
        prog = [(0x0200, 0xA9), (0x0201, 0x42), (0x0202, 0x4C),
                (0x0203, 0x02), (0x0204, 0x02), (0xFFFE, 0x00), (0xFFFF, 0x02)]
        for addr, val in prog:
            oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % val)
        oa.write_prepared_values()
        log(u"память загружена")
        time.sleep(0.6)
        res = {}
        for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.P",
                     u"GVL_CPU.OPs", u"GVL_CPU.LD_A_E", u"GVL_CPU.REG_WR",
                     u"GVL_CPU.WDATA", u"GVL_CPU.EFF", u"GVL_CPU.ADDR_MODE",
                     u"GVL_CPU.LEN", u"GVL_CPU.SRC"):
            try:
                v = oa.read_value(expr)
                res[expr] = u"%s" % v
                log(u"  %-18s = %s" % (expr, v))
            except Exception:
                log(u"  %-18s ошибка чтения" % expr)

        def num(expr):
            s = res.get(expr, u"")
            try:
                return int(s.split(u"#")[-1], 16) if u"#" in s else int(s)
            except Exception:
                return None

        a = num(u"GVL_CPU.A")
        pc = num(u"GVL_CPU.PC")
        log(u"")
        log(u"РЕЗУЛЬТАТ T-LDA-1: A=%s (ожид 66) PC=%s (ожид 514) -> %s"
            % (a, pc, u"PASS" if (a == 0x42 and pc == 0x202) else u"FAIL"))
    except Exception:
        log(u"ТЕСТ ОШИБКА: %s" % traceback.format_exc())

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.close()
except Exception:
    pass
log(u"=== TEST_LDA2 END ===")
try:
    system.exit()
except Exception:
    pass
