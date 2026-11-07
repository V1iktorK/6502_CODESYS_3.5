# -*- coding: utf-8 -*-
"""
patch_min.py -- zamenit' TOLKO izmenivshiesya POU, sobrat' i prognat' testy.

Pochemu ne vse 37: CODESYS 32-bitnyy, i polnaya zamena vseh POU privodit k
ishcherpaniyu adresnogo prostranstva -- process molcha zavershaetsya. Poetomu
menyaem tolko te POU, chto real'no izmenilis' segodnya:
    SL_BRN2 (kontakt OUT + polyarnost')
    SL_PCSEL (kontakt OUT)
    SL_WDATA2 (polyarnost' operanda)
    FB_WriteBack (polyarnost' cepochki SRC)
    FB_CPU_PcWb (provoda PC/PC_NEW + polyarnost')
"""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "patch_min.log")
PLCOPEN = os.path.join(ROOT, "plcopen")
DIR = r"C:\p"
SRC = os.path.join(DIR, u"a.project")
WORK = os.path.join(DIR, u"m.project")
OUT = os.path.join(DIR, u"CPM6502_CPU.project")

TARGETS = [u"FB_ALU6502", u"FB_Flags", u"SL_BRN2", u"SL_PCSEL",
           u"SL_WDATA2", u"FB_WriteBack", u"FB_CPU_PcWb", u"FB_CPU_Core"]

CASES = [
    (u"LDA #$42",     [0xA9, 0x42],                   {u"A": 0x42}),
    (u"LDX #$07",     [0xA2, 0x07],                   {u"X": 0x07}),
    (u"LDY #$09",     [0xA0, 0x09],                   {u"Y": 0x09}),
    (u"TAX",          [0xA9, 0x11, 0xAA],             {u"A": 0x11, u"X": 0x11}),
    (u"TAY",          [0xA9, 0x12, 0xA8],             {u"A": 0x12, u"Y": 0x12}),
    (u"TXA",          [0xA2, 0x22, 0x8A],             {u"A": 0x22, u"X": 0x22}),
    (u"TYA",          [0xA0, 0x33, 0x98],             {u"A": 0x33, u"Y": 0x33}),
    (u"INX",          [0xA2, 0x05, 0xE8],             {u"X": 0x06}),
    (u"DEX",          [0xA2, 0x05, 0xCA],             {u"X": 0x04}),
    (u"INY",          [0xA0, 0x05, 0xC8],             {u"Y": 0x06}),
    (u"DEY",          [0xA0, 0x05, 0x88],             {u"Y": 0x04}),
    (u"ADC 10+05",    [0xA9, 0x10, 0x18, 0x69, 0x05], {u"A": 0x15}),
    (u"ADC +carry",   [0x38, 0xA9, 0x10, 0x69, 0x05], {u"A": 0x16}),
    (u"SBC 10-01",    [0x38, 0xA9, 0x10, 0xE9, 0x01], {u"A": 0x0F}),
    (u"CMP equal",    [0xA9, 0x20, 0xC9, 0x20],       {u"A": 0x20}),
    (u"LDA abs",      [0xAD, 0x00, 0x05],             {u"A": 0x5A}),
    (u"JSR/RTS",      [0x20, 0x20, 0x06, 0xA9, 0x77], {u"A": 0x77}),
    (u"BEQ taken",    [0xA9, 0x00, 0xC9, 0x00, 0xF0, 0x02, 0xA9, 0xFF], {u"A": 0x00}),
    (u"BNE taken",    [0xA9, 0x01, 0xC9, 0x00, 0xD0, 0x02, 0xA9, 0xFF], {u"A": 0x01}),
    (u"SEC/CLC",      [0x38, 0x18, 0xA9, 0x44],       {u"A": 0x44}),
    (u"SEI/CLI",      [0x78, 0x58, 0xA9, 0x55],       {u"A": 0x55}),
]

BASE = 0x0600
SLOT = 0x40


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PATCH_MIN START ===")

for junk in os.listdir(DIR):
    if junk.startswith(u"m.project") or junk.startswith(u"CPM6502_CPU"):
        try:
            os.remove(os.path.join(DIR, junk))
        except Exception:
            pass

