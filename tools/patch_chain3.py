# -*- coding: utf-8 -*-
"""
patch_chain3.py -- sloi poluchayut kontaktnyy vyhod OUT (delаem v GENERATORE).

Pravilo 3 konspekta: telo FB generiruetsya, tolko esli vyzov CHITAETsya.
Bez etogo FB_RegFile ne vypolnyaetsya (A=0, PC stoit pri PC_NEW=$0202).

1) v fbd.py: klapan "u ekzemplyara net vyhodov" neprimenim k sloyam FB_CPU_*/FB_Latch/FB_RegFile;
2) v gen_top3.py: u sloev dobavlyaetsya outputs=[(u"OUT", u"BOOL")] i v tele OUT := Enable;
3) v fb_core: kazhdyy vyzov chitaetsya v GVL_CPU.ChainN.
"""
import io
import ast

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
FB = ROOT + r"\tools\fbd.py"
GT = ROOT + r"\tools\gen_top3.py"
NL = u"\n"

# ------------------------------------------------------------------ 1. fbd.py
t = io.open(FB, "rb").read().decode("utf-8")
old = (u'        if inst and type_name not in OUT_PIN:\n'
       u'            out_pin = None')
new = (u'        LAYER_TYPES = (u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack",\n'
       u'                       u"FB_CPU_AluFlags", u"FB_CPU_PcWb", u"FB_CPU_Store",\n'
       u'                       u"FB_Latch", u"FB_RegFile")\n'
       u'        if inst and type_name not in OUT_PIN and type_name not in LAYER_TYPES:\n'
       u'            out_pin = None')
if old in t:
    t = t.replace(old, new, 1)
    io.open(FB, "wb").write(t.encode("utf-8"))
    ast.parse(io.open(FB, encoding="utf-8").read())
    print(u"1) fbd.py: слоям разрешён выход OUT")
else:
    print(u"1) fbd.py: клапан не найден")

# ------------------------------------------------------------------ 2. gen_top3
t = io.open(GT, "rb").read().decode("utf-8")

LAYERS = [(u"FB_CPU_Addr1", u"fb_addr1", u"S1", 1),
          (u"FB_CPU_Select", u"fb_select", u"S2", 2),
          (u"FB_CPU_Stack", u"fb_stack", u"S3", 3),
          (u"FB_CPU_AluFlags", u"fb_aluflags", u"S4", 4),
          (u"FB_Latch", u"fb_latch", u"S5L", 5),
          (u"FB_CPU_PcWb", u"fb_pcwb", u"S5", 6),
          (u"FB_CPU_Store", u"fb_store", u"S6", 7),
          (u"FB_RegFile", u"fb_regfile", u"S7", 8)]

# 2a. интерфейсы
for name, fn, inst, idx in LAYERS:
    key = u'u"%s", u"functionBlock"' % name
    pos = t.find(key)
    if pos < 0:
        print(u"   интерфейс %s: не найден" % name)
        continue
    seg_end = t.find(u'))', pos)
    seg = t[pos:seg_end]
    if u'outputs=' in seg:
        continue
    if u'inputs=[(u"Enable", u"BOOL")], ' in seg:
        seg = seg.replace(u'inputs=[(u"Enable", u"BOOL")], ',
                          u'inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], ', 1)
    else:
        seg = seg.replace(u'interface(', u'interface(outputs=[(u"OUT", u"BOOL")], ', 1)
    t = t[:pos] + seg + t[seg_end:]

# 2b. тела: OUT := Enable в конце функции слоя
for name, fn, inst, idx in LAYERS:
    marker = u'def %s():' % fn
    pos = t.find(marker)
    if pos < 0:
        print(u"   тело %s: не найдено" % name)
        continue
    ret = t.find(u'    return s', pos)
    if ret < 0:
        continue
    ins = (u'    # Технический выход: гарантирует, что CODESYS сгенерирует и\n'
           u'    # исполнит тело слоя (правило 3 конспекта).\n'
           u'    s.assign(u"OUT", R(s, u"Enable"), 22)\n')
    if u's.assign(u"OUT"' not in t[pos:ret]:
        t = t[:ret] + ins + t[ret:]

# 2c. вызовы в fb_core -> чтение в ChainN
for name, fn, inst, idx in LAYERS:
    # ищем строку вызова (может быть многострочной) по префиксу
    pat = u'    call(s, u"%s", u"%s", [(u"Enable", s.const(u"TRUE", 0))]' % (name, inst)
    p = t.find(pat)
    if p < 0:
        print(u"   вызов %s: не найден" % name)
        continue
    # конец вызова -- закрывающая скобка на этой же строке
    e = t.find(u'\n', p)
    line = t[p:e]
    args_tail = line[len(pat):]        # обычно u', 5, w=140)'
    closing = args_tail.rstrip()
    colw = closing.rstrip(u')')
    newline = (u'    ch = call(s, u"%s", u"%s", [(u"Enable", s.const(u"TRUE", 0))]%s)\n'
               u'    W(s, u"Chain%d", ch, 1)' % (name, inst, colw, idx))
    t = t[:p] + newline + t[e:]

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"2) gen_top3: интерфейсы, тела и чтение OUT готовы")
print(u"   outputs OUT:", t.count(u'u"OUT", u"BOOL"'), u"| Chain:", t.count(u'u"Chain'))
