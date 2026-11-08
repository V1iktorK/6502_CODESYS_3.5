# -*- coding: utf-8 -*-
"""
gen_cpu_split.py -- DEKOMPOZICIYA YADRA 6502 NA SEM POU (vmesto odnogo lista).

Prichina (docs/05_DIAGNOSTIKA_IMPORTA_YADRA.md): edinyy list yadra (2729 elementov)
CODESYS molcha otvergaet nachinaya s elementa #2225, i ni odno iz izmereniy
(ob#em, razmer, otdelnye konstrukcii) eto ne ob#yasnyaet. Pilot
(FB_Fetch + FB_CorePilot) podtverdil, chto dekompoziciya rabotaet i chto
ekzemplyar mozhno podklyuchat KONTAKTAMI.

Sostav:
  FB_Decoder6502  Op -> 23 BOOL + 8 BYTE signalov
  FB_AddrMode     12 rezhimov adresacii -> EFF, WDATA, REL_DEST, BRK_VEC
  FB_ALU6502      slozhenie/vychitanie s perenosom -> ALU_R, CARRY, V, N, Z
  FB_Flags        N V - B D I Z C -> P_NEW + rasupakovannye flagi
  FB_PC_Update    stek + 7 rezhimov PC + vetvleniya -> PC_NEW, SP_NEW, TAKE
  FB_WriteBack    zapis A/X/Y/P/SP/PC -> REG_WR
  FB_CPU_Core     kompoziciya semi ekzemplyarov + tri porta zapisi v pamyat

Ispravleno otnositelno prezhnego vstroennogo varianta:
  * ALU_CIN beretsya iz bita 0 registra P (a ne iz "P <> $FF");
  * udalen mertvyy vyzov "cinx";
  * BYTE-signaly ALU_A/ALU_B privedeny k BOOL yavno cherez EQ s BYTE#1.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml, or_tree_bool
from opcodes import (OPCODES, MODE_CODE, build_effects, BOOL_SIGNALS, BYTE_SIGNALS)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")

CPU, MEM = u"GVL_CPU", u"GVL_MEM"
B0, B1, B2, B3 = u"BYTE#0", u"BYTE#1", u"BYTE#2", u"BYTE#3"
B80, BFF = u"BYTE#16#80", u"BYTE#16#FF"
W0, W1, W2, W256 = u"WORD#0", u"WORD#1", u"WORD#2", u"WORD#256"
T, F = u"TRUE", u"FALSE"
MODES = sorted(set(m for _, m, _ in OPCODES))
EFF = build_effects()
GATE = (u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM")


# ------------------------------------------------------------------ утилиты
def EQv(s, src, val, col):
    return s.blk(u"EQ", [(u"IN1", src), (u"IN2", s.const(val, col))], col)


def ANDb(s, a, b, col):
    return s.blk(u"AND", [(u"IN1", a), (u"IN2", b)], col)


def SELb(s, g, a, b, col):
    # Соглашение CODESYS: при G=TRUE выбирается IN1. Наш смысл: "при g -- a",
    # поэтому a ставим в IN1, а b -- в IN0.
    return s.blk(u"SEL", [(u"G", g), (u"IN0", b), (u"IN1", a)], col)


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


def byt(s, src, col):
    """BYTE-сигнал -> BOOL: истина, когда код равен 1."""
    return EQv(s, src, B1, col)


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-18s %8d байт" % (name, os.path.getsize(p)))


# ============================================================ 1. ДЕШИФРАТОР
def build_decoder():
    s = Sheet(u"FB_Decoder6502: код операции → управляющие сигналы")
    s.add_comment(u"Дешифратор: EQ по каждому коду, затем сборка сигналов деревьями OR / SEL")

    opv = s.ref(u"Op", 0)
    eq = {}
    for mn, md, opc in OPCODES:
        eq[opc] = EQv(s, opv, u"BYTE#16#%02X" % opc, 2)

    def grp(pred):
        return ORB(s, [eq[o] for mn, md, o in OPCODES if pred(o, mn, md)], 6)

    for sig in BOOL_SIGNALS:
        g = grp(lambda o, mn, md, sg=sig: bool(EFF.get(o, {}).get(sg, False)))
        s.assign(sig, g if g is not None else s.const(F, 8), 8)

    for sig in BYTE_SIGNALS:
        vals = sorted(set(EFF.get(o, {}).get(sig, 0) for mn, md, o in OPCODES))
        pairs = [(grp(lambda o, mn, md, sg=sig, vv=v: EFF.get(o, {}).get(sg, 0) == vv), v)
                 for v in vals if v != 0]
        r = CAT(s, pairs, 10)
        s.assign(sig, r if r is not None else s.const(B0, 12), 12)
    return s, []


# ============================================================ 2. АДРЕСАЦИЯ
def build_addrmode():
    s = Sheet(u"FB_AddrMode: 12 режимов адресации → эффективный адрес и операнд")
    s.add_comment(u"Режим выбирается сравнением ADDR_MODE с кодом; результат собирается деревом SEL")

    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    pc2 = s.ref(u"PC2", 0)
    modev = s.ref(u"ADDR_MODE", 0)

    mg = {}
    for m in MODES:
        mg[m] = EQv(s, modev, u"BYTE#%d" % MODE_CODE[m], 1)

    # ---- абсолютный адрес: старший байт слева, младший справа.
    # Вместо связки BYTE_TO_WORD + MUL + BYTE_TO_WORD + ADD — одна функция,
    # на схеме это один именованный блок с двумя входами (и короче, и понятнее).
    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 5, width=110)

    # ---- zero page, zero page,X и zero page,Y
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 3)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 3)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 4, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 6)

    # ---- (indirect,X): указатель лежит в нулевой странице
    izx_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 5, width=140)
    izx_ptr1 = s.blk(u"ADD", [(u"IN1", izx_ptr), (u"IN2", s.const(W1, 5))], 6)
    s.assign(u"IZX_PTR", izx_ptr, 6)
    s.assign(u"IZX_PTR1", izx_ptr1, 6)
    izx_lo = s.ref(MEM + u".Mem[IZX_PTR]", 7)
    izx_hi = s.ref(MEM + u".Mem[IZX_PTR1]", 7)
    izx = s.blk(u"F_Join16", [(u"LO", izx_lo), (u"HI", izx_hi)], 8, width=110)

    # ---- (indirect),Y
    izy_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 5, width=140)
    izy_ptr1 = s.blk(u"ADD", [(u"IN1", izy_ptr), (u"IN2", s.const(W1, 5))], 6)
    s.assign(u"IZY_PTR", izy_ptr, 6)
    s.assign(u"IZY_PTR1", izy_ptr1, 6)
    izy_lo = s.ref(MEM + u".Mem[IZY_PTR]", 7)
    izy_hi = s.ref(MEM + u".Mem[IZY_PTR1]", 7)
    izy_b = s.blk(u"F_Join16", [(u"LO", izy_lo), (u"HI", izy_hi)], 8, width=110)
    izy = s.blk(u"ADD", [(u"IN1", izy_b), (u"IN2", yw)], 9)

    # ---- relative: PC+2 + знаковый offset
    sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 6))], 6)
    off = s.blk(u"SEL", [(u"G", sgn),
                         (u"IN0", op1),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 7))], 7))], 8)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 8, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 8))], 9)
    relw = s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 10)

    # ---- вектор BRK $FFFE/$FFFF
    brk_lo = s.ref(MEM + u".Mem[WORD#16#FFFE]", 7)
    brk_hi = s.ref(MEM + u".Mem[WORD#16#FFFF]", 8)
    brk_v = s.blk(u"F_Join16", [(u"LO", brk_lo), (u"HI", brk_hi)], 10, width=110)

    # ---- immediate: адрес операнда = PC+1
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 9))], 10)

    cands = [(mg[u"imm"], imm_w), (mg[u"zp"], zpw), (mg[u"zpx"], zpxw), (mg[u"zpy"], zpyw),
             (mg[u"abs"], AB), (mg[u"abx"], abx), (mg[u"aby"], aby),
             (mg[u"izx"], izx), (mg[u"izy"], izy), (mg[u"ind"], izx), (mg[u"stk"], AB)]
    wp = [SELb(s, g, s.const(W0, 11), c, 11) for g, c in cands]
    ef = ORT(s, wp, 13)
    s.assign(u"EFF", ef if ef is not None else AB, 15)

    # ---- операнд: для IMM это OP1, иначе память по EFF
    mem_rd = s.ref(MEM + u".Mem[EFF]", 14)
    s.assign(u"WDATA", SELb(s, mg[u"imm"], mem_rd, op1, 16), 17)

    s.assign(u"REL_DEST", relw, 17)
    s.assign(u"BRK_VEC", brk_v, 17)

    L = [(u"IZX_PTR", u"WORD"), (u"IZX_PTR1", u"WORD"),
         (u"IZY_PTR", u"WORD"), (u"IZY_PTR1", u"WORD")]
    return s, L


# ============================================================ 3. АЛУ
def build_alu():
    s = Sheet(u"FB_ALU6502: сложение и вычитание с переносом")
    s.add_comment(u"Перенос: S1 = A + B даёт C1, затем прибавление переноса даёт C2; C = C1 OR C2")

    a = s.ref(u"A", 0)
    xv = s.ref(u"X", 0)
    yv = s.ref(u"Y", 0)
    pv = s.ref(u"P", 0)
    wd = s.ref(u"WDATA", 0)
    ucy = s.ref(u"USE_CARRY", 0)

    # ---- выбор операндов
    # ALU_A: 0 = A, 1 = X, 2 = Y
    au = s.ref(u"ALU_A", 0)
    ax_or_y = SELb(s, EQv(s, au, u"BYTE#2", 1), yv, a, 2)
    alu_a = SELb(s, byt(s, au, 1), ax_or_y, xv, 2)
    # ALU_B: 0 = операнд (MDR/WDATA), 1 = единица
    alu_b = SELb(s, byt(s, s.ref(u"ALU_B", 0), 1), wd, s.const(B1, 2), 2)
    # Команды загрузки не задают F_ADD/F_SUB/F_CMP: тогда АЛУ пропускает операнд,
    # то есть первый слагаемое обнуляется и ALU_R = WDATA.
    op_any = ORB(s, [s.ref(u"F_ADD", 0), s.ref(u"F_SUB", 0), s.ref(u"F_CMP", 0)], 2)
    alu_a = SELb(s, op_any, alu_a, s.const(B0, 2), 3)
    s.assign(u"ALU_AX", alu_a, 3)
    s.assign(u"ALU_BX", alu_b, 3)

    isub = SELb(s, s.ref(u"F_SUB", 0), s.ref(u"F_CMP", 0), s.const(T, 1), 3)
    s.assign(u"ISUB", isub, 4)

    # ---- вычитание через дополнение
    binv = s.blk(u"XOR", [(u"IN1", alu_b), (u"IN2", s.const(BFF, 3))], 4)
    bx = SELb(s, isub, alu_b, binv, 5)

    # ---- перенос на входе: бит 0 регистра P, разрешённый сигналом USE_CARRY
    pbit0 = s.blk(u"AND", [(u"IN1", pv), (u"IN2", s.const(B1, 2))], 2)
    cbit = EQv(s, pbit0, B1, 3) if False else s.blk(
        u"EQ", [(u"IN1", pbit0), (u"IN2", s.const(B1, 3))], 3)
    cin = SELb(s, ucy, s.const(F, 3), cbit, 4)
    s.assign(u"ALU_CIN", cin, 5)

    # ---- S1 = AX + BX; перенос C1 = S1 < AX
    s1 = s.blk(u"ADD", [(u"IN1", alu_a), (u"IN2", bx)], 6)
    c1 = s.blk(u"LT", [(u"IN1", s1), (u"IN2", alu_a)], 6)
    s.assign(u"CARRY1", c1, 7)

    # ---- прибавление переноса; C2 = CIN AND (S2 < S1)
    cb = SELb(s, cin, s.const(B0, 6), s.const(B1, 6), 6)
    s2 = s.blk(u"ADD", [(u"IN1", s1), (u"IN2", cb)], 7)
    c2 = ANDb(s, cin, s.blk(u"LT", [(u"IN1", s2), (u"IN2", s1)], 7), 7)
    s.assign(u"CARRY2", c2, 8)
    s.assign(u"ALU_R", s2, 9)
    s.assign(u"CARRY", s.blk(u"OR", [(u"IN1", c1), (u"IN2", c2)], 8), 9)

    # ---- флаг переполнения V
    xab = s.blk(u"XOR", [(u"IN1", alu_a), (u"IN2", alu_b)], 7)
    xar = s.blk(u"XOR", [(u"IN1", alu_a), (u"IN2", s2)], 9)
    nxab = s.blk(u"XOR", [(u"IN1", xab), (u"IN2", s.const(BFF, 8))], 8)
    va_b = ANDb(s, ANDb(s, nxab, xar, 9), s.const(B80, 9), 9)
    vs_b = ANDb(s, ANDb(s, xab, xar, 9), s.const(B80, 9), 9)
    s.assign(u"V_ADD", s.blk(u"NE", [(u"IN1", va_b), (u"IN2", s.const(B0, 9))], 10), 11)
    s.assign(u"V_SUB", s.blk(u"NE", [(u"IN1", vs_b), (u"IN2", s.const(B0, 9))], 10), 11)

    # ---- N и Z
    s.assign(u"N_F", s.blk(u"GE", [(u"IN1", s2), (u"IN2", s.const(B80, 9))], 10), 11)
    s.assign(u"Z_F", EQv(s, s2, B0, 10), 11)

    L = [(u"ALU_AX", u"BYTE"), (u"ALU_BX", u"BYTE"), 
         (u"ALU_CIN", u"BOOL"), (u"CARRY1", u"BOOL"), (u"CARRY2", u"BOOL")]
    return s, L


# ============================================================ 4. ФЛАГИ
def build_flags():
    s = Sheet(u"FB_Flags: регистр P (N V - B D I Z C), бит 5 всегда 1")
    s.add_comment(u"Каждый флаг собирается из трёх источников: вычисленное значение, команда, старое P")

    pv = s.ref(u"P", 0)
    setnz = s.ref(u"SET_NZ", 0)
    setc = s.ref(u"SET_C", 0)
    setv = s.ref(u"SET_V", 0)
    setb = s.ref(u"SET_B", 0)
    clc = s.ref(u"CMD_CLC", 0)
    sec = s.ref(u"CMD_SEC", 0)
    sei = s.ref(u"CMD_SEI", 0)
    cli = s.ref(u"CMD_CLI", 0)
    fsub = s.ref(u"F_SUB", 0)

    nf = s.ref(u"N_F", 0)
    zf = s.ref(u"Z_F", 0)
    va = s.ref(u"V_ADD", 0)
    vs = s.ref(u"V_SUB", 0)
    cr = s.ref(u"CARRY", 0)

    # ---- распаковка старого P: выход функции -- массив, поэтому через переменную
    s.assign(u"UNP", s.blk(u"F_UnpackByte", [(u"IN", pv)], 2, width=150), 3)

    n_new = SELb(s, setnz, s.ref(u"UNP[0]", 4), nf, 5)
    z_new = SELb(s, setnz, s.ref(u"UNP[6]", 4), zf, 5)
    c_new = SELb(s, setc, s.ref(u"UNP[7]", 4), cr, 5)
    v_new = SELb(s, setv, s.ref(u"UNP[1]", 4), SELb(s, fsub, va, vs, 5), 6)

    # ---- команды CLC/SEC и SEI/CLI имеют наивысший приоритет
    c_cmd = SELb(s, clc, c_new, s.const(F, 6), 7)
    c_cmd2 = SELb(s, sec, c_cmd, s.const(T, 6), 8)
    i_cmd = SELb(s, sei, s.ref(u"UNP[5]", 4), s.const(T, 7), 8)
    i_cmd2 = SELb(s, cli, i_cmd, s.const(F, 7), 9)
    b_new = SELb(s, setb, s.ref(u"UNP[3]", 4), s.const(T, 8), 9)

    s.assign(u"PKD[0]", n_new, 10)
    s.assign(u"PKD[1]", v_new, 10)
    s.assign(u"PKD[2]", s.const(T, 10), 10)          # бит 5 ВСЕГДА 1
    s.assign(u"PKD[3]", b_new, 10)
    s.assign(u"PKD[4]", s.ref(u"UNP[4]", 4), 10)      # D не изменяем
    s.assign(u"PKD[5]", i_cmd2, 10)
    s.assign(u"PKD[6]", z_new, 10)
    s.assign(u"PKD[7]", c_cmd2, 10)

    s.assign(u"P_NEW", s.blk(u"F_PackByte", [(u"B", s.ref(u"PKD", 11))], 11, width=150), 12)

    # ---- флаги НОВОГО P для логики ветвления
    s.assign(u"PUNP", s.blk(u"F_UnpackByte", [(u"IN", s.ref(u"P_NEW", 12))], 12, width=150), 13)
    for k, nm in ((0, u"FN"), (1, u"FV"), (3, u"FB"), (4, u"FD"),
                  (5, u"FI"), (6, u"FZ"), (7, u"FC")):
        s.assign(nm, s.ref(u"PUNP[%d]" % k, 14), 15)

    L = [(u"UNP", u"ARRAY[0..7] OF BOOL"), (u"PKD", u"ARRAY[0..7] OF BOOL"),
         (u"PUNP", u"ARRAY[0..7] OF BOOL")]
    return s, L


# ============================================================ 5. СТЕК + PC
def build_pc():
    s = Sheet(u"FB_PC_Update: стек, 7 режимов PC и ветвления")
    s.add_comment(u"Адреса стека $0100+SP; новый SP по SP_MODE; PC по PC_MODE; ветвление по COND")

    pcs = s.ref(u"PCs", 0)
    pc2 = s.ref(u"PC2", 0)
    eff = s.ref(u"EFF", 0)
    rel = s.ref(u"REL_DEST", 0)
    brk = s.ref(u"BRK_VEC", 0)
    lenv = s.ref(u"LEN", 0)
    pcm = s.ref(u"PC_MODE", 0)
    spm = s.ref(u"SP_MODE", 0)
    cond = s.ref(u"COND", 0)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    spv = s.ref(CPU + u".SP", 0)

    # ---- указатели вокруг SP
    s.assign(u"SPM1", s.blk(u"SUB", [(u"IN1", spv), (u"IN2", s.const(B1, 1))], 1), 2)
    s.assign(u"SPP1", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B1, 1))], 1), 2)
    s.assign(u"SPP2", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B2, 1))], 1), 2)
    s.assign(u"SPP3", s.blk(u"ADD", [(u"IN1", spv), (u"IN2", s.const(B3, 1))], 1), 2)

    def stk(b, col):
        # адрес стека +SP: страница стека всегда , младший байт -- SP
        return s.blk(u"F_Join16", [(u"LO", b), (u"HI", s.const(B1, col))], col, width=110)

    s.assign(u"STK_A0", stk(spv, 3), 4)
    s.assign(u"STK_A1", stk(s.ref(u"SPM1", 2), 3), 4)
    s.assign(u"STK_A2", stk(s.ref(u"SPP1", 2), 3), 4)
    s.assign(u"STK_R0", stk(s.ref(u"SPP1", 2), 4), 5)
    s.assign(u"STK_R1", stk(s.ref(u"SPP2", 2), 4), 5)
    s.assign(u"STK_R2", stk(s.ref(u"SPP3", 2), 4), 5)

    # ---- новый SP по SP_MODE
    d1 = s.blk(u"NE", [(u"IN1", spm), (u"IN2", s.const(B0, 2))], 3)
    push = ORB(s, [EQv(s, spm, B1, 4), EQv(s, spm, u"BYTE#5", 4)], 5)
    d2 = ORB(s, [EQv(s, spm, u"BYTE#5", 4), EQv(s, spm, u"BYTE#6", 4)], 5)
    ns = SELb(s, push,
              SELb(s, d2, s.ref(u"SPP1", 5), s.ref(u"SPP2", 5), 6),
              SELb(s, d2, s.ref(u"SPM1", 5),
                   s.blk(u"SUB", [(u"IN1", spv), (u"IN2", s.const(B3, 6))], 6), 6), 7)
    s.assign(u"SP_NEW", SELb(s, d1, spv, ns, 8), 9)

    # ---- ветвление по COND и флагам НОВОГО P
    take = ORB(s, [
        ANDb(s, EQv(s, cond, B0, 4), fz, 5),
        ANDb(s, EQv(s, cond, B1, 4), s.blk(u"NOT", [(u"IN", fz)], 5), 5),
        ANDb(s, EQv(s, cond, B2, 4), fc, 5),
        ANDb(s, EQv(s, cond, B3, 4), s.blk(u"NOT", [(u"IN", fc)], 5), 5),
    ], 6)
    s.assign(u"TAKE", take if take is not None else s.const(F, 8), 9)

    # ---- новый PC по PC_MODE
    pull_lo = s.ref(MEM + u".Mem[STK_R0]", 3)
    pull_hi = s.ref(MEM + u".Mem[STK_R1]", 3)
    s.assign(u"PULL_LO", pull_lo, 4)

    jret = s.blk(u"F_Join16", [(u"LO", pull_lo), (u"HI", pull_hi)], 7, width=110)
    back = s.blk(u"ADD", [(u"IN1", jret), (u"IN2", s.const(W1, 7))], 8)
    adv = s.blk(u"ADD", [(u"IN1", pcs),
                         (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", lenv)], 4, width=140))], 8)
    brn = SELb(s, s.ref(u"TAKE", 9), pc2, rel, 9)

    sel = [(EQv(s, pcm, B0, 10), adv),
           (EQv(s, pcm, B1, 10), eff),
           (EQv(s, pcm, B2, 10), back),
           (EQv(s, pcm, B3, 10), brn),
           (EQv(s, pcm, u"BYTE#4", 10), pcs),
           (EQv(s, pcm, u"BYTE#5", 10), jret),
           (EQv(s, pcm, u"BYTE#6", 10), brk)]
    wp2 = [SELb(s, g, s.const(W0, 11), c, 11) for g, c in sel]
    s.assign(u"PC_NEW", ORT(s, wp2, 13), 15)

    L = [(u"SPM1", u"BYTE"), (u"SPP1", u"BYTE"), (u"SPP2", u"BYTE"), (u"SPP3", u"BYTE"),
         (u"STK_A0", u"WORD"), (u"STK_A1", u"WORD"), (u"STK_A2", u"WORD"),
         (u"STK_R0", u"WORD"), (u"STK_R1", u"WORD"), (u"STK_R2", u"WORD"),
         (u"SP_NEW", u"BYTE"), (u"TAKE", u"BOOL"), (u"PULL_LO", u"BYTE"),
         (u"PC_NEW", u"WORD")]
    return s, L


# ============================================================ 6. ЗАПИСЬ
def build_writeback():
    s = Sheet(u"FB_WriteBack: запись регистров A, X, Y, P, SP, PC")
    s.add_comment(u"Источник записи выбирается кодом SRC; запрет записи -- сигналами LD_*_E")

    srcc = s.ref(u"SRC", 0)
    a = s.ref(u"A", 0)
    xv = s.ref(u"X", 0)
    yv = s.ref(u"Y", 0)
    pnew = s.ref(u"P_NEW", 0)
    alur = s.ref(u"ALU_R", 0)
    pcl = s.ref(u"PCL", 0)
    pch = s.ref(u"PCH", 0)
    pull = s.ref(u"PULL_LO", 0)

    srcs = [(0, a), (1, xv), (2, yv), (3, pnew), (4, alur),
            (5, pcl), (6, pch), (7, pull)]
    # Выбор источника записи. Вложенные generic-блоки (SEL внутри SEL) CODESYS
    # не типизирует ("Неизвестный тип ... __B..."), поэтому каждый шаг выводится
    # в ИМЕНОВАННУЮ переменную RWn, и следующий шаг читает уже имя, а не блок.
    cur = s.const(B0, 2)
    for i, (k, c) in enumerate(reversed(srcs)):
        g = EQv(s, srcc, u"BYTE#%d" % k, 1)
        # SEL(G, IN0, IN1): pri G=TRUE берётся IN1, poetoму IN1 = kandidat
        cur = SELb(s, g, cur, c, 3 + k)
        nm = u"RW%d" % (7 - k)
        s.assign(nm, cur, 12 + i)
        cur = s.ref(nm, 12 + i)
    s.assign(u"REG_WR", cur, 22)

    # Запись регистров вынесена в слой композиции FB_CPU_PcWb:
    # в этом листе CODESYS не типизировал SEL с регистровыми именами.
    s.assign(CPU + u".REG_WR", cur, 22)

    return s, [(u"RW%d" % k, u"BYTE") for k in range(8)]


# ============================================================ 7. КОМПОЗИЦИЯ
def build_core():
    s = Sheet(u"FB_CPU_Core: один такт MOS 6502 из семи ступеней")
    s.add_comment(u"Выборка → дешифрация → адрес → АЛУ → флаги → PC/стек → запись; "
                  u"плюс три порта записи в память")

    enable = s.ref(u"Enable", 0)

    # ---------------- выборка
    fch = s.blk(u"FB_Fetch", [(u"PCs", s.ref(CPU + u".PC", 2))], 2, width=110, inst=u"Fch")
    for pin, dst in ((u"OPs", u"OP"), (u"OP1", u"OP1"), (u"OP2", u"OP2"),
                     (u"PC2", u"PC2"), (u"PCL", u"PCL"), (u"PCH", u"PCH")):
        s.assign(dst, fch, 4, src_pin=pin)

    # ---------------- дешифрация
    dec = s.blk(u"FB_Decoder6502", [(u"Op", s.ref(u"OP", 5))], 6, width=160, inst=u"Dec")
    for sig in BOOL_SIGNALS:
        s.assign(sig, dec, 8, src_pin=sig)
    for sig in BYTE_SIGNALS:
        s.assign(sig, dec, 9, src_pin=sig)

    # ---------------- гейтирование такта (цепочка ядер)
    for sig in GATE:
        s.assign(sig + u"_E", ANDb(s, s.ref(sig, 10), enable, 11), 12)

    # ---------------- адресация
    adr = s.blk(u"FB_AddrMode",
                [(u"OP1", s.ref(u"OP1", 12)), (u"OP2", s.ref(u"OP2", 12)),
                 (u"X", s.ref(CPU + u".X", 12)), (u"Y", s.ref(CPU + u".Y", 12)),
                 (u"PCs", s.ref(CPU + u".PC", 12)), (u"PC2", s.ref(u"PC2", 12)),
                 (u"ADDR_MODE", s.ref(u"ADDR_MODE", 12))], 13, width=160, inst=u"Adr")
    for pin, dst in ((u"EFF", u"EFF"), (u"WDATA", u"WDATA"),
                     (u"REL_DEST", u"REL_DEST"), (u"BRK_VEC", u"BRK_VEC")):
        s.assign(dst, adr, 15, src_pin=pin)

    # ---------------- АЛУ
    alu = s.blk(u"FB_ALU6502",
                [(u"A", s.ref(CPU + u".A", 17)), (u"X", s.ref(CPU + u".X", 17)),
                 (u"P", s.ref(CPU + u".P", 17)), (u"WDATA", s.ref(u"WDATA", 17)),
                 (u"ALU_A", s.ref(u"ALU_A", 17)), (u"ALU_B", s.ref(u"ALU_B", 17)),
                 (u"F_SUB", s.ref(u"F_SUB", 17)), (u"F_CMP", s.ref(u"F_CMP", 17)),
                 (u"USE_CARRY", s.ref(u"USE_CARRY", 17))], 18, width=130, inst=u"Alu")
    for pin in (u"ALU_R", u"CARRY", u"V_ADD", u"V_SUB", u"N_F", u"Z_F"):
        s.assign(pin, alu, 20, src_pin=pin)

    # ---------------- флаги
    flg = s.blk(u"FB_Flags",
                [(u"P", s.ref(CPU + u".P", 22))] +
                [(sg, s.ref(sg, 22)) for sg in
                 (u"SET_NZ", u"SET_C", u"SET_V", u"SET_B", u"CMD_CLC", u"CMD_SEC",
                  u"CMD_SEI", u"CMD_CLI", u"F_SUB")] +
                [(sg, s.ref(sg, 22)) for sg in (u"N_F", u"Z_F", u"V_ADD", u"V_SUB", u"CARRY")],
                23, width=120, inst=u"Flg")
    for pin in (u"P_NEW", u"FZ", u"FC"):
        s.assign(pin, flg, 25, src_pin=pin)

    # ---------------- PC и стек
    pcu = s.blk(u"FB_PC_Update",
                [(u"PCs", s.ref(CPU + u".PC", 27)), (u"PC2", s.ref(u"PC2", 27)),
                 (u"EFF", s.ref(u"EFF", 27)), (u"REL_DEST", s.ref(u"REL_DEST", 27)),
                 (u"BRK_VEC", s.ref(u"BRK_VEC", 27)), (u"LEN", s.ref(u"LEN", 27)),
                 (u"PC_MODE", s.ref(u"PC_MODE", 27)), (u"SP_MODE", s.ref(u"SP_MODE", 27)),
                 (u"COND", s.ref(u"COND", 27)), (u"FZ", s.ref(u"FZ", 27)),
                 (u"FC", s.ref(u"FC", 27))], 28, width=140, inst=u"Pcu")
    for pin in (u"PC_NEW", u"SP_NEW", u"TAKE", u"PULL_LO",
                u"STK_A0", u"STK_A1", u"STK_A2"):
        s.assign(pin, pcu, 30, src_pin=pin)

    # ---------------- запись регистров
    wbk = s.blk(u"FB_WriteBack",
                [(u"SRC", s.ref(u"SRC", 32)), (u"A", s.ref(CPU + u".A", 32)),
                 (u"X", s.ref(CPU + u".X", 32)), (u"Y", s.ref(CPU + u".Y", 32)),
                 (u"P_NEW", s.ref(u"P_NEW", 32)), (u"ALU_R", s.ref(u"ALU_R", 32)),
                 (u"PCL", s.ref(u"PCL", 32)), (u"PCH", s.ref(u"PCH", 32)),
                 (u"PULL_LO", s.ref(u"PULL_LO", 32)), (u"SP_NEW", s.ref(u"SP_NEW", 32)),
                 (u"PC_NEW", s.ref(u"PC_NEW", 32)), (u"Enable", enable)] +
                [(sg, s.ref(sg, 32)) for sg in
                 (u"LD_A_E", u"LD_X_E", u"LD_Y_E", u"LD_P_E", u"LD_SP_E")],
                33, width=140, inst=u"Wbk")
    s.assign(u"REG_WR", wbk, 35, src_pin=u"REG_WR")

    # ---------------- три порта записи в память
    we = s.ref(u"WR_MEM_E", 36)
    sm = s.ref(u"SP_MODE", 36)
    push1 = EQv(s, sm, B1, 36)
    push3 = EQv(s, sm, u"BYTE#5", 36)
    jsr = s.ref(u"IS_JSR", 36)
    stack_w = s.blk(u"OR", [(u"IN1", push1), (u"IN2", push3)], 37)
    s.assign(u"WR_EN0", ORB(s, [we, jsr, stack_w], 38), 39)
    s.assign(u"WR0", SELb(s, stack_w, s.ref(u"EFF", 37), s.ref(u"STK_A0", 37), 38), 39)
    s.assign(u"WRD0", SELb(s, push3, s.ref(u"REG_WR", 38), s.ref(u"P_NEW", 38), 39), 40)
    s.assign(u"WR1", s.ref(u"STK_A1", 37), 39)
    s.assign(u"WRD1", s.ref(u"PCH", 38), 39)
    s.assign(u"WR_EN1", s.blk(u"OR", [(u"IN1", jsr), (u"IN2", push3)], 38), 39)
    s.assign(u"WR2", s.ref(u"STK_A2", 37), 39)
    s.assign(u"WRD2", s.ref(u"PCL", 38), 39)
    s.assign(u"WR_EN2", push3, 40)

    s.assign(MEM + u".Mem[WR0]",
             SELb(s, s.ref(u"WR_EN0", 40), s.ref(MEM + u".Mem[WR0]", 40),
                  s.ref(u"WRD0", 40), 41), 42)
    s.assign(MEM + u".Mem[WR1]",
             SELb(s, s.ref(u"WR_EN1", 40), s.ref(MEM + u".Mem[WR1]", 40),
                  s.ref(u"WRD1", 40), 41), 42)
    s.assign(MEM + u".Mem[WR2]",
             SELb(s, s.ref(u"WR_EN2", 40), s.ref(MEM + u".Mem[WR2]", 40),
                  s.ref(u"WRD2", 40), 41), 42)

    s.assign(u"Done", enable, 43)
    return s


def core_locals():
    L = [(u"OP", u"BYTE"), (u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
         (u"PCL", u"BYTE"), (u"PCH", u"BYTE"), (u"PC2", u"WORD"),
         (u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
         (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD"),
         (u"ALU_R", u"BYTE"), (u"CARRY", u"BOOL"), (u"V_ADD", u"BOOL"),
         (u"V_SUB", u"BOOL"), (u"N_F", u"BOOL"), (u"Z_F", u"BOOL"),
         (u"P_NEW", u"BYTE"), (u"FZ", u"BOOL"), (u"FC", u"BOOL"),
         (u"PC_NEW", u"WORD"), (u"SP_NEW", u"BYTE"), (u"TAKE", u"BOOL"),
         (u"PULL_LO", u"BYTE"), (u"REG_WR", u"BYTE"),
         (u"STK_A0", u"WORD"), (u"STK_A1", u"WORD"), (u"STK_A2", u"WORD"),
         (u"WR0", u"WORD"), (u"WR1", u"WORD"), (u"WR2", u"WORD"),
         (u"WRD0", u"BYTE"), (u"WRD1", u"BYTE"), (u"WRD2", u"BYTE"),
         (u"WR_EN0", u"BOOL"), (u"WR_EN1", u"BOOL"), (u"WR_EN2", u"BOOL")]
    for sg in BOOL_SIGNALS:
        L.append((sg, u"BOOL"))
    for sg in BYTE_SIGNALS:
        L.append((sg, u"BYTE"))
    for sg in GATE:
        L.append((sg + u"_E", u"BOOL"))
    L.append((u"Done", u"BOOL"))
    for inst, typ in ((u"Fch", u"FB_Fetch"), (u"Dec", u"FB_Decoder6502"),
                      (u"Adr", u"FB_AddrMode"), (u"Alu", u"FB_ALU6502"),
                      (u"Flg", u"FB_Flags"), (u"Pcu", u"FB_PC_Update"),
                      (u"Wbk", u"FB_WriteBack")):
        L.append((inst, typ))
    return L


def main():
    print(u"=== gen_cpu_split: декомпозиция ядра ===")

    s, L = build_decoder()
    write(u"FB_Decoder6502", pou_xml(
        u"FB_Decoder6502", u"functionBlock",
        interface(inputs=[(u"Op", u"BYTE")],
                  outputs=[(sg, (u"BYTE" if sg in BYTE_SIGNALS else u"BOOL"))
                           for sg in list(BOOL_SIGNALS) + list(BYTE_SIGNALS)],
                  locals_=L),
        [s], u"Дешифратор кода операции MOS 6502"))

    s, L = build_addrmode()
    write(u"FB_AddrMode", pou_xml(
        u"FB_AddrMode", u"functionBlock",
        interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                          (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD"),
                          (u"ADDR_MODE", u"BYTE")],
                  outputs=[(u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
                           (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD")],
                  locals_=L),
        [s], u"Адресация MOS 6502"))

    s, L = build_alu()
    write(u"FB_ALU6502", pou_xml(
        u"FB_ALU6502", u"functionBlock",
        interface(inputs=[(u"A", u"BYTE"), (u"X", u"BYTE"), (u"P", u"BYTE"),
                          (u"WDATA", u"BYTE"), (u"ALU_A", u"BYTE"), (u"ALU_B", u"BYTE"),
                          (u"F_SUB", u"BOOL"), (u"F_CMP", u"BOOL"), (u"USE_CARRY", u"BOOL")],
                  outputs=[(u"ALU_R", u"BYTE"), (u"CARRY", u"BOOL"), (u"V_ADD", u"BOOL"),
                           (u"V_SUB", u"BOOL"), (u"N_F", u"BOOL"), (u"Z_F", u"BOOL"),
                           (u"ISUB", u"BOOL")],
                  locals_=L),
        [s], u"АЛУ MOS 6502"))

    s, L = build_flags()
    write(u"FB_Flags", pou_xml(
        u"FB_Flags", u"functionBlock",
        interface(inputs=[(u"P", u"BYTE")] +
                        [(sg, u"BOOL") for sg in
                         (u"SET_NZ", u"SET_C", u"SET_V", u"SET_B", u"CMD_CLC",
                          u"CMD_SEC", u"CMD_SEI", u"CMD_CLI", u"F_SUB")] +
                        [(sg, u"BOOL") for sg in
                         (u"N_F", u"Z_F", u"V_ADD", u"V_SUB", u"CARRY")],
                  outputs=[(u"P_NEW", u"BYTE")] +
                          [(sg, u"BOOL") for sg in
                           (u"FN", u"FV", u"FB", u"FD", u"FI", u"FZ", u"FC")],
                  locals_=L),
        [s], u"Флаги MOS 6502"))

    s, L = build_pc()
    write(u"FB_PC_Update", pou_xml(
        u"FB_PC_Update", u"functionBlock",
        interface(inputs=[(u"PCs", u"WORD"), (u"PC2", u"WORD"), (u"EFF", u"WORD"),
                          (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD"),
                          (u"LEN", u"BYTE"), (u"PC_MODE", u"BYTE"), (u"SP_MODE", u"BYTE"),
                          (u"COND", u"BYTE"), (u"FZ", u"BOOL"), (u"FC", u"BOOL")],
                  outputs=[(u"PC_NEW", u"WORD"), (u"SP_NEW", u"BYTE"), (u"TAKE", u"BOOL"),
                           (u"PULL_LO", u"BYTE"),
                           (u"STK_A0", u"WORD"), (u"STK_A1", u"WORD"), (u"STK_A2", u"WORD"),
                           (u"STK_R0", u"WORD"), (u"STK_R1", u"WORD"), (u"STK_R2", u"WORD")],
                  locals_=L),
        [s], u"PC и стек MOS 6502"))

    s, L = build_writeback()
    write(u"FB_WriteBack", pou_xml(
        u"FB_WriteBack", u"functionBlock",
        interface(inputs=[(u"SRC", u"BYTE"), (u"A", u"BYTE"), (u"X", u"BYTE"), (u"Y", u"BYTE"),
                          (u"P_NEW", u"BYTE"), (u"ALU_R", u"BYTE"), (u"PCL", u"BYTE"),
                          (u"PCH", u"BYTE"), (u"PULL_LO", u"BYTE"), (u"SP_NEW", u"BYTE"),
                          (u"PC_NEW", u"WORD"), (u"Enable", u"BOOL"),
                          (u"LD_A_E", u"BOOL"), (u"LD_X_E", u"BOOL"), (u"LD_Y_E", u"BOOL"),
                          (u"LD_P_E", u"BOOL"), (u"LD_SP_E", u"BOOL")],
                  outputs=[],
                  locals_=L),
        [s], u"Запись регистров MOS 6502"))

    write(u"FB_CPU_Core", pou_xml(
        u"FB_CPU_Core", u"functionBlock",
        interface(inputs=[(u"Enable", u"BOOL")], outputs=[(u"Done", u"BOOL")],
                  locals_=core_locals()),
        [build_core()], u"Один такт MOS 6502"))

    print(u"готово")


if __name__ == "__main__":
    main()
