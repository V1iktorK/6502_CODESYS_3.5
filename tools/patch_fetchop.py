# -*- coding: utf-8 -*-
"""patch_fetchop.py -- propisat FB_FetchOp v konveyer (togvl + build_full)."""
import io

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools"
OLD = u'    u"FB_Fetch", u"FB_Decoder6502"'
NEW = u'    u"FB_Fetch", u"FB_FetchOp", u"FB_Decoder6502"'

for f in (u"togvl.py", u"build_full.py"):
    p = ROOT + u"\\" + f
    t = io.open(p, encoding="utf-8").read()
    if NEW in t:
        print(u"%-14s уже прописан" % f)
        continue
    if OLD not in t:
        print(u"%-14s НЕ найден якорь" % f)
        continue
    t = t.replace(OLD, NEW, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    print(u"%-14s прописан FB_FetchOp" % f)
