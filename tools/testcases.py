# -*- coding: utf-8 -*-
"""
testcases.py -- ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ по тест-кейсам эмулятора MOS 6502.

Зачем: 120+ кейсов, размазанных между документом и тестовым POU в CODESYS,
обязательно разъедутся. Поэтому кейсы описаны один раз здесь, а генератор
выдаёт из них:
  1) docs/02_ПЛАН_ТЕСТИРОВАНИЯ.md  -- читаемый план (таблицы «вход -> ожидание»)
  2) report/testcases.json         -- машинно-читаемый вид (для отчёта прогона)
  3) (позже) ST-код PRG_TESTDATA   -- тестовые данные для CODESYS

ВАЖНО про ожидания: они выведены ИЗ ДОКУМЕНТАЦИИ 6502 (таблицы флагов, правила
адресации), а НЕ из второй реализации эмулятора. Механические поля (PC, длина
инструкции, эффективный адрес) считаются по таблице режимов адресации; поля
флагов и результатов арифметики для ALU-групп заданы явными константами с
пометкой в колонке «Примечание».

Запуск:  python testcases.py
"""

import io
import json
import os

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"

# ---------------------------------------------------------------- биты регистра P
N, V, B, D, I, Z, C = 0x80, 0x40, 0x10, 0x08, 0x04, 0x02, 0x01
BIT5 = 0x20                      # всегда 1
P0 = 0x24                        # стартовое P: bit5=1, I=1 (после сброса 6502)

# ---------------------------------------------------------------- константы среды
PC0 = 0x0200                     # адрес загрузки тестовых программ
SP0 = 0xFD                       # стартовый указатель стека
A0, X0, Y0 = 0x11, 0x22, 0x33    # стартовые значения регистров (разные, чтобы ловить перепутанные провода)
VAL = 0x42                       # значение, которое читают/пишут команды
MEMV = 0x42
ZP = 0x10                        # рабочая ячейка zero page
ABS = 0x0300                     # абсолютный адрес-цель
ABSX = 0x0305                    # ABS + X(5)
ABSY = 0x0305                    # ABS + Y(5)
IDX = 0x05                       # величина индекса X/Y в тестах режимов


def expP(n=None, z=None, c=None, v=None, base=P0):
    """Собрать ожидаемое P: None = бит не меняется, True/False = установить/сбросить."""
    val = base
    for mask, bit in ((N, n), (Z, z), (C, c), (V, v)):
        if bit is None:
            continue
        val = (val | mask) if bit else (val & (~mask & 0xFF))
    return val | BIT5


# ---------------------------------------------------------------- таблица режимов адресации
# ops  -- байты операнда после кода операции
# eff  -- эффективный адрес (или None)
# pre  -- что предварительно положить в память: [(addr, value), ...]
# post -- куда команда запишет результат
MODES = {
    "imp": dict(len=1, ops=[],          eff=None,    pre=[]),
    "imm": dict(len=2, ops=[VAL],       eff=PC0 + 1, pre=[]),
    "zp":  dict(len=2, ops=[ZP],        eff=ZP,      pre=[]),
    "zpx": dict(len=2, ops=[ZP],        eff=ZP + IDX, pre=[], x=IDX),
    "zpy": dict(len=2, ops=[ZP],        eff=ZP + IDX, pre=[], y=IDX),
    "abs": dict(len=3, ops=[ABS & 0xFF, ABS >> 8], eff=ABS, pre=[]),
    "abx": dict(len=3, ops=[ABS & 0xFF, ABS >> 8], eff=ABSX, pre=[], x=IDX),
    "aby": dict(len=3, ops=[ABS & 0xFF, ABS >> 8], eff=ABSY, pre=[], y=IDX),
    # (zp,X): указатель лежит в zero page по адресу (zp + X) & 0xFF
    "izx": dict(len=2, ops=[ZP], eff=ABS, pre=[((ZP + IDX) & 0xFF, ABS & 0xFF), ((ZP + IDX + 1) & 0xFF, ABS >> 8)], x=IDX),
    # (zp),Y: указатель в zero page, затем +Y
    "izy": dict(len=2, ops=[ZP], eff=ABSX, pre=[(ZP, ABS & 0xFF), (ZP + 1, ABS >> 8)], y=IDX),
    "ind": dict(len=3, ops=[ABS & 0xFF, ABS >> 8], eff=None, pre=[(ABS, 0x50), (ABS + 1, 0x04)]),
    "rel": dict(len=2, ops=[0x00], eff=None, pre=[]),
}

MODE_RU = {
    "imp": "неявная", "imm": "immediate #", "zp": "zeropage", "zpx": "zeropage,X",
    "zpy": "zeropage,Y", "abs": "absolute", "abx": "absolute,X", "aby": "absolute,Y",
    "izx": "(indirect,X)", "izy": "(indirect),Y", "ind": "indirect", "rel": "relative",
}

