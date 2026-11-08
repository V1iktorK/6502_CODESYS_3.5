# -*- coding: utf-8 -*-
"""
diag_a.py -- pochemu A obnulyaetsya posle pervogo LDA.

Gruzim $0200: A9 42 (LDA #$42); $0202: 4C 02 02 (JMP $0202).
Posle starta i zapisi programmy snimaem sled po skanam: PC, Ops, LD_A_E,
REG_WR, ALU_R, A. Vidno, na kakom shage A stanovitsya 0.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "diag_a.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DIAG_A START ===")
import scriptengine

WORK = os.path.join(BUILD, u"diaga.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"diaga.project"):
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

writes = [(u"GVL_MEM.Mem[512]", u"16#A9"), (u"GVL_MEM.Mem[513]", u"16#42"),
          (u"GVL_MEM.Mem[514]", u"16#4C"), (u"GVL_MEM.Mem[515]", u"16#02"),
          (u"GVL_MEM.Mem[516]", u"16#02"),
          (u"GVL_MEM.Mem[65534]", u"16#00"), (u"GVL_MEM.Mem[65535]", u"16#02"),
          (u"GVL_CPU.PC", u"16#0200"), (u"GVL_CPU.SP", u"16#FF"),
          (u"GVL_CPU.A", u"16#00"), (u"GVL_CPU.X", u"16#00"),
          (u"GVL_CPU.Y", u"16#00"), (u"GVL_CPU.P", u"16#30")]
for nm, val in writes:
    try:
        oa.set_prepared_value(nm, val)
        oa.write_prepared_values()
    except Exception:
        log(u"  не записалось: %s" % nm)
log(u"программа записана")

import time
prev = None
for k in range(200):
    row = []
    for e in (u"GVL_CPU.PC", u"GVL_CPU.Ops", u"GVL_CPU.LD_A_E", u"GVL_CPU.REG_WR",
              u"GVL_CPU.ALU_R", u"GVL_CPU.A", u"GVL_CPU.PC_MODE",
              u"GVL_CPU.SRC", u"GVL_CPU.WRD0", u"GVL_CPU.WR0", u"GVL_CPU.WR_EN0"):
        try:
            row.append(u"%s" % oa.read_value(e))
        except Exception:
            row.append(u"?")
    cur = tuple(row)
    if cur != prev:
        log(u"  %3d: PC=%s OP=%s LDA_E=%s RWR=%s ALU=%s A=%s PCM=%s SRC=%s WRD0=%s WR0=%s WRE=%s"
            % ((k,) + cur))
        prev = cur
    time.sleep(0.01)

try:
    oa.stop()
    oa.logout()
except Exception:
    pass
try:
    proj.close()
except Exception:
    pass
log(u"=== DIAG_A END ===")
try:
    system.exit()
except Exception:
    pass