_s = io.open(SRC, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()
log(u"копия %d байт" % len(_d))

import scriptengine

proj = projects.open(WORK)
app = proj.active_application
log(u"открыт: %s" % app)

for nm in TARGETS:
    p = os.path.join(PLCOPEN, u"%s.xml" % nm)
    removed = False
    for o in (app.find(nm, True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                removed = True
                break
        except Exception:
            continue
    try:
        app.import_xml(p, False)
        log(u"  %-14s удалён=%s импортирован" % (nm, removed))
    except Exception:
        log(u"  %-14s ОШИБКА импорта: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))

log(u"сборка...")
try:
    app.build()
    log(u"сборка вернулась")
except Exception:
    log(u"сборка ИСКЛЮЧЕНИЕ: %s" % traceback.format_exc().strip().splitlines()[-1])

# SOXRANYAEM SRAZU POSLE SBORKI (do onlajna): onlajn mozhet upast'
try:
    proj.save_as(OUT)
    log(u"сохранено: %s (%d байт)" % (OUT, os.path.getsize(OUT)))
except Exception:
    log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

oa = None
try:
    node = app
    for i in range(6):
        node = node.parent
        if node is None:
            break
        try:
            node.set_simulation_mode(True)
            break
        except Exception:
            continue
    oa = scriptengine.online.create_online_application(app)
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    oa.start()
    log(u"симуляция запущена")
except Exception:
    log(u"ОНЛАЙН: %s" % traceback.format_exc().strip().splitlines()[-1])

if oa is not None:
    def wr(addr, val):
        oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % val)

    def rd(expr):
        v = oa.read_value(expr)
        s = u"%s" % v
        try:
            return int(s.split(u"#")[-1], 16) if u"#" in s else int(s)
        except Exception:
            return None

    try:
        for a, v in ((0x0200, 0xA9), (0x0201, 0x42), (0x0202, 0x4C),
                     (0x0203, 0x02), (0x0204, 0x02),
                     (0xFFFE, 0x00), (0xFFFF, 0x02)):
            wr(a, v)
        oa.write_prepared_values()
        time.sleep(0.6)
        a = rd(u"GVL_CPU.A")
        pc = rd(u"GVL_CPU.PC")
        log(u"T-LDA-1: A=%s PC=%s -> %s" % (a, pc,
            u"PASS" if (a == 0x42 and pc == 0x202) else u"FAIL"))
    except Exception:
        log(u"T-LDA-1: %s" % traceback.format_exc().strip().splitlines()[-1])

    try:
        wr(0x0500, 0x5A)
        wr(0x0620, 0xA9)
        wr(0x0621, 0x77)
        wr(0x0622, 0x60)
        oa.write_prepared_values()
        npass = 0
        for idx, (name, ops, exp) in enumerate(CASES):
            addr = BASE + idx * SLOT
            end = addr + len(ops)
            code = list(ops) + [0x4C, end & 0xFF, (end >> 8) & 0xFF]
            try:
                for i, b in enumerate(code):
                    wr(addr + i, b)
                wr(0xFFFE, addr & 0xFF)
                wr(0xFFFF, (addr >> 8) & 0xFF)
                p = rd(u"GVL_CPU.PC")
                if p is None:
                    raise RuntimeError(u"нет PC")
                wr(p, 0x00)
                oa.write_prepared_values()
                time.sleep(0.3)
                got = {}
                for reg in exp:
                    got[reg] = rd(u"GVL_CPU.%s" % reg)
                ok = all(got.get(r) == v for r, v in exp.items())
                npass += 1 if ok else 0
                log(u"  %-14s ожид %s факт %s -> %s"
                    % (name, exp, got, u"PASS" if ok else u"FAIL"))
            except Exception:
                log(u"  %-14s ошибка: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        log(u"ИТОГ набора: PASS %d из %d" % (npass, len(CASES)))
    except Exception:
        log(u"набор: %s" % traceback.format_exc().strip().splitlines()[-1])

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.save_as(OUT)
    log(u"сохранено: %s" % OUT)
except Exception:
    log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== PATCH_MIN END ===")
try:
    system.exit()
except Exception:
    pass