# ---------------------------------------------------------------- таблица опкодов
# (мнемоника, режим, опкод)
OPCODES = [
    ("LDA", "imm", 0xA9), ("LDA", "zp", 0xA5), ("LDA", "zpx", 0xB5), ("LDA", "abs", 0xAD),
    ("LDA", "abx", 0xBD), ("LDA", "aby", 0xB9), ("LDA", "izx", 0xA1), ("LDA", "izy", 0xB1),
    ("LDX", "imm", 0xA2), ("LDX", "zp", 0xA6), ("LDX", "zpy", 0xB6), ("LDX", "abs", 0xAE), ("LDX", "aby", 0xBE),
    ("LDY", "imm", 0xA0), ("LDY", "zp", 0xA4), ("LDY", "zpx", 0xB4), ("LDY", "abs", 0xAC), ("LDY", "abx", 0xBC),
    ("STA", "zp", 0x85), ("STA", "zpx", 0x95), ("STA", "abs", 0x8D), ("STA", "abx", 0x9D),
    ("STA", "aby", 0x99), ("STA", "izx", 0x81), ("STA", "izy", 0x91),
    ("STX", "zp", 0x86), ("STX", "zpy", 0x96), ("STX", "abs", 0x8E),
    ("STY", "zp", 0x84), ("STY", "zpx", 0x94), ("STY", "abs", 0x8C),
    ("TAX", "imp", 0xAA), ("TAY", "imp", 0xA8), ("TXA", "imp", 0x8A), ("TYA", "imp", 0x98),
    ("ADC", "imm", 0x69), ("ADC", "zp", 0x65), ("ADC", "zpx", 0x75), ("ADC", "abs", 0x6D),
    ("ADC", "abx", 0x7D), ("ADC", "aby", 0x79), ("ADC", "izx", 0x61), ("ADC", "izy", 0x71),
    ("SBC", "imm", 0xE9), ("SBC", "zp", 0xE5), ("SBC", "zpx", 0xF5), ("SBC", "abs", 0xED),
    ("SBC", "abx", 0xFD), ("SBC", "aby", 0xF9), ("SBC", "izx", 0xE1), ("SBC", "izy", 0xF1),
    ("CMP", "imm", 0xC9), ("CMP", "zp", 0xC5), ("CMP", "zpx", 0xD5), ("CMP", "abs", 0xCD),
    ("CMP", "abx", 0xDD), ("CMP", "aby", 0xD9), ("CMP", "izx", 0xC1), ("CMP", "izy", 0xD1),
    ("INX", "imp", 0xE8), ("DEX", "imp", 0xCA), ("INY", "imp", 0xC8), ("DEY", "imp", 0x88),
    ("JMP", "abs", 0x4C), ("JMP", "ind", 0x6C),
    ("JSR", "abs", 0x20), ("RTS", "imp", 0x60),
    ("BEQ", "rel", 0xF0), ("BNE", "rel", 0xD0), ("BCC", "rel", 0x90),
    ("BCS", "rel", 0xB0), ("BPL", "rel", 0x10), ("BMI", "rel", 0x30),
    ("CLC", "imp", 0x18), ("SEC", "imp", 0x38),
    ("NOP", "imp", 0xEA),
    ("PHA", "imp", 0x48), ("PLA", "imp", 0x68), ("PHP", "imp", 0x08), ("PLP", "imp", 0x28),
    ("HLT", "imp", 0x02),
]

# ---------------------------------------------------------------- сборка кейсов
CASES = []


def add(gid, name, code, pc0=PC0, a=A0, x=X0, y=Y0, p=P0, sp=SP0,
        pre=None, steps=1, exp=None, post=None, note=""):
    """exp: (a, x, y, p, sp, pc).  post: [(addr, value), ...] -- ожидаемая память."""
    ea, ex, ey, ep, esp, epc = exp
    CASES.append(dict(
        id="T%03d" % (len(CASES) + 1), group=gid, name=name,
        code=list(code), pc0=pc0,
        init=dict(a=a, x=x, y=y, p=p, sp=sp),
        pre=[list(t) for t in (pre or [])],
        steps=steps,
        exp=dict(a=ea, x=ex, y=ey, p=ep, sp=esp, pc=epc),
        post=[list(t) for t in (post or [])],
        note=note,
    ))


def code_of(mn, mode):
    op = dict(((m, md), o) for m, md, o in OPCODES)[(mn, mode)]
    return [op] + list(MODES[mode]["ops"])


def nmode(mn, mode):
    return "%s %s" % (mn, MODE_RU[mode])


# ---- G01..G06: команды загрузки/записи по всем режимам адресации ----------------
def _mode_regs(md):
    """Стартовые X и Y для режима: индекс X/Y = $05 там, где режим его использует."""
    info = MODES[md]
    return info.get("x", X0), info.get("y", Y0)


