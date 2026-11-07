# -*- coding: utf-8 -*-
"""
patch_latch.py -- ustranyaem narusheniya pravila 2.5 (konspekt kollegi):
"chtenie yacheyki v toy zhe seti, gde ona pishetsya -> staroe znachenie".

Chto bylo ne tak: vnutri odnogo POU vypolnyalis' i zapis', i chtenie:
  FB_CPU_Addr1 : P_BRK  <- BRKV      (BRKV pishet SL_BRK vnutri togo zhe POU)
  FB_CPU_Select: P_EFF  <- EFF       (EFF pishet SL_SELECT12 vnutri togo zhe POU)
  FB_CPU_Stack : P_JRET/P_ADV/P_KEEP/PULL_LO <- JRET/ADV/PC/Mem[STK_R0]
  FB_CPU_PcWb  : P_BRN  <- BRN_TGT   (BRN_TGT pishet SL_BRN2 vnutri togo zhe POU)

Reshenie: otdelnyy POU FB_Latch, kotoryy TOLKO chitaet GVL (ego zapisali drugie
POU v etom zhe skane) i TOLKO pishet P_*. On stavitsya pered FB_CPU_PcWb.
"""
import io
import ast

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
GT = ROOT + r"\tools\gen_top3.py"
NL = u"\n"

t = io.open(GT, "rb").read().decode("utf-8")

# --- 1. ubiraem starye zashchelki iz sloev
removals = [
    u'    W(s, u"P_BRK", R(s, u"BRKV"), 14)',
    u'    W(s, u"P_EFF", R(s, u"EFF"), 4)',
    u'    W(s, u"P_JRET", R(s, u"JRET"), 11)',
    u'    W(s, u"P_ADV", R(s, u"ADV"), 11)',
    u'    W(s, u"P_KEEP", R(s, u"PC"), 11)',
    u'    W(s, u"PULL_LO", s.ref(G.MEM + u".Mem[STK_R0]", 11), 11)',
]
n = 0
for line in removals:
    if line in t:
        t = t.replace(line + NL, u'', 1)
        n += 1
print(u"убранo старых защёлок: %d" % n)

# P_BRN iz PcWb
old_pbrn = u'    GVL(s, u"P_BRN", bt, 3) if False else None'
for cand in (u'    W(s, u"P_BRN", R(s, u"BRN_TGT"), 3)',
             u'    GVL(s, u"P_BRN", bt, 3)'):
    if cand in t:
        t = t.replace(cand + NL, u'', 1)
        print(u"P_BRN из PcWb убран")

# --- 2. novyy POU FB_Latch
if u"def fb_latch():" not in t:
    body = []
    body.append(u'def fb_latch():')
    body.append(u'    """FB_Latch: защёлкивание межуровневых значений в GVL_CPU.')
    body.append(u'')
    body.append(u'    По конспекту (2.5): запись и чтение одной ячейки в пределах одного POU')
    body.append(u'    разъезжаются на такт. Поэтому все "перекладки" P_* живут здесь: этот POU')
    body.append(u'    только читает ячейки, записанные предыдущими слоями, и только пишет P_*.')
    body.append(u'    """')
    body.append(u'    s = Sheet(u"FB_Latch: защёлкивание межуровневых значений")')
    body.append(u'    W(s, u"P_EFF", R(s, u"EFF"), 1)')
    body.append(u'    W(s, u"P_BRK", R(s, u"BRKV"), 3)')
    body.append(u'    W(s, u"P_BRN", R(s, u"BRN_TGT"), 5)')
    body.append(u'    W(s, u"P_JRET", R(s, u"JRET"), 7)')
    body.append(u'    W(s, u"P_ADV", R(s, u"ADV"), 9)')
    body.append(u'    W(s, u"P_KEEP", R(s, u"PC"), 11)')
    body.append(u'    W(s, u"PULL_LO", s.ref(G.MEM + u".Mem[STK_R0]", 13), 14)')
    body.append(u'    return s')
    body.append(u'')
    body.append(u'')
    body.append(u'def fb_core():')
    t = t.replace(u'def fb_core():', NL.join(body), 1)
    print(u"добавлен fb_latch")

# --- 3. vyzov sloya pered PcWb i obyavlenie ekzemplyara
if u'u"S5L"' not in t:
    t = t.replace(u'    call(s, u"FB_CPU_PcWb", u"S5", [], 9, w=140)',
                  u'    call(s, u"FB_Latch", u"S5L", [], 9, w=140)' + NL +
                  u'    call(s, u"FB_CPU_PcWb", u"S5", [], 10, w=140)', 1)
    t = t.replace(u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store", u"S7", u"FB_RegFile")),',
                  u'u"S5L", u"FB_Latch", u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store",'
                  u' u"S7", u"FB_RegFile")),')
    print(u"вызов S5L добавлен")

if u'write(u"FB_Latch"' not in t:
    t = t.replace(u'    write(u"FB_RegFile", pou_xml(',
                  u'    write(u"FB_Latch", pou_xml(' + NL +
                  u'        u"FB_Latch", u"functionBlock",' + NL +
                  u'        interface(locals_=[]),' + NL +
                  u'        [fb_latch()], u"защёлкивание значений"))' + NL + NL +
                  u'    write(u"FB_RegFile", pou_xml(', 1)
    print(u"запись файла FB_Latch добавлена")

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис gen_top3 OK")
