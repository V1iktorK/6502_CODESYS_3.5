# -*- coding: utf-8 -*-
"""
pipeline.py -- polnaya peregeneraciya PLCopen-XML v PRAVILNOM poryadke.

Poryadok vazhen:
  1) generatori POU (stupeni, sloi, kompoziciya);
  2) togvl.py        -- vyhody stupeney -> zapis' v GVL_CPU (konspekt 2.2);
  3) patch_decoder.py-- bajtovye signaly deshifratora -> chtenie GVL_TABLE;
  4) add_out.py      -- garantirovat' kontaktnyy vyhod OUT (pravilo 3).

Zapusk:  python tools\\pipeline.py
Posle etogo: tools\\run_quick.ps1 -Script build_full.py -LogName build_full.log
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    u"gen_cpu_split.py",
    u"gen_fetch.py",
    u"gen_wdata.py",
    u"gen_carry.py",
    u"gen_stwrite.py",
    u"gen_step2.py",
    u"gen_step3.py",
    u"gen_step4.py",
    u"gen_step6.py",
    u"gen_step7.py",
    u"gen_step8.py",
    u"gen_top3.py",
    u"togvl.py",
    u"patch_decoder.py",
    u"add_out.py",
]


def main():
    for st in STEPS:
        p = os.path.join(HERE, st)
        print(u"=== %s" % st)
        r = subprocess.call([sys.executable, p], cwd=HERE)
        if r != 0:
            print(u"ОШИБКА: %s завершился с кодом %d" % (st, r))
            return r
    print(u"=== pipeline готово")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
