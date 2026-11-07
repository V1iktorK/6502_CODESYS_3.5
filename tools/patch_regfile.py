# -*- coding: utf-8 -*-
"""
patch_regfile.py -- po konspektu kollegi (8080/CP/M):

  * 2.2  svyaz "vyhod vyzova FB -> vhod bloka" teryaetsya => NIKAKIH provodov ot
         ekzemplyarov; tolko zashchelka cherez peremennuyu (u nas -- GVL);
  * 2.5  chtenie yacheyki v toy zhe seti, gde ona pishetsya, daet STAROE znachenie
         => zapis registrov vyvoditsya v OTDELNYY POU (FB_RegFile), kotoryy tolko
         chitaet GVL (zapisi drugih POU) i pishet GVL odnim vyrazheniem na registr;
  * 2.1  fan-out zapreshchen => odin outvar na registr, bez promezhutochnyh lokalnyh.

Chto delaem:
  1) otkat "variant A provodami": SL_PCSEL i SL_BRN2 snova pisut v GVL (togvl),
     vyzov v FB_CPU_PcWb snova chitaet GVL_CPU.PC_NEW / P_BRN;
  2) novyy POU FB_RegFile -- tolko zapis A, X, Y, P, SP, PC;
  3) iz FB_CPU_PcWb ubiraem zapis registrov i vyzov FB_RegFile dobavlyaem v
     FB_CPU_Core poslednim sloem.
"""
import io
import ast

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
GS = ROOT + r"\tools\gen_step3.py"
GT = ROOT + r"\tools\gen_top3.py"
TOG = ROOT + r"\tools\togvl.py"

# ---------------------------------------------------------------- 1. откат
t = io.open(GS, "rb").read().decode("utf-8")
t = t.replace(u'    s.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)',
              u'    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)')
t = t.replace(u'    s.assign(u"OUT", cur, 8)',
              u'    s.assign(u"PC_NEW", cur, 8)')
t = t.replace(u'outputs=[(u"OUT", u"WORD")]', u'outputs=[(u"BRN_TGT", u"WORD")]')
io.open(GS, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GS, encoding="utf-8").read())
print(u"gen_step3: откат проводов")

