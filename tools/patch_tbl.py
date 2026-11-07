# -*- coding: utf-8 -*-
"""
patch_tbl.py -- perenesti chtenie tablicy iz deshifratora v kompoziciyu.

Pochemu: deshifrator s chteniem GVL_TABLE.XX[Op] zavisает na importe (276 blokov),
a variant tolko s BOOL-signalami importirovalsya stabilno (547 blokov). Poetomu:
  * v deshifratore ostayutsya tolko BOOL-signaly (EQ + derevya OR);
  * bajtovye signaly chitayutsya iz GVL_TABLE v sloe kompozicii FB_CPU_Core
    (8 prisvoeniy, ochen malenkiy list).
"""
import io

SPLIT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_cpu_split.py"
TOP = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"

# ---------------------------------------------------------------- 1. дешифратор
t = io.open(SPLIT, "rb").read().decode("utf-8")
start = t.find(u"    # БАЙТОВЫЕ сигналы берём из таблицы декодирования GVL_TABLE")
end = t.find(u"    return s, []", start)
if start < 0 or end < 0:
    raise SystemExit(u"НЕ найден блок байтовых сигналов в дешифраторе")
t = t[:start] + (u"    # Байтовые сигналы (ADDR_MODE, LEN, SRC, PC_MODE, SP_MODE, COND,\n"
                 u"    # ALU_A, ALU_B) читаются из таблицы GVL_TABLE в слое композиции:\n"
                 u"    # в этом листе их сборка через SEL/OR в рантайме давала нули.\n") + t[end:]
io.open(SPLIT, "wb").write(t.encode("utf-8"))
import ast
ast.parse(io.open(SPLIT, encoding="utf-8").read())
print(u"дешифратор: только BOOL-сигналы")

# ---------------------------------------------------------------- 2. композиция
t = io.open(TOP, "rb").read().decode("utf-8")
anchor = u'    call(s, u"FB_Decoder6502", u"Dec", [(u"Op", R(s, u"OPs"))], 3, w=170)'
add = (u'    call(s, u"FB_Decoder6502", u"Dec", [(u"Op", R(s, u"OPs"))], 3, w=170)\n'
       u'    # Байтовые сигналы — из таблицы декодирования (данные в GVL_TABLE)\n'
       u'    for sig in (u"ADDR_MODE", u"LEN", u"SRC", u"ALU_A", u"ALU_B",\n'
       u'                u"PC_MODE", u"SP_MODE", u"COND"):\n'
       u'        W(s, sig, s.ref(u"GVL_TABLE.%s[GVL_CPU.OPs]" % sig, 4), 4)\n')
if anchor in t:
    t = t.replace(anchor, add, 1)
    io.open(TOP, "wb").write(t.encode("utf-8"))
    ast.parse(io.open(TOP, encoding="utf-8").read())
    print(u"композиция: чтение таблицы добавлено")
else:
    print(u"НЕ найден вызов декодера в композиции")

# ---------------------------------------------------------------- 3. прямое чтение
help_txt = u"""
Справка: R()/W() работают с GVL_CPU; для GVL_TABLE используется s.ref напрямую.
"""
print(u"готово")
