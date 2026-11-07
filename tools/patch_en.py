# -*- coding: utf-8 -*-
"""
patch_en.py -- u kazhdogo sloya dolzhen byt' hotya by odin VHODNOY kontakt.

Simptom: sloi s "pustym" interfeysom (tolko GVL) ne vypolnyalis: ALU_R ostavalsya 0,
PC ne menyalsya, hotya PC_NEW=0x202 i WDATA=0x42 byli poschitany.
Reshenie: dobavit' vhod En : BOOL i peredavat' TRUE iz FB_CPU_Core.
"""
import io
import ast
import re

GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
NL = u"\n"

t = io.open(GT, "rb").read().decode("utf-8")

LAYERS = [u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack", u"FB_CPU_AluFlags",
          u"FB_Latch", u"FB_CPU_PcWb", u"FB_CPU_Store", u"FB_RegFile"]

# 1) v interfeys kazhdogo sloya dobavit' vhod En
for name in LAYERS:
    pat_plain = u'        interface(locals_='
    # u sloev raznye varianty: interface(locals_=...) ili interface(locals_=...) + [...]
    # prosto podmenyaem "interface(locals_=" na "interface(inputs=[(u\"En\", u\"BOOL\")], locals_="
    # tolko v bloke etogo POU
    idx = t.find(u'u"%s", u"functionBlock"' % name)
    if idx < 0:
        print(u"  %s: не найден в main()" % name)
        continue
    seg_end = t.find(u'))', idx)
    seg = t[idx:seg_end]
    if u'inputs=' in seg:
        continue
    new_seg = seg.replace(u'interface(locals_=',
                          u'interface(inputs=[(u"En", u"BOOL")], locals_=')
    if u'interface(' not in seg:
        new_seg = seg.replace(u'interface(',
                              u'interface(inputs=[(u"En", u"BOOL")], ')
    t = t[:idx] + new_seg + t[seg_end:]

# 2) vyzov kazhdogo sloya v fb_core: dobavit' pin En
for name in LAYERS:
    for inst in (u"S1", u"S2", u"S3", u"S4", u"S5L", u"S5", u"S6", u"S7"):
        old = u'    call(s, u"%s", u"%s", [], ' % (name, inst)
        if old in t:
            t = t.replace(old, u'    call(s, u"%s", u"%s", [(u"En", s.const(u"TRUE", 0))], '
                          % (name, inst), 1)

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис OK")
print(u"вхождений 'En' в интерфейсах:", t.count(u'u"En", u"BOOL"'))
print(u"вызовов с En:", t.count(u'[(u"En", s.const(u"TRUE", 0))]'))
