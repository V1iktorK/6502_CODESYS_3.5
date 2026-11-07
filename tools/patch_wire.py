# -*- coding: utf-8 -*-
"""
patch_wire.py -- variant A dlya PC: odin vyhod OUT i provod v kompozicii.

Chto delаem:
  1) SL_PCSEL: vyhod pereimenovan v OUT (edinstvennyy) -- togda CODESYS sam
     podklyuchaet ego, kogda my ssylaemsya na ekzemplyar;
  2) SL_BRN2: vyhod pereimenovan v OUT;
  3) v FB_CPU_PcWb (gen_top3.py): PC_NEW bеretsya PROVODOM ot ekzemplyara Ps,
     a ne cherez GVL_CPU.PC_NEW. To zhe dlya celi vetvleniya (BT podaetsya
     provodom v kontakt P_BRN).
"""
import io, ast, re

GC = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_cpu_split.py"
GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"

# --- 1/2: pereimenovat vyhody v generatorah shagov (gen_step3.py)
GS = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_step3.py"
t = io.open(GS, "rb").read().decode("utf-8")

t = t.replace(u'    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)',
              u'    s.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)')
t = t.replace(u'    s.assign(u"PC_NEW", cur, 8)',
              u'    s.assign(u"OUT", cur, 8)')
io.open(GS, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GS, encoding="utf-8").read())
print(u"gen_step3: выходы OUT")

# ispravit interfeysy v tom zhe fayle
t = io.open(GS, "rb").read().decode("utf-8")
t = t.replace(u'outputs=[(u"BRN_TGT", u"WORD")]', u'outputs=[(u"OUT", u"WORD")]')
t = t.replace(u'outputs=[(u"PC_NEW", u"WORD")]', u'outputs=[(u"OUT", u"WORD")]')
io.open(GS, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GS, encoding="utf-8").read())
print(u"gen_step3: интерфейсы обновлены")

# --- 3: provoda v gen_top3.py
t = io.open(GT, "rb").read().decode("utf-8")
old = (u'    call(s, u"SL_BRN2", u"Bt",\n'
       u'         [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),\n'
       u'          (u"TAKE", R(s, u"TAKE"))], 1, w=110)\n'
       u'    call(s, u"SL_PCSEL", u"Ps",\n'
       u'         [(u"PC_MODE", R(s, u"PC_MODE"))] + [(n, R(s, n)) for n in PC_CAND],\n'
       u'         2, w=150)')
new = (u'    bt = call(s, u"SL_BRN2", u"Bt",\n'
       u'              [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),\n'
       u'               (u"TAKE", R(s, u"TAKE"))], 1, w=110)\n'
       u'    # цель ветвления подаётся ПРОВОДОМ в контакт P_BRN\n'
       u'    pins = []\n'
       u'    for n in PC_CAND:\n'
       u'        pins.append((n, bt if n == u"P_BRN" else R(s, n)))\n'
       u'    ps = call(s, u"SL_PCSEL", u"Ps", [(u"PC_MODE", R(s, u"PC_MODE"))] + pins,\n'
       u'              2, w=150)')
if old in t:
    t = t.replace(old, new, 1)
    print(u"gen_top3: Bt/Ps соединены проводом")
else:
    print(u"НЕ найден блок Bt/Ps")

old2 = (u'            (u"PC", u"__TRUE__", R(s, u"PC"), R(s, u"PC_NEW"))]')
new2 = (u'            (u"PC", u"__TRUE__", R(s, u"PC"), ps)]')
if old2 in t:
    t = t.replace(old2, new2, 1)
    print(u"gen_top3: PC берётся проводом от Ps")
else:
    print(u"НЕ найдена строка PC")

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис gen_top3 OK")
