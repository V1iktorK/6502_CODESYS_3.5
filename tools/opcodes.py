# -*- coding: utf-8 -*-
"""
opcodes.py -- ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ по системе команд MOS 6502.

Из этой таблицы выводятся ОДНОВРЕМЕННО:
  * декодер FB_Decoder6502 (микрооперации по опкоду),
  * тестовые кейсы (tools/testcases.py),
  * таблица опкодов в документации.

Если менять набор команд -- менять ТОЛЬКО здесь. Иначе декодер и тесты разъедутся.
"""

# ---------------------------------------------------------------- режимы адресации
MODES = [u"imp", u"imm", u"zp", u"zpx", u"zpy", u"abs", u"abx", u"aby",
         u"izx", u"izy", u"ind", u"rel", u"stk"]
MODE_CODE = dict((m, i) for i, m in enumerate(MODES))
MODE_RU = {u"imp": u"неявная", u"imm": u"immediate #", u"zp": u"zeropage",
           u"zpx": u"zeropage,X", u"zpy": u"zeropage,Y", u"abs": u"absolute",
           u"abx": u"absolute,X", u"aby": u"absolute,Y", u"izx": u"(indirect,X)",
           u"izy": u"(indirect),Y", u"ind": u"indirect", u"rel": u"relative",
           u"stk": u"стек"}
MODE_LEN = {u"imp": 1, u"imm": 2, u"zp": 2, u"zpx": 2, u"zpy": 2, u"abs": 3,
            u"abx": 3, u"aby": 3, u"izx": 2, u"izy": 2, u"ind": 3, u"rel": 2,
            u"stk": 1}

# ---------------------------------------------------------------- коды источников данных
SRC_A, SRC_X, SRC_Y, SRC_P, SRC_ALU, SRC_PCL, SRC_PCH, SRC_STK = 0, 1, 2, 3, 4, 5, 6, 7
SRC_RU = {SRC_A: u"A", SRC_X: u"X", SRC_Y: u"Y", SRC_P: u"P", SRC_ALU: u"результат ALU",
          SRC_PCL: u"PCL", SRC_PCH: u"PCH", SRC_STK: u"байт из стека"}

# ---------------------------------------------------------------- режимы PC и стека
PC_LEN, PC_ABS, PC_RTS, PC_BRANCH, PC_HALT, PC_RTI, PC_BRK = 0, 1, 2, 3, 4, 5, 6
PC_RU = {PC_LEN: u"PC+LEN", PC_ABS: u"цель перехода", PC_RTS: u"возврат из подпрограммы",
         PC_BRANCH: u"условный переход", PC_HALT: u"останов"}

SP_NONE, SP_PUSH1, SP_PULL1, SP_PUSH2, SP_PULL2, SP_PUSH3, SP_PULL3 = 0, 1, 2, 3, 4, 5, 6
SP_RU = {SP_NONE: u"нет", SP_PUSH1: u"положить 1 байт", SP_PULL1: u"извлечь 1 байт",
         SP_PUSH2: u"положить 2 байта (JSR)", SP_PULL2: u"извлечь 2 байта (RTS)"}

COND_Z, COND_NZ, COND_C, COND_NC, COND_N, COND_NN = 0, 1, 2, 3, 4, 5
COND_RU = {COND_Z: u"Z=1 (BEQ)", COND_NZ: u"Z=0 (BNE)", COND_C: u"C=1 (BCS)",
           COND_NC: u"C=0 (BCC)", COND_N: u"N=1 (BMI)", COND_NN: u"N=0 (BPL)"}

ALU_A, ALU_X, ALU_Y = 0, 1, 2
ALU_B_MDR, ALU_B_ONE = 0, 1

