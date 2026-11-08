# -*- coding: utf-8 -*-
"""
test_alu2.py -- izolirovannaya proverka PERENOSA v FB_ALU6502.

Vopros: pochemu v sostave yadra C=1 ne stavitsya (ADC/SBC/CMP).
Zdes POU podklyuchaetsya napryamую: vhody -- konstanty, vyhody -- v GVL.

Keysy (SBC umeet F_SUB, poetoму ispolzuem ego):
  A=$01, M=$01, C=1 -> R=$00, CARRY=1  (x - x = 0 bez zaima)
  A=$80, M=$80, C=1 -> R=$00, CARRY=1
  A=$FF, M=$00, C=1 -> R=$00, CARRY=1
  A=$00, M=$01, C=1 -> R=$FF, CARRY=0  (zaim)
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_alu2.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_ALU2 START ===")

# program: odin ekzemplyar ALU s vhodami-konstantami
s = Sheet(u"PLC_PRG: proverka perenosa")
bid = s.blk(u"FB_ALU6502", [
    (u"A", s.const(u"GVL_CPU.TA", 0)),
    (u"X", s.const(u"BYTE#0", 0)),
    (u"P", s.const(u"GVL_CPU.TP", 0)),
    (u"WDATA", s.const(u"GVL_CPU.TM", 0)),
    (u"ALU_A", s.const(u"BYTE#0", 0)),
    (u"ALU_B", s.const(u"BYTE#0", 0)),
    (u"F_SUB", s.const(u"TRUE", 0)),
    (u"F_CMP", s.const(u"FALSE", 0)),
    (u"USE_CARRY", s.const(u"TRUE", 0))], 2, width=150, inst=u"Alu")
s.assign(u"GVL_CPU.Chain1", bid, 4)
prg = pou_xml(u"PLC_PRG", u"program", interface(locals_=[(u"Alu", u"FB_ALU6502")]),
              [s], u"проверка переноса")
p = os.path.join(PLCOPEN, u"PRG_ALU2.xml")
with io.open(p, "wb") as fh:
    fh.write(prg.encode("utf-8"))
log(u"PRG_ALU2: %d байт" % os.path.getsize(p))

import scriptengine

BASE = os.path.join(BUILD, u"alu2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"alu2.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(TPL, "rb")
_d = _s.read()
_s.close()
_o = io.open(BASE, "wb")
_o.write(_d)
_o.close()

proj = projects.open(BASE)
app = proj.active_application

GVL = (u"VAR_GLOBAL\n"
       u"\tTA : BYTE;\n\tTM : BYTE;\n\tTP : BYTE;\n"
       u"\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
       u"\tWDATA : BYTE;\n\tALU_R : BYTE;\n\tCARRY : BOOL;\n"
       u"\tV_ADD : BOOL;\n\tV_SUB : BOOL;\n\tN_F : BOOL;\n\tZ_F : BOOL;\n"
       u"\tF_ADD : BOOL;\n\tF_SUB : BOOL;\n\tF_CMP : BOOL;\n\tUSE_CARRY : BOOL;\n\tCIN_FORCE : BOOL;\n\tChain1 : BOOL;\n"
       u"END_VAR\n")
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(GVL)
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.import_xml(os.path.join(PLCOPEN, u"FB_ALU6502.xml"), False)
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                break
        except Exception:
            continue
    app.import_xml(p, False)
except Exception:
    log(u"импорт: %s" % traceback.format_exc().strip().splitlines()[-1])

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
            low = t.lower()
            if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) and u"0 ошибки" not in t:
                errs += 1
                log(u"  !! %s" % t)
    except Exception:
        pass
log(u"ошибок компиляции: %d" % errs)

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

    def wr(e, v):
        oa.set_prepared_value(e, v)
        oa.write_prepared_values()

    def rd(e):
        try:
            v = u"%s" % oa.read_value(e)
        except Exception:
            return -1
        try:
            if u"16#" in v:
                return int(v.split(u"16#")[-1], 16)
            if u"#" in v:
                return int(v.split(u"#")[-1])
            return 1 if v == u"TRUE" else (0 if v == u"FALSE" else int(v))
        except Exception:
            return -1

    CASES = [(0x01, 0x01, 0x00, 0x01),    # A=01 M=01 -> R=00, C=1
             (0x80, 0x80, 0x00, 0x01),
             (0xFF, 0x00, 0x00, 0x01),
             (0x00, 0x01, 0x00, 0xFF)]
    for a, m, c_in, r_exp in CASES:
        wr(u"GVL_CPU.TA", u"16#%02X" % a)
        wr(u"GVL_CPU.TM", u"16#%02X" % m)
        wr(u"GVL_CPU.TP", u"16#%02X" % (0x24 | (0x01 if c_in else 0x00)))
        time.sleep(0.3)
        r = rd(u"GVL_CPU.ALU_R")
        cy = rd(u"GVL_CPU.CARRY")
        log(u"  A=%02X M=%02X C=%d -> R=%02X (ожид %02X) CARRY=%d"
            % (a, m, c_in, r & 0xFF, r_exp, cy))
    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass
except Exception:
    log(u"онлайн: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== TEST_ALU2 END ===")
try:
    system.exit()
except Exception:
    pass
