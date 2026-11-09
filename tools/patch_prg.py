import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(p, encoding="utf-8").read()
old = 'call(s, u"FB_CPU_Core", u"Core", [(u"Enable", R(s, u"Run"))], 2, w=140)'
new = ('# пульт: Run / пошаговый режим -> GVL_CPU.Enable\n'
       '    call(s, u"SL_STEP", u"Step", [], 1, w=110)\n'
       '    W(s, u"Chain16", R(s, u"Enable"), 1)\n'
       '    call(s, u"FB_CPU_Core", u"Core", [(u"Enable", R(s, u"Enable"))], 2, w=140)')
assert old in t
t = t.replace(old, new, 1)
t = t.replace('interface(locals_=[(u"Core", u"FB_CPU_Core"), (u"Ms0", u"FB_MemStore"), (u"Ms1", u"FB_MemStore"), (u"Ms2", u"FB_MemStore")])',
              'interface(locals_=[(u"Step", u"SL_STEP"), (u"Core", u"FB_CPU_Core"), (u"Ms0", u"FB_MemStore"), (u"Ms1", u"FB_MemStore"), (u"Ms2", u"FB_MemStore")])')
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("prg: SL_STEP добавлен")