t = io.open(TOG, "rb").read().decode("utf-8")
t = t.replace(u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE",',
              u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",')
io.open(TOG, "wb").write(t.encode("utf-8"))
ast.parse(io.open(TOG, encoding="utf-8").read())
print(u"togvl: SL_PCSEL/SL_BRN2 снова пишут в GVL")

# ---------------------------------------------------------------- 2. gen_top3
t = io.open(GT, "rb").read().decode("utf-8")

# 2.1 вернуть чтение GVL для P_BRN и PC_NEW
old_bt = (u'    bt = call(s, u"SL_BRN2", u"Bt",\n'
          u'              [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),\n'
          u'               (u"TAKE", R(s, u"TAKE"))], 1, w=110)\n'
          u'    # цель ветвления подаётся ПРОВОДОМ в контакт P_BRN\n'
          u'    pins = []\n'
          u'    for n in PC_CAND:\n'
          u'        pins.append((n, bt if n == u"P_BRN" else R(s, n)))\n'
          u'    ps = call(s, u"SL_PCSEL", u"Ps", [(u"PC_MODE", R(s, u"PC_MODE"))] + pins,\n'
          u'              2, w=150)')
new_bt = (u'    call(s, u"SL_BRN2", u"Bt",\n'
          u'         [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),\n'
          u'          (u"TAKE", R(s, u"TAKE"))], 1, w=110)\n'
          u'    call(s, u"SL_PCSEL", u"Ps",\n'
          u'         [(u"PC_MODE", R(s, u"PC_MODE"))] + [(n, R(s, n)) for n in PC_CAND],\n'
          u'         2, w=150)')
if old_bt in t:
    t = t.replace(old_bt, new_bt, 1)
    print(u"gen_top3: PC_NEW/P_BRN снова через GVL")
else:
    print(u"НЕ найден блок Bt/Ps (уже откачен?)")

t = t.replace(u'(u"PC_NEW", ps), (u"Enable", R(s, u"Enable"))] +',
              u'(u"PC_NEW", R(s, u"PC_NEW")), (u"Enable", R(s, u"Enable"))] +')

# 2.2 убрать запись регистров из PcWb
start = t.find(u'    # --- запись регистров: считаем в локальную, затем копируем в GVL_CPU ---')
end = t.find(u'    return s', start)
if start > 0 and end > start:
    t = t[:start] + (u'    # Запись регистров вынесена в отдельный POU FB_RegFile: po konspektu\n'
                     u'    # (2.5) chtenie yacheyki v toy zhe seti, gde ona pishetsya, daet staroe\n'
                     u'    # znachenie, poetomu pisat' registr i schitat' ego znachenie nuzhno v raznyh POU.\n') + t[end:]
    print(u"PcWb: запись регистров убрана")
else:
    print(u"НЕ найден блок записи регистров в PcWb")

# 2.3 новый слой FB_RegFile
anchor = u'def fb_core():'
regfile = u'''def fb_regfile():
    """FB_RegFile: zapis registrov. Tolko chtenie GVL i odno vyrazhenie na registr.

    Po konspektu (2.2) svyaz "vyhod vyzova FB -> vhod bloka" teryaetsya, poetomu
    nikakih provodov: vse znacheniya chitayutsya iz GVL (ih zapisali drugie POU
    v etom zhe skane -- mezhsetevoe chtenie rabotaet). Po (2.5) net promezhutochnyh
    peremennyh: odin outvar = odno vyrazhenie.
    """
    s = Sheet(u"FB_RegFile: запись регистров")
    W(s, u"A", s.blk(u"SEL", [(u"G", R(s, u"LD_A_E")), (u"IN0", R(s, u"REG_WR")),
                              (u"IN1", R(s, u"A"))], 1), 2)
    W(s, u"X", s.blk(u"SEL", [(u"G", R(s, u"LD_X_E")), (u"IN0", R(s, u"REG_WR")),
                              (u"IN1", R(s, u"X"))], 3), 4)
    W(s, u"Y", s.blk(u"SEL", [(u"G", R(s, u"LD_Y_E")), (u"IN0", R(s, u"REG_WR")),
                              (u"IN1", R(s, u"Y"))], 5), 6)
    W(s, u"P", s.blk(u"SEL", [(u"G", R(s, u"LD_P_E")), (u"IN0", R(s, u"REG_WR")),
                              (u"IN1", R(s, u"P_NEW"))], 7), 8)
    W(s, u"SP", s.blk(u"SEL", [(u"G", R(s, u"LD_SP_E")), (u"IN0", R(s, u"SP_NEW")),
                               (u"IN1", R(s, u"SP"))], 9), 10)
    W(s, u"PC", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 11)), (u"IN0", R(s, u"PC_NEW")),
                               (u"IN1", R(s, u"PC"))], 11), 12)
    return s


def fb_core():'''
if anchor in t:
    t = t.replace(anchor, regfile, 1)
    print(u"добавлен fb_regfile")
else:
    print(u"НЕ найден fb_core")

# 2.4 вызов S7 в ядре
old_s6 = u'    call(s, u"FB_CPU_Store", u"S6", [], 10, w=140)'
new_s6 = (u'    call(s, u"FB_CPU_Store", u"S6", [], 10, w=140)\n'
          u'    call(s, u"FB_RegFile", u"S7", [], 11, w=140)')
if old_s6 in t:
    t = t.replace(old_s6, new_s6, 1)
    print(u"вызов S7 добавлен")
else:
    print(u"НЕ найден вызов S6")

# 2.5 объявление экземпляра S7
t = t.replace(u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store")),',
              u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store", u"S7", u"FB_RegFile")),')

# 2.6 запись файла FB_RegFile
t = t.replace(u'''    write(u"PRG_PLC", pou_xml(''',
              u'''    write(u"FB_RegFile", pou_xml(
        u"FB_RegFile", u"functionBlock",
        interface(locals_=[]),
        [fb_regfile()], u"запись регистров"))

    write(u"PRG_PLC", pou_xml(''')

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис gen_top3 OK")