def gen_load(mn, reg, gid):
    """LDA/LDX/LDY: значение MEMV из памяти -> регистр; N/Z обновляются.

    ВАЖНО: регистр-индекс (X для zpx/izx, Y для zpy/izy) сохраняет своё
    стартовое значение $05 -- и в начальном состоянии, и в ожидаемом.
    """
    for m, md, op in [(a, b, c) for a, b, c in OPCODES if a == mn]:
        info = MODES[md]
        x0, y0 = _mode_regs(md)
        a, xx, yy = A0, x0, y0
        if reg == "a":
            a = MEMV
        elif reg == "x":
            xx = MEMV
        else:
            yy = MEMV
        pre = list(info["pre"]) + [(info["eff"], MEMV)]
        add(gid, nmode(mn, md), code_of(mn, md), a=A0, x=x0, y=y0, pre=pre,
            exp=(a, xx, yy, expP(n=False, z=False), SP0, PC0 + info["len"]),
            note="N=0,Z=0, загружено $%02X из $%04X" % (MEMV, info["eff"]))


def gen_store(mn, reg, gid):
    """STA/STX/STY: регистр -> память; флаги не меняются."""
    for m, md, op in [(a, b, c) for a, b, c in OPCODES if a == mn]:
        info = MODES[md]
        x0, y0 = _mode_regs(md)
        val = dict(a=0xA5, x=0x5A, y=0x3C)[reg]
        a, xx, yy = A0, x0, y0
        if reg == "a":
            a = val
        elif reg == "x":
            xx = val
        else:
            yy = val
        add(gid, nmode(mn, md), code_of(mn, md), a=a, x=xx, y=yy, pre=info["pre"],
            exp=(a, xx, yy, P0, SP0, PC0 + info["len"]),
            post=[(info["eff"], val)],
            note="P не меняется; запись по адресу $%04X" % info["eff"])


def gen_alu(mn, gid):
    """ADC/SBC/CMP по всем режимам на фиксированных операндах (проверка адресации).

    Различаем СТАРТОВОЕ P (вход, например C=1 для SBC) и ОЖИДАЕМОЕ P (выход) --
    это разные вещи, и путать их нельзя.
    """
    for m, md, op in [(a, b, c) for a, b, c in OPCODES if a == mn]:
        info = MODES[md]
        x0, y0 = _mode_regs(md)
        pre = list(info["pre"]) + ([] if md == "imm" else [(info["eff"], MEMV)])
        if mn == "ADC":                      # A=11 + M=42 + C=0 = 53
            p_in, p_out, ea = P0, expP(c=False), 0x53
            note = "$11+$42+0=$53, C=0,V=0,N=0,Z=0"
        elif mn == "SBC":                    # A=11 - M=42 - 0 = CF, на входе C=1
            p_in, p_out, ea = P0 | C, expP(c=False, n=True, base=P0 | C), 0xCF
            note = "$11-$42=$CF, заём C=0, N=1,V=0 (на входе C=1)"
        else:                                # CMP: A=11 - M=42 -> CF, A не меняется
            p_in, p_out, ea = P0, expP(c=False, n=True), A0
            note = "CMP: $11-$42=$CF, C=0, A не меняется"
        add(gid, nmode(mn, md), code_of(mn, md), a=A0, x=x0, y=y0, p=p_in, pre=pre,
            exp=(ea, x0, y0, p_out, SP0, PC0 + info["len"]), note=note)


gen_load("LDA", "a", "G01 LDA — загрузка аккумулятора")
gen_load("LDX", "x", "G02 LDX — загрузка индексного регистра X")
gen_load("LDY", "y", "G03 LDY — загрузка индексного регистра Y")
gen_store("STA", "a", "G04 STA — запись аккумулятора")
gen_store("STX", "x", "G05 STX — запись регистра X")
gen_store("STY", "y", "G06 STY — запись регистра Y")

# ---- G07: пересылки между регистрами -------------------------------------------
G = "G07 Пересылки A<->X<->Y"
add(G, "TAX", [0xAA], a=0x11, exp=(0x11, 0x11, Y0, expP(n=False, z=False), SP0, PC0 + 1), note="A->X, N/Z")
add(G, "TAX (A=80 -> N=1)", [0xAA], a=0x80, exp=(0x80, 0x80, Y0, expP(n=True, z=False), SP0, PC0 + 1), note="знаковый бит")
add(G, "TAY", [0xA8], a=0x11, exp=(0x11, X0, 0x11, expP(n=False, z=False), SP0, PC0 + 1), note="A->Y, N/Z")
add(G, "TXA", [0x8A], x=0x80, exp=(0x80, 0x80, Y0, expP(n=True, z=False), SP0, PC0 + 1), note="X->A, N/Z")
add(G, "TXA (X=00 -> Z=1)", [0x8A], x=0x00, exp=(0x00, 0x00, Y0, expP(n=False, z=True), SP0, PC0 + 1), note="ноль")
add(G, "TYA", [0x98], y=0x33, exp=(0x33, X0, 0x33, expP(n=False, z=False), SP0, PC0 + 1), note="Y->A, N/Z")

