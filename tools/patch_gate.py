# -*- coding: utf-8 -*-
"""
patch_gate.py -- dobavit dve nedostayushchie chasti kompozicii:

1) razresheniya takta LD_A_E..WR_MEM_E = signal AND Enable;
2) sloy FB_CPU_Store -- tri porta zapisi v pamyat (STA/STX/STY, JSR, BRK).

Bez nih LD_A_E vsegda FALSE (registr A ne zapisyvaetsya), a STA/BRK/JSR ne
pisali v pamyat: pri dekompozicii eti svyazi ostalis v staroy odnolistovoy sheme.
"""
import io
import ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(P, "rb").read().decode("utf-8")

# ---------------------------------------------------------------- 1. гейтирование
anchor = u'    call(s, u"FB_CPU_Addr1", u"S1", [], 5, w=140)'
add = (u'    # Разрешения такта: сигнал И Enable (без этого регистры не пишутся)\n'
       u'    for sig in (u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM"):\n'
       u'        W(s, sig + u"_E",\n'
       u'          s.blk(u"AND", [(u"IN1", R(s, sig)), (u"IN2", R(s, u"Enable"))], 4), 4)\n'
       u'    call(s, u"FB_CPU_Addr1", u"S1", [], 5, w=140)')
if anchor in t:
    t = t.replace(anchor, add, 1)
    print(u"гейтирование добавлено")
else:
    print(u"НЕ найден вызов S1")

# ---------------------------------------------------------------- 2. слой записи в память
anchor2 = u'def fb_core():'
store = u'''def fb_store():
    """FB_CPU_Store: tri porta zapisi v pamyat.

    Port 0 -- obychaya zapis (STA/STX/STY) ili pervyy bajt steka (BRK).
    Porty 1 i 2 -- vtoryy/tretiy bajty dlya JSR (PCH, PCL) i BRK (PCH, PCL).
    """
    s = Sheet(u"FB_CPU_Store: запись в память")
    push1 = s.blk(u"EQ", [(u"IN1", R(s, u"SP_MODE")), (u"IN2", s.const(u"BYTE#1", 1))], 1)
    push3 = s.blk(u"EQ", [(u"IN1", R(s, u"SP_MODE")), (u"IN2", s.const(u"BYTE#5", 1))], 1)
    stack_w = s.blk(u"OR", [(u"IN1", push1), (u"IN2", push3)], 2)

    # --- port 0
    en0 = s.blk(u"OR", [(u"IN1", R(s, u"WR_MEM_E")),
                        (u"IN2", s.blk(u"OR", [(u"IN1", R(s, u"IS_JSR")),
                                               (u"IN2", stack_w)], 3))], 4)
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
    en1 = s.blk(u"OR", [(u"IN1", R(s, u"IS_JSR")), (u"IN2", push3)], 4)
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
    W(s, u"WR_EN2", push3, 6)
    s.assign(u"GVL_MEM.Mem[GVL_CPU.WR2]",
             s.blk(u"SEL", [(u"G", R(s, u"WR_EN2")),
                            (u"IN0", s.ref(u"GVL_MEM.Mem[GVL_CPU.WR2]", 7)),
                            (u"IN1", R(s, u"WRD2"))], 7), 8)
    return s


def fb_core():'''
if anchor2 in t:
    t = t.replace(anchor2, store, 1)
    print(u"слой FB_CPU_Store добавлен")
else:
    print(u"НЕ найден fb_core")

# ---------------------------------------------------------------- 3. вызов слоя
anchor3 = u'    call(s, u"FB_CPU_PcWb", u"S5", [], 9, w=140)'
add3 = (u'    call(s, u"FB_CPU_PcWb", u"S5", [], 9, w=140)\n'
        u'    call(s, u"FB_CPU_Store", u"S6", [], 10, w=140)')
if anchor3 in t:
    t = t.replace(anchor3, add3, 1)
    print(u"вызов S6 добавлен")
else:
    print(u"НЕ найден вызов S5")

# ---------------------------------------------------------------- 4. объявление POU
anchor4 = u'''    write(u"PRG_PLC", pou_xml('''
add4 = u'''    write(u"FB_CPU_Store", pou_xml(
        u"FB_CPU_Store", u"functionBlock",
        interface(locals_=[]),
        [fb_store()], u"запись в память"))

    write(u"PRG_PLC", pou_xml('''
if anchor4 in t:
    t = t.replace(anchor4, add4, 1)
    print(u"запись файла FB_CPU_Store добавлена")
else:
    print(u"НЕ найдено write(PRG_PLC")

# ---------------------------------------------------------------- 5. экземпляр S6
t = t.replace(u'u"S5", u"FB_CPU_PcWb")),',
              u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store")),')

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
