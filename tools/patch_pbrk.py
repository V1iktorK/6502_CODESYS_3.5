# -*- coding: utf-8 -*-
"""
patch_pbrk.py -- dobavit propushchennye prisvoeniya kandidatov PC.

V novoy kompozicii (gen_top3.py) ne prisvaivalis:
  P_BRK := BRKV     (vektor preрыvaniya) -- poetomu PC_NEW vsegda 0 dlya BRK;
  P_EFF := EFF      (absolyutnyy adres dlya JMP/JSR).
"""
import io, ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(P, "rb").read().decode("utf-8")

a = u'    W(s, u"C_STK", R(s, u"C_ABS"), 13)'
b = (u'    W(s, u"C_STK", R(s, u"C_ABS"), 13)\n'
     u'    W(s, u"P_BRK", R(s, u"BRKV"), 14)')
if a in t:
    t = t.replace(a, b, 1)
    print(u"P_BRK добавлен")
else:
    print(u"НЕ найден C_STK")

a2 = u'''    call(s, u"SL_WDATA2", u"Wd",
         [(u"ADDR_MODE", R(s, u"ADDR_MODE")), (u"EFF", R(s, u"EFF")),
          (u"OP1", R(s, u"OP1"))], 3, w=120)
    return s'''
b2 = u'''    call(s, u"SL_WDATA2", u"Wd",
         [(u"ADDR_MODE", R(s, u"ADDR_MODE")), (u"EFF", R(s, u"EFF")),
          (u"OP1", R(s, u"OP1"))], 3, w=120)
    W(s, u"P_EFF", R(s, u"EFF"), 4)
    return s'''
if a2 in t:
    t = t.replace(a2, b2, 1)
    print(u"P_EFF добавлен")
else:
    print(u"НЕ найден Wd")

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
