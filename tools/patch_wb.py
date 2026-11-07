# -*- coding: utf-8 -*-
"""
patch_wb.py -- razovaya pravka generatorov:
  1) vozvrat imen REGA/REGX/REGY -> A/X/Y (oni zаtroнули FB_ALU6502);
  2) FB_WriteBack: ubiraem zapis registrov, ostavlyaem tolko REG_WR -> GVL_CPU;
  3) zapis registrov perenоsim v sloy kompozicii FB_CPU_PcWb (gen_top2.py).
"""
import io
import os
import re

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
SPLIT = os.path.join(ROOT, "tools", "gen_cpu_split.py")
TOP = os.path.join(ROOT, "tools", "gen_top2.py")


def rd(p):
    return io.open(p, "rb").read().decode("utf-8")


def wr(p, t):
    o = io.open(p, "wb")
    o.write(t.encode("utf-8"))
    o.close()


# ------------------------------------------------ 1. откат переименований
t = rd(SPLIT)
t = t.replace(u's.ref(u"REGA", 0)', u's.ref(u"A", 0)')
t = t.replace(u's.ref(u"REGX", 0)', u's.ref(u"X", 0)')
t = t.replace(u's.ref(u"REGY", 0)', u's.ref(u"Y", 0)')
t = t.replace(u'(u"REGA", u"BYTE"), (u"REGX", u"BYTE"), (u"REGY", u"BYTE"),',
              u'(u"A", u"BYTE"), (u"X", u"BYTE"), (u"Y", u"BYTE"),')
print(u"откат имён выполнен")

# ------------------------------------------------ 2. убрать запись регистров
start = t.find(u'    rw = s.ref(u"RW7", 8)')
end = t.find(u'    return s, [(u"REG_WR", u"BYTE")]')
if start < 0 or end < 0 or end < start:
    raise SystemExit(u"НЕ найден блок записи регистров")
new_tail = (u'    # Запись регистров вынесена в слой композиции FB_CPU_PcWb:\n'
            u'    # в этом листе CODESYS не типизировал SEL с регистровыми именами.\n'
            u'    s.assign(CPU + u".REG_WR", cur, 22)\n\n')
t = t[:start] + new_tail + t[end:]
t = t.replace(u'    return s, [(u"REG_WR", u"BYTE")] + [(u"RW%d" % k, u"BYTE") for k in range(8)] + extra',
              u'    return s, [(u"RW%d" % k, u"BYTE") for k in range(8)]')
wr(SPLIT, t)
print(u"FB_WriteBack: запись регистров убрана")

# ------------------------------------------------ 3. запись регистров в композиции
t = rd(TOP)
anchor = u'    return s\n\n\ndef fb_core():'
add = u'''    # --- запись регистров: считаем в локальную, затем копируем в GVL_CPU ---
    regs = [(u"A", u"LD_A_E", R(s, u"A"), R(s, u"REG_WR")),
            (u"X", u"LD_X_E", R(s, u"X"), R(s, u"REG_WR")),
            (u"Y", u"LD_Y_E", R(s, u"Y"), R(s, u"REG_WR")),
            (u"P", u"LD_P_E", R(s, u"P_NEW"), R(s, u"REG_WR")),
            (u"SP", u"LD_SP_E", R(s, u"SP"), R(s, u"SP_NEW")),
            (u"PC", u"Enable", R(s, u"PC"), R(s, u"PC_NEW"))]
    for i, (reg, gate, cur_v, wr_v) in enumerate(regs):
        nm = u"N_%s" % reg
        sel = s.blk(u"SEL", [(u"G", R(s, gate, 6)), (u"IN0", cur_v), (u"IN1", wr_v)], 6)
        s.assign(nm, sel, 8)
        W(s, reg, s.ref(nm, 9), 9)
    return s


def fb_core():'''
if anchor in t:
    t = t.replace(anchor, add, 1)
    wr(TOP, t)
    print(u"FB_CPU_PcWb: запись регистров добавлена")
else:
    print(u"НЕ найден якорь для вставки записи регистров")

# объявить локальные N_* в FB_CPU_PcWb
t = rd(TOP)
old_loc = u'''        interface(locals_=pouloc(u"Bt", u"SL_BRN2", u"Ps", u"SL_PCSEL",
                                 u"Wb", u"FB_WriteBack")),'''
new_loc = u'''        interface(locals_=pouloc(u"Bt", u"SL_BRN2", u"Ps", u"SL_PCSEL",
                                 u"Wb", u"FB_WriteBack") +
                  [(u"N_A", u"BYTE"), (u"N_X", u"BYTE"), (u"N_Y", u"BYTE"),
                   (u"N_P", u"BYTE"), (u"N_SP", u"BYTE"), (u"N_PC", u"WORD")]),'''
if old_loc in t:
    t = t.replace(old_loc, new_loc, 1)
    wr(TOP, t)
    print(u"FB_CPU_PcWb: локальные N_* объявлены")
else:
    print(u"НЕ найдено объявление локалей FB_CPU_PcWb")
