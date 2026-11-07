# -*- coding: utf-8 -*-
"""patch_log.py -- akkuratno popravit build_full.py (logi i perenos strok)."""
import io

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\build_full.py"
t = io.open(P, "rb").read().decode("utf-8")

bad1 = u'    gt.textual_declaration.replace(table_text())\\n    log(u"GVL созданы (GVL_CPU, GVL_TABLE)")'
good1 = (u'    gt.textual_declaration.replace(table_text())\n'
         u'    log(u"GVL созданы (GVL_CPU, GVL_TABLE)")')
if bad1 in t:
    t = t.replace(bad1, good1)
    print(u"исправлена строка GVL")
elif u'log(u"GVL созданы (GVL_CPU, GVL_TABLE)")' not in t:
    t = t.replace(u'    gt.textual_declaration.replace(table_text())',
                  u'    gt.textual_declaration.replace(table_text())\n'
                  u'    log(u"GVL созданы (GVL_CPU, GVL_TABLE)")')
    print(u"добавлен лог GVL")

bad2 = u'        log(u"  импорт %s — ок" % name)\\n        if name not in names():'
good2 = (u'        log(u"  импорт %s — ок" % name)\n'
         u'        if name not in names():')
if bad2 in t:
    t = t.replace(bad2, good2)
    print(u"исправлен лог импорта")

io.open(P, "wb").write(t.encode("utf-8"))

import ast
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