# ---------------------------------------------------------------- таблица команд
# (мнемоника, режим, опкод)
OPCODES = [
    (u"LDA", u"imm", 0xA9), (u"LDA", u"zp", 0xA5), (u"LDA", u"zpx", 0xB5),
    (u"LDA", u"abs", 0xAD), (u"LDA", u"abx", 0xBD), (u"LDA", u"aby", 0xB9),
    (u"LDA", u"izx", 0xA1), (u"LDA", u"izy", 0xB1),
    (u"LDX", u"imm", 0xA2), (u"LDX", u"zp", 0xA6), (u"LDX", u"zpy", 0xB6),
    (u"LDX", u"abs", 0xAE), (u"LDX", u"aby", 0xBE),
    (u"LDY", u"imm", 0xA0), (u"LDY", u"zp", 0xA4), (u"LDY", u"zpx", 0xB4),
    (u"LDY", u"abs", 0xAC), (u"LDY", u"abx", 0xBC),
    (u"STA", u"zp", 0x85), (u"STA", u"zpx", 0x95), (u"STA", u"abs", 0x8D),
    (u"STA", u"abx", 0x9D), (u"STA", u"aby", 0x99), (u"STA", u"izx", 0x81),
    (u"STA", u"izy", 0x91),
    (u"STX", u"zp", 0x86), (u"STX", u"zpy", 0x96), (u"STX", u"abs", 0x8E),
    (u"STY", u"zp", 0x84), (u"STY", u"zpx", 0x94), (u"STY", u"abs", 0x8C),
    (u"TAX", u"imp", 0xAA), (u"TAY", u"imp", 0xA8),
    (u"TXA", u"imp", 0x8A), (u"TYA", u"imp", 0x98),
    (u"ADC", u"imm", 0x69), (u"ADC", u"zp", 0x65), (u"ADC", u"zpx", 0x75),
    (u"ADC", u"abs", 0x6D), (u"ADC", u"abx", 0x7D), (u"ADC", u"aby", 0x79),
    (u"ADC", u"izx", 0x61), (u"ADC", u"izy", 0x71),
    (u"SBC", u"imm", 0xE9), (u"SBC", u"zp", 0xE5), (u"SBC", u"zpx", 0xF5),
    (u"SBC", u"abs", 0xED), (u"SBC", u"abx", 0xFD), (u"SBC", u"aby", 0xF9),
    (u"SBC", u"izx", 0xE1), (u"SBC", u"izy", 0xF1),
    (u"CMP", u"imm", 0xC9), (u"CMP", u"zp", 0xC5), (u"CMP", u"zpx", 0xD5),
    (u"CMP", u"abs", 0xCD), (u"CMP", u"abx", 0xDD), (u"CMP", u"aby", 0xD9),
    (u"CMP", u"izx", 0xC1), (u"CMP", u"izy", 0xD1),
    (u"INX", u"imp", 0xE8), (u"DEX", u"imp", 0xCA),
    (u"INY", u"imp", 0xC8), (u"DEY", u"imp", 0x88),
    (u"JMP", u"abs", 0x4C), (u"JMP", u"ind", 0x6C),
    (u"JSR", u"abs", 0x20), (u"RTS", u"stk", 0x60),
    (u"BEQ", u"rel", 0xF0), (u"BNE", u"rel", 0xD0), (u"BCC", u"rel", 0x90),
    (u"BCS", u"rel", 0xB0), (u"BPL", u"rel", 0x10), (u"BMI", u"rel", 0x30),
    (u"CLC", u"imp", 0x18), (u"SEC", u"imp", 0x38),
    (u"NOP", u"imp", 0xEA),
    (u"PHA", u"stk", 0x48), (u"PLA", u"stk", 0x68),
    (u"PHP", u"stk", 0x08), (u"PLP", u"stk", 0x28),
    (u"HLT", u"imp", 0x02),
    (u"BRK", u"imp", 0x00), (u"RTI", u"imp", 0x40),
    (u"SEI", u"imp", 0x78), (u"CLI", u"imp", 0x58),
]

# ---------------------------------------------------------------- микрооперации
# Каждая запись: {опкод: {имя_сигнала: значение}}, отсутствие = FALSE/0.
# Заполняется функцией build_effects() ниже, чтобы не расписывать сотню строк руками.

