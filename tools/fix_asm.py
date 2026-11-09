import io, re
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\asm6502.py"
t = io.open(p, encoding="utf-8").read()
start = t.index("def assemble(")
end = t.index("def _val(")
new = '''def assemble(src, origin=0x0200):
    """Dvuhprohodnyy: prohod 1 -- adresa metok, prohod 2 -- bayty.

    Bez vtorogo prohoda ne rabotayut perednie ssylki (perehod na metku,
    obyavlennuyu nizhe), a oni v BIOS/BDOS vstrechayutsya postoyanno.
    """
    lines = []
    for raw in src.replace("\\r", "").split("\\n"):
        s = raw.split(";")[0].rstrip()
        if s.strip():
            lines.append(s)
    labels = {}
    out = []
    for _pass in (1, 2):
        pc = origin
        out = []
        for s in lines:
            m = re.match(r"^([A-Za-z_]\\w*):\\s*(.*)$", s.strip())
            if m:
                if _pass == 1:
                    labels[m.group(1)] = pc
                s = m.group(2)
            s = s.strip()
            if not s:
                continue
            parts = s.split(None, 1)
            mn = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""
            if mn == "ORG":
                pc = _val(arg, labels, 0, _pass == 1)
                continue
            if mn == "DB":
                for item in arg.split(","):
                    out.append((pc, _val(item.strip(), labels, 1, _pass == 1)))
                    pc += 1
                continue
            if mn == "DW":
                v = _val(arg, labels, 2, _pass == 1)
                out.append((pc, v & 0xFF))
                out.append((pc + 1, (v >> 8) & 0xFF))
                pc += 2
                continue
            if mn == "DS":
                pc += _val(arg, labels, 0, _pass == 1)
                continue
            if mn not in OPS:
                raise ValueError("неизвестная мнемоника %r в строке %r" % (mn, s))
            code = _emit(mn, arg, labels, pc, None, _pass == 1)
            for i, b in enumerate(code):
                out.append((pc + i, b))
            pc += len(code)
    mem = {}
    for a, b in out:
        mem[a] = b & 0xFF
    return mem, labels


'''
t = t[:start] + new + t[end:]
t = t.replace("def _val(s, labels, size):", "def _val(s, labels, size, lenient=False):")
t = t.replace('''    if s in labels:
        return labels[s]''', '''    if s in labels:
        return labels[s]
    if lenient:
        return 0''')
t = t.replace("def _emit(mn, arg, labels, pc, out):", "def _emit(mn, arg, labels, pc, out, lenient=False):")
t = t.replace("    return [tab[\"imm\"], _val(a, labels, 1)]", "    return [tab[\"imm\"], _val(a, labels, 1, lenient)]")
t = t.replace("        return [tab[\"izy\"], _val(a[1:-3], labels, 1)]", "        return [tab[\"izy\"], _val(a[1:-3], labels, 1, lenient)]")
t = t.replace("        return [tab[\"izx\"], _val(a[1:-3], labels, 1)]", "        return [tab[\"izx\"], _val(a[1:-3], labels, 1, lenient)]")
t = t.replace("            v = _val(a[1:-1], labels, 2)", "            v = _val(a[1:-1], labels, 2, lenient)")
t = t.replace("        return [tab[\"zp\"], _val(a[1:-1], labels, 1)]", "        return [tab[\"zp\"], _val(a[1:-1], labels, 1, lenient)]")
t = t.replace("        v = _val(base, labels, 2)", "        v = _val(base, labels, 2, lenient)")
t = t.replace("    v = _val(a, labels, 2)\n    if \"rel\" in tab:", "    v = _val(a, labels, 2, lenient)\n    if \"rel\" in tab:")
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("assemble rewritten")
