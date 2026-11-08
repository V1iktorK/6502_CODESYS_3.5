# -*- coding: utf-8 -*-
"""
diag_batch.py -- paketnaya diagnostika neskolkih komand za ODIN progon CODESYS.

Dlya kazhdogo keysa: zagruzhaem sostoyanie i programmu (v konce HLT), daem
yadru svobodno otrabotat i pechataem POLNYY snimok vnutrennih signalov:
chto deshifrirovalos, kakoy effektivnyy adres, chto prishlo v WDATA, chto
poluchilos v ALU i chto zapisalos v registry i P.

Eto pozvolyaet ispravlyat srazu gruppu oshibok, a ne po odnoy.
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "diag_batch.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

SIG = [u"PC", u"OPs", u"OP1", u"OP2", u"LEN", u"ADDR_MODE", u"SRC",
       u"EFF", u"WDATA", u"ALU_A", u"ALU_B", u"ALU_R", u"CARRY",
       u"N_F2", u"Z_F2", u"V_SUB", u"REG_WR", u"P_NEW", u"P_WORK",
       u"A", u"X", u"Y", u"P", u"SP", u"LD_A", u"LD_X", u"LD_Y",
       u"LD_A_E", u"LD_X_E", u"LD_Y_E", u"SET_NZ", u"SET_C",
       u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ABS", u"C_ABX", u"C_ABY",
       u"C_IZX", u"C_IZY", u"P_EFF", u"ADV", u"WR_MEM_E",
       u"SP_MODE", u"IS_JSR", u"WRD0", u"STK_D0", u"STK_A0", u"WR0",
       u"PCL", u"PCH", u"WR_EN0"]

# (imya, bayty, A, X, Y, P, pre[(adres,znachenie)])
CASES = [
    (u"PHA", [0x48], 0xA5, 0x22, 0x33, 0x24, []),
    (u"PHP", [0x08], 0x11, 0x22, 0x33, 0x24, []),
    (u"JSR", [0x20, 0x60, 0x02], 0x11, 0x22, 0x33, 0x24, [(0x0260, 0x02)]),
    (u"ADC C=1", [0x69, 0x01], 0x00, 0x22, 0x33, 0x25, []),
]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DIAG_BATCH START ===")
import scriptengine

WORK = os.path.join(BUILD, u"diagbatch.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"diagbatch.project"):
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
    try:
        v = u"%s" % oa.read_value(expr)
    except Exception:
        return -1
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
        return -1


def wrb(a, v):
    wr(u"GVL_MEM.Mem[%d]" % a, u"16#%02X" % (v & 0xFF))


try:
    wr(u"GVL_CPU.Run", u"FALSE")
    wr(u"GVL_CPU.Step_On", u"FALSE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    time.sleep(0.2)

    for name, code, a, x, y, p, pre in CASES:
        wr(u"GVL_CPU.Run", u"FALSE")
        for addr, val in pre:
            wrb(addr, val)
        code = list(code) + [0x02]          # HLT v konce
        for i, b in enumerate(code):
            wrb(0x0200 + i, b)
        want = [(u"GVL_CPU.A", u"16#%02X", a), (u"GVL_CPU.X", u"16#%02X", x),
                (u"GVL_CPU.Y", u"16#%02X", y), (u"GVL_CPU.P", u"16#%02X", p),
                (u"GVL_CPU.SP", u"16#%02X", 0xFD), (u"GVL_CPU.PC", u"16#%04X", 0x200)]
        for _ in range(30):
            off = [k for k, _f, v in want if rd(k) != v]
            if not off:
                break
            for k, fmt, v in want:
                if k in off:
                    wr(k, fmt % v)
            time.sleep(0.02)
        wr(u"GVL_CPU.Run", u"TRUE")
        prev = None
        for _ in range(60):
            time.sleep(0.02)
            pc = rd(u"GVL_CPU.PC")
            if pc == prev:
                break
            prev = pc
        wr(u"GVL_CPU.Run", u"FALSE")
        log(u"--- %s" % name)
        parts = []
        for n in SIG:
            v = rd(u"GVL_CPU.%s" % n)
            try:
                parts.append(u"%s=%02X" % (n, int(v) & 0xFF))
            except Exception:
                parts.append(u"%s=?" % n)
        log(u"  " + u" ".join(parts))
        m10 = rd(u"GVL_MEM.Mem[16]")
        m300 = rd(u"GVL_MEM.Mem[768]")
        log(u"  Mem[0010]=%s Mem[0300]=%s" % (m10, m300))

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"ошибка: %s" % traceback.format_exc())

try:
    proj.close()
except Exception:
    pass
log(u"=== DIAG_BATCH END ===")
try:
    system.exit()
except Exception:
    pass
