# -*- coding: utf-8 -*-
"""
patch_alu.py -- tri ispravleniya v FB_ALU6502 (gen_cpu_split.build_alu).

Kontrakt iz opcodes.py:
    ALU_A, ALU_X, ALU_Y = 0, 1, 2        -- kakoy registr vzyat pervym operandом
    ALU_B_MDR, ALU_B_ONE = 0, 1          -- vtoroy operand: MDR(WDATA) ili edinitsa

Chto bylo ne tak:
  1) ALU_A=2 (Y) obrabatyvalsya kak A -- INY/DEY schitali ne tot registr;
  2) dlya komand ZAGRUZKI (LDA/LDX/LDY/...) v tablice net ni F_ADD, ni F_SUB,
     ni F_CMP, i SRC=ALU_R. Znachit ALU dolzhno PROPUSTIT operand: 0 + WDATA.
     Prezhniy kod vsegda slozhil A + WDATA (dlya A=0 sluchayno sovpadalo).
"""
import io
import ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_cpu_split.py"
t = io.open(P, "rb").read().decode("utf-8")

old_refs = u'''    a = s.ref(u"A", 0)
    xv = s.ref(u"X", 0)'''
new_refs = u'''    a = s.ref(u"A", 0)
    xv = s.ref(u"X", 0)
    yv = s.ref(u"Y", 0)'''
if old_refs in t:
    t = t.replace(old_refs, new_refs, 1)
    print(u"добавлено чтение Y")
else:
    print(u"НЕ найдено чтение A/X")

old_sel = u'''    alu_a = SELb(s, byt(s, s.ref(u"ALU_A", 0), 1), a, xv, 2)
    alu_b = SELb(s, byt(s, s.ref(u"ALU_B", 0), 1), wd, s.const(B1, 2), 2)'''
new_sel = u'''    # ALU_A: 0 = A, 1 = X, 2 = Y
    au = s.ref(u"ALU_A", 0)
    ax_or_y = SELb(s, EQv(s, au, u"BYTE#2", 1), yv, a, 2)
    alu_a = SELb(s, byt(s, au, 1), ax_or_y, xv, 2)
    # ALU_B: 0 = операнд (MDR/WDATA), 1 = единица
    alu_b = SELb(s, byt(s, s.ref(u"ALU_B", 0), 1), wd, s.const(B1, 2), 2)
    # Команды загрузки не задают F_ADD/F_SUB/F_CMP: тогда АЛУ пропускает операнд,
    # то есть первый слагаемое обнуляется и ALU_R = WDATA.
    op_any = ORB(s, [s.ref(u"F_ADD", 0), s.ref(u"F_SUB", 0), s.ref(u"F_CMP", 0)], 2)
    alu_a = SELb(s, op_any, alu_a, s.const(B0, 2), 3)'''
if old_sel in t:
    t = t.replace(old_sel, new_sel, 1)
    print(u"АЛУ: 3-входовой выбор операнда + пропуск для загрузок")
else:
    print(u"НЕ найден выбор операндов АЛУ")

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
