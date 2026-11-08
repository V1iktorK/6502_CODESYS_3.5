# -*- coding: utf-8 -*-
"""
patch_selconv.py -- edinoe soglashenie SEL: G=TRUE -> IN1 (kak v CODESYS).

Ranee v kode smeshalis' dva soglasheniya:
  * SELb(g, a, b)                -- "pri g -- pervyy argument";
  * s.blk("SEL",[(G,g),(IN0,def),(IN1,val)]) -- "pri g -- IN1".
Plyus ya dobavil globalnyy swap v fbd.py, kotoryy sdelal pravilnymi odni mesta
i nepravilnymi drugie.

Teper':
  1) ubiraem globalnyy swap iz fbd.py -- blok vyvoditsya kak est;
  2) SELb(g, a, b) vyvodit IN0=b, IN1=a (to est' pri g -- a);
  3) tri "syrыh" mesta, napisannyh v obratnom poryadke, ispravlyaem:
       SL_WDATA2 (imm -> OP1), SL_BRN2 (TAKE -> C_REL), FB_RegFile (razreshenie -> REG_WR).
"""
import io
import ast

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
FB = ROOT + r"\tools\fbd.py"
GC = ROOT + r"\tools\gen_cpu_split.py"
GS8 = ROOT + r"\tools\gen_step8.py"
GT = ROOT + r"\tools\gen_top3.py"

# ---------------------------------------------------------------- 1. убрать swap
t = io.open(FB, "rb").read().decode("utf-8")
start = t.find(u'        # ВАЖНО: у CODESYS SEL(G, IN0, IN1)')
end = t.find(u'        buf.append(u\'<inputVariables>\')')
if start > 0 and end > start:
    t = t[:start] + t[end:]
    io.open(FB, "wb").write(t.encode("utf-8"))
    ast.parse(io.open(FB, encoding="utf-8").read())
    print(u"1) fbd.py: глобальный swap убран")
else:
    print(u"1) swap не найден")

# ---------------------------------------------------------------- 2. SELb
t = io.open(GC, "rb").read().decode("utf-8")
old = (u'def SELb(s, g, a, b, col):\n'
       u'    return s.blk(u"SEL", [(u"G", g), (u"IN0", a), (u"IN1", b)], col)')
new = (u'def SELb(s, g, a, b, col):\n'
       u'    # Соглашение CODESYS: при G=TRUE выбирается IN1. Наш смысл: "при g -- a",\n'
       u'    # поэтому a ставим в IN1, а b -- в IN0.\n'
       u'    return s.blk(u"SEL", [(u"G", g), (u"IN0", b), (u"IN1", a)], col)')
if old in t:
    t = t.replace(old, new, 1)
    io.open(GC, "wb").write(t.encode("utf-8"))
    ast.parse(io.open(GC, encoding="utf-8").read())
    print(u"2) SELb: a -> IN1")
else:
    print(u"2) SELb не найден")

# ---------------------------------------------------------------- 3. SL_WDATA2
t = io.open(GC, "rb").read().decode("utf-8")
old_w = u'    s.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", op1), (u"IN1", mem)], 3), 5)'
new_w = u'    # при imm (G=TRUE) нужен OP1 -> он должен стоять в IN1\n    s.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", mem), (u"IN1", op1)], 3), 5)'
if old_w in t:
    t = t.replace(old_w, new_w, 1)
    io.open(GC, "wb").write(t.encode("utf-8"))
    print(u"3) SL_WDATA2: imm -> OP1")
else:
    print(u"3) SL_WDATA2 не найден")

# ---------------------------------------------------------------- 4. SL_BRN2
t = io.open(GS8, "rb").read().decode("utf-8")
old_b = u'    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)'
new_b = u'    # при TAKE (G=TRUE) нужна цель перехода C_REL -> она в IN1\n    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)'
if old_b in t:
    t = t.replace(old_b, new_b, 1)
    io.open(GS8, "wb").write(t.encode("utf-8"))
    print(u"4) SL_BRN2: TAKE -> C_REL")
else:
    print(u"4) SL_BRN2 не найден")

# ---------------------------------------------------------------- 5. FB_RegFile
t = io.open(GT, "rb").read().decode("utf-8")
old_r = (u'        body.append(u\'    W(s, u"%s", s.blk(u"SEL", [(u"G", R(s, u"%s")), (u"IN0", R(s, u"%s")),'
         u' (u"IN1", R(s, u"%s"))], %d), %d)\' % (reg, gate, newv, oldv, col, col + 1))')
new_r = (u'        body.append(u\'    W(s, u"%s", s.blk(u"SEL", [(u"G", R(s, u"%s")), (u"IN0", R(s, u"%s")),'
         u' (u"IN1", R(s, u"%s"))], %d), %d)\' % (reg, gate, oldv, newv, col, col + 1))')
if old_r in t:
    t = t.replace(old_r, new_r, 1)
    io.open(GT, "wb").write(t.encode("utf-8"))
    print(u"5) FB_RegFile: разрешение -> новое значение (в IN1)")
else:
    print(u"5) FB_RegFile: шаблон не найден")

# PC в RegFile: (IN0=PC_NEW, IN1=PC) -> нужно PC_NEW в IN1
t = io.open(GT, "rb").read().decode("utf-8")
old_pc = (u'    body.append(u\'    W(s, u"PC", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 11)),'
          u' (u"IN0", R(s, u"PC_NEW")), (u"IN1", R(s, u"PC"))], 11), 12)\')')
new_pc = (u'    body.append(u\'    W(s, u"PC", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 11)),'
          u' (u"IN0", R(s, u"PC")), (u"IN1", R(s, u"PC_NEW"))], 11), 12)\')')
if old_pc in t:
    t = t.replace(old_pc, new_pc, 1)
    io.open(GT, "wb").write(t.encode("utf-8"))
    print(u"6) FB_RegFile: PC := PC_NEW (в IN1)")
else:
    print(u"6) FB_RegFile PC: шаблон не найден")

ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис OK")
