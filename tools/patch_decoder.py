# -*- coding: utf-8 -*-
"""
patch_decoder.py -- tochechnaya pravka GOTOVOGO (ranee importirovavshegosya)
FB_Decoder6502.xml: vosem bajtovyh signalov perevesti na chtenie tablicy.

Pochemu tak: peregenerirovannyy deshifrator (276 blokov) import zavisает, a
prezhniy variant (547 blokov, s CAT) importirovalsya. Poetomu my NE peregeneriruem
shemu, a menjаem v nej tolko vosem vyhodnyh svyazey: istochnik podmenyaetsya na
novyy element-chtenie GVL_TABLE.<signal>[Op]. Ostalnoe (v to chisle nevostrebovannye
bloki CAT) ostavlyaem kak est -- oni bezvredny.
"""
import io
import os
import re
import sys

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
PATH = os.path.join(PLCOPEN, u"FB_Decoder6502.xml")

BYTE_SIGS = [u"ADDR_MODE", u"LEN", u"SRC", u"ALU_A", u"ALU_B",
             u"PC_MODE", u"SP_MODE", u"COND"]


def main():
    text = io.open(PATH, "rb").read().decode("utf-8")
    ids = [int(x) for x in re.findall(r'localId="(\d+)"', text)]
    nid = max(ids) + 1
    added = []
    changed = 0

    for sig in BYTE_SIGS:
        # ищем outVariable, который пишет GVL_CPU.<sig>
        pat = re.compile(
            u'(<outVariable[^>]*>\\s*<position[^/]*/>\\s*<connectionPointIn>'
            u'<relPosition[^/]*/>\\s*<connection refLocalId=")(\\d+)(" )'
            u'[\\s\\S]{0,200}?<expression>(?:GVL_CPU\\.)?%s</expression></outVariable>' % sig)
        m = pat.search(text)
        if not m:
            print(u"  %-10s НЕ найден" % sig)
            continue
        old_src = m.group(2)
        new_id = nid
        nid += 1
        text = text[:m.start(2)] + str(new_id) + text[m.end(2):]
        # добавляем элемент-чтение таблицы
        added.append(
            u'<inVariable localId="%d" height="20" width="170">'
            u'<position x="%d" y="%d" />'
            u'<connectionPointOut><relPosition x="170" y="10" /></connectionPointOut>'
            u'<expression>GVL_TABLE.%s[Op]</expression></inVariable>'
            % (new_id, 20000 + 40 * len(added), 20000 + 40 * len(added), sig))
        changed += 1
        print(u"  %-10s источник %s -> %d (чтение GVL_TABLE)" % (sig, old_src, new_id))

    if not changed:
        print(u"нечего менять")
        return 1

    text = text.replace(u"</FBD>", u"".join(added) + u"</FBD>", 1)
    io.open(PATH, "wb").write(text.encode("utf-8"))
    print(u"изменено присвоений: %d, файл %d байт" % (changed, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
