# -*- coding: utf-8 -*-
"""
gen_core.py -- FB_CPU_Core: ODIN TAKT 6502 NA ODNOM LISTE FBD.

Pochemu vse vstroeno, a ne vyzovy k FB_ALU_6502 / FB_AddrGen / FB_Stack /
FB_Branch: eti chetyre shemy CODESYS otvergaet po soderzhimomu (proverено
mnogokratno, na chistyh sessiyah, pri oboih nastroikah). No odin bolshoy list
importiruetsya nadezhno -- proverено na POU v 2039 elementov / 526 blokov.

Vyzovy FUNKCII (F_Join16, F_Split16, F_PackByte, F_UnpackByte) razresheny --
oni ne trebuyut ekzemplyara i uspeshno rabotayut vnutri FB_FlagsReg.

Sostoyanie zhivet v GVL_CPU, pamyat -- v GVL_MEM, poetomu chislo obrashcheniy
k pamyati ne ogranicheno (u FB_Memory64K bylo by 4 porta, dlya BRK/RTI nuzhno 3).

Vhod  Enable : BOOL -- razreshenie takta (multipleksor tsepochki yader).
Vyhod Done   : BOOL.
Rezultat: plcopen/FB_CPU_Core.xml
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml, or_tree_bool
from opcodes import (OPCODES, MODE_CODE, build_effects, BOOL_SIGNALS, BYTE_SIGNALS,
                     PC_BRK, PC_RTI, SP_PUSH3, SP_PULL3)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
FALLBACK = r"C:\CPM6502_build\plcopen"

CPU, MEM = u"GVL_CPU", u"GVL_MEM"
B0, B1, B2, B3 = u"BYTE#0", u"BYTE#1", u"BYTE#2", u"BYTE#3"
BFF, B80 = u"BYTE#16#FF", u"BYTE#16#80"
W1, W2, W256 = u"WORD#1", u"WORD#2", u"WORD#256"
T, F = u"TRUE", u"FALSE"

MODES = sorted(set(m for _, m, _ in OPCODES))
LOCALS = [
    (u"OP", u"BYTE"), (u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
    (u"EFF", u"WORD"), (u"MDR", u"BYTE"), (u"ALU_R", u"BYTE"),
    (u"ALU_AX", u"BYTE"), (u"ALU_BX", u"BYTE"), (u"ALU_CIN", u"BOOL"),
    (u"WDATA", u"BYTE"), (u"REG_WR", u"BYTE"), (u"TAKE", u"BOOL"),
    (u"PC_NEW", u"WORD"), (u"SP_NEW", u"BYTE"), (u"P_NEW", u"BYTE"),
    (u"UNP", u"ARRAY[0..7] OF BOOL"), (u"PKD", u"ARRAY[0..7] OF BOOL"),
    (u"ISUB", u"BOOL"), (u"CARRY1", u"BOOL"), (u"CARRY2", u"BOOL"),
    (u"ALTB", u"BOOL"), (u"XAB", u"BYTE"), (u"XAR", u"BYTE"), (u"NXAB", u"BYTE"),
]
for _s in BOOL_SIGNALS:
    LOCALS.append((_s, u"BOOL"))
for _s in (u"LD_A_E", u"LD_X_E", u"LD_Y_E", u"LD_P_E", u"LD_SP_E", u"WR_MEM_E"):
    LOCALS.append((_s, u"BOOL"))
for _s in BYTE_SIGNALS:
    LOCALS.append((_s, u"BYTE"))
for _m in MODES:
    LOCALS.append((u"IS_%s" % _m.upper(), u"BOOL"))
LOCALS += [(u"PCL", u"BYTE"), (u"PCH", u"BYTE"), (u"PC2", u"WORD"), (u"PC1", u"WORD"),
           (u"IZX_PTR", u"WORD"), (u"IZX_PTR1", u"WORD"),
           (u"IZY_PTR", u"WORD"), (u"IZY_PTR1", u"WORD"),
           (u"FLG_Z", u"BOOL"), (u"FLG_C", u"BOOL"),
           (u"PUNP", u"ARRAY[0..7] OF BOOL"),
           (u"SPM1", u"BYTE"), (u"SPP1", u"BYTE"), (u"SPP2", u"BYTE"), (u"SPP3", u"BYTE"),
           (u"STK_A0", u"WORD"), (u"STK_A1", u"WORD"), (u"STK_A2", u"WORD"),
           (u"STK_R0", u"WORD"), (u"STK_R1", u"WORD"), (u"STK_R2", u"WORD"),
           (u"WR0", u"WORD"), (u"WR1", u"WORD"), (u"WR2", u"WORD"),
           (u"WRD0", u"BYTE"), (u"WRD1", u"BYTE"), (u"WRD2", u"BYTE"),
           (u"WR_EN0", u"BOOL"), (u"WR_EN1", u"BOOL"), (u"WR_EN2", u"BOOL")]

_A = {}
LEVEL = int(os.environ.get("CORE_LEVEL", "99"))


def A(s, name, src, col=40):
    if name in _A:
        raise RuntimeError(u"повторная запись в %s" % name)
    _A[name] = True
    s.assign(name, src, col)


def E(s, expr, col=0):
    return s.var(expr, col)


def ORB(s, ids, col):
    return or_tree_bool(s, [i for i in ids if i is not None], col)


def ORT(s, ids, col):
    ids = [i for i in ids if i is not None]
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    cur, c = list(ids), col
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur) - 1, 2):
            nxt.append(s.blk(u"OR", [(u"IN1", cur[j]), (u"IN2", cur[j + 1])], c))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur, c = nxt, c + 1
    return cur[0]


def CAT(s, pairs, col):
    parts = []
    for g, v in pairs:
        if g is None:
            continue
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(B0, col)),
                                    (u"IN1", s.const(u"BYTE#%d" % v, col))], col))
    return ORT(s, parts, col + 2)


def gen():
    s = Sheet(u"FB_CPU_Core: выборка → дешифрация → адрес → чтение → ALU → флаги → запись → память → PC")
    eff = build_effects()
    en = s.const(u"TRUE", 0)

    # ============================================================ СНИМОК + ВЫБОРКА
    pc = E(s, CPU + u".PC", 0)
    op = E(s, MEM + u".Mem[" + CPU + u".PC]", 0)
    A(s, u"OP", op, 2)
    pc1 = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", s.const(W1, 0))], 0)
    pc2 = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", s.const(W2, 0))], 0)
    A(s, u"PC1", pc1, 2)
    A(s, u"PC2", pc2, 2)
    o1 = E(s, MEM + u".Mem[PC1]", 1)
    o2 = E(s, MEM + u".Mem[PC2]", 1)
    A(s, u"OP1", o1, 3)
    A(s, u"OP2", o2, 3)
    A(s, u"PCH", s.blk(u"WORD_TO_BYTE", [(u"IN", s.blk(u"SHR", [(u"IN", pc2), (u"N", s.const(u"WORD#8", 1))], 1))], 2), 3)
    A(s, u"PCL", s.blk(u"WORD_TO_BYTE", [(u"IN", pc2)], 2), 3)

    if LEVEL < 2: return s
    # ============================================================ ДЕШИФРАТОР
    # Декодер ВСТРАИВАЕТСЯ прямо в ядро, а не вызывается экземпляром.
    # Основания: (1) вариант с экземпляром FB_Decoder6502 отвергается импортом
    # дважды — в старой и новой среде; (2) встроенная версия на 2039 элементов
    # импортировалась успешно; (3) гипотеза «мешает сочетание экземпляра и
    # функций» ОПРОВЕРГНУТА отдельным пробником (POU C_BOTH создан).
    opv = E(s, u"OP", 4)
    eq = {}
    for mn, md, opc in OPCODES:
        eq[opc] = s.blk(u"EQ", [(u"IN1", opv), (u"IN2", s.const(u"BYTE#16#%02X" % opc, 4))], 4)

    def grp(pred):
        return ORB(s, [eq[o] for mn, md, o in OPCODES if pred(o, mn, md)], 5)

    for sig in BOOL_SIGNALS:
        g = grp(lambda o, mn, md, sg=sig: bool(eff.get(o, {}).get(sg, False)))
        if g is not None:
            A(s, sig, g)
    for sig in BYTE_SIGNALS:
        vals = sorted(set(eff.get(o, {}).get(sig, 0) for mn, md, o in OPCODES))
        pairs = [(grp(lambda o, mn, md, sg=sig, vv=v: eff.get(o, {}).get(sg, 0) == vv), v)
                 for v in vals if v != 0]
        r = CAT(s, pairs, 7)
        A(s, sig, r if r is not None else s.const(B0, 9))

    modev = E(s, u"ADDR_MODE", 10)
    mg = {}
    for m in MODES:
        mg[m] = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % MODE_CODE[m], 10))], 10)
        A(s, u"IS_%s" % m.upper(), mg[m])

    # гейтирование такта
    for sig in (u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM"):
        A(s, sig + u"_E", s.blk(u"SEL", [(u"G", E(s, sig, 11)), (u"IN0", s.const(F, 11)),
                                         (u"IN1", en)], 11))

    if LEVEL < 3: return s
    # ============================================================ АДРЕС
    x, y = E(s, CPU + u".X", 10), E(s, CPU + u".Y", 10)
    wlo = s.blk(u"BYTE_TO_WORD", [(u"IN", E(s, u"OP1", 10))], 10)
    whi = s.blk(u"MUL", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", E(s, u"OP2", 10))], 10)),
                         (u"IN2", s.const(W256, 10))], 11)
    AB = s.blk(u"ADD", [(u"IN1", whi), (u"IN2", wlo)], 12)
    zp = s.blk(u"ADD", [(u"IN1", E(s, u"OP1", 10)), (u"IN2", x)], 11)
    zpy = s.blk(u"ADD", [(u"IN1", E(s, u"OP1", 10)), (u"IN2", y)], 11)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", E(s, u"OP1", 10))], 11)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 12)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 12)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 12)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 12)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 13)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 13)
    # (indirect,X): указатель в нулевой странице, (indirect),Y: указатель, затем +Y
    izx_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 12)
    A(s, u"IZX_PTR", izx_ptr, 13)
    A(s, u"IZX_PTR1", s.blk(u"ADD", [(u"IN1", izx_ptr), (u"IN2", s.const(W1, 13))], 13), 14)
    izx_lo = E(s, MEM + u".Mem[IZX_PTR]", 14)
    izx_hi = E(s, MEM + u".Mem[IZX_PTR1]", 15)
    izx = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", izx_hi)], 14)),
                         (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", izx_lo)], 14))], 15)
    izy_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", E(s, u"OP1", 12))], 12)
    A(s, u"IZY_PTR", izy_ptr, 13)
    A(s, u"IZY_PTR1", s.blk(u"ADD", [(u"IN1", izy_ptr), (u"IN2", s.const(W1, 13))], 13), 14)
    izy_lo = E(s, MEM + u".Mem[IZY_PTR]", 14)
    izy_hi = E(s, MEM + u".Mem[IZY_PTR1]", 15)
    izy_b = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", izy_hi)], 14)),
                           (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", izy_lo)], 14))], 15)
    izy = s.blk(u"ADD", [(u"IN1", izy_b), (u"IN2", yw)], 16)
    # relative: PC+2 + знаковый offset
    sgn = s.blk(u"GE", [(u"IN1", E(s, u"OP1", 13)), (u"IN2", s.const(B80, 13))], 13)
    off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", E(s, u"OP1", 14)),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", E(s, u"OP1", 13)),
                                                 (u"IN2", s.const(B80, 14))], 14))], 15)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 15)),
                          (u"IN2", s.const(u"WORD#16#FF00", 15))], 16)
    relw = s.blk(u"ADD", [(u"IN1", E(s, u"PC2", 16)), (u"IN2", offw)], 17)
    # BRK: вектор $FFFE/FFFF читается как обычная память
    brk_lo = E(s, MEM + u".Mem[WORD#16#FFFE]", 14)
    brk_hi = E(s, MEM + u".Mem[WORD#16#FFFF]", 15)
    brk_v = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", brk_hi)], 15)),
                           (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", brk_lo)], 15))], 16)
    imm_w = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", s.const(W1, 16))], 17)

    cands = [(mg[u"imm"], imm_w), (mg[u"zp"], zpw), (mg[u"zpx"], zpxw), (mg[u"zpy"], zpyw),
             (mg[u"abs"], AB), (mg[u"abx"], abx), (mg[u"aby"], aby),
             (mg[u"izx"], izx), (mg[u"izy"], izy), (mg[u"ind"], izx), (mg[u"stk"], AB)]
    wp = [s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(u"WORD#0", 17)), (u"IN1", c)], 17)
          for g, c in cands]
    ef = ORT(s, wp, 19)
    A(s, u"EFF", ef if ef is not None else AB, 20)
    A(s, u"MDR", E(s, u"MDR_IMM", 20), 20) if False else None

    # чтение операнда: для IMM это OP1, иначе память по EFF
    mem_rd = E(s, MEM + u".Mem[EFF]", 20)
    A(s, u"WDATA", s.blk(u"SEL", [(u"G", mg[u"imm"]), (u"IN0", mem_rd),
                                  (u"IN1", E(s, u"OP1", 20))], 21), 22)

    if LEVEL < 4: return s
    # ============================================================ ALU
    a = E(s, CPU + u".A", 11)
    pv = E(s, CPU + u".P", 11)
    cin = s.blk(u"AND", [(u"IN1", pv), (u"IN2", s.const(B1, 11))], 11)   # бит C регистра P
    alu_a = s.blk(u"SEL", [(u"G", s.blk(u"EQ", [(u"IN1", E(s, u"ALU_A", 11)),
                                                (u"IN2", s.const(B1, 11))], 11)),
                            (u"IN0", a), (u"IN1", x)], 12)
    alu_b = s.blk(u"SEL", [(u"G", E(s, u"ALU_B", 11)),
                           (u"IN0", E(s, u"WDATA", 12)),
                           (u"IN1", s.const(B1, 12))], 12)
    A(s, u"ALU_AX", alu_a, 13)
    A(s, u"ALU_BX", alu_b, 13)
    isub = s.blk(u"SEL", [(u"G", E(s, u"F_SUB", 12)), (u"IN0", E(s, u"F_CMP", 12)),
                          (u"IN1", s.const(T, 12))], 13)
    A(s, u"ISUB", isub, 14)
    binv = s.blk(u"XOR", [(u"IN1", E(s, u"ALU_BX", 13)), (u"IN2", s.const(BFF, 13))], 14)
    bx = s.blk(u"SEL", [(u"G", E(s, u"ISUB", 14)), (u"IN0", E(s, u"ALU_BX", 13)),
                        (u"IN1", binv)], 15)
    cinx = s.blk(u"SEL", [(u"G", E(s, u"F_CMP", 13)), (u"IN0", E(s, u"ALU_CIN", 13)),
                          (u"IN1", s.const(T, 13))], 14)
    A(s, u"ALU_CIN", s.blk(u"SEL", [(u"G", E(s, u"USE_CARRY", 13)),
                                    (u"IN0", s.const(F, 13)),
                                    (u"IN1", s.blk(u"NE", [(u"IN1", E(s, CPU + u".P", 13)),
                                                           (u"IN2", s.const(u"BYTE#16#FF", 13))], 13))], 14), 15)
    s1 = s.blk(u"ADD", [(u"IN1", E(s, u"ALU_AX", 13)), (u"IN2", bx)], 16)
    c1 = s.blk(u"LT", [(u"IN1", s1), (u"IN2", E(s, u"ALU_AX", 13))], 16)
    A(s, u"CARRY1", c1, 17)
    cb = s.blk(u"SEL", [(u"G", E(s, u"ALU_CIN", 15)), (u"IN0", s.const(B0, 16)),
                        (u"IN1", s.const(B1, 16))], 16)
    s2 = s.blk(u"ADD", [(u"IN1", s1), (u"IN2", cb)], 17)
    c2 = s.blk(u"AND", [(u"IN1", E(s, u"ALU_CIN", 15)),
                        (u"IN2", s.blk(u"LT", [(u"IN1", s2), (u"IN2", s1)], 17))], 17)
    A(s, u"CARRY2", c2, 18)
    A(s, u"ALU_R", s2, 19)
    # V: ADC ~(A^B)&(A^R)&$80 ; SBC (A^B)&(A^R)&$80
    xab = s.blk(u"XOR", [(u"IN1", E(s, u"ALU_AX", 13)), (u"IN2", E(s, u"ALU_BX", 13))], 16)
    xar = s.blk(u"XOR", [(u"IN1", E(s, u"ALU_AX", 13)), (u"IN2", E(s, u"ALU_R", 19))], 19)
    A(s, u"XAB", xab, 17)
    A(s, u"XAR", xar, 20)
    A(s, u"NXAB", s.blk(u"XOR", [(u"IN1", E(s, u"XAB", 17)), (u"IN2", s.const(BFF, 17))], 18), 19)
    vadd_a = s.blk(u"AND", [(u"IN1", E(s, u"NXAB", 19)), (u"IN2", E(s, u"XAR", 20))], 20)
    vadd_b = s.blk(u"AND", [(u"IN1", vadd_a), (u"IN2", s.const(B80, 20))], 21)
    v_add = s.blk(u"NE", [(u"IN1", vadd_b), (u"IN2", s.const(B0, 21))], 22)
    vsub_a = s.blk(u"AND", [(u"IN1", E(s, u"XAB", 17)), (u"IN2", E(s, u"XAR", 20))], 20)
    vsub_b = s.blk(u"AND", [(u"IN1", vsub_a), (u"IN2", s.const(B80, 20))], 21)
    v_sub = s.blk(u"NE", [(u"IN1", vsub_b), (u"IN2", s.const(B0, 21))], 22)
    nf = s.blk(u"GE", [(u"IN1", E(s, u"ALU_R", 19)), (u"IN2", s.const(B80, 19))], 20)
    zf = s.blk(u"EQ", [(u"IN1", E(s, u"ALU_R", 19)), (u"IN2", s.const(B0, 19))], 20)

    if LEVEL < 5: return s
    # ============================================================ ФЛАГИ P
    unp = s.blk(u"F_UnpackByte", [(u"IN", E(s, CPU + u".P", 11))], 20)
    A(s, u"UNP", unp, 22)
    cs = s.blk(u"OR", [(u"IN1", E(s, u"CARRY1", 17)), (u"IN2", E(s, u"CARRY2", 18))], 18)
    n_new = s.blk(u"SEL", [(u"G", E(s, u"SET_NZ", 20)), (u"IN0", E(s, u"UNP[0]", 22)),
                           (u"IN1", nf)], 24)
    z_new = s.blk(u"SEL", [(u"G", E(s, u"SET_NZ", 20)), (u"IN0", E(s, u"UNP[6]", 22)),
                           (u"IN1", zf)], 24)
    c_new = s.blk(u"SEL", [(u"G", E(s, u"SET_C", 20)), (u"IN0", E(s, u"UNP[7]", 22)),
                           (u"IN1", cs)], 24)
    v_new = s.blk(u"SEL", [(u"G", E(s, u"SET_V", 20)), (u"IN0", E(s, u"UNP[1]", 22)),
                           (u"IN1", s.blk(u"SEL", [(u"G", E(s, u"F_SUB", 20)),
                                                   (u"IN0", v_add), (u"IN1", v_sub)], 22))], 24)
    c_cmd = s.blk(u"SEL", [(u"G", E(s, u"CMD_CLC", 24)), (u"IN0", c_new),
                           (u"IN1", s.const(F, 24))], 25)
    c_cmd2 = s.blk(u"SEL", [(u"G", E(s, u"CMD_SEC", 25)), (u"IN0", c_cmd),
                            (u"IN1", s.const(T, 25))], 26)
    i_cmd = s.blk(u"SEL", [(u"G", E(s, u"CMD_SEI", 24)), (u"IN0", E(s, u"UNP[5]", 22)),
                           (u"IN1", s.const(T, 24))], 25)
    i_cmd2 = s.blk(u"SEL", [(u"G", E(s, u"CMD_CLI", 25)), (u"IN0", i_cmd),
                            (u"IN1", s.const(F, 25))], 26)
    b_new = s.blk(u"SEL", [(u"G", E(s, u"SET_B", 24)), (u"IN0", E(s, u"UNP[3]", 22)),
                           (u"IN1", s.const(T, 24))], 25)
    A(s, u"PKD[0]", n_new, 27)
    A(s, u"PKD[1]", v_new, 27)
    A(s, u"PKD[2]", s.const(T, 27), 27)      # bit5 ВСЕГДА 1
    A(s, u"PKD[3]", b_new, 27)
    A(s, u"PKD[4]", E(s, u"UNP[4]", 22), 27)  # D не трогаем
    A(s, u"PKD[5]", i_cmd2, 27)
    A(s, u"PKD[6]", z_new, 27)
    A(s, u"PKD[7]", c_cmd2, 27)
    pnew = s.blk(u"F_PackByte", [(u"B", E(s, u"PKD", 28))], 29)
    A(s, u"P_NEW", pnew, 30)

    if LEVEL < 6: return s
    # ============================================================ СТЕК
    spv = E(s, CPU + u".SP", 10)
    A(s, u"SPM1", s.blk(u"SUB", [(u"IN1", spv), (u"IN2", s.const(B1, 10))], 11), 12)
    A(s, u"SPP1", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B1, 10))], 11), 12)
    A(s, u"SPP2", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B2, 11))], 11), 12)
    A(s, u"SPP3", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B3, 11))], 11), 12)

    def stk(b, col):
        return s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", b)], col)),
                              (u"IN2", s.const(u"WORD#256", col))], col)

    A(s, u"STK_A0", stk(spv, 13), 14)
    A(s, u"STK_A1", stk(E(s, u"SPM1", 12), 13), 14)
    A(s, u"STK_A2", stk(E(s, u"SPP1", 12), 13), 14)
    A(s, u"STK_R0", stk(E(s, u"SPP1", 12), 15), 16)
    A(s, u"STK_R1", stk(E(s, u"SPP2", 12), 15), 16)
    A(s, u"STK_R2", stk(E(s, u"SPP3", 12), 15), 16)

    # новый SP по SP_MODE
    sp_keep = E(s, CPU + u".SP", 12)
    d1 = s.blk(u"NE", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(B0, 12))], 12)
    push = s.blk(u"OR", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(B1, 12))], 12)),
                         (u"IN2", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(u"BYTE#5", 12))], 12))], 13)
    pull = s.blk(u"OR", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(B2, 12))], 12)),
                         (u"IN2", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(u"BYTE#6", 12))], 12))], 13)
    d2 = s.blk(u"OR", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(u"BYTE#5", 12))], 12)),
                       (u"IN2", s.blk(u"EQ", [(u"IN1", E(s, u"SP_MODE", 10)), (u"IN2", s.const(u"BYTE#6", 12))], 12))], 13)
    ns = s.blk(u"SEL", [(u"G", push), (u"IN0", s.blk(u"SEL", [(u"G", d2), (u"IN0", E(s, u"SPP1", 12)),
                                                               (u"IN1", E(s, u"SPP2", 12))], 14)),
                         (u"IN1", s.blk(u"SEL", [(u"G", d2), (u"IN0", E(s, u"SPM1", 12)),
                                                 (u"IN1", s.blk(u"SUB", [(u"IN1", E(s, CPU + u".SP", 12)),
                                                                         (u"IN2", s.const(B3, 13))], 13))], 14))], 15)
    A(s, u"SP_NEW", s.blk(u"SEL", [(u"G", d1), (u"IN0", sp_keep), (u"IN1", ns)], 17), 18)

    if LEVEL < 7: return s
    # ============================================================ ВЕТВЛЕНИЕ
    fl = s.blk(u"F_UnpackByte", [(u"IN", E(s, u"P_NEW", 30))], 31)
    # Флаги для ветвления берутся из НОВОГО значения P (с учётом SET_NZ/SET_C),
    # а не из старого: иначе BEQ/BNE/BCS/BCC сработают на устаревших флагах.
    # Выход функции -- массив, поэтому сначала кладём его в переменную PUNP,
    # а затем читаем элементы (так же сделано в FB_FlagsReg).
    A(s, u"PUNP", fl, 32)
    A(s, u"FLG_Z", E(s, u"PUNP[6]", 33), 34)
    A(s, u"FLG_C", E(s, u"PUNP[7]", 33), 34)
    take = ORB(s, [
        s.blk(u"AND", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"COND", 11)), (u"IN2", s.const(B0, 31))], 31)),
                       (u"IN2", E(s, u"FLG_Z", 32))], 32),
        s.blk(u"AND", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"COND", 11)), (u"IN2", s.const(B1, 31))], 31)),
                       (u"IN2", s.blk(u"XOR", [(u"IN1", E(s, u"FLG_Z", 32)), (u"IN2", s.const(T, 32))], 32))], 32),
        s.blk(u"AND", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"COND", 11)), (u"IN2", s.const(B2, 31))], 31)),
                       (u"IN2", E(s, u"FLG_C", 32))], 32),
        s.blk(u"AND", [(u"IN1", s.blk(u"EQ", [(u"IN1", E(s, u"COND", 11)), (u"IN2", s.const(B3, 31))], 31)),
                       (u"IN2", s.blk(u"XOR", [(u"IN1", E(s, u"FLG_C", 32)), (u"IN2", s.const(T, 32))], 32))], 32),
    ], 33)
    A(s, u"TAKE", take, 35)

    if LEVEL < 8: return s
    # ============================================================ НОВЫЙ PC
    p_w = s.blk(u"BYTE_TO_WORD", [(u"IN", E(s, u"LEN", 10))], 30)
    adv = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", p_w)], 31)
    pull_lo = E(s, MEM + u".Mem[STK_R0]", 30)
    pull_hi = E(s, MEM + u".Mem[STK_R1]", 30)
    jret = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", pull_hi)], 31)),
                          (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", pull_lo)], 31))], 32)
    back = s.blk(u"ADD", [(u"IN1", jret), (u"IN2", s.const(W1, 32))], 33)
    brn = s.blk(u"SEL", [(u"G", E(s, u"TAKE", 35)), (u"IN0", E(s, u"PC2", 33)),
                         (u"IN1", relw)], 34)
    pcm = E(s, u"PC_MODE", 30)
    sel = [(s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(B0, 34))], 34), adv),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(B1, 34))], 34), E(s, u"EFF", 20)),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(B2, 34))], 34), back),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(B3, 34))], 34), brn),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(u"BYTE#4", 34))], 34), pc),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(u"BYTE#5", 34))], 34), jret),
           (s.blk(u"EQ", [(u"IN1", pcm), (u"IN2", s.const(u"BYTE#6", 34))], 34), brk_v)]
    wp2 = [s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(u"WORD#0", 35)), (u"IN1", c)], 35)
           for g, c in sel]
    A(s, u"PC_NEW", ORT(s, wp2, 37), 39)

    if LEVEL < 9: return s
    # ============================================================ ЗАПИСЬ РЕГИСТРОВ
    # источник данных для записи в регистр
    sv = E(s, u"SRC", 30)
    srcs = [(0, E(s, CPU + u".A", 30)), (1, E(s, CPU + u".X", 30)), (2, E(s, CPU + u".Y", 30)),
            (3, E(s, u"P_NEW", 30)), (4, E(s, u"ALU_R", 30)), (5, E(s, u"PCL", 30)),
            (6, E(s, u"PCH", 30)), (7, pull_lo)]
    wp3 = [s.blk(u"SEL", [(u"G", s.blk(u"EQ", [(u"IN1", sv), (u"IN2", s.const(u"BYTE#%d" % k, 36))], 36)),
                          (u"IN0", s.const(B0, 36)), (u"IN1", c)], 36) for k, c in srcs]
    A(s, u"REG_WR", ORT(s, wp3, 38), 39)

    s.assign(CPU + u".A", s.blk(u"SEL", [(u"G", E(s, u"LD_A_E", 11)),
                                         (u"IN0", E(s, CPU + u".A", 39)),
                                         (u"IN1", E(s, u"REG_WR", 39))], 40), 41)
    s.assign(CPU + u".X", s.blk(u"SEL", [(u"G", E(s, u"LD_X_E", 11)),
                                         (u"IN0", E(s, CPU + u".X", 39)),
                                         (u"IN1", E(s, u"REG_WR", 39))], 40), 41)
    s.assign(CPU + u".Y", s.blk(u"SEL", [(u"G", E(s, u"LD_Y_E", 11)),
                                         (u"IN0", E(s, CPU + u".Y", 39)),
                                         (u"IN1", E(s, u"REG_WR", 39))], 40), 41)
    s.assign(CPU + u".P", s.blk(u"SEL", [(u"G", E(s, u"LD_P_E", 11)),
                                         (u"IN0", E(s, u"P_NEW", 41)),
                                         (u"IN1", E(s, u"REG_WR", 40))], 41), 42)
    s.assign(CPU + u".SP", s.blk(u"SEL", [(u"G", E(s, u"LD_SP_E", 11)),
                                          (u"IN0", E(s, CPU + u".SP", 39)),
                                          (u"IN1", E(s, u"SP_NEW", 39))], 40), 41)
    s.assign(CPU + u".PC", s.blk(u"SEL", [(u"G", en), (u"IN0", E(s, CPU + u".PC", 39)),
                                          (u"IN1", E(s, u"PC_NEW", 39))], 40), 41)

    if LEVEL < 10: return s
    # ============================================================ ЗАПИСЬ В ПАМЯТЬ
    # Три порта записи: обычная запись (STA/STX/STY), второй и третий байты
    # для JSR (PCH, PCL) и BRK (флаги, PCH, PCL). Адреса стека берутся из FB_Stack-логики.
    we = E(s, u"WR_MEM_E", 11)
    sm = E(s, u"SP_MODE", 10)
    push1 = s.blk(u"EQ", [(u"IN1", sm), (u"IN2", s.const(B1, 42))], 42)
    push3 = s.blk(u"EQ", [(u"IN1", sm), (u"IN2", s.const(u"BYTE#5", 42))], 42)
    jsr = E(s, u"IS_JSR", 42)
    stack_w = s.blk(u"OR", [(u"IN1", push1), (u"IN2", push3)], 43)
    wr_en0 = s.blk(u"OR", [(u"IN1", we), (u"IN2", s.blk(u"OR", [
        (u"IN1", jsr), (u"IN2", stack_w)], 43))], 44)          # пишем всегда, когда есть запись
    A(s, u"WR_EN0", wr_en0, 45)
    wr_addr = s.blk(u"SEL", [(u"G", stack_w), (u"IN0", E(s, u"EFF", 20)),
                             (u"IN1", E(s, u"STK_A0", 14))], 44)
    A(s, u"WR0", wr_addr, 45)
    wr_data = s.blk(u"SEL", [(u"G", push3), (u"IN0", E(s, u"REG_WR", 40)),
                             (u"IN1", E(s, u"P_NEW", 44))], 45)
    A(s, u"WRD0", wr_data, 46)
    A(s, u"WR1", E(s, u"STK_A1", 14), 45)
    A(s, u"WRD1", E(s, u"PCH", 30), 45)
    A(s, u"WR_EN1", s.blk(u"OR", [(u"IN1", jsr), (u"IN2", push3)], 45), 46)
    A(s, u"WR2", E(s, u"STK_A2", 14), 45)
    A(s, u"WRD2", E(s, u"PCL", 30), 45)
    A(s, u"WR_EN2", push3, 46)
    s.assign(MEM + u".Mem[WR0]", s.blk(u"SEL", [(u"G", E(s, u"WR_EN0", 45)),
                                         (u"IN0", E(s, MEM + u".Mem[WR0]", 46)),
                                         (u"IN1", E(s, u"WRD0", 46))], 47), 48)
    s.assign(MEM + u".Mem[WR1]", s.blk(u"SEL", [(u"G", E(s, u"WR_EN1", 46)),
                                         (u"IN0", E(s, MEM + u".Mem[WR1]", 46)),
                                         (u"IN1", E(s, u"WRD1", 46))], 47), 48)
    s.assign(MEM + u".Mem[WR2]", s.blk(u"SEL", [(u"G", E(s, u"WR_EN2", 46)),
                                         (u"IN0", E(s, MEM + u".Mem[WR2]", 46)),
                                         (u"IN1", E(s, u"WRD2", 46))], 47), 48)
    # программа не имеет выходов и входов: Enable заменён константой TRUE
    return s


def main():
    _A.clear()
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print(u"Генерация ядра FB_CPU_Core:")
    s = gen()
    xml = pou_xml(u"PRG_CPU_CORE", u"program",
                  interface(
                            locals_=LOCALS),
                  [s], u"Один такт MOS 6502: выборка, дешифрация, адрес, чтение, ALU, флаги, запись, стек, PC")
    # Декодер встроен в саму схему, поэтому экземпляр объявлять не нужно:
    # никаких <derived> и instanceName в этом POU нет.
    path = os.path.join(OUT, (u"PRG_CORE_L%d.xml" % LEVEL))
    try:
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
    except (IOError, OSError):
        path = os.path.join(FALLBACK, (u"PRG_CORE_L%d.xml" % LEVEL))
        if not os.path.isdir(FALLBACK):
            os.makedirs(FALLBACK)
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
        print(u"  ! записан в резервную папку")
    print(u"  элементов=%d блоков=%d -> %s"
          % (len(s.els), sum(1 for e in s.els if e.startswith(u"<block")), path))


if __name__ == "__main__":
    main()
