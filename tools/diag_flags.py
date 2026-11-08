# -*- coding: utf-8 -*-
"""
diag_flags.py -- pochemu registr P ne prinimaet zadannoe znachenie.

Yadro ostanovleno (Run=FALSE, Step_On=FALSE), poetomu nikakie komandy ne
ispolnyayutsya. Pishem P=0x24 i smotrim, chto vosstanavlivaetsya: P i P_NEW,
a takzhe vse vhody sloya flagov (signaly deshifratora, rezultaty ALU).
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "diag_flags.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

FLAGIN = [u"P", u"P_NEW", u"SET_NZ", u"SET_C", u"SET_V", u"SET_B",
          u"CMD_CLC", u"CMD_SEC", u"CMD_SEI", u"CMD_CLI", u"F_SUB",
          u"N_F", u"Z_F", u"CARRY", u"V_ADD", u"V_SUB", u"ALU_R",
          u"LD_P", u"LD_P_E", u"REG_WR", u"OPs", u"Enable", u"Run"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DIAG_FLAGS START ===")
import scriptengine

WORK = os.path.join(BUILD, u"diagflags.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"diagflags.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
s = io.open(PROJ, "rb")
d = s.read()
s.close()
o = io.open(WORK, "wb")
o.write(d)
o.close()

proj = projects.open(WORK)
app = proj.active_application
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


def wr(expr, val):
    oa.set_prepared_value(expr, val)
    oa.write_prepared_values()


def rd(expr):
    v = u"%s" % oa.read_value(expr)
    try:
        if u"16#" in v:
            return int(v.split(u"16#")[-1], 16)
        if u"#" in v:
            return int(v.split(u"#")[-1])
        if v == u"TRUE":
            return 1
        if v == u"FALSE":
            return 0
        return int(v)
    except Exception:
        return u"?"


def dump(tag):
    log(u"%s" % tag)
    log(u"  " + u"  ".join(u"%s=%s" % (n, rd(u"GVL_CPU.%s" % n)) for n in FLAGIN))


try:
    wr(u"GVL_CPU.Run", u"FALSE")
    wr(u"GVL_CPU.Step_On", u"FALSE")
    wr(u"GVL_MEM.Mem[512]", u"16#A9")     # opcode LDA # (v pamyati na sluchay)
    wr(u"GVL_CPU.PC", u"16#0200")
    time.sleep(0.2)
    dump(u"после остановки (начальное P):")

    for val in (0x24, 0x00, 0xFF, 0x24):
        wr(u"GVL_CPU.P", u"16#%02X" % val)
        time.sleep(0.35)
        log(u"записали P=%02X ->" % val)
        dump(u"  состояние:")

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"ошибка: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== DIAG_FLAGS END ===")
try:
    system.exit()
except Exception:
    pass
