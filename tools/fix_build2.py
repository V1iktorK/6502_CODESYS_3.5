import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\build_full.py"
t = io.open(p, encoding="utf-8").read()
if "nsum" not in t:
    anchor = "    ok = (not bad) and (not errs)"
    add = '''    # Итоговая строка компилятора: "Компиляция завершена -- N ошибок".
    # РАНЬШЕ она не учитывалась: проект сохранялся с ошибками, и стенд потом
    # не мог войти в симуляцию ("При компиляции возникли ошибки").
    nsum = 0
    for x in list(errs) + list(info):
        msum = re.search(r"завершена\\s*--\\s*(\\d+)\\s*ошиб", u"%s" % x)
        if msum:
            nsum = int(msum.group(1))
    if nsum:
        log(u"КОМПИЛЯТОР СООБЩИЛ %d ОШИБОК -- все сообщения:" % nsum)
        for x in list(errs) + list(info) + list(other):
            log(u"   %s" % x)
        errs = list(errs) + [u"итог компилятора: %d ошибок" % nsum]
    ok = (not bad) and (not errs)'''
    t = t.replace(anchor, add, 1)
    if "import re" not in t:
        t = t.replace("import os", "import os\nimport re", 1)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    print("детектор добавлен")
else:
    print("уже есть")