def build_effects():
    """Вывести карту микроопераций из таблицы команд."""
    eff = {}

    def set_(op, **kw):
        eff.setdefault(op, {}).update(kw)

    mode_of = {}
    for mn, md, op in OPCODES:
        mode_of[op] = (mn, md)
        set_(op, ADDR_MODE=MODE_CODE[md], LEN=MODE_LEN[md])

    # --- семейства ---
    for mn, md, op in OPCODES:
        if mn == u"LDA":
            set_(op, LD_A=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_A, ALU_B=ALU_B_MDR)
        elif mn == u"LDX":
            set_(op, LD_X=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_A, ALU_B=ALU_B_MDR)
        elif mn == u"LDY":
            set_(op, LD_Y=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_A, ALU_B=ALU_B_MDR)
        elif mn in (u"STA", u"STX", u"STY"):
            set_(op, WR_MEM=True, SRC={u"STA": SRC_A, u"STX": SRC_X, u"STY": SRC_Y}[mn])
        elif mn in (u"TAX", u"TAY", u"TXA", u"TYA"):
            src = {u"TAX": SRC_A, u"TAY": SRC_A, u"TXA": SRC_X, u"TYA": SRC_Y}[mn]
            dst = {u"TAX": u"LD_X", u"TAY": u"LD_Y", u"TXA": u"LD_A", u"TYA": u"LD_A"}[mn]
            set_(op, SET_NZ=True, SRC=src, **{dst: True})
        elif mn in (u"ADC", u"SBC", u"CMP"):
            # SRC=SRC_ALU и для CMP: CMP ничего не пишет в регистры, но его
            # результат (A - M) нужен как источник флагов N/Z. Пусть REG_WR
            # несёт результат АЛУ и для CMP -- тогда флаги для ВСЕХ команд
            # берутся из одного места (REG_WR), а не из двух разных.
            set_(op, LD_A=(mn != u"CMP"), SET_NZ=True, SET_C=True,
                 USE_CARRY=(mn != u"CMP"), SET_V=(mn != u"CMP"),
                 SRC=SRC_ALU,
                 ALU_A=ALU_A, ALU_B=ALU_B_MDR,
                 F_ADD=(mn == u"ADC"), F_SUB=(mn == u"SBC"), F_CMP=(mn == u"CMP"))
        elif mn == u"INX":
            set_(op, LD_X=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_X, ALU_B=ALU_B_ONE, F_ADD=True)
        elif mn == u"INY":
            set_(op, LD_Y=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_Y, ALU_B=ALU_B_ONE, F_ADD=True)
        elif mn == u"DEX":
            set_(op, LD_X=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_X, ALU_B=ALU_B_ONE,
                 F_SUB=True, CIN_FORCE=True)
        elif mn == u"DEY":
            set_(op, LD_Y=True, SET_NZ=True, SRC=SRC_ALU, ALU_A=ALU_Y, ALU_B=ALU_B_ONE,
                 F_SUB=True, CIN_FORCE=True)
        elif mn == u"JMP":
            set_(op, PC_MODE=PC_ABS)
        elif mn == u"JSR":
            set_(op, PC_MODE=PC_ABS, SP_MODE=SP_PUSH2, IS_JSR=True)
        elif mn == u"RTS":
            set_(op, PC_MODE=PC_RTS, SP_MODE=SP_PULL2, IS_RTS=True)
        elif mn in (u"BEQ", u"BNE", u"BCC", u"BCS", u"BPL", u"BMI"):
            set_(op, PC_MODE=PC_BRANCH,
                 COND={u"BEQ": COND_Z, u"BNE": COND_NZ, u"BCC": COND_NC,
                       u"BCS": COND_C, u"BPL": COND_NN, u"BMI": COND_N}[mn])
        elif mn == u"CLC":
            set_(op, CMD_CLC=True)
        elif mn == u"SEC":
            set_(op, CMD_SEC=True)
        elif mn == u"PHA":
            set_(op, SP_MODE=SP_PUSH1, SRC=SRC_A)
        elif mn == u"PHP":
            set_(op, SP_MODE=SP_PUSH1, SRC=SRC_P)
        elif mn == u"PLA":
            set_(op, SP_MODE=SP_PULL1, LD_A=True, SET_NZ=True, SRC=SRC_STK)
        elif mn == u"PLP":
            set_(op, SP_MODE=SP_PULL1, LD_P=True, SRC=SRC_STK)
        elif mn == u"HLT":
            set_(op, HALT=True, PC_MODE=PC_HALT)
        elif mn == u"SEI":
            set_(op, CMD_SEI=True)
        elif mn == u"CLI":
            set_(op, CMD_CLI=True)
        elif mn == u"BRK":
            # BRK: в стек кладутся флаги (с B=1) и адрес возврата PC+2,
            # затем переход по вектору / и установка I
            set_(op, PC_MODE=PC_BRK, SP_MODE=SP_PUSH3, SET_B=True,
                 CMD_SEI=True, WR_MEM=True, SRC=SRC_P)
        elif mn == u"RTI":
            # RTI: извлекаются флаги и адрес возврата БЕЗ +1
            set_(op, PC_MODE=PC_RTI, SP_MODE=SP_PULL3, LD_P=True, SRC=SRC_STK)
        elif mn == u"NOP":
            pass

    # --- загрузка SP: обязана срабатывать везде, где стек меняет указатель ---
    # Без этого сигнала SP_NEW вычислялся бы, но в регистр SP никогда не попадал.
    for op, d in eff.items():
        if d.get(u"SP_MODE", SP_NONE) != SP_NONE:
            d[u"LD_SP"] = True
    return eff


# Имена всех BOOL-сигналов декодера (порядок = порядок вывода на листе)
# IS_PUSH/IS_PULL намеренно отсутствуют: что именно делает стек, полностью
# описывает код SP_MODE, дублировать его булевыми линиями -- значит плодить
# два источника истины для одного решения.
BOOL_SIGNALS = [u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP",
                u"WR_MEM", u"USE_CARRY", u"CIN_FORCE",
                u"SET_NZ", u"SET_C", u"SET_V",
                u"CMD_CLC", u"CMD_SEC", u"HALT",
                u"F_ADD", u"F_SUB", u"F_CMP",
                u"IS_JSR", u"IS_RTS", u"CMD_SEI", u"CMD_CLI", u"SET_B"]

# BYTE-коды декодера: имя -> (значение по умолчанию, {значение: [опкоды]})
BYTE_SIGNALS = [u"ADDR_MODE", u"LEN", u"SRC", u"ALU_A", u"ALU_B",
                u"PC_MODE", u"SP_MODE", u"COND"]

if __name__ == u"__main__":
    e = build_effects()
    print(u"опкодов: %d" % len(OPCODES))
    used = set()
    for op, d in e.items():
        used.update(d.keys())
    print(u"использованные сигналы: %s" % u", ".join(sorted(used)))
    missing = [s for s in BOOL_SIGNALS + BYTE_SIGNALS if s not in used]
    print(u"НЕ использованы: %s" % (u", ".join(missing) or u"(нет)"))
    mn = {}
    for m, md, o in OPCODES:
        mn.setdefault(m, []).append(u"%s/%02X" % (md, o))
    for k in sorted(mn):
        print(u"  %-4s %s" % (k, u" ".join(mn[k])))
