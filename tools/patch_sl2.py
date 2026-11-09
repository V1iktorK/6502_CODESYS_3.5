import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(p, encoding="utf-8").read()
# 1) убирём пульт из fb_core
start = t.index("    # ---- пульт: Run / пошаговый режим")
end = t.index('    call(s, u"FB_Fetch", u"Fch"')
t = t[:start] + "    # ---- пульт вынесен в отдельную ступень SL_STEP (см. gen_step.py)\n" + t[end:]
# 2) в prg вызываем SL_STEP перед ядром
old = 'call(s, u"FB_CPU_Core", u"Core", [(u"Enable", R(s, u"Run"))], 2, w=140)'
assert old in t
t = t.replace(old, 'call(s, u"SL_STEP", u"Step", [], 1, w=110)\n'
                   '    W(s, u"Chain16", R(s, u"Enable"), 1)\n'
                   '    call(s, u"FB_CPU_Core", u"Core", [(u"Enable", R(s, u"Enable"))], 2, w=140)', 1)
t = t.replace('(u"Core", u"FB_CPU_Core"), (u"Ms0", u"FB_MemStore")',
              '(u"Step", u"SL_STEP"), (u"Core", u"FB_CPU_Core"), (u"Ms0", u"FB_MemStore")', 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("gen_top3 обновлён")
