# -*- coding: utf-8 -*-
"""
patch_wire2.py -- dovesti variant A do konca dlya PC.

1) isklyuchit SL_PCSEL i SL_BRN2 iz togvl (oni dolzhny ostatsya s kontaktom OUT,
   a ne pisat v GVL_CPU.OUT);
2) v FB_CPU_PcWb peredat provod ps v kontakt PC_NEW bloka FB_WriteBack.
"""
import io, ast

TOG = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\togvl.py"
GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"

t = io.open(TOG, "rb").read().decode("utf-8")
t = t.replace(u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",',
              u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE",')
io.open(TOG, "wb").write(t.encode("utf-8"))
ast.parse(io.open(TOG, encoding="utf-8").read())
print(u"togvl: SL_PCSEL и SL_BRN2 больше не переводятся в GVL")

t = io.open(GT, "rb").read().decode("utf-8")
old = u'          (u"PC_NEW", R(s, u"PC_NEW")), (u"Enable", R(s, u"Enable"))] +'
new = u'          (u"PC_NEW", ps), (u"Enable", R(s, u"Enable"))] +'
if old in t:
    t = t.replace(old, new, 1)
    print(u"gen_top3: PC_NEW подан проводом в FB_WriteBack")
else:
    print(u"НЕ найдена строка PC_NEW в вызове Wb")
io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис OK")
