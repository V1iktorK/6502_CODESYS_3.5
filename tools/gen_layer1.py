# -*- coding: utf-8 -*-
"""
gen_layer1.py -- генератор FBD-схем базовых блоков эмулятора MOS 6502.

Слой 1 (этот файл): примитивы и арифметика
    F_UnpackByte, F_PackByte      -- распаковка/упаковка BYTE <-> ARRAY[0..7] OF BOOL
    F_Join16, F_Split16           -- сборка/разбор WORD из двух BYTE
    FB_Reg8, FB_Reg16             -- регистры с защёлкой загрузки
    FB_FlagsReg                   -- регистр состояния P
    FB_ALU_6502                   -- арифметико-логическое устройство

ИНЖЕНЕРНЫЕ РЕШЕНИЯ (почему так):

1. Перенос (флаг C) считается НА БАЙТОВОМ УРОВНЕ:
       S1 := A + B (байт, с переполнением)   C1 := (S1 < A)
       S2 := S1 + CIN                        C2 := CIN AND (S2 < S1)
       C_out := C1 OR C2
   Это избавляет от 16-разрядных сумм и, главное, от блоков преобразования
   типов (BYTE_TO_WORD и т.п.), имена входных пинов у которых непроверяемы.
   Побочная выгода: логика переноса видна на схеме глазами, как в реальном ALU.

2. Дополнение операнда в SBC делается через XOR с $FF, а НЕ через блок NOT:
   семейство XOR/AND/OR имеет проверенные пины IN1/IN2, у NOT пин IN.

3. F_* (FUNCTION) против FB_* (FUNCTION_BLOCK):
   блоки без состояния (битовые операции, ALU, декодер) объявлены ФУНКЦИЯМИ --
   функцию можно вызывать из другой функции без экземпляра. Функциональные
   блоки оставлены там, где есть состояние (регистры, память) -- и именно они
   инстанцируются на главном листе.

Запуск:  python gen_layer1.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbd import Sheet, interface, pou_xml, or_bool, and_bool, or_tree_bool

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")

BYTE0 = u"BYTE#0"
BYTE1 = u"BYTE#1"
BYTEFF = u"BYTE#16#FF"
BYTE80 = u"BYTE#16#80"
TRUE = u"TRUE"
FALSE = u"FALSE"


def emit(name, kind, iface, sheets, comment=None):
    xml = pou_xml(name, kind, iface, sheets, comment)
    path = os.path.join(OUT, "%s.xml" % name)
    f = io.open(path, "w", encoding="utf-8")
    f.write(xml)
    f.close()
    nb = sum(len(s.els) for s in sheets)
    print(u"  %-16s %-14s сетей=%d элементов=%d -> %s.xml" % (name, kind, len(sheets), nb, name))
    return path


# =====================================================================
#  F_UnpackByte : BYTE -> ARRAY[0..7] OF BOOL
# =====================================================================
def gen_unpack():
    s = Sheet(u"Распаковка байта в 8 бит")
    v = s.var(u"IN", 0)
    for i in range(8):
        a = s.blk(u"AND", [(u"IN1", v), (u"IN2", s.const(u"BYTE#16#%02X" % (1 << i), 0))], 1)
        n = s.blk(u"NE", [(u"IN1", a), (u"IN2", s.const(BYTE0, 0))], 2, anchor=a)
        s.assign(u"B[%d]" % i, n, 3, anchor=a)
    return [s]


# =====================================================================
#  F_PackByte : ARRAY[0..7] OF BOOL -> BYTE
# =====================================================================
def gen_pack():
    s = Sheet(u"Упаковка 8 бит в байт")
    parts = []
    for i in range(8):
        b = s.var(u"B[%d]" % i, 0)
        t = s.blk(u"SEL", [(u"G", b), (u"IN0", s.const(BYTE0, 0)),
                           (u"IN1", s.const(u"BYTE#16#%02X" % (1 << i), 0))], 1)
        parts.append(t)
    # дерево OR
    col = 2
    while len(parts) > 1:
        nxt = []
        for j in range(0, len(parts) - 1, 2):
            nxt.append(s.blk(u"OR", [(u"IN1", parts[j]), (u"IN2", parts[j + 1])], col))
        if len(parts) % 2:
            nxt.append(parts[-1])
        parts = nxt
        col += 1
    s.assign(u"OUT", parts[0], col)
    return [s]


# =====================================================================
#  F_Join16 / F_Split16 : WORD <-> два BYTE  (little-endian)
# =====================================================================
def gen_join16():
    s = Sheet(u"Сборка 16-бит адреса: HI*256 + LO (little-endian)")
    lo = s.var(u"LO", 0)
    hi = s.var(u"HI", 0)
    wl = s.blk(u"BYTE_TO_WORD", [(u"IN", lo)], 1)
    wh = s.blk(u"BYTE_TO_WORD", [(u"IN", hi)], 1)
    sh = s.blk(u"MUL", [(u"IN1", wh), (u"IN2", s.const(u"WORD#256", 1))], 2)
    ad = s.blk(u"ADD", [(u"IN1", sh), (u"IN2", wl)], 3)
    s.assign(u"Q", ad, 4)
    return [s]


def gen_split16():
    s = Sheet(u"Разбор 16-бит адреса на LO и HI (little-endian)")
    v = s.var(u"IN", 0)
    lo = s.blk(u"WORD_TO_BYTE", [(u"IN", v)], 1)
    s.assign(u"LO", lo, 2)
    sh = s.blk(u"SHR", [(u"IN", v), (u"N", s.const(u"WORD#8", 1))], 1)
    hi = s.blk(u"WORD_TO_BYTE", [(u"IN", sh)], 2)
    s.assign(u"HI", hi, 3)
    return [s]


# =====================================================================
#  FB_Reg8 : регистр с защёлкой загрузки
#     Q := SEL(RESET, SEL(LOAD, Q, D), 0)
# =====================================================================
def gen_reg8():
    s = Sheet(u"Q := SEL(RESET, SEL(LOAD, Q, D), 0) — запись только при LOAD=TRUE")
    d = s.var(u"D", 0)
    q = s.var(u"Q", 0)
    ld = s.var(u"LOAD", 0)
    m = s.blk(u"SEL", [(u"G", ld), (u"IN0", q), (u"IN1", d)], 2)
    rs = s.var(u"RESET", 0)
    m2 = s.blk(u"SEL", [(u"G", rs), (u"IN0", m), (u"IN1", s.const(BYTE0, 2))], 3)
    s.assign(u"Q", m2, 4)
    return [s]


# =====================================================================
#  FB_Reg16 : 16-битный регистр (LO и HI отдельными защёлками)
#     Внутренние регистры сделаны встроенно (без вызова FB_Reg8),
#     чтобы у блока не было вложенных экземпляров.
# =====================================================================
def gen_reg16():
    s = Sheet(u"Старший и младший байты — две независимые защёлки LOAD/RESET")
    lo = s.var(u"D_LO", 0)
    hi = s.var(u"D_HI", 0)
    ql = s.var(u"Q_LO", 0)
    qh = s.var(u"Q_HI", 0)
    ld = s.var(u"LOAD", 0)
    rs = s.var(u"RESET", 0)
    m1 = s.blk(u"SEL", [(u"G", ld), (u"IN0", ql), (u"IN1", lo)], 2)
    m2 = s.blk(u"SEL", [(u"G", rs), (u"IN0", m1), (u"IN1", s.const(BYTE0, 2))], 3)
    s.assign(u"Q_LO", m2, 4)
    s.skip(0, 20)
    h1 = s.blk(u"SEL", [(u"G", ld), (u"IN0", qh), (u"IN1", hi)], 2)
    h2 = s.blk(u"SEL", [(u"G", rs), (u"IN0", h1), (u"IN1", s.const(BYTE0, 2))], 3)
    s.assign(u"Q_HI", h2, 4)
    return [s]


# =====================================================================
#  FB_FlagsReg : регистр состояния P
# =====================================================================
def gen_flags():
    s = Sheet(u"P_IN -> биты; обновление по SET_*; bit5 принудительно 1; обратно в P_OUT")
    p = s.var(u"P_IN", 0)
    unp = s.blk(u"F_UnpackByte", [(u"IN", p)], 1)
    s.assign(u"UNP", unp, 2)          # ВАЖНО: выход функции обязан попасть в UNP,
                                      # иначе биты UNP[i] читались бы "из ниоткуда"
    # локальные имена: B[0]=N B[1]=V B[2]=1 B[3]=B B[4]=D B[5]=I B[6]=Z B[7]=C
    ni = s.var(u"N_IN", 0)
    zi = s.var(u"Z_IN", 0)
    vi = s.var(u"V_IN", 0)
    ci = s.var(u"C_IN", 0)
    sn = s.var(u"SET_NZ", 0)
    sc = s.var(u"SET_C", 0)
    sv = s.var(u"SET_V", 0)
    clc = s.var(u"CMD_CLC", 0)
    sec = s.var(u"CMD_SEC", 0)

    def bit(i):
        return s.var(u"UNP[%d]" % i, 3)

    n = s.blk(u"SEL", [(u"G", sn), (u"IN0", bit(0)), (u"IN1", ni)], 4)
    z = s.blk(u"SEL", [(u"G", sn), (u"IN0", bit(6)), (u"IN1", zi)], 4)
    v = s.blk(u"SEL", [(u"G", sv), (u"IN0", bit(1)), (u"IN1", vi)], 4)
    c1 = s.blk(u"SEL", [(u"G", sc), (u"IN0", bit(7)), (u"IN1", ci)], 4)
    c2 = s.blk(u"SEL", [(u"G", sec), (u"IN0", c1), (u"IN1", s.const(TRUE, 4))], 5)
    c3 = s.blk(u"SEL", [(u"G", clc), (u"IN0", c2), (u"IN1", s.const(FALSE, 5))], 6)
    s.assign(u"PKD[0]", n, 7)
    s.assign(u"PKD[1]", v, 7)
    s.assign(u"PKD[2]", s.const(TRUE, 7), 7)          # bit5 ВСЕГДА 1
    s.assign(u"PKD[3]", bit(3), 7)                    # B
    s.assign(u"PKD[4]", bit(4), 7)                    # D
    s.assign(u"PKD[5]", bit(5), 7)                    # I
    s.assign(u"PKD[6]", z, 7)
    s.assign(u"PKD[7]", c3, 7)
    pk = s.blk(u"F_PackByte", [(u"B", s.var(u"PKD", 8))], 9)
    s.assign(u"P_OUT", pk, 10)
    # открытые наружу биты
    s.assign(u"N", n, 8)
    s.assign(u"Z", z, 8)
    s.assign(u"V", v, 8)
    s.assign(u"C", c3, 8)
    s.assign(u"B_FLAG", bit(3), 8)
    s.assign(u"D_FLAG", bit(4), 8)
    s.assign(u"I_FLAG", bit(5), 8)
    return [s]


# =====================================================================
#  FB_ALU_6502
# =====================================================================
def gen_alu():
    s = Sheet(u"ALU: BX — операнд, S1/S2 — байтовые суммы, C1/C2 — переносы, V — знаковое переполнение")
    s.wrap_cmp = False   # проверено: этой схеме разрыв связей компараторов вредит
    a = s.var(u"A", 0)
    b = s.var(u"B", 0)
    cin = s.var(u"CIN", 0)
    f_add = s.var(u"F_ADD", 0)
    f_sub = s.var(u"F_SUB", 0)
    f_cmp = s.var(u"F_CMP", 0)

    # --- выбор операнда: для SBC/CMP берём дополнение ---
    # Булева логика собрана на SEL (см. fbd.or_bool/and_bool): блоки OR/AND над
    # BOOL, соединяющие выходы других блоков, CODESYS при импорте не принимает.
    sub_or_cmp = or_bool(s, f_sub, f_cmp, 1)
    b_inv = s.blk(u"XOR", [(u"IN1", b), (u"IN2", s.const(BYTEFF, 1))], 1)
    bx = s.blk(u"SEL", [(u"G", sub_or_cmp), (u"IN0", b), (u"IN1", b_inv)], 2)

    # --- CINX: для ADC/SBC это входной C, для CMP всегда 1 ---
    cin_gate = and_bool(s, f_add, cin, 1)
    cin_gate2 = and_bool(s, f_sub, cin, 1)
    cin_or = or_bool(s, cin_gate, cin_gate2, 2)
    cinx = or_bool(s, cin_or, f_cmp, 3)

    # --- байтовые суммы и переносы ---
    s1 = s.blk(u"ADD", [(u"IN1", a), (u"IN2", bx)], 3)
    c1 = s.blk(u"LT", [(u"IN1", s1), (u"IN2", a)], 4)
    cinx_b = s.blk(u"SEL", [(u"G", cinx), (u"IN0", s.const(BYTE0, 4)), (u"IN1", s.const(BYTE1, 4))], 4)
    s2 = s.blk(u"ADD", [(u"IN1", s1), (u"IN2", cinx_b)], 5)
    lt2 = s.blk(u"LT", [(u"IN1", s2), (u"IN2", s1)], 5)
    c2 = and_bool(s, cinx, lt2, 6)
    c_out = or_bool(s, c1, c2, 7)

    # --- N и Z ---
    nf = s.blk(u"GE", [(u"IN1", s2), (u"IN2", s.const(BYTE80, 6))], 6)
    zf = s.blk(u"EQ", [(u"IN1", s2), (u"IN2", s.const(BYTE0, 6))], 6)

    # --- V: ADC  V = ~(A^B) & (A^S2) & $80
    #        SBC  V =  (A^B) & (A^S2) & $80   (B -- исходный операнд)
    xab = s.blk(u"XOR", [(u"IN1", a), (u"IN2", b)], 5)
    xar = s.blk(u"XOR", [(u"IN1", a), (u"IN2", s2)], 5)
    nxab = s.blk(u"XOR", [(u"IN1", xab), (u"IN2", s.const(BYTEFF, 5))], 6)
    va1 = and_bool(s, nxab, xar, 7)
    va2 = s.blk(u"AND", [(u"IN1", va1), (u"IN2", s.const(BYTE80, 7))], 8)
    v_add = s.blk(u"NE", [(u"IN1", va2), (u"IN2", s.const(BYTE0, 8))], 9)
    vs1 = and_bool(s, xab, xar, 7)
    vs2 = s.blk(u"AND", [(u"IN1", vs1), (u"IN2", s.const(BYTE80, 7))], 8)
    v_sub = s.blk(u"NE", [(u"IN1", vs2), (u"IN2", s.const(BYTE0, 8))], 9)
    vf = or_bool(s, v_add, v_sub, 10)

    s.assign(u"R", s2, 11)
    s.assign(u"N", nf, 11)
    s.assign(u"Z", zf, 11)
    s.assign(u"C", c_out, 11)
    s.assign(u"V", vf, 11)
    return [s]


# =====================================================================
def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print(u"Генерация слоя 1:")

    # ---- функции (без состояния) ----
    emit(u"F_UnpackByte", u"function",
         interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"B", u"ARRAY[0..7] OF BOOL")]),
         gen_unpack(), u"Распаковка BYTE в 8 логических бит. Здесь и только здесь биты выделяются из байта.")

    emit(u"F_PackByte", u"function",
         interface(inputs=[(u"B", u"ARRAY[0..7] OF BOOL")], outputs=[(u"OUT", u"BYTE")]),
         gen_pack(), u"Упаковка 8 бит в байт. Здесь и только здесь биты собираются в байт.")

    emit(u"F_Join16", u"function",
         interface(inputs=[(u"LO", u"BYTE"), (u"HI", u"BYTE")], outputs=[(u"Q", u"WORD")]),
         gen_join16(), u"Сборка 16-битного значения из двух байт, младший байт первый (little-endian).")

    emit(u"F_Split16", u"function",
         interface(inputs=[(u"IN", u"WORD")], outputs=[(u"LO", u"BYTE"), (u"HI", u"BYTE")]),
         gen_split16(), u"Разбор 16-битного значения на младший и старший байты.")

    # ---- функциональные блоки (есть состояние) ----
    emit(u"FB_Reg8", u"functionBlock",
         interface(inputs=[(u"D", u"BYTE"), (u"LOAD", u"BOOL"), (u"RESET", u"BOOL")],
                   outputs=[(u"Q", u"BYTE")]),
         gen_reg8(), u"8-битный регистр с защёлкой: пишется только при LOAD=TRUE. Комбинационный, не по фронту: такт задан сканом PLC.")

    emit(u"FB_Reg16", u"functionBlock",
         interface(inputs=[(u"D_LO", u"BYTE"), (u"D_HI", u"BYTE"), (u"LOAD", u"BOOL"), (u"RESET", u"BOOL")],
                   outputs=[(u"Q_LO", u"BYTE"), (u"Q_HI", u"BYTE")]),
         gen_reg16(), u"16-битный регистр (PC): два байта, две независимые защёлки загрузки.")

    emit(u"FB_FlagsReg", u"functionBlock",
         interface(inputs=[(u"P_IN", u"BYTE"), (u"N_IN", u"BOOL"), (u"Z_IN", u"BOOL"),
                           (u"C_IN", u"BOOL"), (u"V_IN", u"BOOL"),
                           (u"SET_NZ", u"BOOL"), (u"SET_C", u"BOOL"), (u"SET_V", u"BOOL"),
                           (u"CMD_CLC", u"BOOL"), (u"CMD_SEC", u"BOOL")],
                   outputs=[(u"P_OUT", u"BYTE"), (u"N", u"BOOL"), (u"Z", u"BOOL"),
                            (u"V", u"BOOL"), (u"C", u"BOOL"),
                            (u"B_FLAG", u"BOOL"), (u"D_FLAG", u"BOOL"), (u"I_FLAG", u"BOOL")],
                   locals_=[(u"UNP", u"ARRAY[0..7] OF BOOL"), (u"PKD", u"ARRAY[0..7] OF BOOL")]),
         gen_flags(), u"Регистр состояния P: N V 1 B D I Z C. Биты распаковываются F_UnpackByte, собираются F_PackByte; bit5 при упаковке ВСЕГДА 1.")

    emit(u"FB_ALU_6502", u"functionBlock",
         interface(inputs=[(u"A", u"BYTE"), (u"B", u"BYTE"), (u"CIN", u"BOOL"),
                           (u"F_ADD", u"BOOL"), (u"F_SUB", u"BOOL"), (u"F_CMP", u"BOOL")],
                   outputs=[(u"R", u"BYTE"), (u"N", u"BOOL"), (u"Z", u"BOOL"),
                            (u"C", u"BOOL"), (u"V", u"BOOL")],
                   locals_=[(u"BX", u"BYTE"), (u"S1", u"BYTE"), (u"S2", u"BYTE")]),
         gen_alu(), u"ALU 6502: ADC/SBC/CMP. Перенос считается на байтовом уровне (C1 := S1<A, C2 := CIN AND S2<S1), поэтому 16-битные суммы и преобразования типов не нужны.")

    print(u"Готово.")


if __name__ == "__main__":
    main()
