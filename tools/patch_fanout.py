import io, re
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(p, encoding="utf-8").read()
# Убираем ПОВТОРНОЕ чтение выхода ступени: call() уже читает OUT в Chain1,
# а явные W(ChainN, ch) создавали второго потребителя -> fan-out клонировал
# блок вместе с ветвью, и в листе появлялись ДВЕ копии всей цепочки.
n = len(re.findall(r"\n    W\(s, u\"Chain\d+\", ch, 1\)", t))
t = re.sub(r"\n    W\(s, u\"Chain\d+\", ch, 1\)", "", t)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("удалено повторных чтений OUT: %d" % n)
