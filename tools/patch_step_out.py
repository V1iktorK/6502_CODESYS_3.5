# -*- coding: utf-8 -*-
"""
patch_step_out.py -- u KAZHDOY stupeni poyavlyaetsya kontaktnyy vyhod OUT,
a kazhdyy vyzov ego chitaet.

Pochemu: FB_ALU6502 (i drugie stupeni) posle togvl ne imeyut kontaktnyh vyhodov,
poetomu CODESYS ne generiruet/ne ispolnyaet ih telo -- ALU_R ostavalsya 0, hotya
offlajn-model' na tom zhe XML daet 0x42.

Transformaciya vypolnyaetsya po togvl (togvl uzhe ubral starye vyhody):
  1) v kazhdom sloe-stupeni: dobavlyaem outputVars OUT : BOOL i `OUT := TRUE`;
  2) v kazhdom POU, kotoryy vyzyvaet stupen': u bloka ob"yavlyaem vyhodnoy
     kontakt OUT i chitaem ego v GVL_CPU.Chain1 (yacheyka-diagnostika).
"""
import io
import os
import re

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PL = os.path.join(ROOT, "plcopen")

STEPS = [u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"FB_WriteBack",
         u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
         u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
         u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
         u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL"]

CALLERS = [u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack", u"FB_CPU_AluFlags",
           u"FB_CPU_PcWb", u"FB_CPU_Core"]


def rd(p):
    return io.open(p, "rb").read().decode("utf-8")


def wr(p, t):
    io.open(p, "wb").write(t.encode("utf-8"))


def maxid(t):
    ids = [int(x) for x in re.findall(r'localId="(\d+)"', t)]
    return max(ids) if ids else 0


# ---------------------------------------------------------------- 1. ступени
for name in STEPS:
    p = os.path.join(PL, name + ".xml")
    if not os.path.exists(p):
        continue
    t = rd(p)
    if u'name="OUT"' in t:
        continue
    nid = maxid(t) + 1
    if u"<outputVars>" in t:
        t = t.replace(u"</outputVars>",
                      u'<variable name="OUT"><type><BOOL /></type></variable></outputVars>', 1)
    else:
        t = t.replace(u"</interface>",
                      u'<outputVars><variable name="OUT"><type><BOOL /></type></variable>'
                      u'</outputVars></interface>', 1)
    t = t.replace(u"</FBD>",
                  u'<inVariable localId="%d" height="20" width="60">'
                  u'<position x="22000" y="22000" />'
                  u'<connectionPointOut><relPosition x="60" y="10" /></connectionPointOut>'
                  u'<expression>TRUE</expression></inVariable>' % nid, 1)
    t = t.replace(u"</FBD>",
                  u'<outVariable localId="%d" height="20" width="60">'
                  u'<position x="22100" y="22000" />'
                  u'<connectionPointIn><relPosition x="0" y="10" />'
                  u'<connection refLocalId="%d" /></connectionPointIn>'
                  u'<expression>OUT</expression></outVariable>' % (nid + 1, nid), 1)
    wr(p, t)
print(u"1) ступеням добавлен выход OUT")

# ---------------------------------------------------------------- 2. вызывающие
total = 0
for cname in CALLERS:
    p = os.path.join(PL, cname + ".xml")
    if not os.path.exists(p):
        continue
    t = rd(p)
    nid = maxid(t) + 1
    added = 0
    # u kazhdogo vyzova stupeni (est instanceName) ob"yavlyaem vyhod OUT
    def fix(m):
        global nid, added
        blk = m.group(0)
        if u'formalParameter="OUT"' in blk:
            return blk
        if u"<outputVariables />" not in blk:
            return blk
        new = blk.replace(u"<outputVariables />",
                          u'<outputVariables><variable formalParameter="OUT">'
                          u'<connectionPointOut><relPosition x="80" y="10" />'
                          u'</connectionPointOut></variable></outputVariables>', 1)
        added += 1
        return new
    t = re.sub(r'<block[^>]*instanceName="[^"]+"[^>]*>[\s\S]*?</block>', fix, t)
    if added:
        # chitaem kazhdyy takoy vyzov v GVL_CPU.Chain1
        blocks = []
        for m in re.finditer(r'<block[^>]*instanceName="[^"]+"[^>]*>', t):
            if u'formalParameter="OUT"' in t[m.start():m.start() + 3000]:
                bid = re.search(r'localId="(\d+)"', m.group(0)).group(1)
                blocks.append(bid)
        for i, bid in enumerate(blocks):
            t = t.replace(u"</FBD>",
                          u'<outVariable localId="%d" height="20" width="70">'
                          u'<position x="%d" y="%d" />'
                          u'<connectionPointIn><relPosition x="0" y="10" />'
                          u'<connection refLocalId="%s" formalParameter="OUT" />'
                          u'</connectionPointIn>'
                          u'<expression>GVL_CPU.Chain1</expression></outVariable>'
                          % (nid + i, 23000 + 40 * i, 23000, bid), 1)
        nid += len(blocks)
        total += added
    wr(p, t)
print(u"2) вызовы читают OUT: %d" % total)
