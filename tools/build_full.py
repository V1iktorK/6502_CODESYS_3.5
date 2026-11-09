# -*- coding: utf-8 -*-
"""
build_full.py -- polnaya sborka s realnoy proverkoу kompilyacii.

Otlичия ot build_top:
  * posle importa vseh POU programa PLC_PRG (pustaya ST iz shablona) udalyaetsya
    i na ee mesto importiruetsya FBD-programma PLC_PRG s ekzemplyarom FB_CPU_Core;
  * tolko teper kompilyator proveryaet vse shemy gluboko (est vyzov yadra);
  * soobshcheniya filtruyutsya: shum TargetVars ('не имеет действия') skryvaem,
    oshibki vidny polnostyu.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "build_full.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from opcodes import BOOL_SIGNALS, BYTE_SIGNALS, build_effects

ORDER = [
    u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
    u"FB_Fetch", u"FB_FetchOp", u"FB_Decoder6502", u"FB_ALU6502",
    u"SL_VSEL", u"SL_NZF", u"SL_CARRY", u"SL_PREP", u"SL_STDATA", u"SL_REGSEL", u"SL_SNAPSHOT", u"SL_FLG_N", u"SL_FLG_Z", u"SL_FLG_C", u"SL_FLG_V", u"SL_FLG_I",
    u"SL_FLG_B", u"SL_FLG5", u"FB_WriteBack",
    u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
    u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
    u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",
    u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack", u"FB_CPU_AluFlags",
    u"FB_CPU_PcWb", u"FB_CPU_Store", u"FB_CPU_Flags", u"FB_Latch", u"FB_RegFile", u"FB_CPU_Core",
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
        (u"V_SUB", u"BOOL"), (u"N_F", u"BOOL"), (u"Z_F", u"BOOL"), (u"N_F2", u"BOOL"), (u"Z_F2", u"BOOL"),
        (u"P_NEW", u"BYTE"), (u"FZ", u"BOOL"), (u"FC", u"BOOL"), (u"TAKE", u"BOOL"),
        # P_WORK -- рабочая копия регистра P, которую по одному биту правят
        # ступени SL_FLG_*; VSEL -- выбранный источник флага V
        (u"P_WORK", u"BYTE"), (u"VSEL", u"BOOL"),
        # ALU_AX/ALU_BX/ALU_CIN -- operandы АЛУ наружу (для ступени SL_CARRY);
        # CARRY1/CARRY2 больше не используются
        (u"ALU_AX", u"BYTE"), (u"ALU_BX", u"BYTE"), (u"ALU_CIN", u"BOOL"),
        # снимок последнего такта (панель и диагностика)
        (u"LAST_OPs", u"BYTE"), (u"LAST_SP_MODE", u"BYTE"), (u"LAST_SRC", u"BYTE"),
        (u"LAST_IS_JSR", u"BOOL"), (u"LAST_REG_WR", u"BYTE"), (u"LAST_WRD0", u"BYTE"),
        (u"LAST_WR0", u"WORD"), (u"LAST_WR_EN0", u"BOOL"), (u"LAST_EFF", u"WORD"),
        (u"LAST_P_NEW", u"BYTE"), (u"LAST_ALU_R", u"BYTE"), (u"LAST_PC", u"WORD"),
        (u"LAST_A", u"BYTE"), (u"LAST_X", u"BYTE"), (u"LAST_Y", u"BYTE"), (u"LAST_SP", u"BYTE"),
        # история на один такт назад (после парковки JMP именно здесь
        # лежат сигналы тестируемой команды)
        (u"PREV_OPs", u"BYTE"), (u"PREV_SP_MODE", u"BYTE"), (u"PREV_SRC", u"BYTE"),
        (u"PREV_IS_JSR", u"BOOL"), (u"PREV_REG_WR", u"BYTE"), (u"PREV_WRD0", u"BYTE"),
        (u"PREV_WR0", u"WORD"), (u"PREV_WR_EN0", u"BOOL"), (u"PREV_EFF", u"WORD"),
        (u"PREV_P_NEW", u"BYTE"), (u"PREV_ALU_R", u"BYTE"), (u"PREV_PC", u"WORD"),
        (u"WRS0", u"BOOL"), (u"WRS1", u"BOOL"), (u"WRS2", u"BOOL"),
        (u"RD_ADR", u"WORD"), (u"RD_VAL", u"BYTE"),
        (u"PREV_A", u"BYTE"), (u"PREV_X", u"BYTE"), (u"PREV_Y", u"BYTE"), (u"PREV_SP", u"BYTE")]
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
         (u"Enable", u"BOOL"), (u"Done", u"BOOL"),
         (u"OPs", u"BYTE"), (u"REG_WR", u"BYTE"), (u"BRN_TGT", u"WORD"),
         (u"ISUB", u"BOOL"), (u"FN", u"BOOL"), (u"FV", u"BOOL"), (u"FB", u"BOOL"),
         (u"FD", u"BOOL"), (u"FI", u"BOOL"),
         (u"WR0", u"WORD"), (u"WR1", u"WORD"), (u"WR2", u"WORD"),
         (u"WRD0", u"BYTE"), (u"WRD1", u"BYTE"), (u"STK_D0", u"BYTE"), (u"WRD2", u"BYTE"),
         (u"WR_EN0", u"BOOL"), (u"WR_EN1", u"BOOL"), (u"WR_EN2", u"BOOL"),
         (u"Chain1", u"BOOL"), (u"Chain2", u"BOOL"), (u"Chain3", u"BOOL"), (u"Chain4", u"BOOL"),
         (u"Chain5", u"BOOL"), (u"Chain6", u"BOOL"), (u"Chain7", u"BOOL"), (u"Chain8", u"BOOL"), (u"Chain9", u"BOOL"), (u"Chain10", u"BOOL"), (u"Chain11", u"BOOL"), (u"Chain12", u"BOOL"), (u"Chain13", u"BOOL"), (u"Chain14", u"BOOL")]


def table_text():
    """GVL_TABLE: tablicy dekodirovaniya (kod operacii -> signal). Eto dannye,
    initsializiruemye v obyavlenii GVL, a ne logika: bazovye bitovye signaly
    deshifrator schitaet shemoy, a bajtovye -- chteniem tablicy."""
    out = [u"VAR_GLOBAL", u"\t(* таблицы декодирования: код операции -> сигнал *)"]
    for sig in BYTE_SIGNALS:
        vals = [int(EFF.get(opc, {}).get(sig, 0)) for opc in range(256)]
        out.append(u"\t%s : ARRAY[0..255] OF BYTE := [%s];"
                   % (sig, u", ".join(u"%d" % v for v in vals)))
    out.append(u"END_VAR")
    return u"\n".join(out) + u"\n"


def gvl_text():
    out = [u"VAR_GLOBAL", u"\t(* --- регистры --- *)"]
    for n, t in STATE:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- выборка --- *)")
    for n, t in FETCHV:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- сигналы дешифратора --- *)")
    for n in BOOL_SIGNALS:
        out.append(u"\t%s : BOOL;" % n)
    for n in BYTE_SIGNALS:
        out.append(u"\t%s : BYTE;" % n)
    out.append(u"\t(* --- адресация --- *)")
    for n, t in ADDRV:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- АЛУ и флаги --- *)")
    for n, t in ALUV:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- стек --- *)")
    for n, t in STKV:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- PC --- *)")
    for n, t in PCV:
        out.append(u"\t%s : %s;" % (n, t))
    out.append(u"\t(* --- разрешения такта --- *)")
    for n, t in GATEV:
        out.append(u"\t%s : %s;" % (n, t))
    # Пульт процессора. Run=FALSE по умолчанию: ядро стартует ОСТАНОВЛЕННЫМ,
    # иначе до первого нажатия «Пуск» оно успевает выполнить мусор по адресу
    # сброса и, например, защёлкнуть бит B в регистре P. Пуск -- оператором
    # (HMI) или тестом (GVL_CPU.Run := TRUE + пошаговые импульсы).
    out.append(u"\t(* --- пульт --- *)")
    out.append(u"\tRun : BOOL := FALSE;")
    out.append(u"\tStep_On : BOOL;")
    out.append(u"\tStep_Pulse : BOOL;")
    out.append(u"\tStep_Taken : BOOL;")
    out.append(u"\tInsts : UDINT;")
    out.append(u"END_VAR")
    return u"\n".join(out) + u"\n"

EFF = build_effects()

NOISE = (u"не имеет действия", u"TargetVars.", u"Более 100 предупреждений",
         u"CmpTargetVisu", u"0 ошибки", u"Доп. проверки кода завершены")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def main():
    f = io.open(LOG, "w", encoding="utf-8")
    f.write(u"")
    f.close()
    log(u"=== BUILD_FULL START ===")
    import scriptengine

    BASE = os.path.join(BUILD, u"bfull.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"bfull.project"):
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
    log(u"проект открыт")

    g2 = app.create_gvl(u"GVL_MEM")
    g2.textual_declaration.replace(
        u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(gvl_text())
    gt = app.create_gvl(u"GVL_TABLE")
    gt.textual_declaration.replace(table_text())
    log(u"GVL созданы (GVL_CPU, GVL_TABLE)")

    # FB_MemStore -- ЕДИНСТВЕННАЯ ПОУ на ST в проекте: один оператор записи в
    # эмулируемую RAM. Вынужденное отступление, см. docs/09_БЛОКЕР_ЗАПИСЬ_В_ПАМЯТЬ.md
    try:
        mp = app.create_pou(u"FB_MemStore", PouType.FunctionBlock)
        mp0 = mp; mp.textual_declaration.replace(
            u"FUNCTION_BLOCK FB_MemStore\nVAR_INPUT\n\tAddr : WORD;\n\tData : BYTE;\n\tEn : BOOL;\nEND_VAR\nVAR\n\tpB : POINTER TO BYTE;\n\tpC : POINTER TO BYTE;\n\tInit : BOOL;\nEND_VAR\n"
            u"VAR_OUTPUT\n\tOUT : BOOL;\nEND_VAR")
        mp.textual_implementation.replace(
            u"IF NOT Init THEN\n\tpB := ADR(GVL_MEM.Mem[0]);\n\tInit := TRUE;\nEND_IF\nIF En THEN\n\tpC := pB + Addr;\n\tpC^ := Data;\nEND_IF\nGVL_CPU.RD_VAL := GVL_MEM.Mem[GVL_CPU.RD_ADR];\nOUT := TRUE;")
        log(u"FB_MemStore создана (ST, один оператор записи в RAM)")
        log(u"  декларация: [%s]" % u" | ".join(mp.textual_declaration.text.splitlines()))
        log(u"  реализация: [%s]" % u" | ".join(mp.textual_implementation.text.splitlines()))
    except Exception:
        log(u"FB_MemStore: %s" % traceback.format_exc().strip().splitlines()[-1])

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

    log(u"")
    bad = []
    for name in ORDER:
        p = os.path.join(PLCOPEN, u"%s.xml" % name)
        if not os.path.exists(p):
            log(u"  %-16s НЕТ ФАЙЛА" % name)
            bad.append(name)
            continue
        try:
            app.import_xml(p, False)
        except Exception:
            log(u"  %-16s ИСКЛЮЧЕНИЕ" % name)
            bad.append(name)
            continue
        log(u"  импорт %s — ок" % name)
        if name not in names():
            log(u"  %-16s НЕ СОЗДАН" % name)
            bad.append(name)
    log(u"импортировано POU: %d из %d" % (len(ORDER) - len(bad), len(ORDER)))

    # ---------------- диагностика: как CODESYS понял декларации
    log(u"")
    log(u"--- декларации после импорта ---")
    for nm in (u"FB_WriteBack", u"FB_ALU6502", u"SL_STK2"):
        try:
            found = None
            for o in (app.find(nm, True) or []):
                try:
                    if o.textual_declaration is not None and o.textual_declaration.text:
                        found = o.textual_declaration.text
                        break
                except Exception:
                    continue
            if found:
                log(u"  [%s] %s" % (nm, found.replace(u"\n", u" | ")[:600]))
            else:
                log(u"  [%s] декларация недоступна" % nm)
        except Exception:
            log(u"  [%s] ошибка чтения" % nm)

    # ---------------- точка входа
    log(u"")
    log(u"--- точка входа ---")
    try:
        prg = None
        for o in (app.find(u"PLC_PRG", True) or []):
            try:
                if o.textual_declaration is not None and o.textual_declaration.text:
                    prg = o
                    break
            except Exception:
                continue
        if prg is not None:
            prg.remove()
            log(u"  пустая ST-программа PLC_PRG удалена")
        app.import_xml(os.path.join(PLCOPEN, u"PRG_PLC.xml"), False)
        log(u"  FBD-программа PLC_PRG импортирована")
    except Exception:
        log(u"  ОШИБКА: %s" % traceback.format_exc())

    # ---------------- сборка
    log(u"")
    log(u"--- сборка ---")
    try:
        app.build()
    except Exception:
        pass
    errs, warns, info = [], [], []
    for c in system.get_message_categories():
        try:
            for m in system.get_messages(c):
                try:
                    t = u"%s" % (m,)
                except Exception:
                    continue
                if any(x in t for x in NOISE):
                    continue
                low = t.lower()
                if u"ошибк" in low or u"требуется" in low or u"недопустим" in low \
                        or u"неизвестн" in low or u"уже задана" in low or u"не задан" in low \
                        or u"невозможно конвертировать" in low:
                    errs.append(t)
                elif u"завершена" in low or u"завершены" in low or u"типизировать" in low:
                    info.append(t)
                else:
                    warns.append(t)
        except Exception:
            pass
    for t in info:
        log(u"  %s" % t)
    log(u"  ВСЕГО подозрительных строк: %d" % len(errs))
    for t in errs:
        log(u"  !! %s" % t)
    log(u"  прочих предупреждений (без шума TargetVars): %d" % len(warns))
    for t in warns:
        log(u"     %s" % t)

    ok = (not bad) and (not errs)
    log(u"")
    log(u"ИТОГ: POU %d/%d, ошибок %d -> %s" %
        (len(ORDER) - len(bad), len(ORDER), len(errs), u"ГОТОВО" if ok else u"НЕ ГОТОВО"))
    if ok:
        try:
            proj.save_as(OUTPROJ)
            log(u"проект сохранён: %s" % OUTPROJ)
        except Exception:
            log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

    log(u"=== BUILD_FULL END ===")
    try:
        proj.close()
    except Exception:
        pass
    try:
        system.exit()
    except Exception:
        pass


main()