# ---- G08: ADC — граничные случаи флагов ---------------------------------------
G = "G08 ADC — арифметика и флаги (граничные случаи)"
add(G, "ADC #$01, A=00, C=0", [0x69, 0x01], a=0x00, p=expP(c=False),
    exp=(0x01, X0, Y0, expP(n=False, z=False, c=False, v=False), SP0, PC0 + 2), note="простое сложение")
add(G, "ADC #$01, A=00, C=1", [0x69, 0x01], a=0x00, p=expP(c=True),
    exp=(0x02, X0, Y0, expP(n=False, z=False, c=False, v=False, base=P0 | C), SP0, PC0 + 2), note="учёт входного C")
add(G, "ADC #$7F, A=7F -> V=1", [0x69, 0x7F], a=0x7F, p=expP(c=False),
    exp=(0xFE, X0, Y0, expP(n=True, z=False, c=False, v=True), SP0, PC0 + 2), note="переполнение знака")
add(G, "ADC #$80, A=80 -> C=1,V=1,Z=1", [0x69, 0x80], a=0x80, p=expP(c=False),
    exp=(0x00, X0, Y0, expP(n=False, z=True, c=True, v=True), SP0, PC0 + 2), note="перенос из бита 7")
add(G, "ADC #$FF, A=FF -> C=1,N=1", [0x69, 0xFF], a=0xFF, p=expP(c=False),
    exp=(0xFE, X0, Y0, expP(n=True, z=False, c=True, v=False), SP0, PC0 + 2), note="C=1, V=0")
add(G, "ADC #$00, A=FF, C=1 -> Z=1,C=1", [0x69, 0x00], a=0xFF, p=expP(c=True),
    exp=(0x00, X0, Y0, expP(n=False, z=True, c=True, v=False, base=P0 | C), SP0, PC0 + 2),
    note="перенос в ноль")
gen_alu("ADC", G)

# ---- G09: SBC ------------------------------------------------------------------
G = "G09 SBC — арифметика и флаги (граничные случаи)"
add(G, "SBC #$01, A=00, C=1 -> FF", [0xE9, 0x01], a=0x00, p=expP(c=True),
    exp=(0xFF, X0, Y0, expP(n=True, z=False, c=False, v=False, base=P0 | C), SP0, PC0 + 2),
    note="0-1=FF, заём (C=0)")
add(G, "SBC #$01, A=00, C=0 -> FE", [0xE9, 0x01], a=0x00, p=expP(c=False),
    exp=(0xFE, X0, Y0, expP(n=True, z=False, c=False, v=False), SP0, PC0 + 2),
    note="учёт входного C=0")
add(G, "SBC #$80, A=80, C=1 -> 00", [0xE9, 0x80], a=0x80, p=expP(c=True),
    exp=(0x00, X0, Y0, expP(n=False, z=True, c=True, v=False, base=P0 | C), SP0, PC0 + 2),
    note="равные -> Z=1,C=1")
add(G, "SBC #$01, A=01, C=1 -> 00", [0xE9, 0x01], a=0x01, p=expP(c=True),
    exp=(0x00, X0, Y0, expP(n=False, z=True, c=True, v=False, base=P0 | C), SP0, PC0 + 2),
    note="граница нуля")
add(G, "SBC #$B0, A=50, C=1 -> V=1", [0xE9, 0xB0], a=0x50, p=expP(c=True),
    exp=(0xA0, X0, Y0, expP(n=True, z=False, c=False, v=True, base=P0 | C), SP0, PC0 + 2),
    note="80-(-80): переполнение")
add(G, "SBC #$70, A=50, C=1 -> V=0", [0xE9, 0x70], a=0x50, p=expP(c=True),
    exp=(0xE0, X0, Y0, expP(n=True, z=False, c=False, v=False, base=P0 | C), SP0, PC0 + 2),
    note="80-112: без переполнения")
gen_alu("SBC", G)

# ---- G10: CMP ------------------------------------------------------------------
G = "G10 CMP — сравнение"
add(G, "CMP #$42, A=42 -> Z=1,C=1", [0xC9, 0x42], a=0x42,
    exp=(0x42, X0, Y0, expP(n=False, z=True, c=True), SP0, PC0 + 2), note="равно")
