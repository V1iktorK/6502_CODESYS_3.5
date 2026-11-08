# -*- coding: utf-8 -*-
"""
add_out.py -- garantirovat kontaktnyy vyhod OUT u stupeney.

Zachem: CODESYS ispolnyaet telo POU tolko togda, kogda ego vyzov chto-to
chitaet (pravilo 3 konspekta). Poetomu kazhdaya stupen (FB_*, SL_*) obyazana
imet:
    * v interfejse  VAR_OUTPUT  OUT : BOOL;
    * v tele          TRUE -> OUT
Kompoziciya (FB_CPU_Core) chitaet inst.OUT i pishet ego v GVL_CPU.Chain1.

Skript idempotenten: esli OUT uzhe obedavlen, fayl ne menyaetsya.
Zapuskat POSLE togvl.py i patch_decoder.py (oni ne dolzhny videt OUT kak
obychnyy vyhod i perevodit ego v GVL_CPU).
"""
import io
import os
import re
import sys

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")

NAMES = [
    u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"FB_WriteBack",
    u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
    u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
    u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",
]

OUT_DECL = (u'<outputVars><variable name="OUT">'
            u'<type><BOOL /></type></variable></outputVars>')


def add_out(name):
    path = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(path):
        return u"нет файла"
    text = io.open(path, "rb").read().decode("utf-8")
    if u'variable name="OUT"' in text:
        return u"уже есть"

    m = re.search(u'<interface>.*?</interface>', text, re.S)
    if not m:
        return u"НЕТ ИНТЕРФЕЙСА"
    ifce = m.group(0)
    if u"<outputVars>" in ifce:
        ifce_new = ifce.replace(u"</outputVars>",
                                u'<variable name="OUT"><type><BOOL /></type>'
                                u'</variable></outputVars>', 1)
    else:
        ifce_new = ifce.replace(u"</interface>", OUT_DECL + u"</interface>", 1)
    text = text[:m.start()] + ifce_new + text[m.end():]

    nxt = 1 + max([int(x) for x in re.findall(u'localId="(\d+)"', text)] or [0])
    ys = [int(x) for x in re.findall(u'<position x="\d+" y="(\d+)"', text)] or [0]
    y = max(ys) + 60
    conn = (u'<inVariable localId="%d" height="20" width="70">'
            u'<position x="60" y="%d" />'
            u'<connectionPointOut><relPosition x="70" y="10" />'
            u'</connectionPointOut><expression>TRUE</expression></inVariable>'
            % (nxt, y))
    outv = (u'<outVariable localId="%d" height="20" width="70">'
            u'<position x="200" y="%d" />'
            u'<connectionPointIn><relPosition x="0" y="10" />'
            u'<connection refLocalId="%d" /></connectionPointIn>'
            u'<expression>OUT</expression></outVariable>' % (nxt + 1, y, nxt))
    if u"</FBD>" not in text:
        return u"НЕТ FBD"
    text = text.replace(u"</FBD>", conn + outv + u"</FBD>", 1)

    io.open(path, "wb").write(text.encode("utf-8"))
    return u"OUT добавлен"


def main():
    print(u"=== add_out ===")
    done = 0
    for n in NAMES:
        r = add_out(n)
        if r == u"OUT добавлен":
            done += 1
        print(u"  %-16s %s" % (n, r))
    print(u"всего добавлено: %d" % done)


if __name__ == "__main__":
    sys.exit(main())
