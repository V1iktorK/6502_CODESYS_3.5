# -*- coding: utf-8 -*-
"""
diag_step.py -- poshagovyy razbor odnoy komandy s polnym daмпom signalov.

Rezhim: GVL_CPU.Run=TRUE, GVL_CPU.Step_On=TRUE. Kogda Step_On=TRUE, yadro
razreshaet takt tolko po impulsu Step_Pulse i tolko odin raz (zashchelka
STaken v FB_CPU_Core), poetomu kazhdyy impuls = rovno odna komanda MOS 6502.

Programma: $0200: A9 42  (LDA #$42);  $0202: 4C 02 02 (parkovka)

Dlya kazhdogo shaga pechataem: PC, OPs, OP1, LEN, ADDR_MODE, SRC, EFF, WDATA,
ALU_R, LD_A, LD_A_E, REG_WR, A, P, P_NEW.
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "diag_step.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

WATCH = [u"PC", u"OPs", u"OP1", u"OP2", u"PC1", u"PC2", u"LEN", u"ADDR_MODE",
         u"SRC", u"EFF", u"WDATA", u"ALU_R", u"LD_A", u"LD_A_E", u"REG_WR",
         u"A", u"X", u"Y", u"P", u"P_NEW", u"SP", u"PC_NEW"]

# Отдельно смотрим булевы сигналы дешифратора: именно они решают, какие
# регистры и флаги пишутся. Если здесь мусор -- регистры/флаги поедут.
SIG = [u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM",
       u"USE_CARRY", u"CIN_FORCE", u"SET_NZ", u"SET_C", u"SET_V",
       u"CMD_CLC", u"CMD_SEC", u"HALT", u"F_ADD", u"F_SUB", u"F_CMP",
       u"IS_JSR", u"IS_RTS", u"CMD_SEI", u"CMD_CLI", u"SET_B"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def hax(v):
    try:
        return u"%04X" % int(v)
    except Exception:
        return u"%s" % v


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== DIAG_STEP START ===")
import scriptengine

WORK = os.path.join(BUILD, u"diagstep.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"diagstep.project"):
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


def wrb(a, v):
    wr(u"GVL_MEM.Mem[%d]" % a, u"16#%02X" % (v & 0xFF))


def snap():
    core = u"  ".join(u"%s=%s" % (n, hax(rd(u"GVL_CPU.%s" % n))) for n in WATCH)
    on = [n for n in SIG if rd(u"GVL_CPU.%s" % n) == 1]
    return core + u"\n     сигналы=1: " + (u", ".join(on) or u"(нет)")


def step():
    wr(u"GVL_CPU.Step_Pulse", u"TRUE")
    time.sleep(0.12)
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    time.sleep(0.08)


try:
    wr(u"GVL_CPU.Run", u"TRUE")
    wr(u"GVL_CPU.Step_On", u"TRUE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    # программа и состояние
    for i, b in enumerate((0xA9, 0x42, 0x4C, 0x02, 0x02)):
        wrb(0x0200 + i, b)
    wrb(0x10, 0x5A)
    wr(u"GVL_CPU.A", u"16#11")
    wr(u"GVL_CPU.X", u"16#22")
    wr(u"GVL_CPU.Y", u"16#33")
    wr(u"GVL_CPU.P", u"16#24")
    wr(u"GVL_CPU.SP", u"16#FD")
    wr(u"GVL_CPU.PC", u"16#0200")
    time.sleep(0.2)

    log(u"после загрузки:")
    log(snap())
    log(u"контроль загрузки: A=%s P=%s PC=%s (ждали 11/24/0200)"
        % (hax(rd(u"GVL_CPU.A")), hax(rd(u"GVL_CPU.P")), hax(rd(u"GVL_CPU.PC"))))

    for k in range(4):
        step()
        log(u"шаг %d:" % (k + 1))
        log(snap())

    wr(u"GVL_CPU.Step_On", u"FALSE")
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
log(u"=== DIAG_STEP END ===")
try:
    system.exit()
except Exception:
    pass