add(G, "CMP #$42, A=41 -> C=0,N=1", [0xC9, 0x42], a=0x41,
    exp=(0x41, X0, Y0, expP(n=True, z=False, c=False), SP0, PC0 + 2), note="меньше")
add(G, "CMP #$42, A=43 -> C=1", [0xC9, 0x42], a=0x43,
    exp=(0x43, X0, Y0, expP(n=False, z=False, c=True), SP0, PC0 + 2), note="больше")
add(G, "CMP #$00, A=00 -> Z=1,C=1", [0xC9, 0x00], a=0x00,
    exp=(0x00, X0, Y0, expP(n=False, z=True, c=True), SP0, PC0 + 2), note="ноль")
gen_alu("CMP", G)

# ---- G11: инкремент/декремент --------------------------------------------------
G = "G11 INX/DEX/INY/DEY"
add(G, "INX", [0xE8], x=0x22, exp=(A0, 0x23, Y0, expP(n=False, z=False), SP0, PC0 + 1), note="только N/Z")
add(G, "INX (X=FF -> 00, Z=1)", [0xE8], x=0xFF, exp=(A0, 0x00, Y0, expP(n=False, z=True), SP0, PC0 + 1), note="переполнение")
add(G, "INX (X=7F -> 80, N=1)", [0xE8], x=0x7F, exp=(A0, 0x80, Y0, expP(n=True, z=False), SP0, PC0 + 1), note="знаковый бит")
add(G, "DEX", [0xCA], x=0x22, exp=(A0, 0x21, Y0, expP(n=False, z=False), SP0, PC0 + 1), note="только N/Z")
add(G, "DEX (X=00 -> FF, N=1)", [0xCA], x=0x00, exp=(A0, 0xFF, Y0, expP(n=True, z=False), SP0, PC0 + 1), note="заём через ноль")
add(G, "INY", [0xC8], y=0x33, exp=(A0, X0, 0x34, expP(n=False, z=False), SP0, PC0 + 1), note="только N/Z")
add(G, "DEY", [0x88], y=0x33, exp=(A0, X0, 0x32, expP(n=False, z=False), SP0, PC0 + 1), note="только N/Z")
add(G, "DEY (Y=01 -> 00, Z=1)", [0x88], y=0x01, exp=(A0, X0, 0x00, expP(n=False, z=True), SP0, PC0 + 1), note="ноль")

# ---- G12: установка/сброс переноса ---------------------------------------------
G = "G12 CLC/SEC"
add(G, "CLC (C=1 -> 0)", [0x18], p=expP(c=True), exp=(A0, X0, Y0, expP(c=False, base=P0 | C), SP0, PC0 + 1), note="гасит только C")
add(G, "SEC (C=0 -> 1)", [0x38], p=expP(c=False), exp=(A0, X0, Y0, expP(c=True), SP0, PC0 + 1), note="ставит только C")
add(G, "SEC;ADC #$05, A=10 -> 16", [0x38, 0x69, 0x05], steps=2, a=0x10, p=expP(c=False),
    exp=(0x16, X0, Y0, expP(n=False, z=False, c=False, v=False, base=P0 | C), SP0, PC0 + 3),
    note="влияние C на ADC: 10+5+1=16")

# ---- G13: JMP ------------------------------------------------------------------
G = "G13 JMP"
add(G, "JMP $0300 (absolute)", [0x4C, 0x00, 0x03], exp=(A0, X0, Y0, P0, SP0, 0x0300), note="прямой переход")
add(G, "JMP ($0300) (indirect)", [0x6C, 0x00, 0x03], pre=[(ABS, 0x50), (ABS + 1, 0x04)],
    exp=(A0, X0, Y0, P0, SP0, 0x0450), note="косвенный переход")
add(G, "JMP ($03FF) — аппаратный баг страницы", [0x6C, 0xFF, 0x03],
    pre=[(0x03FF, 0x50), (0x0300, 0x04), (0x0400, 0x99)],
    exp=(A0, X0, Y0, P0, SP0, 0x0450),
    note="старший байт берётся из $0300, а не из $0400 (баг 6502 воспроизводим)")

# ---- G14: JSR/RTS --------------------------------------------------------------
G = "G14 JSR/RTS и стек"
# JSR в 0x0250: адрес возврата = 0x0253, в стек кладётся 0x0252 (на 1 меньше)
add(G, "JSR $0260", [0x20, 0x60, 0x02], pc0=0x0250, sp=SP0,
    exp=(A0, X0, Y0, P0, SP0 - 2, 0x0260),
    post=[(0x01FD, 0x02), (0x01FC, 0x52)],
    note="PCH в $01FD, PCL в $01FC, SP=FB; адрес возврата-1 = 0252")
add(G, "RTS", [0x60], pc0=0x0253, sp=0xFB, pre=[(0x01FC, 0x52), (0x01FD, 0x02)],
    exp=(A0, X0, Y0, P0, SP0, 0x0253),
    note="извлечено 0252, +1 -> 0253; SP вернулся в FD")
