# -*- coding: utf-8 -*-
"""
gen_top3.py -- KOMPOZICIYA YADRA 6502 (stupeni pishut v GVL_CPU).

Zamena gen_top2.py (tot povredilsya pri pravke). Vse stupeni
(FB_Fetch, FB_Decoder6502, FB_ALU6502, FB_Flags, FB_WriteBack, SL_*)
zapisyvayut rezultaty PRYAMO v GVL_CPU i ne imeyut vyhodnyh kontaktov,
poetomu kompoziciya -- tolko vyzovy s vhodnymi kontaktami.

  FB_CPU_Addr1      A1..A7: SL_C1A, SL_C1B, SL_YW, SL_IND2, SL_INDP,
                           SL_RELA, SL_RELC, SL_BRK
  FB_CPU_Select     Pick (SL_SELECT12), Wd (SL_WDATA2)
  FB_CPU_Stack      St1..St4, SpSel, Adv, Jr
  FB_CPU_AluFlags   Alu, Flg, Br
  FB_CPU_PcWb       Bt, Ps, Wb + zapis registrov A/X/Y/P/SP/PC
  FB_CPU_Core       Fch, Dec + S1..S5
  PLC_PRG           Core(Enable := TRUE)
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml
import gen_cpu_split as G

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
CPU = G.CPU

CAND12 = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX",
          u"C_ABY", u"C_IZX", u"C_IZY", u"C_IND", u"C_REL", u"C_STK"]
PC_CAND = [u"P_ADV", u"P_EFF", u"P_BACK", u"P_BRN", u"P_KEEP", u"P_JRET", u"P_BRK"]


def R(s, name, col=0):
    """Чтение GVL_CPU.<name>."""
    return s.ref(CPU + u"." + name, col)


def W(s, name, src, col):
    """Запись GVL_CPU.<name>."""
    s.assign(CPU + u"." + name, src, col)


def call(s, typ, inst, pins, col, w=140):
    """Вызов ступени/слоя. Выход OUT сразу читается в GVL_CPU.Chain1.

    Чтение обязательно: CODESYS исполняет тело вызываемого ПОУ только тогда,
    когда вызов что-то отдаёт (правило 3 конспекта). Без него ALU_R = 0.
    """
    bid = s.blk(typ, pins, col, width=w, inst=inst)
    s.assign(u"GVL_CPU.Chain1", bid, col + 1)
    return bid


def pouloc(*args):
    it = iter(args)
    return list(zip(it, it))


def fb_addr1():
    s = Sheet(u"FB_CPU_Addr1: кандидаты адресов")
    call(s, u"SL_C1A", u"A1",
         [(u"OP1", R(s, u"OP1")), (u"X", R(s, u"X")), (u"Y", R(s, u"Y")),
          (u"PCs", R(s, u"PC"))], 1)
    call(s, u"SL_C1B", u"A2",
         [(u"OP1", R(s, u"OP1")), (u"OP2", R(s, u"OP2")),
          (u"X", R(s, u"X")), (u"Y", R(s, u"Y"))], 3)
    call(s, u"SL_YW", u"YW1", [(u"Y", R(s, u"Y"))], 5, w=90)
    call(s, u"SL_IND2", u"A3",
         [(u"OP1", R(s, u"OP1")), (u"X", R(s, u"X")), (u"Y", R(s, u"Y")),
          (u"YW", R(s, u"YW"))], 6)
    call(s, u"SL_INDP", u"A4", [(u"PTR", R(s, u"C_ABS"))], 8, w=100)
    call(s, u"SL_RELA", u"A5", [(u"OP1", R(s, u"OP1"))], 9, w=100)
    call(s, u"SL_RELC", u"A6",
         [(u"OFFW", R(s, u"OFFW")), (u"PC2", R(s, u"PC2"))], 10)
    call(s, u"SL_BRK", u"A7", [], 12, w=100)
    W(s, u"C_STK", R(s, u"C_ABS"), 13)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_select():
    s = Sheet(u"FB_CPU_Select: эффективный адрес и операнд")
    call(s, u"SL_SELECT12", u"Pick",
         [(u"ADDR_MODE", R(s, u"ADDR_MODE"))] +
         [(n, R(s, n)) for n in CAND12], 1, w=160)
    call(s, u"SL_WDATA2", u"Wd",
         [(u"ADDR_MODE", R(s, u"ADDR_MODE")), (u"EFF", R(s, u"EFF")),
          (u"OP1", R(s, u"OP1"))], 3, w=120)
    # (SL_WDATA2 dlya imm bеret OP1 -- sm. shapku modulya)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_stack():
    s = Sheet(u"FB_CPU_Stack: указатель стека и его адреса")
    call(s, u"SL_STK1", u"St1", [(u"SP", R(s, u"SP"))], 1, w=100)
    call(s, u"SL_STK3", u"St3", [(u"SP", R(s, u"SP"))], 2, w=100)
    call(s, u"SL_STK2", u"St2",
         [(u"SP", R(s, u"SP")), (u"SPM1", R(s, u"SPM1")), (u"SPP1", R(s, u"SPP1")),
          (u"SPP2", R(s, u"SPP2")), (u"SPP3", R(s, u"SPP3"))], 3)
    call(s, u"SL_STK4", u"St4", [(u"SPM2", R(s, u"SPM2"))], 5, w=100)
    call(s, u"SL_SPSEL", u"SpSel",
         [(u"SP_MODE", R(s, u"SP_MODE")), (u"S_KEEP", R(s, u"SP")),
          (u"S_P1", R(s, u"SPM1")), (u"S_M1", R(s, u"SPP1")),
          (u"S_M3", R(s, u"SPM3")), (u"S_P3", R(s, u"SPP3"))], 6, w=150)
    call(s, u"SL_ADV", u"Adv",
         [(u"PCs", R(s, u"PC")), (u"LEN", R(s, u"LEN"))], 8, w=100)
    call(s, u"SL_JRET", u"Jr",
         [(u"STK_R0", R(s, u"STK_R0")), (u"STK_R1", R(s, u"STK_R1"))], 9, w=110)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_aluflags():
    s = Sheet(u"FB_CPU_AluFlags: АЛУ и регистр признаков")
    call(s, u"FB_ALU6502", u"Alu",
         [(u"A", R(s, u"A")), (u"X", R(s, u"X")), (u"P", R(s, u"P")),
          (u"WDATA", R(s, u"WDATA")), (u"ALU_A", R(s, u"ALU_A")),
          (u"ALU_B", R(s, u"ALU_B")), (u"F_SUB", R(s, u"F_SUB")),
          (u"F_CMP", R(s, u"F_CMP")), (u"USE_CARRY", R(s, u"USE_CARRY"))],
         1, w=140)
    # Регистр P собирается КОНВЕЙЕРОМ ступеней через GVL_CPU.P_WORK:
    # по одному биту за ступень. Так каждое «изменить бит» читает только
    # входную переменную, и fan-out не размножает цепочку (см. gen_flags.py).
    # Стартовое значение P_WORK := P пишет сама первая ступень -- запись и
    # чтение одной ячейки внутри одного ПОУ дают старое значение (правило 2.5).
    call(s, u"SL_VSEL", u"Vsl", [], 1, w=110)
    call(s, u"SL_FLG_N", u"Fn", [(u"SET_NZ", R(s, u"SET_NZ")),
                                 (u"N_F", R(s, u"N_F"))], 2, w=110)
    call(s, u"SL_FLG_Z", u"Fz", [(u"SET_NZ", R(s, u"SET_NZ")),
                                 (u"Z_F", R(s, u"Z_F"))], 2, w=110)
    call(s, u"SL_FLG_C", u"Fc", [(u"SET_C", R(s, u"SET_C")),
                                 (u"CARRY", R(s, u"CARRY")),
                                 (u"CMD_CLC", R(s, u"CMD_CLC")),
                                 (u"CMD_SEC", R(s, u"CMD_SEC"))], 3, w=120)
    call(s, u"SL_FLG_V", u"Fv", [(u"SET_V", R(s, u"SET_V"))], 3, w=110)
    call(s, u"SL_FLG_I", u"Fi", [(u"CMD_SEI", R(s, u"CMD_SEI")),
                                 (u"CMD_CLI", R(s, u"CMD_CLI"))], 4, w=110)
    call(s, u"SL_FLG_B", u"Fb2", [(u"SET_B", R(s, u"SET_B"))], 4, w=110)
    call(s, u"SL_FLG5", u"F5", [], 5, w=90)
    W(s, u"P_NEW", R(s, u"P_WORK"), 6)
    # Флаги НОВОГО P для логики ветвления: (P_NEW AND маска) <> 0
    for m, nm in ((0x80, u"FN"), (0x40, u"FV"), (0x10, u"FB"), (0x08, u"FD"),
                  (0x04, u"FI"), (0x02, u"FZ"), (0x01, u"FC")):
        W(s, nm, s.blk(u"NE", [(u"IN1", s.blk(u"AND", [(u"IN1", R(s, u"P_NEW")),
                                                      (u"IN2", s.const(u"BYTE#16#%02X" % m, 7))], 7)),
                                (u"IN2", s.const(u"BYTE#0", 7))], 8), 9)
    call(s, u"SL_BRNE", u"Br",
         [(u"COND", R(s, u"COND")), (u"FZ", R(s, u"FZ")), (u"FC", R(s, u"FC"))],
         11, w=110)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_pcwb():
    s = Sheet(u"FB_CPU_PcWb: новый PC и запись регистров")
    call(s, u"SL_BRN2", u"Bt",
         [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),
          (u"TAKE", R(s, u"TAKE"))], 1, w=110)
    call(s, u"SL_PCSEL", u"Ps",
         [(u"PC_MODE", R(s, u"PC_MODE"))] + [(n, R(s, n)) for n in PC_CAND],
         2, w=150)
    call(s, u"FB_WriteBack", u"Wb",
         [(u"SRC", R(s, u"SRC")), (u"A", R(s, u"A")), (u"X", R(s, u"X")),
          (u"Y", R(s, u"Y")), (u"P_NEW", R(s, u"P_NEW")),
          (u"ALU_R", R(s, u"ALU_R")), (u"PCL", R(s, u"PCL")),
          (u"PCH", R(s, u"PCH")), (u"PULL_LO", R(s, u"PULL_LO")),
          (u"SP_NEW", R(s, u"SP_NEW")), (u"PC_NEW", R(s, u"PC_NEW")),
          (u"Enable", R(s, u"Enable"))] +
         [(n, R(s, n)) for n in
          (u"LD_A_E", u"LD_X_E", u"LD_Y_E", u"LD_P_E", u"LD_SP_E")],
         4, w=150)
    # Запись регистров вынесена в отдельный POU FB_RegFile:
    # по конспекту (2.5) чтение ячейки в той же сети, где она
    # пишется, даёт старое значение.
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_store():
    """FB_CPU_Store: tri porta zapisi v pamyat.

    Port 0 -- obychaya zapis (STA/STX/STY) ili pervyy bajt steka (BRK).
    Porty 1 i 2 -- vtoryy/tretiy bajty dlya JSR (PCH, PCL) i BRK (PCH, PCL).
    """
    s = Sheet(u"FB_CPU_Store: запись в память")
    push1 = s.blk(u"EQ", [(u"IN1", R(s, u"SP_MODE")), (u"IN2", s.const(u"BYTE#1", 1))], 1)
    push3 = s.blk(u"EQ", [(u"IN1", R(s, u"SP_MODE")), (u"IN2", s.const(u"BYTE#5", 1))], 1)
    stack_w = s.blk(u"OR", [(u"IN1", push1), (u"IN2", push3)], 2)

    # --- port 0
    en0 = s.blk(u"AND", [(u"IN1", R(s, u"Enable")),
                         (u"IN2", s.blk(u"OR", [(u"IN1", R(s, u"WR_MEM_E")),
                                                (u"IN2", s.blk(u"OR", [(u"IN1", R(s, u"IS_JSR")),
                                                                       (u"IN2", stack_w)], 3))], 3))], 4)
    W(s, u"WR0", s.blk(u"SEL", [(u"G", stack_w), (u"IN0", R(s, u"EFF")),
                                (u"IN1", R(s, u"STK_A0"))], 4), 5)
    W(s, u"WRD0", s.blk(u"SEL", [(u"G", push3), (u"IN0", R(s, u"REG_WR")),
                                 (u"IN1", R(s, u"P_NEW"))], 5), 6)
    W(s, u"WR_EN0", en0, 6)
    s.assign(u"GVL_MEM.Mem[GVL_CPU.WR0]",
             s.blk(u"SEL", [(u"G", R(s, u"WR_EN0")),
                            (u"IN0", s.ref(u"GVL_MEM.Mem[GVL_CPU.WR0]", 7)),
                            (u"IN1", R(s, u"WRD0"))], 7), 8)

    # --- port 1 (JSR: PCH, BRK: PCH)
    en1 = s.blk(u"AND", [(u"IN1", R(s, u"Enable")),
                         (u"IN2", s.blk(u"OR", [(u"IN1", R(s, u"IS_JSR")),
                                                (u"IN2", push3)], 3))], 4)
    W(s, u"WR1", R(s, u"STK_A1"), 5)
    W(s, u"WRD1", R(s, u"PCH"), 6)
    W(s, u"WR_EN1", en1, 6)
    s.assign(u"GVL_MEM.Mem[GVL_CPU.WR1]",
             s.blk(u"SEL", [(u"G", R(s, u"WR_EN1")),
                            (u"IN0", s.ref(u"GVL_MEM.Mem[GVL_CPU.WR1]", 7)),
                            (u"IN1", R(s, u"WRD1"))], 7), 8)

    # --- port 2 (JSR: PCL, BRK: PCL)
    W(s, u"WR2", R(s, u"STK_A2"), 5)
    W(s, u"WRD2", R(s, u"PCL"), 6)
    W(s, u"WR_EN2", s.blk(u"AND", [(u"IN1", R(s, u"Enable")), (u"IN2", push3)], 6), 6)
    s.assign(u"GVL_MEM.Mem[GVL_CPU.WR2]",
             s.blk(u"SEL", [(u"G", R(s, u"WR_EN2")),
                            (u"IN0", s.ref(u"GVL_MEM.Mem[GVL_CPU.WR2]", 7)),
                            (u"IN1", R(s, u"WRD2"))], 7), 8)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_regfile():
    """FB_RegFile: запись A, X, Y, P, SP, PC.

    По конспекту: (2.2) связь "выход вызова FB -> вход блока" теряется,
    поэтому никаких проводов -- только чтение GVL (его записали другие POU
    в этом же скане) и один outvar на регистр (2.5: без промежуточных
    переменных, чтобы не читать ячейку в той же сети, где пишем).
    """
    s = Sheet(u"FB_RegFile: запись регистров")
    W(s, u"A", s.blk(u"SEL", [(u"G", R(s, u"LD_A_E")), (u"IN0", R(s, u"A")), (u"IN1", R(s, u"REG_WR"))], 1), 2)
    W(s, u"X", s.blk(u"SEL", [(u"G", R(s, u"LD_X_E")), (u"IN0", R(s, u"X")), (u"IN1", R(s, u"REG_WR"))], 3), 4)
    W(s, u"Y", s.blk(u"SEL", [(u"G", R(s, u"LD_Y_E")), (u"IN0", R(s, u"Y")), (u"IN1", R(s, u"REG_WR"))], 5), 6)
    W(s, u"P", s.blk(u"SEL", [(u"G", R(s, u"LD_P_E")), (u"IN0", R(s, u"P_NEW")), (u"IN1", R(s, u"REG_WR"))], 7), 8)
    W(s, u"SP", s.blk(u"SEL", [(u"G", R(s, u"LD_SP_E")), (u"IN0", R(s, u"SP")), (u"IN1", R(s, u"SP_NEW"))], 9), 10)
    # PC пишется только при разрешённом такте: иначе Run=FALSE не заморозит ядро.
    W(s, u"PC", s.blk(u"SEL", [(u"G", R(s, u"Enable")), (u"IN0", R(s, u"PC")), (u"IN1", R(s, u"PC_NEW"))], 11), 12)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_latch():
    """FB_Latch: защёлкивание межуровневых значений в GVL_CPU.

    По конспекту (2.5): запись и чтение одной ячейки в пределах одного POU
    разъезжаются на такт. Поэтому все "перекладки" P_* живут здесь: этот POU
    только читает ячейки, записанные предыдущими слоями, и только пишет P_*.
    """
    s = Sheet(u"FB_Latch: защёлкивание межуровневых значений")
    W(s, u"P_EFF", R(s, u"EFF"), 1)
    W(s, u"P_BRK", R(s, u"BRKV"), 3)
    W(s, u"P_BRN", R(s, u"BRN_TGT"), 5)
    W(s, u"P_JRET", R(s, u"JRET"), 7)
    W(s, u"P_ADV", R(s, u"ADV"), 9)
    W(s, u"P_KEEP", R(s, u"PC"), 11)
    W(s, u"PULL_LO", s.ref(G.MEM + u".Mem[STK_R0]", 13), 14)
    # Технический выход: гарантирует, что CODESYS сгенерирует и
    # исполнит тело слоя (правило 3 конспекта).
    s.assign(u"OUT", R(s, u"Enable"), 22)
    return s


def fb_core():
    s = Sheet(u"FB_CPU_Core: один такт MOS 6502")
    # ---- пульт: Run / пошаговый режим
    # В пошаговом режиме такт разрешён только по импульсу Step_Pulse и только
    # один раз: защёлка STaken (локальная переменная ПОУ) помнит, что шаг уже
    # сделан, и снимается вместе с импульсом. Это нужно и тестам (точная
    # постановка состояния без гонки), и операторской панели HMI.
    run = s.ref(u"Enable", 0)
    st_on = R(s, u"Step_On")
    pulse = R(s, u"Step_Pulse")
    stak = s.ref(u"STaken", 0)
    permit = s.blk(u"AND", [(u"IN1", pulse),
                            (u"IN2", s.blk(u"NOT", [(u"IN", stak)], 1))], 2)
    en = s.blk(u"AND", [(u"IN1", run),
                        (u"IN2", s.blk(u"OR", [(u"IN1", s.blk(u"NOT", [(u"IN", st_on)], 1)),
                                               (u"IN2", permit)], 2))], 3)
    W(s, u"Enable", en, 4)
    s.assign(u"STaken", s.blk(u"AND", [(u"IN1", s.blk(u"OR", [(u"IN1", stak),
                                                              (u"IN2", s.blk(u"AND", [(u"IN1", st_on),
                                                                                      (u"IN2", permit)], 3))], 3)),
                              (u"IN2", pulse)], 4), 5)
    W(s, u"Step_Taken", s.ref(u"STaken", 6), 6)
    call(s, u"FB_Fetch", u"Fch", [(u"PCs", R(s, u"PC"))], 2, w=110)
    call(s, u"FB_FetchOp", u"Fop",
         [(u"PC1", R(s, u"PC1")), (u"PC2", R(s, u"PC2"))], 2, w=120)
    call(s, u"FB_Decoder6502", u"Dec", [(u"Op", R(s, u"OPs"))], 3, w=170)
    # Байтовые сигналы — из таблицы декодирования (данные в GVL_TABLE).
    # SP_MODE пропускается через разрешение такта: иначе при Run=FALSE ядро
    # продолжало бы толкать байты в стек каждый скан (SP_MODE не зависит от PC).
    for sig in (u"ADDR_MODE", u"LEN", u"SRC", u"ALU_A", u"ALU_B",
                u"PC_MODE", u"COND"):
        W(s, sig, s.ref(u"GVL_TABLE.%s[GVL_CPU.OPs]" % sig, 4), 4)
    W(s, u"SP_MODE",
      s.blk(u"SEL", [(u"G", R(s, u"Enable")), (u"IN0", s.const(u"BYTE#0", 4)),
                     (u"IN1", s.ref(u"GVL_TABLE.SP_MODE[GVL_CPU.OPs]", 4))], 4), 4)

    # Разрешения такта: сигнал И Enable (без этого регистры не пишутся)
    for sig in (u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM"):
        W(s, sig + u"_E",
          s.blk(u"AND", [(u"IN1", R(s, sig)), (u"IN2", R(s, u"Enable"))], 4), 4)
    ch = call(s, u"FB_CPU_Addr1", u"S1", [(u"Enable", s.const(u"TRUE", 0))], 5, w=140)
    W(s, u"Chain1", ch, 1)
    ch = call(s, u"FB_CPU_Select", u"S2", [(u"Enable", s.const(u"TRUE", 0))], 6, w=140)
    W(s, u"Chain2", ch, 1)
    ch = call(s, u"FB_CPU_Stack", u"S3", [(u"Enable", s.const(u"TRUE", 0))], 7, w=140)
    W(s, u"Chain3", ch, 1)
    ch = call(s, u"FB_CPU_AluFlags", u"S4", [(u"Enable", s.const(u"TRUE", 0))], 8, w=140)
    W(s, u"Chain4", ch, 1)
    ch = call(s, u"FB_Latch", u"S5L", [(u"Enable", s.const(u"TRUE", 0))], 9, w=140)
    W(s, u"Chain5", ch, 1)
    ch = call(s, u"FB_CPU_PcWb", u"S5", [(u"Enable", s.const(u"TRUE", 0))], 10, w=140)
    W(s, u"Chain6", ch, 1)
    ch = call(s, u"FB_CPU_Store", u"S6", [(u"Enable", s.const(u"TRUE", 0))], 10, w=140)
    W(s, u"Chain7", ch, 1)
    ch = call(s, u"FB_RegFile", u"S7", [(u"Enable", s.const(u"TRUE", 0))], 11, w=140)
    W(s, u"Chain8", ch, 1)
    W(s, u"Done", R(s, u"Enable"), 11)
    return s


def prg():
    s = Sheet(u"PLC_PRG: один такт процессора за скан задачи")
    s.add_comment(u"Каждый скан задачи выполняется ровно одна команда MOS 6502")
    call(s, u"FB_CPU_Core", u"Core", [(u"Enable", R(s, u"Run"))], 2, w=140)
    return s


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-16s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_top3 ===")

    write(u"FB_CPU_Addr1", pou_xml(
        u"FB_CPU_Addr1", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=pouloc(u"A1", u"SL_C1A", u"A2", u"SL_C1B", u"YW1", u"SL_YW",
                                 u"A3", u"SL_IND2", u"A4", u"SL_INDP", u"A5", u"SL_RELA",
                                 u"A6", u"SL_RELC", u"A7", u"SL_BRK")),
        [fb_addr1()], u"кандидаты адресов"))

    write(u"FB_CPU_Select", pou_xml(
        u"FB_CPU_Select", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=pouloc(u"Pick", u"SL_SELECT12", u"Wd", u"SL_WDATA2")),
        [fb_select()], u"выбор адреса"))

    write(u"FB_CPU_Stack", pou_xml(
        u"FB_CPU_Stack", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=pouloc(u"St1", u"SL_STK1", u"St2", u"SL_STK2",
                                 u"St3", u"SL_STK3", u"St4", u"SL_STK4",
                                 u"SpSel", u"SL_SPSEL", u"Adv", u"SL_ADV",
                                 u"Jr", u"SL_JRET")),
        [fb_stack()], u"стек"))

    write(u"FB_CPU_AluFlags", pou_xml(
        u"FB_CPU_AluFlags", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")],
                  locals_=pouloc(u"Alu", u"FB_ALU6502", u"Vsl", u"SL_VSEL",
                                 u"Fn", u"SL_FLG_N", u"Fz", u"SL_FLG_Z",
                                 u"Fc", u"SL_FLG_C", u"Fv", u"SL_FLG_V",
                                 u"Fi", u"SL_FLG_I", u"Fb2", u"SL_FLG_B",
                                 u"F5", u"SL_FLG5",
                                 u"Br", u"SL_BRNE")),
        [fb_aluflags()], u"АЛУ и флаги"))

    write(u"FB_CPU_PcWb", pou_xml(
        u"FB_CPU_PcWb", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=pouloc(u"Bt", u"SL_BRN2", u"Ps", u"SL_PCSEL",
                                 u"Wb", u"FB_WriteBack") +
                  [(u"N_A", u"BYTE"), (u"N_X", u"BYTE"), (u"N_Y", u"BYTE"),
                   (u"N_P", u"BYTE"), (u"N_SP", u"BYTE"), (u"N_PC", u"WORD")]),
        [fb_pcwb()], u"PC и запись"))

    write(u"FB_CPU_Core", pou_xml(
        u"FB_CPU_Core", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")],
                  locals_=pouloc(u"Fch", u"FB_Fetch", u"Fop", u"FB_FetchOp",
                                 u"Dec", u"FB_Decoder6502",
                                 u"S1", u"FB_CPU_Addr1", u"S2", u"FB_CPU_Select",
                                 u"S3", u"FB_CPU_Stack", u"S4", u"FB_CPU_AluFlags",
                                 u"S5L", u"FB_Latch", u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store", u"S7", u"FB_RegFile")
                  + [(u"STaken", u"BOOL")]),
        [fb_core()], u"такт"))

    write(u"FB_CPU_Store", pou_xml(
        u"FB_CPU_Store", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=[]),
        [fb_store()], u"запись в память"))

    write(u"FB_Latch", pou_xml(
        u"FB_Latch", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=[]),
        [fb_latch()], u"защёлкивание значений"))

    write(u"FB_RegFile", pou_xml(
        u"FB_RegFile", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], locals_=[]),
        [fb_regfile()], u"запись регистров"))

    write(u"PRG_PLC", pou_xml(
        u"PLC_PRG", u"program",
        interface(locals_=[(u"Core", u"FB_CPU_Core")]),
        [prg()], u"точка входа задачи"))
    print(u"готово")


if __name__ == "__main__":
    main()
