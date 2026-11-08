# -*- coding: utf-8 -*-
"""
patch_layer_out.py -- POU-sloi poluchayut kontaktnyy vyhod OUT, kotoryy chitaet yadro.

Prichina: sloy bez kontaktnyh vyhodov CODESYS ne ispolnyaet (FB_RegFile pishет
GVL, no znacheniya ne menyayutsya: A=0, PC=0, SP ne menyaetsya).
Po konspektu (pravilo 3): telo FB generiruetsya, tolko esli vyzov CHITAETsya.

Delaem pryamuyu pravku sgenerirovannyh XML (nadezhnee, chem pravit' generator):
  1) v kazhdom sloe: dobavlyaem v <outputVars> peremennuyu OUT : BOOL i
     prisvoenie OUT := <vhodnaya peremennaya Enable>;
  2) v FB_CPU_Core: u kazhdogo vyzova sloya ob"yavlyaem vyhodnoy kontakt OUT i
     chitaem ego v GVL_CPU.ChainN.
"""
import io
import os
import re

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PL = os.path.join(ROOT, "plcopen")

LAYERS = [(u"FB_CPU_Addr1", u"S1", 1), (u"FB_CPU_Select", u"S2", 2),
          (u"FB_CPU_Stack", u"S3", 3), (u"FB_CPU_AluFlags", u"S4", 4),
          (u"FB_Latch", u"S5L", 5), (u"FB_CPU_PcWb", u"S5", 6),
          (u"FB_CPU_Store", u"S6", 7), (u"FB_RegFile", u"S7", 8)]


def rd(p):
    return io.open(p, "rb").read().decode("utf-8")


def wr(p, t):
    io.open(p, "wb").write(t.encode("utf-8"))


def maxid(t):
    ids = [int(x) for x in re.findall(r'localId="(\d+)"', t)]
    return max(ids) if ids else 0


# ------------------------------------------------ 1. слой: выход OUT
for name, inst, idx in LAYERS:
    p = os.path.join(PL, name + ".xml")
    t = rd(p)
    if u'name="OUT"' in t:
        print(u"  %-16s уже есть OUT" % name)
        continue
    nid = maxid(t) + 1

    # 1a. интерфейс: outputVars
    if u"<outputVars>" in t:
        t = t.replace(u"</outputVars>",
                      u'<variable name="OUT"><type><BOOL /></type></variable></outputVars>', 1)
    else:
        t = t.replace(u"</interface>",
                      u'<outputVars><variable name="OUT"><type><BOOL /></type></variable>'
                      u'</outputVars></interface>', 1)

    # 1b. тело: OUT := <вход Enable>
    m = re.search(u'<inVariable[^>]*localId="(\\d+)"[^>]*>[\\s\\S]{0,200}?<expression>Enable</expression>',
                  t)
    src = m.group(1) if m else None
    if src is None:
        # если входа Enable нет — берём константу TRUE
        t = t.replace(u"</FBD>",
                      u'<inVariable localId="%d" height="20" width="70">'
                      u'<position x="20000" y="20000" />'
                      u'<connectionPointOut><relPosition x="70" y="10" /></connectionPointOut>'
                      u'<expression>TRUE</expression></inVariable>' % nid, 1)
        src = str(nid)
        nid += 1
    t = t.replace(u"</FBD>",
                  u'<outVariable localId="%d" height="20" width="70">'
                  u'<position x="20200" y="20000" />'
                  u'<connectionPointIn><relPosition x="0" y="10" />'
                  u'<connection refLocalId="%s" /></connectionPointIn>'
                  u'<expression>OUT</expression></outVariable>' % (nid, src), 1)
    wr(p, t)
    print(u"  %-16s добавлен выход OUT" % name)

# ------------------------------------------------ 2. ядро: читаем OUT слоёв
p = os.path.join(PL, "FB_CPU_Core.xml")
t = rd(p)
nid = maxid(t) + 1

for name, inst, idx in LAYERS:
    # находим вызов: block с instanceName="<inst>"
    m = re.search(u'<block[^>]*instanceName="%s"[^>]*>(.*?)</block>' % re.escape(inst), t, re.S)
    if not m:
        print(u"  %-16s вызов %s не найден" % (name, inst))
        continue
    blk = m.group(0)
    if u'formalParameter="OUT"' in blk:
        continue
    new_blk = blk.replace(u"<outputVariables />",
                          u'<outputVariables><variable formalParameter="OUT">'
                          u'<connectionPointOut><relPosition x="80" y="10" />'
                          u'</connectionPointOut></variable></outputVariables>', 1)
    if new_blk == blk:
        continue
    blkid = re.search(r'localId="(\d+)"', new_blk[:200]).group(1)
    t = t.replace(blk, new_blk, 1)
    # добавляем чтение в Chain<idx>
    t = t.replace(u"</FBD>",
                  u'<outVariable localId="%d" height="20" width="80">'
                  u'<position x="%d" y="%d" />'
                  u'<connectionPointIn><relPosition x="0" y="10" />'
                  u'<connection refLocalId="%s" formalParameter="OUT" />'
                  u'</connectionPointIn>'
                  u'<expression>GVL_CPU.Chain%d</expression></outVariable>'
                  % (nid, 21000 + 40 * idx, 21000, blkid, idx), 1)
    nid += 1
    print(u"  %-16s OUT -> GVL_CPU.Chain%d" % (name, idx))

wr(p, t)
print(u"готово")
