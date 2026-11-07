# -*- coding: utf-8 -*-
"""
fbd_sim2.py -- offlajn-simulyator KOMPOZICII (neskolko POU vmeste).

Zachem: odin progon CODESYS teper zanimaet 10-15 minut, poetomu otladku logiki
nuzhno vesti oflajn. Modeliruem:
  * vyzovy ekzemplyarov (ekzemplyar nashego POU -- rekursivno);
  * obshchee sostoyanie GVL_CPU i GVL_TABLE i pamyat' Mem[];
  * chtenie/za pis elementov massivov (GVL_TABLE.X[k], GVL_MEM.Mem[a], Mem[a]).

Poryadok vyhoda -- po localId (tak zhe oni i generiruyutsya).

Zapusk: python fbd_sim2.py <POU> <начальный PC> ...
"""
import io
import os
import re
import sys

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")

BOOL_WORDS = ("TRUE", "FALSE")
KNOWN = set([
    u"EQ", u"NE", u"LT", u"LE", u"GT", u"GE", u"AND", u"OR", u"XOR", u"NOT",
    u"SEL", u"MOVE", u"ADD", u"SUB", u"MUL", u"DIV", u"SHR", u"SHL",
    u"BYTE_TO_WORD", u"WORD_TO_BYTE", u"F_Join16", u"F_UnpackByte", u"F_PackByte",
    u"F_Split16", u"F_Add16",
])


def split_fbd(text):
    i = text.find("<FBD")
    j = text.find(">", i)
    k = text.find("</FBD>", j)
    body = text[j + 1:k]
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
    return els


def parse_el(e):
    lm = re.search(r'localId="(\d+)"', e[:200])
    if not lm:
        return None
    nid = int(lm.group(1))
    ex = re.search(r"<expression>([^<]*)</expression>", e)
    if e.startswith(u"<inVariable"):
        return {"kind": u"in", "id": nid, "expr": ex.group(1) if ex else u""}
    if e.startswith(u"<outVariable"):
        src = re.findall(r'refLocalId="(\d+)"', e)
        return {"kind": u"out", "id": nid, "expr": ex.group(1) if ex else u"",
                "src": int(src[0]) if src else None}
    if e.startswith(u"<comment"):
        return None
    tm = re.search(r'typeName="([^"]+)"', e)
    if not tm:
        return None
    pins = {}
    for m in re.finditer(u'<variable formalParameter="([^"]+)">'
                         u'<connectionPointIn>.*?refLocalId="(\\d+)"', e, re.S):
        pins[m.group(1)] = int(m.group(2))
    return {"kind": u"blk", "id": nid, "type": tm.group(1), "pins": pins}


def lit(s):
    s = s.strip()
    if s.upper() in BOOL_WORDS:
        return s.upper() == "TRUE"
    m = re.match(r"^([A-Za-z_]+)#(.*)$", s)
    if not m:
        return None
    body = m.group(2)
    try:
        return int(body.split("#")[1], 16) if "#" in body else int(body, 10)
    except Exception:
        return None


def asint(v):
    if isinstance(v, bool):
        return 1 if v else 0
    return v if isinstance(v, int) else 0


def asbool(v):
    return v if isinstance(v, bool) else asint(v) != 0


class Machine(object):
    """Obshchee sostoyanie: GVL_CPU, GVL_TABLE, Mem[]."""
    def __init__(self):
        self.cpu = {}
        self.tbl = {}
        self.mem = {}
        self.depth = 0

    def reset_cpu(self, **kw):
        self.cpu.update(kw)


