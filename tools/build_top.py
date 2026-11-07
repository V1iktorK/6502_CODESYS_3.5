# -*- coding: utf-8 -*-
"""
build_top.py -- POLNAYA SBORKA yadra 6502 iz proverennyh POU + kompilyaciya.

Poryadok importa -- po zavisimostyam. V kontse: sborka i sokhranenie
build/CPM6502_CPU.project.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "build_top.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from opcodes import BOOL_SIGNALS, BYTE_SIGNALS

ORDER = [
    u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
    u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"FB_WriteBack",
    u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
    u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
    u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",
    u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack", u"FB_CPU_AluFlags",
    u"FB_CPU_PcWb", u"FB_CPU_Core",
]

STATE = [(u"A", u"BYTE"), (u"X", u"BYTE"), (u"Y", u"BYTE"), (u"P", u"BYTE"),
         (u"SP", u"BYTE"), (u"PC", u"WORD")]
FETCHV = [(u"OP", u"BYTE"), (u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
          (u"PC1", u"WORD"), (u"PC2", u"WORD"), (u"PCL", u"BYTE"), (u"PCH", u"BYTE")]
ADDRV = [(u"C_IMM", u"WORD"), (u"C_ZP", u"WORD"), (u"C_ZPX", u"WORD"),
         (u"C_ZPY", u"WORD"), (u"C_ABS", u"WORD"), (u"C_ABX", u"WORD"),
         (u"C_ABY", u"WORD"), (u"C_IZX", u"WORD"), (u"C_IZY", u"WORD"),
         (u"C_IND", u"WORD"), (u"C_REL", u"WORD"), (u"C_STK", u"WORD"),
         (u"OFFW", u"WORD"), (u"YW", u"WORD"), (u"EFF", u"WORD"),
         (u"WDATA", u"BYTE"), (u"BRKV", u"WORD")]
ALUV = [(u"ALU_R", u"BYTE"), (u"CARRY", u"BOOL"), (u"V_ADD", u"BOOL"),
        (u"V_SUB", u"BOOL"), (u"N_F", u"BOOL"), (u"Z_F", u"BOOL"),
        (u"P_NEW", u"BYTE"), (u"FZ", u"BOOL"), (u"FC", u"BOOL"), (u"TAKE", u"BOOL")]
STKV = [(u"SPM1", u"BYTE"), (u"SPM2", u"BYTE"), (u"SPM3", u"BYTE"),
        (u"SPP1", u"BYTE"), (u"SPP2", u"BYTE"), (u"SPP3", u"BYTE"),
        (u"SP_NEW", u"BYTE"),
        (u"STK_A0", u"WORD"), (u"STK_A1", u"WORD"), (u"STK_A2", u"WORD"),
        (u"STK_A3", u"WORD"),
        (u"STK_R0", u"WORD"), (u"STK_R1", u"WORD"), (u"STK_R2", u"WORD"),
        (u"ADV", u"WORD"), (u"JRET", u"WORD"), (u"BACK", u"WORD"),
        (u"PULL_LO", u"BYTE")]
PCV = [(u"P_ADV", u"WORD"), (u"P_EFF", u"WORD"), (u"P_BACK", u"WORD"),
       (u"P_BRN", u"WORD"), (u"P_KEEP", u"WORD"), (u"P_JRET", u"WORD"),
       (u"P_BRK", u"WORD"), (u"PC_NEW", u"WORD")]
GATEV = [(u"LD_A_E", u"BOOL"), (u"LD_X_E", u"BOOL"), (u"LD_Y_E", u"BOOL"),
         (u"LD_P_E", u"BOOL"), (u"LD_SP_E", u"BOOL"), (u"WR_MEM_E", u"BOOL"),
         (u"Done", u"BOOL")]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def gvl_text():
    lines = [u"VAR_GLOBAL"]
    lines.append(u"\t(* --- регистры процессора --- *)")
    for n, t in STATE:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- выборка --- *)")
    for n, t in FETCHV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- дешифратор: сигналы --- *)")
    for n in BOOL_SIGNALS:
        lines.append(u"\t%s : BOOL;" % n)
    for n in BYTE_SIGNALS:
        lines.append(u"\t%s : BYTE;" % n)
    lines.append(u"\t(* --- адресация --- *)")
    for n, t in ADDRV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- АЛУ и флаги --- *)")
    for n, t in ALUV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- стек --- *)")
    for n, t in STKV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- программный счётчик --- *)")
    for n, t in PCV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"\t(* --- разрешения такта --- *)")
    for n, t in GATEV:
        lines.append(u"\t%s : %s;" % (n, t))
    lines.append(u"END_VAR")
    return u"\n".join(lines) + u"\n"


def main():
    f = io.open(LOG, "w", encoding="utf-8")
    f.write(u"")
    f.close()
    log(u"=== BUILD_TOP START ===")
    import scriptengine

    BASE = os.path.join(BUILD, u"btop.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"btop.project"):
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

    proj = app = None
    try:
        proj = projects.open(BASE)
        app = proj.active_application
        log(u"проект открыт")
    except Exception:
        log(traceback.format_exc())

    try:
        g2 = app.create_gvl(u"GVL_MEM")
        g2.textual_declaration.replace(
            u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
        g = app.create_gvl(u"GVL_CPU")
        g.textual_declaration.replace(gvl_text())
        log(u"GVL созданы (%d переменных в GVL_CPU)" %
            (len(STATE) + len(FETCHV) + len(BOOL_SIGNALS) + len(BYTE_SIGNALS) +
             len(ADDRV) + len(ALUV) + len(STKV) + len(PCV) + len(GATEV)))
    except Exception:
        log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

    def names():
        out = set()
        try:
            for ch in app.get_children():
                try:
                    out.add(ch.get_name())
                except Exception:
                    s = str(ch)
                    if u"Name=" in s:
                        out.add(s.split(u"Name=")[1].split(u",")[0])
        except Exception:
            pass
        return out

    log(u"")
    bad = []
    for name in ORDER:
        p = os.path.join(PLCOPEN, u"%s.xml" % name)
        if not os.path.exists(p):
            log(u"  %-16s НЕТ ФАЙЛА" % name)
            bad.append(name)
            continue
        exc = None
        try:
            app.import_xml(p, False)
        except Exception:
            exc = traceback.format_exc().strip().splitlines()[-1]
        ok = name in names()
        log(u"  %-16s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                                  (u"  (искл: %s)" % exc) if exc else u""))
        if not ok:
            bad.append(name)

    log(u"")
    log(u"--- сборка ---")
    try:
        app.build()
    except Exception:
        log(u"  исключение: %s" % traceback.format_exc().strip().splitlines()[-1])
    for c in system.get_message_categories():
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        for m in msgs:
            try:
                log(u"  %s" % (m,))
            except Exception:
                pass

    log(u"не создано POU: %d (%s)" % (len(bad), u", ".join(bad) if bad else u"нет"))
    if proj is not None and not bad:
        try:
            if not os.path.isdir(os.path.dirname(OUTPROJ)):
                os.makedirs(os.path.dirname(OUTPROJ))
            proj.save_as(OUTPROJ)
            log(u"проект сохранён: %s" % OUTPROJ)
        except Exception:
            log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

    log(u"=== BUILD_TOP END ===")
    try:
        proj.close()
    except Exception:
        pass
    try:
        system.exit()
    except Exception:
        pass


main()
