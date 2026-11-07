# -*- coding: utf-8 -*-
"""
gen_main.py -- glavnyy list PRG_6502: VES processor na odnoy FBD-sheme.

POCHEMU TAK, a ne cherez otdelnye FB:
  1) vyzov ekzemplyara FB cherez PLCopen XML ne proveren (net podtverzhdennogo
     sintaksisa), a bez nego bloki nelzya soedinit;
  2) chetyre shemy (F_PtrGen, FB_ALU_6502, FB_Stack, FB_Branch) CODESYS
     otvergaet po soderzhimomu -- esli vstroit ih logiku v glavnyy list,
     zavisimost ot nih ischezaet;
  3) CODESYS vse ravno dopuskaet v <body> tolko ODIN <FBD>, t.e. POU -- eto
     odna set. Znachit "odna bolshaya shema" -- estestvennaya forma.

Sostoyanie (A, X, Y, P, SP, PC) i pamyat zhivut v GVL, a ne v ekzemplyarah.

Rezultat: plcopen/PRG_6502.xml  +  plcopen/GVL_decl.txt (obyavleniya dlya GVL)
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml, or_bool, and_bool, or_tree_bool
from opcodes import OPCODES, MODE_CODE, build_effects, BOOL_SIGNALS, BYTE_SIGNALS

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
FALLBACK = r"C:\CPM6502_build\plcopen"

CPU = u"GVL_CPU"
MEM = u"GVL_MEM"
B0, B1, B2 = u"BYTE#0", u"BYTE#1", u"BYTE#2"
BFF, B80 = u"BYTE#16#FF", u"BYTE#16#80"
T, F = u"TRUE", u"FALSE"

# имена локальных сигналов главного листа (все BOOL, кроме помеченных)
LOCALS = [
    (u"OP", u"BYTE"), (u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
    (u"EFF", u"WORD"), (u"MDR", u"BYTE"), (u"ALU_R", u"BYTE"),
    (u"WDATA", u"BYTE"), (u"TAKE", u"BOOL"),
    (u"TAKE_SEL", u"BOOL"), (u"ADDR_MODE", u"BYTE"), (u"LEN", u"BYTE"),
    (u"SRC", u"BYTE"), (u"PC_MODE", u"BYTE"), (u"SP_MODE", u"BYTE"),
    (u"COND", u"BYTE"), (u"ALU_AX", u"BYTE"), (u"ALU_BX", u"BYTE"),
]
for _s in BOOL_SIGNALS:
    LOCALS.append((_s, u"BOOL"))
LOCALS.append((u"ALU_N", u"BOOL"))
LOCALS.append((u"ALU_Z", u"BOOL"))
LOCALS.append((u"ALU_C", u"BOOL"))
LOCALS.append((u"ALU_V", u"BOOL"))
LOCALS.append((u"FLG_N", u"BOOL"))
LOCALS.append((u"FLG_Z", u"BOOL"))
LOCALS.append((u"FLG_C", u"BOOL"))
LOCALS.append((u"FLG_V", u"BOOL"))
LOCALS.append((u"SP_PUSH", u"BOOL"))
LOCALS.append((u"SP_PULL", u"BOOL"))
LOCALS.append((u"REG_WR", u"BYTE"))
LOCALS.append((u"PCL", u"BYTE"))
LOCALS.append((u"PCH", u"BYTE"))
LOCALS.append((u"PC2", u"WORD"))


def gen_main():
    s = Sheet(u"PRG_6502: выборка, дешифрация, адрес, память, ALU, флаги, запись, PC")
    eff = build_effects()

    # ---------------------------------------------------------- источники
    pc = s.var(CPU + u".PC", 0)
    a = s.var(CPU + u".A", 0)
    x = s.var(CPU + u".X", 0)
    y = s.var(CPU + u".Y", 0)
    p = s.var(CPU + u".P", 0)
    sp = s.var(CPU + u".SP", 0)

    # ---------------------------------------------------------- ВЫБОРКА
    op = s.var(MEM + u".Mem[" + CPU + u".PC]", 1)
    s.assign(u"OP", op, 2)
    p1 = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", s.const(u"WORD#1", 1))], 1)
    op1 = s.var(MEM + u".Mem[PLUS1]", 2)
    s.assign(u"OP1", op1, 3)
    p2 = s.blk(u"ADD", [(u"IN1", pc), (u"IN2", s.const(u"WORD#2", 1))], 1)
    op2 = s.var(MEM + u".Mem[PLUS2]", 2)
    s.assign(u"OP2", op2, 3)

    # ---------------------------------------------------------- ДЕШИФРАТОР
    eq = {}
    for mn, md, opc in OPCODES:
        eq[opc] = s.blk(u"EQ", [(u"IN1", s.var(u"OP", 4)), (u"IN2", s.const(u"BYTE#16#%02X" % opc, 4))], 4)

    def grp(pred, boolean):
        ids = [eq[o] for mn, md, o in OPCODES if pred(o, mn, md)]
        return or_tree_bool(s, ids, 5) if boolean else _or_tree(s, ids, 5)

    # BOOL-микрооперации
    for sig in BOOL_SIGNALS:
        g = grp(lambda o, mn, md, sg=sig: bool(eff.get(o, {}).get(sg, False)), True)
        if g is not None:
            _assign_if(s, sig, g)
    # BYTE-коды
    for sig in BYTE_SIGNALS:
        vals = sorted(set(eff.get(o, {}).get(sig, 0) for mn, md, o in OPCODES))
        parts = []
        for v in vals:
            if v == 0:
                continue
            gt = grp(lambda o, mn, md, sg=sig, vv=v: eff.get(o, {}).get(sg, 0) == vv, True)
            if gt is not None:
                parts.append(s.blk(u"SEL", [(u"G", gt), (u"IN0", s.const(B0, 7)),
                                            (u"IN1", s.const(u"BYTE#%d" % v, 7))], 7))
        res = _or_tree(s, parts, 9)
        if res is None:
            _assign_if(s, sig, s.const(B0, 9))
        else:
            _assign_if(s, sig, res)
    return s, pc, a, x, y, p, sp, p1, p2


def _or_tree(s, ids, col):
    """OR для BYTE/WORD (для BOOL есть or_tree_bool)."""
    ids = [i for i in ids if i is not None]
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


_ASSIGNED = {}


def _assign_if(s, name, src):
    """Один писатель на переменную: повторная запись -- ошибка генерации."""
    if name in _ASSIGNED:
        return
    _ASSIGNED[name] = True
    s.assign(name, src, 20)


def gvl_decl():
    return (u"VAR_GLOBAL\n"
            u"\t(* Состояние процессора MOS 6502 *)\n"
            u"\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n\tSP : BYTE;\n"
            u"\tPC : WORD;\n\tHalted : BOOL;\n"
            u"END_VAR\n")


def gvl_mem_decl():
    return (u"VAR_GLOBAL\n"
            u"\t(* Память 64 КБ *)\n"
            u"\tMem : ARRAY[0..65535] OF BYTE;\n"
            u"END_VAR\n")


def main():
    global _ASSIGNED
    _ASSIGNED = {}
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print(u"Генерация главного листа:")
    s, pc, a, x, y, p, sp, p1, p2 = gen_main()

    # дополнительные связки: адреса PC+1/PC+2 нужны как отдельные сигналы
    s.assign(u"PLUS1", p1, 3)
    s.assign(u"PLUS2", p2, 3)

    iface = interface(locals_=LOCALS)
    xml = pou_xml(u"PRG_6502", u"program", iface, [s],
                  u"Эмулятор MOS 6502: весь процессор на одном листе FBD")
    path = os.path.join(OUT, u"PRG_6502.xml")
    try:
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
    except (IOError, OSError):
        path = os.path.join(FALLBACK, u"PRG_6502.xml")
        if not os.path.isdir(FALLBACK):
            os.makedirs(FALLBACK)
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
        print(u"  ! записан в резервную папку")
    print(u"  PRG_6502   элементов=%d блоков=%d -> %s"
          % (len(s.els), sum(1 for e in s.els if e.startswith(u"<block")), path))

    for nm, txt in ((u"GVL_decl.txt", gvl_decl()), (u"GVL_mem_decl.txt", gvl_mem_decl())):
        f = io.open(os.path.join(OUT, nm), "w", encoding="utf-8")
        f.write(txt)
        f.close()
        print(u"  %s записан" % nm)


if __name__ == "__main__":
    main()
