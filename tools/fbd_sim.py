# -*- coding: utf-8 -*-
"""
fbd_sim.py -- offlajn-interpretator FBD-shemy (PLCopen XML).

Zachem: chtoby otdelit oshibku GENERATORA ot povedeniya CODESYS. Berem
sgenerirovannyy XML, schitaem znacheniya vseh vyhodov dlya zadannyh vhodov i
sravnivaem s tem, chto dolzhno byt po TZ.

Podderzhivaetsya: EQ NE LT LE GT GE AND OR XOR NOT SEL ADD SUB MUL SHR SHL
BYTE_TO_WORD WORD_TO_BYTE, vyzovy F_Join16 / F_UnpackByte / F_PackByte
(realizuyutsya pryamo), chtenie Mem[...] iz peredannogo sostoyaniya.

Zapusk:
  python fbd_sim.py FB_Decoder6502 "Op=16#A9" [imya_peremennyh]
"""
import io
import os
import re
import sys

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")


# ------------------------------------------------------------------ razbor XML
def split_fbd(text):
    i = text.find("<FBD")
    j = text.find(">", i)
    head = text[:j + 1]
    k = text.find("</FBD>", j)
    body = text[j + 1:k]
    tail = text[k:]
    els = []
    depth = 0
    start = None
    q = False
    p = 0
    n = len(body)
    while p < n:
        c = body[p]
        if q:
            if c == '"':
                q = False
            p += 1
            continue
        if c == '"':
            q = True
            p += 1
            continue
        if c == "<":
            if body.startswith("<!--", p):
                e = body.find("-->", p)
                if depth == 0:
                    els.append(body[p:e + 3])
                p = e + 3
                continue
            if body.startswith("</", p):
                e = body.find(">", p)
                depth -= 1
                if depth == 0 and start is not None:
                    els.append(body[start:e + 1])
                    start = None
                p = e + 1
                continue
            if depth == 0:
                start = p
            e = body.find(">", p)
            if body[e - 1] == "/":
                if depth == 0 and start is not None:
                    els.append(body[start:e + 1])
                    start = None
            else:
                depth += 1
            p = e + 1
            continue
        p += 1
    return head, els, tail


def parse_element(e):
    """-> dict(kind, id, type, pins{name: src_id}, expr, out_pin)"""
    lm = re.search(r'localId="(\d+)"', e[:200])
    if not lm:
        return None
    node = {"id": int(lm.group(1)), "kind": "", "type": None, "pins": {}, "expr": None}
    tm = re.search(r'typeName="([^"]+)"', e)
    ex = re.search(r"<expression>([^<]*)</expression>", e)
    if e.startswith(u"<inVariable"):
        node["kind"] = u"in"
        node["expr"] = ex.group(1) if ex else u""
        return node
    if e.startswith(u"<outVariable"):
        node["kind"] = u"out"
        node["expr"] = ex.group(1) if ex else u""
        for m in re.finditer(r'refLocalId="(\d+)"', e):
            node["pins"][u"__in"] = int(m.group(1))
        return node
    if e.startswith(u"<comment"):
        return None
    if tm:
        node["kind"] = u"block"
        node["type"] = tm.group(1)
        for m in re.finditer(u'<variable formalParameter="([^"]+)">'
                             u'<connectionPointIn>.*?refLocalId="(\\d+)"', e, re.S):
            node["pins"][m.group(1)] = int(m.group(2))
        return node
    return None


# ------------------------------------------------------------------ znacheniya
def parse_literal(s):
    """BYTE#16#A9 -> 169, WORD#256 -> 256, TRUE/FALSE -> bool, None esli ne literal."""
    s = s.strip()
    if s.upper() in ("TRUE", "FALSE"):
        return s.upper() == "TRUE"
    m = re.match(r"^([A-Za-z_]+)#(.*)$", s)
    if not m:
        return None
    body = m.group(2)
    try:
        if "#" in body:
            return int(body.split("#")[1], 16)
        return int(body, 10)
    except Exception:
        return None


