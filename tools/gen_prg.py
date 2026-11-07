# -*- coding: utf-8 -*-
"""
gen_prg.py -- programma-tochka vhoda dlya zadachi (FBD).

V CODESYS programma zadachi dolzhna byt PROGRAM. Sozdaem FBD-programmu s
odnim ekzemplyarom FB_CPU_Core; vsya logika ostaetsya v FBD.
Generiruem dva varianta:
  PRG_CPU.xml  -- imya PRG_CPU   (dlya proverki importa)
  PRG_PLC.xml  -- imya PLC_PRG   (chtoby zamenit pustuyu ST-programmu shablona)
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")


def build(name):
    s = Sheet(u"%s: один такт процессора за скан задачи" % name)
    s.add_comment(u"Каждый скан задачи выполняется ровно одна команда MOS 6502")
    core = s.blk(u"FB_CPU_Core", [(u"Enable", s.const(u"TRUE", 0))], 2,
                 width=140, inst=u"Core")
    s.assign(u"GVL_CPU.Done", core, 4, src_pin=u"Done")
    return s


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_prg ===")
    for pou, fname in ((u"PRG_CPU", u"PRG_CPU"), (u"PLC_PRG", u"PRG_PLC")):
        write(fname, pou_xml(pou, u"program",
                             interface(locals_=[(u"Core", u"FB_CPU_Core")]),
                             [build(pou)],
                             comment=u"Точка входа задачи: один такт ядра за скан"))
    print(u"готово")


if __name__ == "__main__":
    main()
