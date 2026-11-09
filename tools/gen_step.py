# -*- coding: utf-8 -*-
"""gen_step.py -- stupen SL_STEP: pul't (Run/poshagovo) i razreshenie takta.

    permit    := Step_Pulse AND NOT Step_Taken
    Enable    := Run AND (NOT Step_On OR permit)
    Step_Taken:= (Step_Taken OR (Step_On AND permit)) AND Step_Pulse

Pochemu otdelnyy POU: vnutri FB_CPU_Core zashchelka Step_Taken byla LOKALNOY
peremennoy, i CODESYS uspeval prochitat' ee ran'she zapisi -- takt razreshalsya
DVA skana podryad, i kazhdaya komanda ispolnyalas' dvazhdy (v konsoli CP/M eto
bylo vidno kak udvoennye simvoly).

Zdes Step_Taken hranitsya v GVL: POU chitaet ego v nachale skana i pishet v
konce, to est' poluchaet znachenie PROSHLOGO skana -- imenno to, chto nuzhno
dlya zashchelki "odin impuls = odin takt".
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
CPU = u"GVL_CPU"


def build():
    s = Sheet(u"SL_STEP: пульт и разрешение такта")
    s.add_comment(u"один импульс Step_Pulse = ровно один такт")
    run = s.ref(CPU + u".Run", 0)
    on = s.ref(CPU + u".Step_On", 0)
    pulse = s.ref(CPU + u".Step_Pulse", 0)
    taken = s.ref(CPU + u".Step_Taken", 0)
    permit = s.blk(u"AND", [(u"IN1", pulse),
                            (u"IN2", s.blk(u"NOT", [(u"IN", taken)], 1))], 2)
    s.assign(CPU + u".Enable",
             s.blk(u"AND", [(u"IN1", run),
                            (u"IN2", s.blk(u"OR", [(u"IN1", s.blk(u"NOT", [(u"IN", on)], 1)),
                                                   (u"IN2", permit)], 2))], 3), 4)
    s.assign(CPU + u".Step_Taken",
             s.blk(u"AND", [(u"IN1", s.blk(u"OR", [(u"IN1", s.ref(CPU + u".Step_Taken", 3)),
                                                   (u"IN2", s.blk(u"AND", [(u"IN1", s.ref(CPU + u".Step_On", 3)),
                                                                           (u"IN2", permit)], 4))], 4)),
                            (u"IN2", s.ref(CPU + u".Step_Pulse", 4))], 5), 6)
    return s


def main():
    print(u"=== gen_step ===")
    x = pou_xml(u"SL_STEP", u"functionBlock", interface(), [build()],
                comment=u"пульт процессора")
    p = os.path.join(OUT, u"SL_STEP.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_STEP  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