def as_int(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    return 0


def as_bool(v):
    if isinstance(v, bool):
        return v
    return as_int(v) != 0


class Sim(object):
    def __init__(self, name, inputs):
        self.name = name
        path = os.path.join(PLCOPEN, u"%s.xml" % name)
        self.text = io.open(path, "rb").read().decode("utf-8")
        head, els, tail = split_fbd(self.text)
        self.nodes = {}
        self.outs = []
        for e in els:
            n = parse_element(e)
            if n is None:
                continue
            self.nodes[n["id"]] = n
            if n["kind"] == u"out":
                self.outs.append(n)
        self.env = dict(inputs)
        self.memo = {}
        self.busy = set()
        # локальные переменные схемы (ворота, промежуточные и т.п.):
        # имя -> id элемента, который её записывает
        self.locals = {}
        for o in self.outs:
            nm = (o["expr"] or u"").strip()
            if nm and not nm.startswith(u"GVL_"):
                self.locals[nm] = o["id"]

    def read_var(self, expr):
        expr = expr.strip()
        lit = parse_literal(expr)
        if lit is not None:
            return lit
        if expr in self.env:
            return self.env[expr]
        if expr in self.locals:
            return self.val(self.locals[expr])
        # Mem[...] и глобальные — berem iz okruzheniya kak est
        return 0

    def val(self, nid):
        if nid in self.memo:
            return self.memo[nid]
        if nid in self.busy:
            raise RuntimeError(u"цикл в схеме на узле %d" % nid)
        n = self.nodes.get(nid)
        if n is None:
            return 0
        self.busy.add(nid)
        try:
            v = self._eval(n)
        finally:
            self.busy.discard(nid)
        self.memo[nid] = v
        return v

    def _eval(self, n):
        if n["kind"] == u"in":
            return self.read_var(n["expr"])
        if n["kind"] == u"out":
            return self.val(n["pins"][u"__in"])
        t = n["type"]
        p = n["pins"]
        g = lambda k: self.val(p[k]) if k in p else 0
        if t == u"EQ":
            return as_int(g(u"IN1")) == as_int(g(u"IN2"))
        if t == u"NE":
            return as_int(g(u"IN1")) != as_int(g(u"IN2"))
        if t == u"LT":
            return as_int(g(u"IN1")) < as_int(g(u"IN2"))
        if t == u"LE":
            return as_int(g(u"IN1")) <= as_int(g(u"IN2"))
        if t == u"GT":
            return as_int(g(u"IN1")) > as_int(g(u"IN2"))
        if t == u"GE":
            return as_int(g(u"IN1")) >= as_int(g(u"IN2"))
        if t == u"AND":
            return as_int(g(u"IN1")) & as_int(g(u"IN2"))
        if t == u"OR":
            return as_int(g(u"IN1")) | as_int(g(u"IN2"))
        if t == u"XOR":
            return as_int(g(u"IN1")) ^ as_int(g(u"IN2"))
        if t == u"NOT":
            return 0 if as_bool(g(u"IN")) else 1
        if t == u"SEL":
            return g(u"IN1") if as_bool(g(u"G")) else g(u"IN0")
        if t == u"ADD":
            return as_int(g(u"IN1")) + as_int(g(u"IN2"))
        if t == u"SUB":
            return as_int(g(u"IN1")) - as_int(g(u"IN2"))
        if t == u"MUL":
            return as_int(g(u"IN1")) * as_int(g(u"IN2"))
        if t == u"SHR":
            return as_int(g(u"IN")) >> as_int(g(u"N"))
        if t == u"SHL":
            return as_int(g(u"IN")) << as_int(g(u"N"))
        if t == u"BYTE_TO_WORD":
            return as_int(g(u"IN"))
        if t == u"WORD_TO_BYTE":
            return as_int(g(u"IN")) & 0xFF
        if t == u"F_Join16":
            return (as_int(g(u"HI")) << 8) | (as_int(g(u"LO")) & 0xFF)
        if t == u"F_PackByte":
            b = g(u"B")
            if not isinstance(b, list):
                return as_int(b) & 0xFF
            v = 0
            for k in range(8):
                if as_bool(b[k] if k < len(b) else False):
                    v |= (1 << k)
            return v
        if t == u"F_UnpackByte":
            v = as_int(g(u"IN")) & 0xFF
            return [bool(v & (1 << k)) for k in range(8)]
        raise RuntimeError(u"неизвестный блок %s" % t)

    def run(self):
        res = {}
        for o in self.outs:
            try:
                res[o["expr"]] = self.val(o["id"])
            except Exception as e:
                res[o["expr"]] = u"ОШИБКА: %s" % e
        return res


def main():
    if len(sys.argv) < 2:
        print(u"usage: fbd_sim.py POU 'VAR=VALUE;...' [имена через запятую]")
        return 1
    name = sys.argv[1]
    env = {}
    if len(sys.argv) > 2:
        for part in sys.argv[2].split(u";"):
            part = part.strip()
            if not part:
                continue
            k, v = part.split(u"=", 1)
            lit = parse_literal(v)
            env[k.strip()] = lit if lit is not None else int(v, 0)
    only = None
    if len(sys.argv) > 3:
        only = [x.strip() for x in sys.argv[3].split(u",")]
    s = Sim(name, env)
    res = s.run()
    print(u"=== %s : входы %s ===" % (name, env))
    for k in sorted(res):
        if only and k.split(u".")[-1] not in only:
            continue
        print(u"  %-24s = %s" % (k, res[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