class Sim(object):
    def __init__(self, m, name, env):
        self.m = m
        self.name = name
        path = os.path.join(PLCOPEN, u"%s.xml" % name)
        self.els = []
        if os.path.exists(path):
            text = io.open(path, "rb").read().decode("utf-8")
            for e in split_fbd(text):
                p = parse_el(e)
                if p:
                    self.els.append(p)
        self.els.sort(key=lambda x: x["id"])
        self.env = dict(env)
        self.val = {}
        self.locals = {}

    # ---------- chtenie vyrazheniy
    def read(self, expr):
        expr = expr.strip()
        L = lit(expr)
        if L is not None:
            return L
        if expr in self.env:
            return self.env[expr]
        if expr in self.locals:
            return self.locals[expr]
        m = re.match(r"^GVL_TABLE\.([A-Za-z_0-9]+)\[(.+)\]$", expr)
        if m:
            k = asint(self.read(m.group(2)))
            return self.m.tbl.get((m.group(1), k), 0)
        m = re.match(r"^GVL_CPU\.([A-Za-z_0-9]+)$", expr)
        if m:
            return self.m.cpu.get(m.group(1), 0)
        m = re.match(r"^GVL_MEM\.Mem\[(.+)\]$", expr)
        if m:
            return self.m.mem.get(asint(self.read(m.group(1))), 0)
        m = re.match(r"^Mem\[(.+)\]$", expr)
        if m:
            return self.m.mem.get(asint(self.read(m.group(1))), 0)
        # imya bez kvalifikatora: GVL_CPU (tak ego razreshaet CODESYS posle togvl)
        if expr in self.m.cpu:
            return self.m.cpu[expr]
        return 0

    def write(self, expr, v):
        expr = expr.strip()
        m = re.match(r"^GVL_CPU\.([A-Za-z_0-9]+)$", expr)
        if m:
            self.m.cpu[m.group(1)] = v
            return
        m = re.match(r"^GVL_MEM\.Mem\[(.+)\]$", expr)
        if m:
            self.m.mem[asint(self.read(m.group(1)))] = v
            return
        m = re.match(r"^Mem\[(.+)\]$", expr)
        if m:
            self.m.mem[asint(self.read(m.group(1)))] = v
            return
        self.locals[expr] = v

    # ---------- vychislenie
    def w(self, nid):
        if nid is None:
            return 0
        if nid in self.val:
            return self.val[nid]
        n = None
        for e in self.els:
            if e["id"] == nid:
                n = e
                break
        if n is None:
            return 0
        v = self.ev(n)
        self.val[nid] = v
        return v

    def ev(self, n):
        if n["kind"] == u"in":
            return self.read(n["expr"])
        if n["kind"] == u"out":
            return self.w(n["src"])
        t = n["type"]
        p = n["pins"]
        g = lambda k: self.w(p[k]) if k in p else 0
        if t in KNOWN:
            return self.std(t, g)
        # --- vyzov ekzemplyara nashego POU
        env = {}
        for k, src in p.items():
            env[k] = self.w(src)
        if self.m.depth > 40:
            return 0
        self.m.depth += 1
        try:
            child = Sim(self.m, t, env)
            out = child.run()
        finally:
            self.m.depth -= 1
        return out

    def std(self, t, g):
        if t == u"EQ":
            return asint(g(u"IN1")) == asint(g(u"IN2"))
        if t == u"NE":
            return asint(g(u"IN1")) != asint(g(u"IN2"))
        if t == u"LT":
            return asint(g(u"IN1")) < asint(g(u"IN2"))
        if t == u"LE":
            return asint(g(u"IN1")) <= asint(g(u"IN2"))
        if t == u"GT":
            return asint(g(u"IN1")) > asint(g(u"IN2"))
        if t == u"GE":
            return asint(g(u"IN1")) >= asint(g(u"IN2"))
        if t == u"AND":
            return asint(g(u"IN1")) & asint(g(u"IN2"))
        if t == u"OR":
            return asint(g(u"IN1")) | asint(g(u"IN2"))
        if t == u"XOR":
            return asint(g(u"IN1")) ^ asint(g(u"IN2"))
        if t == u"NOT":
            return 0 if asbool(g(u"IN")) else 1
        if t == u"SEL":
            return g(u"IN1") if asbool(g(u"G")) else g(u"IN0")
        if t == u"MOVE":
            return g(u"IN")
        if t == u"ADD":
            return asint(g(u"IN1")) + asint(g(u"IN2"))
        if t == u"SUB":
            return asint(g(u"IN1")) - asint(g(u"IN2"))
        if t == u"MUL":
            return asint(g(u"IN1")) * asint(g(u"IN2"))
        if t == u"SHR":
            return asint(g(u"IN")) >> asint(g(u"N"))
        if t == u"SHL":
            return asint(g(u"IN")) << asint(g(u"N"))
        if t == u"BYTE_TO_WORD":
            return asint(g(u"IN")) & 0xFF
        if t == u"WORD_TO_BYTE":
            return asint(g(u"IN")) & 0xFF
        if t == u"F_Join16":
            return ((asint(g(u"HI")) & 0xFF) << 8) | (asint(g(u"LO")) & 0xFF)
        if t == u"F_UnpackByte":
            v = asint(g(u"IN")) & 0xFF
            return [bool(v >> k & 1) for k in range(8)]
        if t == u"F_PackByte":
            b = g(u"B")
            v = 0
            if isinstance(b, list):
                for k in range(8):
                    if k < len(b) and asbool(b[k]):
                        v |= (1 << k)
            else:
                v = asint(b) & 0xFF
            return v
        return 0

    def run(self):
        """Vypolnit' POU: elementy v poryadke localId, vyhody pisutsya na meste."""
        for n in self.els:
            if n["kind"] == u"out":
                v = self.w(n["src"])
                self.write(n["expr"], v)
            elif n["kind"] == u"blk" and n["type"] not in KNOWN:
                # vyzov ekzemplyara: vypolnit' srazu (pobochnye effekty v GVL)
                self.ev(n)
        # vyhod OUT: on mozhet byt' v lokalyh ili zapisan v GVL
        if u"OUT" in self.locals:
            return self.locals[u"OUT"]
        return 0