add(G, "JSR вложенный стек (2 уровня)", [0x20, 0x60, 0x02], pc0=0x0250, sp=0xF9,
    exp=(A0, X0, Y0, P0, 0xF7, 0x0260),
    post=[(0x01F9, 0x02), (0x01F8, 0x52)],
    note="проверка адресации стека при непустом стеке")

# ---- G15: ветвления ------------------------------------------------------------
G = "G15 Ветвления BEQ/BNE/BCC/BCS/BPL/BMI"
BR = [("BEQ", 0xF0, dict(z=True), dict(z=False)),
      ("BNE", 0xD0, dict(z=False), dict(z=True)),
      ("BCC", 0x90, dict(c=False), dict(c=True)),
      ("BCS", 0xB0, dict(c=True), dict(c=False)),
      ("BPL", 0x10, dict(n=False), dict(n=True)),
      ("BMI", 0x30, dict(n=True), dict(n=False))]
for mn, op, on, off in BR:
    add(G, "%s +5 (переход выполнен)" % mn, [op, 0x05], p=expP(base=P0, **on),
        exp=(A0, X0, Y0, expP(base=P0, **on), SP0, PC0 + 2 + 0x05),
        note="PC = PC+2+offset")
    add(G, "%s +5 (переход не выполнен)" % mn, [op, 0x05], p=expP(base=P0, **off),
        exp=(A0, X0, Y0, expP(base=P0, **off), SP0, PC0 + 2),
        note="условие ложно -> PC только +2")
add(G, "BNE назад (offset FC = -4)", [0xD0, 0xFC], p=expP(z=False),
    exp=(A0, X0, Y0, expP(z=False), SP0, PC0 + 2 - 4),
    note="знаковое расширение offset")

# ---- G16: стек -----------------------------------------------------------------
G = "G16 Стек: PHA/PLA/PHP/PLP"
add(G, "PHA (SP=FD)", [0x48], a=0xA5, exp=(0xA5, X0, Y0, P0, SP0 - 1, PC0 + 1),
    post=[(0x01FD, 0xA5)], note="запись по $01FD, затем SP-1")
add(G, "PLA (SP=FD)", [0x68], sp=SP0, pre=[(0x01FE, 0x42)],
    exp=(0x42, X0, Y0, expP(n=False, z=False), SP0 + 1, PC0 + 1),
    note="сначала SP+1, затем чтение $01FE")
add(G, "PLA -> N=1", [0x68], sp=SP0, pre=[(0x01FE, 0x80)],
    exp=(0x80, X0, Y0, expP(n=True, z=False), SP0 + 1, PC0 + 1), note="PLA обновляет N/Z")
add(G, "PHP (в стеке B=1 и bit5=1)", [0x08], p=expP(), exp=(A0, X0, Y0, expP(), SP0 - 1, PC0 + 1),
    post=[(0x01FD, expP() | 0x30)], note="в стеке P с B=1 (30)")
add(G, "PLP", [0x28], sp=SP0, pre=[(0x01FE, 0x34)],
    exp=(A0, X0, Y0, 0x34 | BIT5, SP0 + 1, PC0 + 1), note="bit5 принудительно 1")

# ---- G17: little-endian --------------------------------------------------------
G = "G17 Little-endian (порядок байт адреса)"
add(G, "LDA $0342 — младший байт первый", [0xAD, 0x42, 0x03],
    pre=[(0x0342, 0x77), (0x4203, 0x99)],
    exp=(0x77, X0, Y0, expP(n=False, z=False), SP0, PC0 + 3),
    note="читается $0342; значение из $4203 доказывает, что байты НЕ переставлены")
add(G, "LDA $4203 — обратный порядок отвергнут", [0xAD, 0x03, 0x42],
    pre=[(0x0342, 0x77), (0x4203, 0x99)],
    exp=(0x99, X0, Y0, expP(n=True, z=False), SP0, PC0 + 3),
    note="03,42 => адрес $4203")

# ---- G18: NOP / HLT / инварианты ------------------------------------------------
G = "G18 NOP/HLT и инварианты"
add(G, "NOP", [0xEA], exp=(A0, X0, Y0, P0, SP0, PC0 + 1), note="ничего не меняет")
add(G, "HLT (неофициальный $02)", [0x02], exp=(A0, X0, Y0, P0, SP0, PC0), note="PC заморожен, останов")
add(G, "HLT не трогает регистры", [0x02], a=0x99, exp=(0x99, X0, Y0, P0, SP0, PC0), note="останов без побочных эффектов")

