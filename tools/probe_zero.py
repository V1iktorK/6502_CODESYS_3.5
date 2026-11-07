# -*- coding: utf-8 -*-
"""
probe_zero.py -- proverka yadra BEZ vektora BRK.

PC pri starte = 0, poetomu kladem programmu po adresu 0:
    $0000: A9 42     LDA #$42
    $0002: 4C 02 00  JMP $0002   (samopovtor)
Ozhidaem: A=$42, PC=$0002.
"""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_zero.log")
DIR = r"C:\p"
SRC = os.path.join(DIR, u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_ZERO START ===")

import scriptengine

proj = projects.open(SRC)
app = proj.active_application
log(u"открыт")

oa = None
try:
    node = app
    for i in range(6):
        node = node.parent
        if node is None:
            break
        try:
            node.set_simulation_mode(True)
            break
        except Exception:
            continue
    oa = scriptengine.online.create_online_application(app)
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    oa.start()
    log(u"симуляция запущена")
except Exception:
    log(u"ОНЛАЙН: %s" % traceback.format_exc().strip().splitlines()[-1])

if oa is not None:
    prog = [(0x0000, 0xA9), (0x0001, 0x42),
            (0x0002, 0x4C), (0x0003, 0x02), (0x0004, 0x00)]
    try:
        for a, v in prog:
            oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % a, u"16#%02X" % v)
        oa.write_prepared_values()
        log(u"программа загружена по адресу 0")
    except Exception:
        log(u"запись: %s" % traceback.format_exc().strip().splitlines()[-1])

    time.sleep(0.8)
    for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.ALU_R",
                 u"GVL_CPU.ALU_AX", u"GVL_CPU.ALU_BX", u"GVL_CPU.REG_WR",
                 u"GVL_CPU.RW0", u"GVL_CPU.RW3", u"GVL_CPU.RW4", u"GVL_CPU.RW7",
                 u"GVL_CPU.F_ADD", u"GVL_CPU.ALU_A", u"GVL_CPU.ALU_B",
                 u"GVL_CPU.CARRY", u"GVL_CPU.P_NEW"):
        try:
            log(u"  %-18s = %s" % (expr, oa.read_value(expr)))
        except Exception:
            log(u"  %-18s ошибка" % expr)

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_ZERO END ===")
try:
    system.exit()
except Exception:
    pass
