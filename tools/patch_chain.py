# -*- coding: utf-8 -*-
"""
patch_chain.py -- tekhnicheskiy vyhod OUT u kazhdogo sloya.

Prichina ostatka: sloi, u kotoryh net ni odnogo kontaktnogo vyhoda
(FB_CPU_AluFlags, FB_RegFile i dr.), ne vypolnyalis: ALU_R ostavalsya 0,
registry ne zapisyvalis. Po konspektu (00_ГЛАВНОЕ, pravilo 3) telo POU
generiruetsya tolko esli vyzov CHITAETsya.

Reshenie: kazhdyy sloy otdaet tekhnicheskiy vyhod OUT := Enable, a FB_CPU_Core
chitaet ego v GVL_CPU.Chain1..Chain8. Togda vse sloi garantirovanno ispolnyayutsya.
"""
import io
import ast

GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
NL = u"\n"

LAYERS = [(u"FB_CPU_Addr1", u"S1", 1),
          (u"FB_CPU_Select", u"S2", 2),
          (u"FB_CPU_Stack", u"S3", 3),
          (u"FB_CPU_AluFlags", u"S4", 4),
          (u"FB_Latch", u"S5L", 5),
          (u"FB_CPU_PcWb", u"S5", 6),
          (u"FB_CPU_Store", u"S6", 7),
          (u"FB_RegFile", u"S7", 8)]

t = io.open(GT, "rb").read().decode("utf-8")

# ------------------------------------------------------------------ 1. interfeys
for name, inst, idx in LAYERS:
    key = u'u"%s", u"functionBlock"' % name
    pos = t.find(key)
    if pos < 0:
        print(u"  %s: не найден" % name)
        continue
    # ishem blok interface( ... ) posle etogo i dobavlyaem outputs, esli ih net
    seg_end = t.find(u'))', pos)
    seg = t[pos:seg_end]
    if u'outputs=' in seg:
        continue
    if u'inputs=[(u"Enable", u"BOOL")], ' in seg:
        seg = seg.replace(u'inputs=[(u"Enable", u"BOOL")], ',
                          u'inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], ')
    else:
        seg = seg.replace(u'interface(', u'interface(outputs=[(u"OUT", u"BOOL")], ')
    t = t[:pos] + seg + t[seg_end:]

# ------------------------------------------------------------------ 2. telo sloya
def add_out(body_marker, t):
    """Dobavit' v konce funkcii sloya stroku s.assign(u"OUT", R(s,u"Enable"))"""
    pos = t.find(body_marker)
    if pos < 0:
        return t, False
    ret = t.find(u'    return s', pos)
    if ret < 0:
        return t, False
    ins = (u'    # технический выход: гарантирует генерацию/исполнение тела слоя\n'
           u'    s.assign(u"OUT", R(s, u"Enable"), 20)\n')
    return t[:ret] + ins + t[ret:], True

for name, inst, idx in LAYERS:
    marker = u'def %s():' % name.lower().replace(u"_", u"_")
    # imena funkciy v generatorе: fb_addr1, fb_select, fb_stack, fb_aluflags,
    # fb_latch, fb_pcwb, fb_store, fb_regfile
    pass

FUNCS = {u"FB_CPU_Addr1": u"def fb_addr1():",
         u"FB_CPU_Select": u"def fb_select():",
         u"FB_CPU_Stack": u"def fb_stack():",
         u"FB_CPU_AluFlags": u"def fb_aluflags():",
         u"FB_Latch": u"def fb_latch():",
         u"FB_CPU_PcWb": u"def fb_pcwb():",
         u"FB_CPU_Store": u"def fb_store():",
         u"FB_RegFile": u"def fb_regfile():"}
for name, inst, idx in LAYERS:
    fn = FUNCS.get(name)
    if not fn:
        continue
    if u's.assign(u"OUT", R(s, u"Enable")' in t:
        # uzhe est hotya by v odnom -- proverim po imenu funkcii
        pass
    t, ok = add_out(fn, t)
    if not ok:
        print(u"  %s: не удалось добавить OUT" % name)

# ------------------------------------------------------------------ 3. vyzov: chitat' OUT
for name, inst, idx in LAYERS:
    old = u'    call(s, u"%s", u"%s", [(u"Enable", s.const(u"TRUE", 0))], ' % (name, inst)
    if old in t:
        # naidem nomer stroki i zamеnим vyzov na prisvoenie v Chain<idx>
        p = t.find(old)
        end = t.find(u')', p)
        line = t[p:end + 1]
        colpart = line[line.rfind(u',') + 1:].strip()
        t = (t[:p] + u'    ch = call(s, u"%s", u"%s", [(u"Enable", s.const(u"TRUE", 0))], 0)\n'
             % (name, inst) +
             u'    W(s, u"Chain%d", ch, 1)\n' % idx +
             t[end + 1:])

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис OK; outputs OUT:", t.count(u'u"OUT", u"BOOL"'),
      u"; Chain:", t.count(u'u"Chain'))
