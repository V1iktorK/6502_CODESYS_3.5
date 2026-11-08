# -*- coding: utf-8 -*-
"""
patch_fbd2.py -- dva ispravleniya v fbd.py:

1) pou_xml() soбirал telo kak "<FBD>"+els i NE vyzyval Sheet.xml(), poetomu
   razvorachivanie fan-out (pravilo 2.1) ne rabotalo vovse. Teper' telo
   sobiраetsya cherez ob"edinennyy Sheet.xml().
2) Stupeni (SL_*, FB_Fetch, FB_Decoder6502, FB_ALU6502, FB_Flags, FB_WriteBack)
   poluchayut kontaktnyy vyhod OUT := TRUE -- bez etogo CODESYS ne ispolnyaet
   ih telo (ALU_R ostavalsya 0).
3) u ekzemplyarov bolshe ne otnimaetsya vyhodnoy kontakt.
"""
import io
import ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\fbd.py"
t = io.open(P, "rb").read().decode("utf-8")

# ---------------------------------------------------------------- 1. клапан
old_clamp = (u'        LAYER_TYPES = (u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack",\n'
             u'                       u"FB_CPU_AluFlags", u"FB_CPU_PcWb", u"FB_CPU_Store",\n'
             u'                       u"FB_Latch", u"FB_RegFile")\n'
             u'        if inst and type_name not in OUT_PIN and type_name not in LAYER_TYPES:\n'
             u'            out_pin = None\n')
if old_clamp in t:
    t = t.replace(old_clamp, u'', 1)
    print(u"1) клапан, отнимавший выход у экземпляров, убран")
else:
    old2 = (u'        if inst and type_name not in OUT_PIN:\n'
            u'            out_pin = None\n')
    if old2 in t:
        t = t.replace(old2, u'', 1)
        print(u"1) клапан убран")
    else:
        print(u"1) клапан не найден")

# ---------------------------------------------------------------- 2. шаги + OUT
anchor = u'    all_els = []\n    for s in sheets:\n        all_els.extend(s.els)\n    body = u"<FBD>" + u"".join(all_els) + u"</FBD>"'
if anchor not in t:
    print(u"2) НЕ найден блок сборки тела")
else:
    steps = (u'STEPS_NEED_OUT = (u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags",\n'
             u'                    u"FB_WriteBack", u"SL_C1A", u"SL_C1B", u"SL_YW",\n'
             u'                    u"SL_IND2", u"SL_INDP", u"SL_RELA", u"SL_RELC", u"SL_BRK",\n'
             u'                    u"SL_SELECT12", u"SL_WDATA2", u"SL_STK1", u"SL_STK2",\n'
             u'                    u"SL_STK3", u"SL_STK4", u"SL_SPSEL", u"SL_ADV",\n'
             u'                    u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL")\n')
    new_body = (u'    # Ступеням нужен контактный выход: CODESYS исполняет тело ПОУ только\n'
                u'    # тогда, когда его вызов что-то читает (правило 3 конспекта).\n'
                u'    if name in STEPS_NEED_OUT and u\'name="OUT"\' not in iface:\n'
                u'        sheets[0].assign(u"OUT", sheets[0].const(u"TRUE", 0), 0)\n'
                u'        if u"<outputVars>" in iface:\n'
                u'            iface = iface.replace(u"</outputVars>",\n'
                u'                u\'<variable name="OUT"><type><BOOL /></type></variable></outputVars>\', 1)\n'
                u'        else:\n'
                u'            iface = iface.replace(u"</interface>", u\'<outputVars>\'\n'
                u'                u\'<variable name="OUT"><type><BOOL /></type></variable>\'\n'
                u'                u\'</outputVars></interface>\', 1)\n'
                u'    _merged = Sheet(u"")\n'
                u'    _merged.els.extend([e for s in sheets for e in s.els])\n'
                u'    body = _merged.xml()')
    t = t.replace(anchor, new_body, 1)
    # steps-константа перед функцией
    t = t.replace(u'def pou_xml(name, pou_type, iface, sheets, comment=None):',
                  steps + u'\n\ndef pou_xml(name, pou_type, iface, sheets, comment=None):', 1)
    print(u"2) ступени получают OUT, тело собирается через xml() с fan-out")

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис fbd.py OK")

# ---------------------------------------------------------------- 3. вызовы читают OUT
G = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(G, "rb").read().decode("utf-8")
old_call = (u'def call(s, typ, inst, pins, col, w=140):\n'
            u'    return s.blk(typ, pins, col, width=w, inst=inst)')
new_call = (u'def call(s, typ, inst, pins, col, w=140):\n'
            u'    """Вызов ПОУ. Возвращает id блока; выход OUT сразу читается в GVL.\n'
            u'\n'
            u'    Чтение обязательно: CODESYS исполняет тело вызываемого ПОУ только тогда,\n'
            u'    когда вызов что-то отдаёт (правило 3 конспекта).\n'
            u'    """\n'
            u'    bid = s.blk(typ, pins, col, width=w, inst=inst)\n'
            u'    s.assign(u"GVL_CPU.Chain1", bid, col + 1)\n'
            u'    return bid')
if old_call in t:
    t = t.replace(old_call, new_call, 1)
    io.open(G, "wb").write(t.encode("utf-8"))
    ast.parse(io.open(G, encoding="utf-8").read())
    print(u"3) call(): выход OUT читается в GVL_CPU.Chain1")
else:
    print(u"3) call() не найден")