# ---- G19: программы ------------------------------------------------------------
G = "G19 Программы (многотактовые сценарии)"
# (a) два числа через zero page + ADC с учётом C
prog_a = [0xA9, 0x05,        # LDA #$05
          0x85, 0x10,        # STA $10
          0xA9, 0x03,        # LDA #$03
          0x85, 0x11,        # STA $11
          0x18,              # CLC
          0xA5, 0x10,        # LDA $10
          0x65, 0x11,        # ADC $11
          0x85, 0x12]        # STA $12
add(G, "Программа: пересылка через ZP + ADC", prog_a, steps=8,
    exp=(0x08, X0, Y0, expP(n=False, z=False, c=False, v=False), SP0, PC0 + 15),
    post=[(0x10, 0x05), (0x11, 0x03), (0x12, 0x08)],
    note="8 инструкций, 15 байт; $05+$03=$08, C=0")
# (b) тот же сценарий с учётом входного переноса
prog_b = [0xA9, 0x05, 0x85, 0x10,
          0xA9, 0x03, 0x85, 0x11,
          0x38,              # SEC  -> C=1
          0xA5, 0x10,
          0x65, 0x11,        # ADC с C=1
          0x85, 0x12]
add(G, "Программа: то же, но SEC (C=1)", prog_b, steps=8,
    exp=(0x09, X0, Y0, expP(n=False, z=False, c=False, v=False), SP0, PC0 + 15),
    post=[(0x12, 0x09)], note="$05+$03+1=$09 — проверка влияния входного C")
# (c) цикл LDX #N + DEX + BNE
prog_c = [0xA2, 0x05,        # LDX #$05       @0200
          0xCA,              # DEX            @0202
          0xD0, 0xFD]        # BNE -3 -> 0202 @0203 (смещение = 0202h - 0205h = -3)
add(G, "Цикл: LDX #5 + DEX + BNE", prog_c, steps=11,
    exp=(A0, 0x00, Y0, expP(n=False, z=True), SP0, PC0 + 5),
    note="1 + 5*2 = 11 тактов; выход по Z=1; PC = $0205")
# (d) подпрограмма JSR + RTS
prog_d = {0x0250: [0x20, 0x60, 0x02],   # JSR $0260
          0x0253: [0xA9, 0xAA],         # LDA #$AA
          0x0255: [0x02],               # HLT
          0x0260: [0xA2, 0x07],         # LDX #$07
          0x0262: [0x60]}               # RTS
code_d = [0x20, 0x60, 0x02]
add(G, "Подпрограмма: JSR $0260 + RTS + HLT", code_d, pc0=0x0250, steps=5,
    exp=(0xAA, 0x07, Y0, expP(n=False, z=False), SP0, 0x0255),
    pre=[], post=[(0x01FD, 0x02), (0x01FC, 0x52)],
    note="5 тактов: JSR, LDX, RTS, LDA, HLT; SP вернулся в FD")

# ---------------------------------------------------------------- вывод: Markdown
HEAD = u"""# План тестирования эмулятора MOS 6502 (CODESYS 3.5 / FBD)

Документ **сгенерирован** из `tools/testcases.py` — не редактировать вручную.
Единый источник истины по кейсам находится в Python-файле.

## 1. Соглашения

| Параметр | Значение | Почему так |
|---|---|---|
| Адрес загрузки программ | `$0200` | вне zero page и вне страницы стека — ошибки адресации видны сразу |
| Стартовый `SP` | `$FD` | как после сброса; в стеке есть место под 3 push |
| Стартовое `P` | `$24` (`bit5=1`, `I=1`) | соответствует состоянию после сброса 6502 |
| Стартовые `A / X / Y` | `$11 / $22 / $33` | **все разные**, чтобы перепутанные провода в FBD дали FAIL, а не совпадение |
| Значение-нагрузка | `$42` | читается командами загрузки/ALU |
| Рабочая ячейка ZP | `$10` | |
| Абсолютный адрес-цель | `$0300` | |
| Индекс X/Y в тестах режимов | `$05` | `$0300+$05 = $0305` |
| Байт `P` | `N V 1 B D I Z C` | `bit5` всегда `1` — проверяется отдельно |

**Ожидания выведены из документации 6502** (таблицы флагов, правила режимов
адресации), а не из второй реализации эмулятора. Для механических полей (`PC`,
длина инструкции, эффективный адрес) значения вычисляются по таблице режимов;
для арифметики и флагов заданы явными константами, каждая с пояснением.

## 2. Как это будет исполняться в CODESYS

Один такт ЦПУ = один скан PLC, поэтому кейс — это **последовательность сканов**:

1. `TEST_6502` грузит программу кейса в память, ставит `A/X/Y/P/SP/PC`, снимает `CPU_Enable`;
2. `CPU_Enable := TRUE`, счётчик `CTU` отсчитывает `steps` сканов (по одной инструкции за скан);
3. по достижении `steps` — сравнение факта с эталоном через `FB_AssertEq` (`EQ` → `PASS`);
4. результат пишется в `GVL_TEST.Pass[i]`, счётчики PASS/FAIL — `CTU`, далее следующий кейс.

Сетка ассертов на каждый кейс: `A`, `X`, `Y`, `P`, `SP`, `PC` + проверки памяти
(для `STA/STX/STY`, `JSR`, `PHA`, программ). Дополнительно на каждом кейсе
проверяется инвариант `(P AND $20) = $20`.

## 3. Сводка

| Группа | Кейсов |
|---|---:|
"""