def make_machine(pc=0x0200, code=(), sp=0xFF, a=0, x=0, y=0, pflags=0x30):
    m = Machine()
    m.reset_cpu(A=a, X=x, Y=y, P=pflags, SP=sp, PC=pc)
    for i, b in enumerate(code):
        m.mem[pc + i] = b
    m.mem[0xFFFE] = pc & 0xFF
    m.mem[0xFFFF] = (pc >> 8) & 0xFF
    return m


def load_tables():
    """Zapolnit' tablicy dekodirovaniya iz opcodes.py."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from opcodes import build_effects, BYTE_SIGNALS
    eff = build_effects()
    return eff, BYTE_SIGNALS


def main():
    eff, sigs = load_tables()
    m = make_machine(pc=0x0200, code=(0xA9, 0x42, 0x4C, 0x02, 0x02))
    for s in sigs:
        for opc in range(256):
            m.tbl[(s, opc)] = int(eff.get(opc, {}).get(s, 0))

    for tick in range(6):
        pc0 = m.cpu.get("PC")
        Sim(m, u"FB_CPU_Core", {u"Enable": True}).run()
        keys = (u"OP1", u"OP2", u"PC2", u"PC_MODE", u"ADV", u"P_ADV",
                u"LD_A_E", u"REG_WR", u"P_BRK", u"FZ", u"FC")
        print(u"такт %d: PC %s -> %s  OPs=%s AM=%s LEN=%s SRC=%s  A=%s  ALU_R=%s EFF=%s WDATA=%s"
              % (tick, pc0, m.cpu.get("PC"), m.cpu.get("OPs"), m.cpu.get("ADDR_MODE"),
                 m.cpu.get("LEN"), m.cpu.get("SRC"), m.cpu.get("A"),
                 m.cpu.get("ALU_R"), m.cpu.get("EFF"), m.cpu.get("WDATA")))
        print(u"        " + u"  ".join(u"%s=%s" % (k, m.cpu.get(k)) for k in keys))
    print(u"итог: A=%s PC=%s P=%s SP=%s" % (m.cpu.get("A"), m.cpu.get("PC"),
                                           m.cpu.get("P"), m.cpu.get("SP")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
