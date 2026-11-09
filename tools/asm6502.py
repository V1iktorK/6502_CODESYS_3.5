# -*- coding: utf-8 -*-
"""asm6502.py -- minimalnyy assembler MOS 6502 dlya BIOS/BDOS/CCP.

Podderzhivaet tolko to, chto nuzhno proektu:
    LDA/LDX/LDY  #imm, zp, abs, abs,X, abs,Y, (zp),Y
    STA/STX/STY  zp, abs, abs,X, abs,Y
    ADC/SBC/CMP  #imm, zp, abs
    INX INY DEX DEY TAX TXA TAY TYA PHA PLA PHP PLP
    CLC SEC SEI CLI CLD SED
    JMP abs, JMP (abs)
    JSR abs, RTS, RTI, BRK, HLT
    BEQ BNE BCC BCS BPL BMI (otnositelnye)
    NOP
Direktivy: ORG <addr>, DB <bayty>, DW <slovo>, DS <n> (rezerv), LABEL:

Dvuhprohodnyy: pervyy prohod schitaet adresa, vtoroy vydaet bayty.
"""
import re

OPS = {
    # mnemonika: {rezhim: opcode}
    "LDA": {"imm": 0xA9, "zp": 0xA5, "zpx": 0xB5, "abs": 0xAD, "abx": 0xBD,
            "aby": 0xB9, "izy": 0xB1, "izx": 0xA1},
    "LDX": {"imm": 0xA2, "zp": 0xA6, "zpy": 0xB6, "abs": 0xAE},
    "LDY": {"imm": 0xA0, "zp": 0xA4, "zpx": 0xB4, "abs": 0xAC},
    "STA": {"zp": 0x85, "zpx": 0x95, "abs": 0x8D, "abx": 0x9D, "aby": 0x99,
            "izy": 0x91, "izx": 0x81},
    "STX": {"zp": 0x86, "abs": 0x8E},
    "STY": {"zp": 0x84, "abs": 0x8C},
    "ADC": {"imm": 0x69, "zp": 0x65, "abs": 0x6D},
    "SBC": {"imm": 0xE9, "zp": 0xE5, "abs": 0xED},
    "CMP": {"imm": 0xC9, "zp": 0xC5, "abs": 0xCD},
    "CPX": {"imm": 0xE0},
    "CPY": {"imm": 0xC0},
    "AND": {"imm": 0x29},
    "ORA": {"imm": 0x09},
    "EOR": {"imm": 0x49},
    "INX": {"imp": 0xE8}, "INY": {"imp": 0xC8},
    "DEX": {"imp": 0xCA}, "DEY": {"imp": 0x88},
    "TAX": {"imp": 0xAA}, "TAY": {"imp": 0xA8},
    "TXA": {"imp": 0x8A}, "TYA": {"imp": 0x98},
    "PHA": {"imp": 0x48}, "PLA": {"imp": 0x68},
    "PHP": {"imp": 0x08}, "PLP": {"imp": 0x28},
    "CLC": {"imp": 0x18}, "SEC": {"imp": 0x38},
    "SEI": {"imp": 0x78}, "CLI": {"imp": 0x58},
    "CLD": {"imp": 0xD8}, "SED": {"imp": 0xF8},
    "JMP": {"abs": 0x4C, "ind": 0x6C},
    "JSR": {"abs": 0x20},
    "RTS": {"imp": 0x60}, "RTI": {"imp": 0x40}, "BRK": {"imp": 0x00},
    "NOP": {"imp": 0xEA}, "HLT": {"imp": 0x02},
    "BEQ": {"rel": 0xF0}, "BNE": {"rel": 0xD0},
    "BCC": {"rel": 0x90}, "BCS": {"rel": 0xB0},
    "BPL": {"rel": 0x10}, "BMI": {"rel": 0x30},
}
IMP = [k for k, v in OPS.items() if "imp" in v]


def assemble(src, origin=0x0200):
    """Dvuhprohodnyy: prohod 1 -- adresa metok, prohod 2 -- bayty.

    Bez vtorogo prohoda ne rabotayut perednie ssylki (perehod na metku,
    obyavlennuyu nizhe), a oni v BIOS/BDOS vstrechayutsya postoyanno.
    """
    lines = []
    for raw in src.replace("\r", "").split("\n"):
        s = raw.split(";")[0].rstrip()
        if s.strip():
            lines.append(s)
    labels = {}
    out = []
    for _pass in (1, 2):
        pc = origin
        out = []
        for s in lines:
            m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", s.strip())
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


def _val(s, labels, size, lenient=False):
    s = s.strip()
    if s.startswith("#"):
        s = s[1:].strip()
    if s in labels:
        return labels[s]
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.lower().startswith("0x"):
        return int(s, 16)
    if s.startswith("%"):
        return int(s[1:], 2)
    try:
        return int(s, 0)
    except ValueError:
        if lenient:
            return 0
        raise


def _emit(mn, arg, labels, pc, out, lenient=False):
    a = arg.strip()
    tab = OPS[mn]
    if "imp" in tab and not a:
        return [tab["imp"]]
    if a.startswith("#"):
        return [tab["imm"], _val(a, labels, 1, lenient)]
    if a.startswith("(") and a.endswith("),Y"):
        return [tab["izy"], _val(a[1:-3], labels, 1, lenient)]
    if a.startswith("(") and a.endswith(",X)"):
        return [tab["izx"], _val(a[1:-3], labels, 1, lenient)]
    if a.startswith("(") and a.endswith(")"):
        if "ind" in tab:
            v = _val(a[1:-1], labels, 2, lenient)
            return [tab["ind"], v & 0xFF, (v >> 8) & 0xFF]
        return [tab["zp"], _val(a[1:-1], labels, 1, lenient)]
    m = re.match(r"^(.*),\s*([XYxy])$", a)
    if m:
        base, reg = m.group(1).strip(), m.group(2).upper()
        v = _val(base, labels, 2, lenient)
        if "rel" in tab:
            d = v - (pc + 2)
            return [tab["rel"], d & 0xFF]
        if v < 0x100:
            key = "zpx" if reg == "X" else "zpy"
            if key in tab:
                return [tab[key], v]
        key = "abx" if reg == "X" else "aby"
        if key in tab:
            return [tab[key], v & 0xFF, (v >> 8) & 0xFF]
        raise ValueError("нет режима %s,X для %s" % (mn, reg))
    v = _val(a, labels, 2, lenient)
    if "rel" in tab:
        d = v - (pc + 2)
        return [tab["rel"], d & 0xFF]
    if v < 0x100 and "zp" in tab:
        return [tab["zp"], v]
    if "abs" in tab:
        return [tab["abs"], v & 0xFF, (v >> 8) & 0xFF]
    if "zp" in tab:
        return [tab["zp"], v & 0xFF]
    raise ValueError("нет режима для %s %s" % (mn, a))


def to_hex(mem):
    """Chitaemyy vid: spisok strok 'AAAA: BB BB ...'."""
    out = []
    if not mem:
        return out
    lo, hi = min(mem), max(mem)
    a = lo
    while a <= hi:
        chunk = [mem.get(x) for x in range(a, min(a + 16, hi + 1))]
        s = u"%04X: " % a
        s += u" ".join(u"%02X" % c if c is not None else u".." for c in chunk)
        out.append(s)
        a += 16
    return out