def fmt_regs(d):
    return "`%02X / %02X / %02X / %02X / %02X / %04X`" % (d["a"], d["x"], d["y"], d["p"], d["sp"], d["pc"])


def fmt_mem(lst):
    if not lst:
        return "—"
    return ", ".join("`%04X=%02X`" % (a, v) for a, v in lst)


def fmt_code(code):
    return "`" + " ".join("%02X" % b for b in code) + "`"


def plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not (12 <= n100 <= 14):
        return few
    return many


def render():
    out = [HEAD]
    groups = []
    for c in CASES:
        if c["group"] not in groups:
            groups.append(c["group"])
    for g in groups:
        n = len([c for c in CASES if c["group"] == g])
        out.append(u"| %s | %d |\n" % (g, n))
    out.append(u"| **ИТОГО** | **%d** |\n" % len(CASES))

    out.append(u"""
**Всего кейсов: %d.**

Колонки таблиц: `A / X / Y / P / SP / PC`.

---

## 4. Тест-кейсы по группам
""" % len(CASES))

    for g in groups:
        gl = [c for c in CASES if c["group"] == g]
        out.append(u"\n### %s  (%d %s)\n\n" % (g, len(gl), plural(len(gl), u"кейс", u"кейса", u"кейсов")))
        out.append(u"| ID | Кейс | Программа | Старт: A/X/Y/P/SP/PC | Память до | Тактов | Ожидаемо: A/X/Y/P/SP/PC | Память после | Примечание |\n")
        out.append(u"|---|---|---|---|---|---|---|---|---|\n")
        for c in gl:
            out.append(u"| %s | %s | %s | %s | %s | %d | %s | %s | %s |\n" % (
                c["id"], c["name"], fmt_code(c["code"]),
                fmt_regs(dict(c["init"], pc=c["pc0"])),
                fmt_mem(c["pre"]), c["steps"],
                fmt_regs(c["exp"]), fmt_mem(c["post"]), c["note"]))
    out.append(u"""
---

## 5. Отдельные проверки, не покрытые построчными кейсами

| Проверка | Как проверяется | Ожидание |
|---|---|---|
| `bit5` регистра `P` всегда `1` | инвариант на каждом кейсе + 4 кейса записи в `P` | `(P AND $20) = $20` |
| Биты `D` и `I` не портятся | кейсы `CLC/SEC/ADC/SBC/PLP` | `P AND $0C` неизменно |
| `CMP` не меняет регистр-источник | кейс `CMP`, группа G10 | `A` на выходе = `A` на входе |
| Запись не «протекает» в соседние ячейки | все кейсы `STA/STX/STY` | изменена ровно одна ячейка |
| Одновременность `RTS`-выборки | кейс `RTS` | два чтения стека в одном скане, `SP += 2` |
| Адресация стека не уходит из `$01xx` | кейсы `PHA/PLA/JSR/RTS` | старший байт адреса всегда `$01` |
| Независимость от порядка блоков | прогон с изменённым `Execution Order` | результат идентичен (архитектура snapshot) |
| Соответствие опкодов | группа `G20` ниже | таблица опкодов совпадает с декодером |

## 6. Таблица опкодов (эталон для сверки с декодером FBD)

| Мнемоника | Режим | Опкод | Длина |
|---|---|---|---:|
""")
    for mn, md, op in OPCODES:
        out.append(u"| `%s` | %s | `%02X` | %d |" % (mn, MODE_RU[md], op, MODES[md]["len"]) + "\n")
    return u"".join(out)


def main():
    md = render()
    d = os.path.join(ROOT, "docs")
    r = os.path.join(ROOT, "report")
    for p in (d, r):
        if not os.path.isdir(p):
            os.makedirs(p)
    with io.open(os.path.join(d, u"02_ПЛАН_ТЕСТИРОВАНИЯ.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with io.open(os.path.join(r, u"testcases.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(CASES, ensure_ascii=False, indent=1))
    print("cases: %d" % len(CASES))
    groups = []
    for c in CASES:
        if c["group"] not in groups:
            groups.append(c["group"])
    for g in groups:
        print("  %-45s %3d" % (g, len([c for c in CASES if c["group"] == g])))


if __name__ == "__main__":
    main()
