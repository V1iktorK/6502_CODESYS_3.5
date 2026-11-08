# -*- coding: utf-8 -*-
"""test_wb.py -- izolirovannaya proverka FB_WriteBack: vybor istochnika SRC."""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fbd import Sheet, interface, pou_xml

LOG = os.path.join(ROOT, "log", "test_wb.log")
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
log(u"=== TEST_WB START ===")

s = Sheet(u"PLC_PRG: проверка выбора источника записи")
bid = s.blk(u"FB_WriteBack", [
    (u"SRC", s.const(u"GVL_CPU.TSRC", 0)),
    (u"A", s.const(u"BYTE#16#A5", 0)),
    (u"X", s.const(u"BYTE#16#5A", 0)),
    (u"Y", s.const(u"BYTE#16#3C", 0)),
    (u"P_NEW", s.const(u"BYTE#16#24", 0)),
    (u"ALU_R", s.const(u"BYTE#16#77", 0)),
    (u"PCL", s.const(u"BYTE#16#12", 0)),
    (u"PCH", s.const(u"BYTE#16#34", 0)),
    (u"PULL_LO", s.const(u"BYTE#16#99", 0)),
    (u"SP_NEW", s.const(u"BYTE#16#FD", 0)),
    (u"PC_NEW", s.const(u"WORD#16#0202", 0)),
    (u"Enable", s.const(u"TRUE", 0)),
    (u"LD_A_E", s.const(u"FALSE", 0)),
    (u"LD_X_E", s.const(u"FALSE", 0)),
    (u"LD_Y_E", s.const(u"FALSE", 0)),
    (u"LD_P_E", s.const(u"FALSE", 0)),
    (u"LD_SP_E", s.const(u"FALSE", 0))], 2, width=150, inst=u"Wb")
s.assign(u"GVL_CPU.REG_WR", bid, 6)
prg = pou_xml(u"PLC_PRG", u"program", interface(locals_=[(u"Wb", u"FB_WriteBack")]),
              [s], u"проверка выбора источника")
p = os.path.join(PLCOPEN, u"PRG_WB.xml")
with io.open(p, "wb") as fh:
    fh.write(prg.encode("utf-8"))

import scriptengine

BASE = os.path.join(BUILD, u"wb.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"wb.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
src = io.open(TPL, "rb")
data = src.read()
src.close()
dst = io.open(BASE, "wb")
dst.write(data)
dst.close()

proj = projects.open(BASE)
app = proj.active_application

GVL = (u"VAR_GLOBAL\n"
       u"\tTSRC : BYTE;\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
       u"\tP_NEW : BYTE;\n\tALU_R : BYTE;\n\tPCL : BYTE;\n\tPCH : BYTE;\n"
       u"\tPULL_LO : BYTE;\n\tSP_NEW : BYTE;\n\tPC_NEW : WORD;\n"
       u"\tREG_WR : BYTE;\n\tEnable : BOOL;\n"
       u"END_VAR\n")
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(GVL)
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    app.import_xml(os.path.join(PLCOPEN, u"FB_WriteBack.xml"), False)
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
                log(u"  !! %s" % t[:150])
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
            return int(v)
        except Exception:
            return -1

    exp = {0: 0xA5, 1: 0x5A, 2: 0x3C, 3: 0x24, 4: 0x77, 5: 0x12, 6: 0x34, 7: 0x99}
    for k in sorted(exp):
        wr(u"GVL_CPU.TSRC", u"16#%02X" % k)
        time.sleep(0.25)
        got = rd(u"GVL_CPU.REG_WR")
        log(u"  SRC=%d -> REG_WR=%02X (ожид %02X) %s"
            % (k, got & 0xFF, exp[k], u"PASS" if (got & 0xFF) == exp[k] else u"FAIL"))
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
log(u"=== TEST_WB END ===")
try:
    system.exit()
except Exception:
    pass
