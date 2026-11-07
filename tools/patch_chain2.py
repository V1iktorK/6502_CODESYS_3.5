# -*- coding: utf-8 -*-
"""
patch_chain2.py -- tekhnicheskiy vyhod OUT u sloev (akkuratno, po strokam).

Pravilo 3 iz 00_ГЛАВНОЕ: telo POU generiruetsya tolko esli ego vyzov CHITAETsya.
Pojetomu kazhdyy sloy poluchaet vyhod OUT := Enable, a FB_CPU_Core chitaet ego
v GVL_CPU.Chain1..Chain8.
"""
import io
import ast

GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"

LAYERS = [(u"FB_CPU_Addr1", u"S1", 1),
          (u"FB_CPU_Select", u"S2", 2),
          (u"FB_CPU_Stack", u"S3", 3),
          (u"FB_CPU_AluFlags", u"S4", 4),
          (u"FB_Latch", u"S5L", 5),
          (u"FB_CPU_PcWb", u"S5", 6),
          (u"FB_CPU_Store", u"S6", 7),
          (u"FB_RegFile", u"S7", 8)]

FUNCS = {u"FB_CPU_Addr1": u"def fb_addr1():",
         u"FB_CPU_Select": u"def fb_select():",
         u"FB_CPU_Stack": u"def fb_stack():",
         u"FB_CPU_AluFlags": u"def fb_aluflags():",
         u"FB_Latch": u"def fb_latch():",
         u"FB_CPU_PcWb": u"def fb_pcwb():",
         u"FB_CPU_Store": u"def fb_store():",
         u"FB_RegFile": u"def fb_regfile():"}

src = io.open(GT, "rb").read().decode("utf-8")
lines = src.split(u"\n")
out = []
added_out_body = {k: False for k in FUNCS}
cur_fn = None

for line in lines:
    # sledim, vnutri kakoy funkcii my
    for nm, fn in FUNCS.items():
        if line.startswith(fn):
            cur_fn = nm
            break
    else:
        if line.startswith(u"def "):
            cur_fn = None

    # 1) vyzov sloya -> chitaem OUT v Chain<idx>
    replaced = False
    for name, inst, idx in LAYERS:
        prefix = u'    call(s, u"%s", u"%s", ' % (name, inst)
        if line.startswith(prefix):
            rest = line[len(prefix):]
            # razbiraem argumenty: pins, col, w=...
            parts = rest.rsplit(u", ", 2)
            pins = parts[0]
            col = parts[1]
            tail = parts[2].rstrip(u")")
            out.append(u'    ch = call(s, u"%s", u"%s", %s, %s, %s)'
                       % (name, inst, pins, col, tail))
            out.append(u'    W(s, u"Chain%d", ch, 1)' % idx)
            replaced = True
            break
    if replaced:
        continue

    # 2) v konce tela sloya dobavim OUT := Enable
    if cur_fn and not added_out_body[cur_fn] and line == u"    return s":
        out.append(u'    s.assign(u"OUT", R(s, u"Enable"), 20)')
        added_out_body[cur_fn] = True
        out.append(line)
        continue

    # 3) interfeys sloya: dobavit' outputs, esli ih net
    if u'u"functionBlock"' in line:
        for name, inst, idx in LAYERS:
            if u'u"%s", u"functionBlock"' % name in line:
                break
        else:
            out.append(line)
            continue
        # sleduyushchaya stroka s interface( -- obrabotaem zdes' zhe
        out.append(line)
        continue

    if u'interface(' in line and u'outputs=' not in line:
        target = None
        for name, inst, idx in LAYERS:
            if u'u"%s", u"functionBlock"' % name in (out[-1] if out else u""):
                target = name
                break
        if target is not None:
            if u'inputs=[(u"Enable", u"BOOL")], ' in line:
                line = line.replace(u'inputs=[(u"Enable", u"BOOL")], ',
                                    u'inputs=[(u"Enable", u"BOOL")], outputs=[(u"OUT", u"BOOL")], ')
            else:
                line = line.replace(u'interface(', u'interface(outputs=[(u"OUT", u"BOOL")], ')
    out.append(line)

new_src = u"\n".join(out)
io.open(GT, "wb").write(new_src.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"синтаксис OK")
print(u"outputs OUT:", new_src.count(u'u"OUT", u"BOOL"'))
print(u"Chain:", new_src.count(u'u"Chain'))
print(u"тел с OUT:", sum(1 for k, v in added_out_body.items() if v))
