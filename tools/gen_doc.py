# -*- coding: utf-8 -*-
"""
gen_doc.py -- документация по схемам, СГЕНЕРИРОВАННАЯ ИЗ САМИХ XML.

Смысл: описание интерфейсов не пишется руками, а читается из тех же файлов,
которые импортируются в CODESYS. Разъехаться они не могут по построению.

Результат: docs/04_СХЕМЫ.md
"""
import glob
import io
import os
import xml.etree.ElementTree as ET

NS = "{http://www.plcopen.org/xml/tc6_0200}"
ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"

LAYERS = {
    u"F_": u"Примитивы и функции (без состояния)",
    u"FB_": u"Функциональные блоки (с состоянием или крупная логика)",
}


def typestr(v):
    t = v.find(NS + "type")
    if t is None:
        return u"?"
    arr = t.find(NS + "array")
    if arr is not None:
        d = arr.find(NS + "dimension")
        b = arr.find(NS + "baseType")
        base = list(b)[0].tag.replace(NS, "") if b is not None and len(b) else u"?"
        return u"ARRAY[%s..%s] OF %s" % (d.get("lower"), d.get("upper"), base)
    return list(t)[0].tag.replace(NS, "")


def block_of(pou):
    fbd = pou.find(NS + "body/" + NS + "FBD")
    if fbd is None:
        return [], []
    blocks = [b.get("typeName") for b in fbd.findall(NS + "block")]
    return list(fbd), blocks


def main():
    rows = []
    groups = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "plcopen", "*.xml"))):
        n = os.path.basename(p)
        if n.startswith((u"gen_", u"rt_", u"rt2_", u"probe_")):
            continue
        r = ET.parse(p).getroot()
        pou = r.find(NS + "types/" + NS + "pous/" + NS + "pou")
        name = pou.get("name")
        kind = pou.get("pouType")
        doc = pou.find(NS + "documentation")
        comment = u" ".join(u"".join(doc.itertext()).split()) if doc is not None else u""
        iface = pou.find(NS + "interface")
        ins, outs, locs = [], [], []
        for tag, bucket in ((u"inputVars", ins), (u"outputVars", outs), (u"localVars", locs)):
            holder = iface.find(NS + tag)
            if holder is None:
                continue
            for v in holder.findall(NS + "variable"):
                bucket.append((v.get("name"), typestr(v)))
        els, blocks = block_of(pou)
        from collections import Counter
        cnt = Counter(blocks)
        rows.append(dict(name=name, kind=kind, comment=comment, ins=ins, outs=outs,
                         locs=locs, els=len(els), blocks=len(blocks), cnt=cnt))
        key = u"F_" if name.startswith(u"F_") else u"FB_"
        groups.setdefault(key, []).append(name)

    out = []
    out.append(u"# Схемы проекта: интерфейсы и состав\n")
    out.append(u"Документ **сгенерирован** из `plcopen\\*.xml` (`tools\\gen_doc.py`) — "
               u"не редактировать вручную.\n")
    total_el = sum(r["els"] for r in rows)
    total_bl = sum(r["blocks"] for r in rows)
    out.append(u"Всего POU: **%d**, элементов FBD: **%d**, функциональных блоков: **%d**.\n"
               % (len(rows), total_el, total_bl))

    out.append(u"\n## Сводка\n")
    out.append(u"| POU | Тип | Элементов | Блоков | Назначение |")
    out.append(u"|---|---|---:|---:|---|")
    for r in sorted(rows, key=lambda x: (x["kind"], x["name"])):
        out.append(u"| `%s` | %s | %d | %d | %s |"
                   % (r["name"], r["kind"], r["els"], r["blocks"], r["comment"][:95]))
    out.append(u"")

    for key in (u"F_", u"FB_"):
        if key not in groups:
            continue
        out.append(u"\n## %s\n" % LAYERS[key])
        for r in sorted(rows, key=lambda x: x["name"]):
            if not r["name"].startswith(key):
                continue
            out.append(u"\n### `%s` (%s)\n" % (r["name"], r["kind"]))
            out.append(u"%s\n" % r["comment"])
            if r["ins"]:
                out.append(u"\n**Входы:** " + u", ".join(u"`%s : %s`" % t for t in r["ins"]))
            if r["outs"]:
                out.append(u"\n\n**Выходы:** " + u", ".join(u"`%s : %s`" % t for t in r["outs"]))
            if r["locs"]:
                out.append(u"\n\n**Локальные:** " + u", ".join(u"`%s : %s`" % t for t in r["locs"]))
            if r["cnt"]:
                top = u", ".join(u"%s ×%d" % (k, v) for k, v in sorted(r["cnt"].items(), key=lambda x: -x[1]))
                out.append(u"\n\n**Состав:** %s" % top)
            out.append(u"\n")

    path = os.path.join(ROOT, "docs", u"04_СХЕМЫ.md")
    f = io.open(path, "w", encoding="utf-8")
    f.write(u"\n".join(out))
    f.close()
    print(u"документ: %s" % path)
    print(u"POU=%d элементов=%d блоков=%d" % (len(rows), total_el, total_bl))


if __name__ == "__main__":
    main()
