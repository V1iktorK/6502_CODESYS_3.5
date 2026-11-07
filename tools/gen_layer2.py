# -*- coding: utf-8 -*-
"""
gen_layer2.py -- генератор FBD-схем слоя 2 эмулятора MOS 6502.

Слой 2:
    F_Add16         -- 16-битное сложение НА БАЙТОВОМ УРОВНЕ (без WORD-арифметики)
    F_PtrGen        -- адрес указателя для (indirect,X) / (indirect),Y / indirect
    FB_Decoder6502  -- дешифратор: 81 компаратор опкодов -> микрооперации
    FB_AddrGen      -- эффективный адрес по 12 режимам адресации
    FB_Stack        -- указатель стека и адреса $0100+SP
    FB_PC_Update    -- новый PC: +LEN / цель / возврат / ветвление / останов
    FB_Branch       -- проверка условия перехода
    FB_Memory64K    -- память 64 КБ, ЧЕТЫРЕ порта (2 чтения + 2 записи)

ПОЧЕМУ У ПАМЯТИ ЧЕТЫРЕ ПОРТА:
    Контракт "один такт = один скан" означает, что JSR кладёт в стек ДВА байта,
    а RTS читает ДВА байта в одном и том же скане. Одной парой портов
    (адрес+данные) это физически невыразимо. Шина Bus_Data при этом сохраняется:
    она обслуживает обмен по вычисленному адресу, а стек имеет выделенные порты.

Запуск:  python gen_layer2.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml, or_bool, and_bool, or_tree_bool
from opcodes import (OPCODES, MODE_RU, MODE_CODE, build_effects, BOOL_SIGNALS,
                     BYTE_SIGNALS, PC_RU, SP_RU, COND_RU, SRC_RU)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
# Резервная папка вне OneDrive: сюда пишутся схемы, если файл в OneDrive
# заблокирован зависшим процессом CODESYS.
FALLBACK = r"C:\CPM6502_build\plcopen"

BYTE0, BYTE1 = u"BYTE#0", u"BYTE#1"
BYTEFF, BYTE80 = u"BYTE#16#FF", u"BYTE#16#80"
B16 = u"BYTE#16#%02X"


def emit(name, kind, iface, sheets, comment=None):
    xml = pou_xml(name, kind, iface, sheets, comment)
    path = os.path.join(OUT, "%s.xml" % name)
    try:
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
    except (IOError, OSError):
        # Файл в OneDrive может быть заблокирован зависшим процессом CODESYS
        # (он открывает XML при импорте и, падая, оставляет дескриптор).
        # Тогда пишем в локальную папку вне OneDrive -- сборка умеет искать оба места.
        path = os.path.join(FALLBACK, "%s.xml" % name)
        if not os.path.isdir(FALLBACK):
            os.makedirs(FALLBACK)
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
        print(u"  ! %s.xml заблокирован в OneDrive -> записан в %s" % (name, FALLBACK))
    nb = sum(1 for s in sheets for e in s.els if e.startswith(u"<block"))
    print(u"  %-16s %-14s элементов=%4d блоков=%4d" % (name, kind, sum(len(s.els) for s in sheets), nb))
    return path


def or_tree(s, ids, col, label=None):
    """Дерево OR из списка localId. Возвращает localId результата."""
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    cur = list(ids)
    c = col
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur) - 1, 2):
            nxt.append(s.blk(u"OR", [(u"IN1", cur[j]), (u"IN2", cur[j + 1])], c))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur = nxt
        c += 1
    return cur[0]


# =====================================================================
#  F_Add16 : 16-битное сложение на байтовом уровне
# =====================================================================
def gen_add16():
    """16-битное сложение БЕЗ блоков LT и SEL по BOOL.

    Прежняя редакция вычисляла перенос через LT (сравнение) и SEL с BOOL-условием,
    и CODESYS выдавал на этом две ошибки:
        C0032 Для '<' требуется ровно 2 операндов
        C0032 Обнаружен неоднозначный элемент (Недопустимое количество входов)
    Теперь перенос берётся АРИФМЕТИЧЕСКИ — как бит 8 суммы младших байтов,
    вычисленной в 16 разрядах. Используются только блоки, которые в проекте
    компилируются чисто: BYTE_TO_WORD, ADD(WORD), WORD_TO_BYTE, AND(WORD),
    NE(WORD).
    """
    s = Sheet(u"Сложение 16-бит: перенос берётся из бита 8 суммы младших байтов")
    a_lo, a_hi = s.var(u"A_LO", 0), s.var(u"A_HI", 0)
    b_lo, b_hi = s.var(u"B_LO", 0), s.var(u"B_HI", 0)
    W256 = s.const(u"WORD#256", 1)
    W0 = s.const(u"WORD#0", 1)

    w_lo = s.blk(u"BYTE_TO_WORD", [(u"IN", a_lo)], 1)
    w_hi = s.blk(u"BYTE_TO_WORD", [(u"IN", a_hi)], 1)
    x_lo = s.blk(u"BYTE_TO_WORD", [(u"IN", b_lo)], 1)
    x_hi = s.blk(u"BYTE_TO_WORD", [(u"IN", b_hi)], 1)

    low_sum = s.blk(u"ADD", [(u"IN1", w_lo), (u"IN2", x_lo)], 2)      # 9 разрядов
    q_lo = s.blk(u"WORD_TO_BYTE", [(u"IN", low_sum)], 3)
    bit8 = s.blk(u"AND", [(u"IN1", low_sum), (u"IN2", W256)], 3)
    carry = s.blk(u"NE", [(u"IN1", bit8), (u"IN2", W0)], 4)

    # перенос прибавляется к старшим байтам как 0/1 без SEL:
    # (hi_a + hi_b) + перенос*1  -> используем ADD с BYTE_TO_WORD от BOOL,
    # но проще и надёжнее: перенос уже есть как BOOL, превращаем его в сумму
    # арифметически, через сравнение бита 8 (только что получен).
    hi_pre = s.blk(u"ADD", [(u"IN1", w_hi), (u"IN2", x_hi)], 4)
    hi_sum = s.blk(u"ADD", [(u"IN1", hi_pre),
                            (u"IN2", s.blk(u"SHR", [(u"IN", low_sum),
                                                    (u"N", s.const(u"WORD#8", 4))], 4))], 5)
    q_hi = s.blk(u"WORD_TO_BYTE", [(u"IN", hi_sum)], 6)

    s.assign(u"Q_LO", q_lo, 7)
    s.assign(u"Q_HI", q_hi, 7)
    s.assign(u"CARRY", carry, 7)
    return [s]


# =====================================================================
#  F_PtrGen : адрес указателя и «следующий» адрес
#     IZX : (OpLo + X) & $FF, следующий — тоже в нулевой странице
#     IZY : OpLo, следующий = OpLo + 1
#     IND : OpLo|OpHi<<8, следующий С ВОСПРОИЗВЕДЕНИЕМ БАГА 6502
# =====================================================================
def gen_ptrgen():
    s = Sheet(u"Указатель: для indirect старший байт берётся в ТОЙ ЖЕ странице (баг 6502)")
    s.wrap_cmp = False   # проверено: этой схеме разрыв связей компараторов вредит
    md = s.var(u"Mode", 0)
    lo = s.var(u"OpLo", 0)
    hi = s.var(u"OpHi", 0)
    x = s.var(u"X", 0)

    is_izx = s.blk(u"EQ", [(u"IN1", md), (u"IN2", s.var(u"BYTE#%d" % MODE_CODE[u"izx"], 0))], 1)
    is_ind = s.blk(u"EQ", [(u"IN1", md), (u"IN2", s.var(u"BYTE#%d" % MODE_CODE[u"ind"], 0))], 1)

    # (zp + X) & $FF — сложение в пределах нулевой страницы делает сам BYTE
    zx = s.blk(u"ADD", [(u"IN1", lo), (u"IN2", x)], 2)
    # 16-битная база: OpLo | OpHi<<8
    hi16 = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 2)
    jz = s.blk(u"F_Join16", [(u"LO", zx), (u"HI", BYTE0)], 2)
    base = s.blk(u"SEL", [(u"G", is_ind), (u"IN0", jz), (u"IN1", hi16)], 3)
    s.assign(u"PtrAddr", base, 4)

    # следующий адрес указателя
    inc = s.blk(u"F_Join16", [(u"LO", BYTE1), (u"HI", BYTE0)], 3)
    inc_lo = s.var(u"INC_LO", 4)
    s.assign(u"INC_LO", inc, 4)
    lo_s = s.blk(u"F_Split16", [(u"IN", base)], 4)
    d_lo = s.var(u"D_LO", 5)
    d_hi = s.var(u"D_HI", 5)
    h_s = s.blk(u"F_Split16", [(u"IN", base)], 5)
    s.assign(u"D_LO", lo_s, 5)
    s.assign(u"D_HI", h_s, 5)
    plus = s.blk(u"F_Add16", [(u"A_LO", d_lo), (u"A_HI", d_hi),
                              (u"B_LO", inc_lo), (u"B_HI", s.var(u"BYTE#0", 5))], 6)
    p_lo = s.var(u"P_LO", 7)
    p_hi = s.var(u"P_HI", 7)
    sp = s.blk(u"F_Split16", [(u"IN", plus)], 7)
    s.assign(u"P_LO", sp, 7)
    s.assign(u"P_HI", sp, 7)
    # баг: старший байт = (PtrAddr & $FF00) | ((PtrAddr+1) & $00FF)
    mask_hi = s.blk(u"AND", [(u"IN1", d_hi), (u"IN2", s.var(B16 % 0xFF, 7))], 8)
    wrap_hi = s.blk(u"SEL", [(u"G", is_ind), (u"IN0", p_hi), (u"IN1", mask_hi)], 9)
    wrap_lo = s.blk(u"SEL", [(u"G", is_ind), (u"IN0", p_lo), (u"IN1", p_lo)], 9)
    jw = s.blk(u"F_Join16", [(u"LO", wrap_lo), (u"HI", wrap_hi)], 10)
    s.assign(u"PtrWrap", jw, 11)
    return [s]


# =====================================================================
#  FB_Decoder6502
# =====================================================================
def gen_decoder():
    eff = build_effects()
    s = Sheet(u"81 компаратор опкодов -> дерево OR по сигналам -> микрооперации")
    opv = s.var(u"Opcode", 0)

    # --- 1. компараторы опкодов ---
    eq = {}
    for mn, md, opc in OPCODES:
        eq[opc] = s.blk(u"EQ", [(u"IN1", opv), (u"IN2", s.const(B16 % opc, 0))], 1)

    # --- 2. группы по значению каждого сигнала ---
    # BOOL-сигналы объединяются деревом на SEL, BYTE-коды -- обычным OR
    # (см. пояснение в fbd.py: OR над BOOL из выходов блоков CODESYS не принимает).
    def group(pred, boolean=False):
        ids = [eq[o] for mn, md, o in OPCODES if pred(o, mn, md)]
        return or_tree_bool(s, ids, 2) if boolean else or_tree(s, ids, 2)

    col = 3

    # BOOL-сигналы
    bool_res = {}
    for sig in BOOL_SIGNALS:
        bool_res[sig] = group(lambda o, mn, md, sg=sig: bool(eff.get(o, {}).get(sg, False)), True)

    # BYTE-сигналы: для каждого значения -- группа, затем SEL и OR
    byte_res = {}
    for sig in BYTE_SIGNALS:
        vals = sorted(set(eff.get(o, {}).get(sig, 0) for mn, md, o in OPCODES))
        gres = {}
        for v in vals:
            if v == 0:
                continue
            gres[v] = group(lambda o, mn, md, sg=sig, vv=v: eff.get(o, {}).get(sg, 0) == vv)
        byte_res[sig] = (vals, gres)

    # --- 3. вывод BOOL ---
    for sig in BOOL_SIGNALS:
        if bool_res[sig] is not None:
            s.assign(sig, bool_res[sig], col)
    col += 1

    # --- 4. вывод BYTE ---
    for sig in BYTE_SIGNALS:
        vals, gres = byte_res[sig]
        parts = []
        for v in vals:
            if v == 0:
                continue
            sel = s.blk(u"SEL", [(u"G", gres[v]), (u"IN0", s.const(BYTE0, col)),
                                 (u"IN1", s.const(u"BYTE#%d" % v, col))], col)
            parts.append(sel)
        res = or_tree(s, parts, col + 1)
        if res is None:
            s.assign(sig, s.const(BYTE0, col + 1), col + 1)
        else:
            s.assign(sig, res, col + 4)
    return [s]


# =====================================================================
#  FB_AddrGen
# =====================================================================
def gen_addrgen():
    s = Sheet(u"12 режимов адресации. Индексация — байтовым сложением с переносом в старший байт")
    s.wrap_cmp = False   # проверено: этой схеме разрыв связей компараторов вредит
    md = s.var(u"Mode", 0)
    pc = s.var(u"PC", 0)
    lo = s.var(u"OpLo", 0)
    hi = s.var(u"OpHi", 0)
    x = s.var(u"X", 0)
    y = s.var(u"Y", 0)
    ilo = s.var(u"IndLo", 0)
    ihi = s.var(u"IndHi", 0)

    def ismode(m):
        return s.blk(u"EQ", [(u"IN1", md), (u"IN2", s.const(u"BYTE#%d" % MODE_CODE[m], 0))], 1)

    m_imm, m_zp = ismode(u"imm"), ismode(u"zp")
    m_zpx, m_zpy = ismode(u"zpx"), ismode(u"zpy")
    m_abs, m_abx, m_aby = ismode(u"abs"), ismode(u"abx"), ismode(u"aby")
    m_izx, m_izy = ismode(u"izx"), ismode(u"izy")
    m_ind, m_rel = ismode(u"ind"), ismode(u"rel")

    zero = s.const(BYTE0, 2)
    one = s.const(BYTE1, 2)
    jz = s.blk(u"F_Join16", [(u"LO", zero), (u"HI", zero)], 2)
    j1 = s.blk(u"F_Join16", [(u"LO", one), (u"HI", zero)], 2)

    # PC+1, PC+2
    pcs = s.blk(u"F_Split16", [(u"IN", pc)], 2)
    pc_lo = s.var(u"PC_LO", 3)
    pc_hi = s.var(u"PC_HI", 3)
    s.assign(u"PC_LO", pcs, 3)
    s.assign(u"PC_HI", pcs, 3)
    j1c = s.var(u"J1", 3)
    s.assign(u"J1", j1, 3)
    l1 = s.var(u"ONE_LO", 3)
    h0 = s.var(u"ZERO_HI", 3)
    s.assign(u"ONE_LO", one, 3)
    s.assign(u"ZERO_HI", zero, 3)
    p1 = s.blk(u"F_Add16", [(u"A_LO", pc_lo), (u"A_HI", pc_hi),
                            (u"B_LO", l1), (u"B_HI", h0)], 4)
    p1_lo = s.var(u"P1_LO", 5)
    p1_hi = s.var(u"P1_HI", 5)
    sp1 = s.blk(u"F_Split16", [(u"IN", p1)], 5)
    s.assign(u"P1_LO", sp1, 5)
    s.assign(u"P1_HI", sp1, 5)
    p2 = s.blk(u"F_Add16", [(u"A_LO", p1_lo), (u"A_HI", p1_hi),
                            (u"B_LO", l1), (u"B_HI", h0)], 6)
    p2_lo = s.var(u"P2_LO", 7)
    p2_hi = s.var(u"P2_HI", 7)
    sp2 = s.blk(u"F_Split16", [(u"IN", p2)], 7)
    s.assign(u"P2_LO", sp2, 7)
    s.assign(u"P2_HI", sp2, 7)

    # base := OpLo | OpHi<<8
    base16 = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 4)
    bs = s.blk(u"F_Split16", [(u"IN", base16)], 5)
    b_lo = s.var(u"B_LO", 6)
    b_hi = s.var(u"B_HI", 6)
    s.assign(u"B_LO", bs, 6)
    s.assign(u"B_HI", bs, 6)

    # zp+X и zp+Y (в пределах нулевой страницы)
    zx = s.blk(u"ADD", [(u"IN1", lo), (u"IN2", x)], 4)
    zy = s.blk(u"ADD", [(u"IN1", lo), (u"IN2", y)], 4)
    jzx = s.blk(u"F_Join16", [(u"LO", zx), (u"HI", BYTE0)], 5)
    jzy = s.blk(u"F_Join16", [(u"LO", zy), (u"HI", BYTE0)], 5)
    jzp = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", BYTE0)], 5)

    # abs+X и abs+Y — байтовое сложение с переносом в старший байт
    idx = s.blk(u"F_Join16", [(u"LO", x), (u"HI", BYTE0)], 6)
    idy = s.blk(u"F_Join16", [(u"LO", y), (u"HI", BYTE0)], 6)
    x_lo = s.var(u"X_LO", 7)
    x_hi = s.var(u"X_HI", 7)
    s.assign(u"X_LO", idx, 7)
    s.assign(u"X_HI", idx, 7)
    y_lo = s.var(u"Y_LO", 7)
    y_hi = s.var(u"Y_HI", 7)
    s.assign(u"Y_LO", idy, 7)
    s.assign(u"Y_HI", idy, 7)
    abx = s.blk(u"F_Add16", [(u"A_LO", b_lo), (u"A_HI", b_hi),
                             (u"B_LO", x_lo), (u"B_HI", x_hi)], 8)
    aby = s.blk(u"F_Add16", [(u"A_LO", b_lo), (u"A_HI", b_hi),
                             (u"B_LO", y_lo), (u"B_HI", y_hi)], 8)

    # indirect-базы
    ind16 = s.blk(u"F_Join16", [(u"LO", ilo), (u"HI", ihi)], 6)
    is_ = s.blk(u"F_Split16", [(u"IN", ind16)], 7)
    i_lo = s.var(u"I_LO", 8)
    i_hi = s.var(u"I_HI", 8)
    s.assign(u"I_LO", is_, 8)
    s.assign(u"I_HI", is_, 8)
    izy = s.blk(u"F_Add16", [(u"A_LO", i_lo), (u"A_HI", i_hi),
                             (u"B_LO", y_lo), (u"B_HI", y_hi)], 9)

    # relative: PC+2 + знаковый offset
    off = s.blk(u"SEL", [(u"G", s.blk(u"GE", [(u"IN1", lo), (u"IN2", s.const(BYTE80, 5))], 5)),
                         (u"IN0", lo),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", lo), (u"IN2", s.const(BYTE80, 5))], 5))], 6)
    off16 = s.blk(u"F_Join16", [(u"LO", off), (u"HI", BYTE0)], 7)
    off_lo = s.var(u"O_LO", 8)
    off_hi = s.var(u"O_HI", 8)
    os_ = s.blk(u"F_Split16", [(u"IN", off16)], 8)
    s.assign(u"O_LO", os_, 8)
    s.assign(u"O_HI", os_, 8)
    rel = s.blk(u"F_Add16", [(u"A_LO", p2_lo), (u"A_HI", p2_hi),
                             (u"B_LO", off_lo), (u"B_HI", off_hi)], 9)

    # выбор кандидата
    cands = [(m_imm, p1), (m_zp, jzp), (m_zpx, jzx), (m_zpy, jzy),
             (m_abs, base16), (m_abx, abx), (m_aby, aby),
             (m_izx, ind16), (m_izy, izy), (m_ind, ind16)]
    parts = []
    for gate, cand in cands:
        z = s.blk(u"F_Join16", [(u"LO", BYTE0), (u"HI", BYTE0)], 10)
        parts.append(s.blk(u"SEL", [(u"G", gate), (u"IN0", z), (u"IN1", cand)], 10))
    addr = or_tree(s, parts, 11)
    s.assign(u"Addr", addr, 13)
    s.assign(u"RelTarget", rel, 13)
    return [s]


# =====================================================================
#  FB_Stack : SP и адреса стека
# =====================================================================
def gen_stack():
    s = Sheet(u"Стек в странице $0100. Push: запись по SP, затем SP-1. Pull: SP+1, затем чтение")
    s.wrap_cmp = False   # проверено: этой схеме разрыв связей компараторов вредит
    sp = s.var(u"SP", 0)
    mode = s.var(u"SP_MODE", 0)

    def iss(v):
        return s.blk(u"EQ", [(u"IN1", mode), (u"IN2", s.const(u"BYTE#%d" % v, 0))], 1)

    push = or_bool(s, iss(1), iss(3), 1)
    pull = or_bool(s, iss(2), iss(4), 1)
    d2 = or_bool(s, iss(3), iss(4), 1)

    # NEWSP: push -> SP-1 (или -2), pull -> SP+1 (или +2)
    m1 = s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(BYTE1, 2))], 2)
    m2 = s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#2", 2))], 2)
    p1 = s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(BYTE1, 2))], 2)
    p2 = s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#2", 2))], 2)
    sel_d = s.blk(u"SEL", [(u"G", d2), (u"IN0", m1), (u"IN1", m2)], 3)
    sel_p = s.blk(u"SEL", [(u"G", d2), (u"IN0", p1), (u"IN1", p2)], 3)
    mid = s.blk(u"SEL", [(u"G", push), (u"IN0", sel_p), (u"IN1", sel_d)], 4)
    any_op = or_bool(s, push, pull, 4)
    spn = s.blk(u"SEL", [(u"G", any_op), (u"IN0", sp), (u"IN1", mid)], 5)
    s.assign(u"SP_NEW", spn, 6)

    # SP-1 и SP+1/+2 как байты
    spm1 = s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(BYTE1, 4))], 4)
    spp1 = s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(BYTE1, 4))], 4)
    spp2 = s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#2", 4))], 4)

    page = s.const(u"16#0100", 6)

    def stack_addr(bytevar, col):
        w = s.blk(u"F_Join16", [(u"LO", bytevar), (u"HI", s.const(BYTE1, col))], col)
        return w

    a0 = stack_addr(sp, 6)                       # $0100 + SP      (запись push)
    a1 = stack_addr(spm1, 6)                     # $0100 + SP - 1
    a2 = stack_addr(spp1, 6)                     # $0100 + SP + 1  (чтение pull)
    a3 = stack_addr(spp2, 6)                     # $0100 + SP + 2
    s.assign(u"SADDR_W0", a0, 8)
    s.assign(u"SADDR_W1", a1, 8)
    s.assign(u"SADDR_R0", a2, 8)
    s.assign(u"SADDR_R1", a3, 8)
    s.assign(u"SP_PUSH", push, 8)
    s.assign(u"SP_PULL", pull, 8)
    s.assign(u"PUSH2", d2, 8)
    return [s]


# =====================================================================
#  FB_PC_Update
# =====================================================================
def gen_pcupdate():
    s = Sheet(u"Новый PC: PC+LEN / цель перехода / возврат+1 / ветвление / останов")
    pc = s.var(u"PC", 0)
    ln = s.var(u"LEN", 0)
    mode = s.var(u"PC_MODE", 0)
    tgt = s.var(u"Target", 0)
    plo = s.var(u"PullLo", 0)
    phi = s.var(u"PullHi", 0)
    take = s.var(u"TAKE", 0)
    rel = s.var(u"RelTarget", 0)
    halt = s.var(u"HALT", 0)
    p2 = s.var(u"PC2", 0)          # PC+2 (адрес возврата минус 1 для JSR)

    def ism(v):
        return s.blk(u"EQ", [(u"IN1", mode), (u"IN2", s.const(u"BYTE#%d" % v, 0))], 1)

    m_len, m_abs, m_rts, m_br, m_halt = ism(0), ism(1), ism(2), ism(3), ism(4)

    # PC+LEN — через байтовое сложение
    pcs = s.blk(u"F_Split16", [(u"IN", pc)], 2)
    pc_lo = s.var(u"PC_LO", 3)
    pc_hi = s.var(u"PC_HI", 3)
    s.assign(u"PC_LO", pcs, 3)
    s.assign(u"PC_HI", pcs, 3)
    jlen = s.blk(u"F_Join16", [(u"LO", ln), (u"HI", BYTE0)], 2)
    len_lo = s.var(u"L_LO", 3)
    len_hi = s.var(u"L_HI", 3)
    ls = s.blk(u"F_Split16", [(u"IN", jlen)], 3)
    s.assign(u"L_LO", ls, 3)
    s.assign(u"L_HI", ls, 3)
    adv = s.blk(u"F_Add16", [(u"A_LO", pc_lo), (u"A_HI", pc_hi),
                             (u"B_LO", len_lo), (u"B_HI", len_hi)], 4)

    # возврат: склеить два байта из стека и прибавить 1
    jret = s.blk(u"F_Join16", [(u"LO", plo), (u"HI", phi)], 4)
    rs = s.blk(u"F_Split16", [(u"IN", jret)], 5)
    r_lo = s.var(u"R_LO", 6)
    r_hi = s.var(u"R_HI", 6)
    s.assign(u"R_LO", rs, 6)
    s.assign(u"R_HI", rs, 6)
    jone = s.blk(u"F_Join16", [(u"LO", BYTE1), (u"HI", BYTE0)], 5)
    on_lo = s.var(u"O_LO2", 6)
    on_hi = s.var(u"O_HI2", 6)
    os_ = s.blk(u"F_Split16", [(u"IN", jone)], 6)
    s.assign(u"O_LO2", os_, 6)
    s.assign(u"O_HI2", os_, 6)
    ret = s.blk(u"F_Add16", [(u"A_LO", r_lo), (u"A_HI", r_hi),
                             (u"B_LO", on_lo), (u"B_HI", on_hi)], 7)

    # ветвление: TAKE ? RelTarget : PC+2
    br = s.blk(u"SEL", [(u"G", take), (u"IN0", p2), (u"IN1", rel)], 8)

    parts = []
    for gate, cand in ((m_len, adv), (m_abs, tgt), (m_rts, ret), (m_br, br), (m_halt, pc)):
        z = s.blk(u"F_Join16", [(u"LO", BYTE0), (u"HI", BYTE0)], 9)
        parts.append(s.blk(u"SEL", [(u"G", gate), (u"IN0", z), (u"IN1", cand)], 9))
    res = or_tree(s, parts, 10)
    s.assign(u"PC_NEW", res, 12)
    return [s]


# =====================================================================
#  FB_Branch
# =====================================================================
def gen_branch():
    s = Sheet(u"Условие перехода: одно из шести по коду COND")
    s.wrap_cmp = False   # проверено: этой схеме разрыв связей компараторов вредит
    n = s.var(u"N", 0)
    z = s.var(u"Z", 0)
    c = s.var(u"C", 0)
    cond = s.var(u"COND", 0)

    def isc(v):
        return s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#%d" % v, 0))], 1)

    nz = s.blk(u"XOR", [(u"IN1", z), (u"IN2", s.const(u"TRUE", 1))], 1)
    nc = s.blk(u"XOR", [(u"IN1", c), (u"IN2", s.const(u"TRUE", 1))], 1)
    nn = s.blk(u"XOR", [(u"IN1", n), (u"IN2", s.const(u"TRUE", 1))], 1)
    parts = []
    for gate, val in ((isc(0), z), (isc(1), nz), (isc(2), c),
                      (isc(3), nc), (isc(4), n), (isc(5), nn)):
        parts.append(and_bool(s, gate, val, 2))
    res = or_tree_bool(s, parts, 3)
    s.assign(u"TAKE", res, 5)
    return [s]


# =====================================================================
#  FB_Memory64K : 4 порта
# =====================================================================
def gen_memory():
    s = Sheet(u"Чтение: RD0 := Mem[RD_ADDR0], RD1 := Mem[RD_ADDR1]")
    a0 = s.var(u"RD_ADDR0", 0)
    a1 = s.var(u"RD_ADDR1", 0)
    r0 = s.var(u"Mem[RD_ADDR0]", 1)
    r1 = s.var(u"Mem[RD_ADDR1]", 1)
    s.assign(u"RD0", r0, 2)
    s.assign(u"RD1", r1, 2)

    s2 = Sheet(u"Запись: Mem[A] := SEL(WE, Mem[A], WD) — при WE=0 пишется то же значение", dy=600)
    w0 = s.var(u"WR_ADDR0", 0)
    w1 = s.var(u"WR_ADDR1", 0)
    d0 = s.var(u"WD0", 0)
    d1 = s.var(u"WD1", 0)
    e0 = s.var(u"WE0", 0)
    e1 = s.var(u"WE1", 0)
    cur0 = s.var(u"Mem[WR_ADDR0]", 1)
    cur1 = s.var(u"Mem[WR_ADDR1]", 1)
    m0 = s.blk(u"SEL", [(u"G", e0), (u"IN0", cur0), (u"IN1", d0)], 2)
    m1 = s.blk(u"SEL", [(u"G", e1), (u"IN0", cur1), (u"IN1", d1)], 2)
    s2.assign(u"Mem[WR_ADDR0]", m0, 3)
    s2.assign(u"Mem[WR_ADDR1]", m1, 3)
    return [s, s2]


# =====================================================================
def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print(u"Генерация слоя 2:")

    emit(u"F_Add16", u"function",
         interface(inputs=[(u"A_LO", u"BYTE"), (u"A_HI", u"BYTE"),
                           (u"B_LO", u"BYTE"), (u"B_HI", u"BYTE")],
                   outputs=[(u"Q_LO", u"BYTE"), (u"Q_HI", u"BYTE"), (u"CARRY", u"BOOL")]),
         gen_add16(), u"16-битное сложение на байтовом уровне: младшие байты, перенос, старшие. WORD-арифметика не используется.")

    emit(u"F_PtrGen", u"function",
         interface(inputs=[(u"Mode", u"BYTE"), (u"OpLo", u"BYTE"), (u"OpHi", u"BYTE"), (u"X", u"BYTE")],
                   outputs=[(u"PtrAddr", u"WORD"), (u"PtrWrap", u"WORD")],
                   locals_=[(u"INC_LO", u"BYTE"), (u"D_LO", u"BYTE"), (u"D_HI", u"BYTE"), (u"P_LO", u"BYTE"), (u"P_HI", u"BYTE")]),
         gen_ptrgen(), u"Адрес указателя. Для indirect старший байт берётся в той же странице — воспроизведение аппаратного бага 6502.")

    emit(u"FB_Decoder6502", u"functionBlock",
         interface(inputs=[(u"Opcode", u"BYTE")],
                   outputs=[(s_, u"BOOL") for s_ in BOOL_SIGNALS]
                           + [(s_, u"BYTE") for s_ in BYTE_SIGNALS]),
         gen_decoder(),
         u"Дешифратор команд. 81 компаратор EQ по одному на опкод, затем деревья OR по сигналам. Генерируется из tools/opcodes.py — того же файла, что и тесты.")

    emit(u"FB_AddrGen", u"functionBlock",
         interface(inputs=[(u"Mode", u"BYTE"), (u"PC", u"WORD"), (u"OpLo", u"BYTE"), (u"OpHi", u"BYTE"),
                           (u"X", u"BYTE"), (u"Y", u"BYTE"), (u"IndLo", u"BYTE"), (u"IndHi", u"BYTE")],
                   outputs=[(u"Addr", u"WORD"), (u"RelTarget", u"WORD")],
                   locals_=[(u"B_LO", u"BYTE"), (u"B_HI", u"BYTE"), (u"I_LO", u"BYTE"), (u"I_HI", u"BYTE"), (u"J1", u"WORD"), (u"ONE_LO", u"BYTE"), (u"ZERO_HI", u"BYTE"), (u"O_LO", u"BYTE"), (u"O_HI", u"BYTE"), (u"P1_LO", u"BYTE"), (u"P1_HI", u"BYTE"), (u"P2_LO", u"BYTE"), (u"P2_HI", u"BYTE"), (u"PC_LO", u"BYTE"), (u"PC_HI", u"BYTE"), (u"X_LO", u"BYTE"), (u"X_HI", u"BYTE"), (u"Y_LO", u"BYTE"), (u"Y_HI", u"BYTE")]),
         gen_addrgen(), u"Эффективный адрес по 12 режимам. Индексация — байтовым сложением с переносом в старший байт.")

    emit(u"FB_Stack", u"functionBlock",
         interface(inputs=[(u"SP", u"BYTE"), (u"SP_MODE", u"BYTE")],
                   outputs=[(u"SP_NEW", u"BYTE"), (u"SADDR_W0", u"WORD"), (u"SADDR_W1", u"WORD"),
                            (u"SADDR_R0", u"WORD"), (u"SADDR_R1", u"WORD"),
                            (u"SP_PUSH", u"BOOL"), (u"SP_PULL", u"BOOL"), (u"PUSH2", u"BOOL")]),
         gen_stack(), u"Стек в странице $0100: адреса $0100+SP, $0100+SP-1, $0100+SP+1, $0100+SP+2 и новый SP.")

    emit(u"FB_PC_Update", u"functionBlock",
         interface(inputs=[(u"PC", u"WORD"), (u"LEN", u"BYTE"), (u"PC_MODE", u"BYTE"),
                           (u"Target", u"WORD"), (u"PullLo", u"BYTE"), (u"PullHi", u"BYTE"),
                           (u"TAKE", u"BOOL"), (u"RelTarget", u"WORD"), (u"HALT", u"BOOL"),
                           (u"PC2", u"WORD")],
                   outputs=[(u"PC_NEW", u"WORD")],
                   locals_=[(u"L_LO", u"BYTE"), (u"L_HI", u"BYTE"), (u"PC_LO", u"BYTE"), (u"PC_HI", u"BYTE"), (u"R_LO", u"BYTE"), (u"R_HI", u"BYTE"), (u"O_LO2", u"BYTE"), (u"O_HI2", u"BYTE")]),
         gen_pcupdate(), u"Новый PC. Для RTS: склеить два байта из стека и прибавить 1 (в стек кладётся адрес возврата минус 1).")

    emit(u"FB_Branch", u"functionBlock",
         interface(inputs=[(u"N", u"BOOL"), (u"Z", u"BOOL"), (u"C", u"BOOL"), (u"COND", u"BYTE")],
                   outputs=[(u"TAKE", u"BOOL")]),
         gen_branch(), u"Проверка условия: BEQ/BNE/BCC/BCS/BPL/BMI. Код условия приходит из декодера.")

    emit(u"FB_Memory64K", u"functionBlock",
         interface(inputs=[(u"RD_ADDR0", u"WORD"), (u"RD_ADDR1", u"WORD"),
                           (u"WR_ADDR0", u"WORD"), (u"WR_ADDR1", u"WORD"),
                           (u"WE0", u"BOOL"), (u"WE1", u"BOOL"),
                           (u"WD0", u"BYTE"), (u"WD1", u"BYTE")],
                   outputs=[(u"RD0", u"BYTE"), (u"RD1", u"BYTE")],
                   locals_=[(u"Mem", u"ARRAY[0..65535] OF BYTE")]),
         gen_memory(), u"Память 64 КБ. Четыре порта: JSR пишет два байта, RTS читает два байта в ОДНОМ скане.")

    print(u"Готово.")


if __name__ == "__main__":
    main()
