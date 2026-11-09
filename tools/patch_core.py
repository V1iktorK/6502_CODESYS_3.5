import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(p, encoding="utf-8").read()
start = t.index('    # ---- пульт: Run / пошаговый режим')
end = t.index('    call(s, u"FB_Fetch", u"Fch"')
t = t[:start] + '''    # ---- пульт вынесен в ступень SL_STEP (см. gen_step.py): там защёлка
    # Step_Taken хранится в GVL и читается со сдвигом на скан, поэтому такт
    # разрешается РОВНО один скан на импульс.
''' + t[end:]
# Enable пробрасываем как есть
t = t.replace('    call(s, u"FB_Fetch", u"Fch", [(u"PCs", R(s, u"PC"))], 2, w=110)',
              '    call(s, u"FB_Fetch", u"Fch", [(u"PCs", R(s, u"PC"))], 2, w=110)', 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("fb_core: пульт убран")
