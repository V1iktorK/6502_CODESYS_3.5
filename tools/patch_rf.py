# -*- coding: utf-8 -*-
"""patch_rf.py -- regfile po konspektu (2.1/2.2/2.5), akkuratnaya versiya."""
import io
import ast

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
GS = ROOT + r"\tools\gen_step3.py"
GT = ROOT + r"\tools\gen_top3.py"
TOG = ROOT + r"\tools\togvl.py"

NL = u"\n"

# -------- 1. откат проводов в gen_step3
t = io.open(GS, "rb").read().decode("utf-8")
t = t.replace(u'    s.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)',
              u'    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)')
t = t.replace(u'    s.assign(u"OUT", cur, 8)', u'    s.assign(u"PC_NEW", cur, 8)')
t = t.replace(u'outputs=[(u"OUT", u"WORD")]', u'outputs=[(u"BRN_TGT", u"WORD")]')
io.open(GS, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GS, encoding="utf-8").read())
print(u"1) gen_step3 откачен")

# -------- 2. togvl: вернуть SL_PCSEL / SL_BRN2
t = io.open(TOG, "rb").read().decode("utf-8")
if u"u\"SL_PCSEL\"" not in t:
    t = t.replace(u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE",',
                  u'    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",')
io.open(TOG, "wb").write(t.encode("utf-8"))
ast.parse(io.open(TOG, encoding="utf-8").read())
print(u"2) togvl: PCSEL/BRN2 снова в GVL")

# -------- 3. gen_top3
t = io.open(GT, "rb").read().decode("utf-8")

lines_old_bt = [u'    bt = call(s, u"SL_BRN2", u"Bt",',
                u'              [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),',
                u'               (u"TAKE", R(s, u"TAKE"))], 1, w=110)',
                u'    # цель ветвления подаётся ПРОВОДОМ в контакт P_BRN',
                u'    pins = []',
                u'    for n in PC_CAND:',
                u'        pins.append((n, bt if n == u"P_BRN" else R(s, n)))',
                u'    ps = call(s, u"SL_PCSEL", u"Ps", [(u"PC_MODE", R(s, u"PC_MODE"))] + pins,',
                u'              2, w=150)']
lines_new_bt = [u'    call(s, u"SL_BRN2", u"Bt",',
                u'         [(u"PC2", R(s, u"PC2")), (u"C_REL", R(s, u"C_REL")),',
                u'          (u"TAKE", R(s, u"TAKE"))], 1, w=110)',
                u'    call(s, u"SL_PCSEL", u"Ps",',
                u'         [(u"PC_MODE", R(s, u"PC_MODE"))] + [(n, R(s, n)) for n in PC_CAND],',
                u'         2, w=150)']
old_bt = NL.join(lines_old_bt)
if old_bt in t:
    t = t.replace(old_bt, NL.join(lines_new_bt), 1)
    print(u"3) gen_top3: Bt/Ps через GVL")
else:
    print(u"3) блок Bt/Ps не найден (уже откачен)")

t = t.replace(u'(u"PC_NEW", ps), (u"Enable", R(s, u"Enable"))] +',
              u'(u"PC_NEW", R(s, u"PC_NEW")), (u"Enable", R(s, u"Enable"))] +')

# убрать запись регистров из PcWb
start = t.find(u'    # --- запись регистров')
end = t.find(u'    return s', start)
if start > 0 and end > start:
    note = NL.join([u'    # Запись регистров вынесена в отдельный POU FB_RegFile:',
                    u'    # по конспекту (2.5) чтение ячейки в той же сети, где она',
                    u'    # пишется, даёт старое значение.',
                    u''])
    t = t[:start] + note + t[end:]
    print(u"4) PcWb: запись регистров убрана")
else:
    print(u"4) блок записи регистров в PcWb не найден")

# fb_regfile
if u"def fb_regfile():" not in t:
    body = []
    body.append(u'def fb_regfile():')
    body.append(u'    """FB_RegFile: запись A, X, Y, P, SP, PC.')
    body.append(u'')
    body.append(u'    По конспекту: (2.2) связь "выход вызова FB -> вход блока" теряется,')
    body.append(u'    поэтому никаких проводов -- только чтение GVL (его записали другие POU');
    body.append(u'    в этом же скане) и один outvar на регистр (2.5: без промежуточных')
    body.append(u'    переменных, чтобы не читать ячейку в той же сети, где пишем).')
    body.append(u'    """')
    body.append(u'    s = Sheet(u"FB_RegFile: запись регистров")')
    specs = [(u"A", u"LD_A_E", u"REG_WR", u"A", 1),
             (u"X", u"LD_X_E", u"REG_WR", u"X", 3),
             (u"Y", u"LD_Y_E", u"REG_WR", u"Y", 5),
             (u"P", u"LD_P_E", u"REG_WR", u"P_NEW", 7),
             (u"SP", u"LD_SP_E", u"SP_NEW", u"SP", 9)]
    for reg, gate, newv, oldv, col in specs:
        body.append(u'    W(s, u"%s", s.blk(u"SEL", [(u"G", R(s, u"%s")), (u"IN0", R(s, u"%s")),'
                    u' (u"IN1", R(s, u"%s"))], %d), %d)' % (reg, gate, newv, oldv, col, col + 1))
    body.append(u'    W(s, u"PC", s.blk(u"SEL", [(u"G", s.const(u"TRUE", 11)),'
                u' (u"IN0", R(s, u"PC_NEW")), (u"IN1", R(s, u"PC"))], 11), 12)')
    body.append(u'    return s')
    body.append(u'')
    body.append(u'')
    body.append(u'def fb_core():')
    t = t.replace(u'def fb_core():', NL.join(body), 1)
    print(u"5) fb_regfile добавлен")
else:
    print(u"5) fb_regfile уже есть")

# вызов S7
if u'u"S7"' not in t:
    t = t.replace(u'    call(s, u"FB_CPU_Store", u"S6", [], 10, w=140)',
                  u'    call(s, u"FB_CPU_Store", u"S6", [], 10, w=140)' + NL +
                  u'    call(s, u"FB_RegFile", u"S7", [], 11, w=140)', 1)
    t = t.replace(u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store")),',
                  u'u"S5", u"FB_CPU_PcWb", u"S6", u"FB_CPU_Store", u"S7", u"FB_RegFile")),')
    print(u"6) вызов S7 добавлен")
else:
    print(u"6) S7 уже есть")

# запись файла
if u'write(u"FB_RegFile"' not in t:
    t = t.replace(u'    write(u"PRG_PLC", pou_xml(',
                  u'    write(u"FB_RegFile", pou_xml(' + NL +
                  u'        u"FB_RegFile", u"functionBlock",' + NL +
                  u'        interface(locals_=[]),' + NL +
                  u'        [fb_regfile()], u"запись регистров"))' + NL + NL +
                  u'    write(u"PRG_PLC", pou_xml(', 1)
    print(u"7) запись файла FB_RegFile добавлена")

io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис gen_top3 OK")
