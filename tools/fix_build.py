import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\build_full.py"
t = io.open(p, encoding="utf-8").read()
anchor = '    log(u"ИТОГ: POU %d/%d, ошибок %d -> %s"'
if anchor in t:
    add = ('    # Итоговая строка компилятора: "Компиляция завершена -- N ошибок".\n'
           '    # Раньше она НЕ учитывалась, и проект сохранялся с ошибками.\n'
           '    nsum = 0\n'
           '    for x in info + errs:\n'
           '        msum = re.search(r"завершена\\s*--\\s*(\\d+)\\s*ошиб", u"%s" % x)\n'
           '        if msum:\n'
           '            nsum = int(msum.group(1))\n'
           '    if nsum:\n'
           '        errs = list(errs) + [u"компилятор сообщил %d ошибок" % nsum]\n'
           '        log(u"ВСЕ СООБЩЕНИЯ:")\n'
           '        for x in info + errs:\n'
           '            log(u"   %s" % x)\n')
    t = t.replace(anchor, add + anchor, 1)
    if u"import re" not in t:
        t = t.replace(u"import os", u"import os\nimport re", 1)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    print("детектор ошибок добавлен")
else:
    print("якорь не найден")
