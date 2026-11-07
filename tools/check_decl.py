# -*- coding: utf-8 -*-
"""
check_decl.py -- PROVERKA OBYAVLENIY: vse li imena iz shemy obyavleny v verkhnem okne.

В CODESYS верхнее окно POU — раздел объявлений (VAR_INPUT / VAR_OUTPUT / VAR /
VAR_IN_OUT), нижнее — реализация (сама схема FBD). Переменные объявляются ТОЛЬКО
в верхнем окне; в схеме допустимы лишь ССЫЛКИ на объявленные имена.

Если схема ссылается на имя, которого нет в объявлении, POU не компилируется, а
при импорте через PLCopen XML CODESYS молча его НЕ СОЗДАЁТ — без исключения.
Именно так и вели себя 5 «упрямых» схем и ядро FB_CPU_Core.

Скрипт разбирает сгенерированные XML (не CODESYS!) и выводит для каждого POU
список необъявленных имён. Это позволяет ловить класс ошибок до сборки.

Запуск: python check_decl.py
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

# Глобальные переменные проекта (объявлены в GVL, а не в POU)
GVLS = {
    u"GVL_CPU": {u"A", u"X", u"Y", u"P", u"SP", u"PC", u"Halted"},
    u"GVL_MEM": {u"Mem"},
    u"GVL_IO": {u"Io_In", u"Io_Out", u"Ai0", u"Ao0", u"IrqMask", u"Latch", u"Tick"},
    u"GVL_BUS": {u"Bus_Data", u"Bus_Addr", u"Bus_WE", u"Bus_RE"},
}

# Литералы и ключевые слова IEC, объявлять не нужно
KW = {u"TRUE", u"FALSE", u"NULL"}
TYPED_LIT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*#")

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def typenames(decl_text):
    """Имена типов и ключевые слова IEC, которые не являются переменными."""
    t = set()
    for m in re.finditer(r"\b(BYTE|WORD|DWORD|BOOL|INT|UINT|DINT|SINT|USINT|UDINT|"
                         r"REAL|LREAL|TIME|STRING|ARRAY|OF|VAR|VAR_INPUT|VAR_OUTPUT|"
                         r"VAR_IN_OUT|VAR_GLOBAL|END_VAR|FUNCTION_BLOCK|FUNCTION|PROGRAM|"
                         r"STRUCT|END_STRUCT|TYPE|END_TYPE)\b", decl_text, re.I):
        t.add(m.group(1).upper())
        t.add(m.group(1))
    return t


def strip_literals(expr):
    """Убрать типизированные литералы вида BYTE#16#FF, WORD#256."""
    out = []
    for tok in re.split(r"(\s+|\[|\]|\(|\)|\.|,)", expr):
        if TYPED_LIT.match(tok):
            continue
        out.append(tok)
    return u"".join(out)


def check_file(path):
    tree = ET.parse(path)
    root = tree.getroot()
    pou = root.find(NS + "types/" + NS + "pous/" + NS + "pou")
    if pou is None:
        return None
    name = pou.get("name")
    kind = pou.get("pouType")

    # ---- объявленные имена (верхнее окно) ----
    declared = set()
    iface = pou.find(NS + "interface")
    for tag in ("inputVars", "outputVars", "inOutVars", "localVars", "tempVars",
                "externalVars", "globalVars"):
        holder = iface.find(NS + tag) if iface is not None else None
        if holder is None:
            continue
        for v in holder.findall(NS + "variable"):
            declared.add(v.get("name"))

    # ---- все ссылки из схемы ----
    fbd = pou.find(NS + "body/" + NS + "FBD")
    refs = {}
    if fbd is not None:
        for el in fbd:
            tag = el.tag.replace(NS, "")
            if tag not in ("inVariable", "outVariable"):
                continue
            e = el.find(NS + "expression")
            if e is None or not e.text:
                continue
            refs.setdefault(e.text.strip(), 0)
            refs[e.text.strip()] += 1

    tnames = typenames(ET.tostring(iface, encoding="unicode") if iface is not None else u"")
    undeclared = {}
    for expr, cnt in refs.items():
        clean = strip_literals(expr)
        # индексные выражения вида Mem[XXX] и поля UNP[0] разбираем по частям
        for m in IDENT.finditer(clean):
            tok = m.group(0)
            if tok.upper() in [k.upper() for k in KW] or tok.upper() in tnames:
                continue
            # имена самих списков глобальных переменных (GVL_CPU, GVL_MEM, ...)
            # объявлять в POU не нужно: это контейнеры, а не переменные
            if tok in GVLS:
                continue
            # имя вида GVL_CPU.A -> проверяем принадлежность GVL
            dot = clean.find(u"." + tok)
            if dot > 0:
                prefix = IDENT.findall(clean[:dot])
                if prefix and prefix[-1] in GVLS:
                    if tok in GVLS[prefix[-1]]:
                        continue
            if tok in declared:
                continue
            # имена типов блоков (FB_..., F_...) не являются переменными
            if tok.startswith(u"FB_") or tok.startswith(u"F_"):
                continue
            undeclared[tok] = undeclared.get(tok, 0) + cnt
    return dict(name=name, kind=kind, declared=declared, refs=len(refs),
                undeclared=undeclared)


def main():
    names = []
    for p in sorted(glob.glob(os.path.join(PLCOPEN, "*.xml"))):
        b = os.path.basename(p)
        if b.startswith(("gen_", "rt_", "rt2_", "probe_", "inst", "bisect_", "var_", "add16_")):
            continue
        try:
            r = check_file(p)
        except Exception as e:
            print(u"%-18s ОШИБКА РАЗБОРА: %s" % (b, e))
            continue
        if r is None:
            continue
        names.append(r)

    bad = [r for r in names if r["undeclared"]]
    print(u"Проверено POU: %d" % len(names))
    print(u"POU с НЕОБЪЯВЛЕННЫМИ именами: %d" % len(bad))
    print(u"")
    for r in names:
        mark = u"!!" if r["undeclared"] else u"ok"
        print(u"%s %-18s %-14s ссылок=%-4d объявлено=%-4d %s"
              % (mark, r["name"], r["kind"], r["refs"], len(r["declared"]),
                 (u"НЕ ОБЪЯВЛЕНО: " + u", ".join(sorted(r["undeclared"]))) if r["undeclared"] else u""))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
