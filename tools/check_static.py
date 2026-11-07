# -*- coding: utf-8 -*-
"""
check_static.py -- staticheskaya proverka shem do sborki.

Lovit klass oshibok, kotorye CODESYS vydaet kak C0032 na etape kompilyacii:
  * blok s nedopustimym chislom vhodov ("Обнаружен неоднозначный элемент");
  * operator sravneniya ne s dvumya operandami ("Для '<' требуется ровно 2 операндов").

Dopolnitelno: ssylki na neobyavlennye imena i na bloki, kotorye ne budut
sozdany (chto daet molchalivyi otkaz pri importe).

Zapusk: python check_static.py
"""
import glob
import io
import os
import re
import sys
from xml.etree import ElementTree as ET

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
NS = "{http://www.plcopen.org/xml/tc6_0200}"

# Сколько входов обязан иметь блок (min, max). None = без ограничения сверху.
PINS = {
    u"LT": (2, 2), u"LE": (2, 2), u"GT": (2, 2), u"GE": (2, 2),
    u"EQ": (2, 2), u"NE": (2, 2),                 # сравнения: строго 2 операнда
    u"SEL": (3, 3),                               # G, IN0, IN1
    u"NOT": (1, 1), u"MOVE": (1, 1),
    u"BYTE_TO_WORD": (1, 1), u"WORD_TO_BYTE": (1, 1),
    u"BYTE_TO_INT": (1, 1), u"INT_TO_BYTE": (1, 1),
    u"SHR": (2, 2), u"SHL": (2, 2), u"ROL": (2, 2), u"ROR": (2, 2),
    u"ADD": (2, None), u"SUB": (2, 2), u"MUL": (2, None), u"DIV": (2, 2),
    u"AND": (2, None), u"OR": (2, None), u"XOR": (2, None),
}

WIDE = (u"BYTE", u"WORD", u"INT", u"UINT", u"DINT", u"SINT")

GVLS = {
    u"GVL_CPU": {u"A", u"X", u"Y", u"P", u"SP", u"PC", u"Halted"},
    u"GVL_MEM": {u"Mem"},
}
KW = {u"TRUE", u"FALSE"}
TYPED_LIT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*#(?:16#)?[0-9A-Fa-f]+")
# Квалифицированные имена GVL вида GVL_CPU.A или GVL_MEM.Mem -- не локальные
GVL_REF = re.compile(r"GVL_[A-Za-z0-9_]+.[A-Za-z0-9_]+")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def declared_names(pou):
    names = set()
    iface = pou.find(NS + "interface")
    if iface is None:
        return names
    for tag in ("inputVars", "outputVars", "inOutVars", "localVars", "tempVars"):
        h = iface.find(NS + tag)
        if h is None:
            continue
        for v in h.findall(NS + "variable"):
            names.add(v.get("name"))
    return names


def main():
    problems = 0
    checked = 0
    for p in sorted(glob.glob(os.path.join(PLCOPEN, "*.xml"))):
        b = os.path.basename(p)
        if b.startswith(("gen_", "rt_", "rt2_", "probe_", "inst", "bis_", "var_",
                         "add16_", "p2_", "inst2_")):
            continue
        try:
            pou = ET.parse(p).getroot().find(NS + "types/" + NS + "pous/" + NS + "pou")
            fbd = pou.find(NS + "body/" + NS + "FBD")
        except Exception as e:
            print(u"%-18s ОШИБКА РАЗБОРА: %s" % (b, e))
            problems += 1
            continue
        checked += 1
        decl = declared_names(pou)
        issues = []

        if fbd is None:
            issues.append(u"нет тела FBD")
        else:
            for blk in fbd.findall(NS + "block"):
                t = blk.get("typeName")
                pins = [v.get("formalParameter")
                        for v in blk.findall(NS + "inputVariables/" + NS + "variable")]
                n = len(pins)
                if t in PINS:
                    lo, hi = PINS[t]
                    if n < lo or (hi is not None and n > hi):
                        issues.append(u"%s: %d входов (ожидается %s) — %s"
                                      % (t, n, (u"%d..%d" % (lo, hi)) if hi else (u"не менее %d" % lo),
                                         u", ".join(pins)))
                # дубли пинов внутри блока
                if len(set(pins)) != n:
                    issues.append(u"%s: дублирующиеся входы %s" % (t, pins))
                # пустые имена
                if any(not x for x in pins):
                    issues.append(u"%s: пустое имя входа" % t)

            # ссылки на имена
            refs = set()
            for el in fbd:
                if el.tag.replace(NS, "") not in ("inVariable", "outVariable"):
                    continue
                e = el.find(NS + "expression")
                if e is None or not e.text:
                    continue
                # Сначала убираем литералы (BYTE#16#A9) и квалифицированные имена
                # GVL (GVL_CPU.A) -- они не являются локальными переменными POU.
                src = GVL_REF.sub(u" ", TYPED_LIT.sub(u" ", e.text.strip()))
                for m in IDENT.finditer(src):
                    tok = m.group(0)
                    if tok.upper() in KW or tok in decl:
                        continue
                    if tok in GVLS:
                        continue
                    if tok.startswith((u"FB_", u"F_", u"WORD", u"BYTE", u"TRUE", u"FALSE")):
                        continue
                    refs.add(tok)
            if refs:
                issues.append(u"ссылки вне объявлений: %s" % u", ".join(sorted(refs)))

        if issues:
            problems += 1
            print(u"!! %-18s" % pou.get("name"))
            for i in issues:
                print(u"     %s" % i)

    print(u"")
    print(u"Проверено схем: %d, с замечаниями: %d" % (checked, problems))
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
