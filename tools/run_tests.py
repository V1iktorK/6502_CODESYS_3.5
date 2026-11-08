# -*- coding: utf-8 -*-
"""
run_tests.py -- paketnyy progon nabora komand MOS 6502 v odnu sessiyu CODESYS.

Mehanika odnogo keysa:
  1) programma keysa zapisyvaetsya po svoeemu adresu (BASE + i*SLOT);
  2) v konce programmy -- beskonechnyy JMP na sebya, poetomu posle vypolneniya
     programmy registiry "zamiraуt";
  3) vektor BRK ($FFFE/$FFFF) = adres programmy keysa; po tekushchemu PC
     zapisyvaetsya bayt BRK ($00) -- yadro vypolnyaet BRK i uhodit na novuyu
     programmu (tak pereklyuchayutsya keysy bez ostanovki PLC);
  4) zhdyom, poka PC ne vstanet na adres etogo JMP (oprosom), i chitaem registry.

Vazhno (konspekt 5.5): write_prepared_values() primenyaet tolko POSLEDNEE
znachenie, poetomu kazhdoe znachenie zapisyvaetsya i podtverzhdaetsya otdelno.

Vazhno: chisla CODESYS pechataet v desyatichnom vide ("BYTE#66"); shestnadtsaterichnoe
znachenie prihodit tolko s prefiksom "16#". Poetomu razbor chisel -- otdelnaya
funktsiya num().
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "run_tests.log")
BUILD = r"C:\CPM6502_build"
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

BASE = 0x0600
SLOT = 0x60
PARK = 0x0F00           # sverh-bystryy park (JMP na sebya) dlya nachalnogo starta

ONLY = None             # dlya bystrogo otseva: spisok imen chastey
MAXPOLL = 400           # oprosov PC na keys
POLLSLEEP = 0.01


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


# ------------------------------------------------------------------ набор команд
def C(name, code, expect=None, mem_in=None, mem_out=None, flags=None):
    return {"name": name, "code": list(code), "expect": expect or {},
            "mem_in": mem_in or {}, "mem_out": mem_out or {}, "flags": flags or {}}


CASES = [
    # ---------------- пересылки и загрузки
    C(u"LDA #$42", [0xA9, 0x42], {u"A": 0x42}),
    C(u"LDX #$07", [0xA2, 0x07], {u"X": 0x07}),
    C(u"LDY #$09", [0xA0, 0x09], {u"Y": 0x09}),
    C(u"LDA zp", [0xA5, 0x10], {u"A": 0x5A}, {0x10: 0x5A}),
    C(u"LDA zp,X", [0xA2, 0x02, 0xB5, 0x10], {u"A": 0x5B}, {0x12: 0x5B}),
    C(u"LDA abs", [0xAD, 0x00, 0x05], {u"A": 0x7C}, {0x0500: 0x7C}),
    C(u"LDA abs,X", [0xA2, 0x03, 0xBD, 0x00, 0x05], {u"A": 0x7D}, {0x0503: 0x7D}),
    C(u"LDA abs,Y", [0xA0, 0x04, 0xB9, 0x00, 0x05], {u"A": 0x7E}, {0x0504: 0x7E}),
    C(u"LDA (zp,X)", [0xA2, 0x01, 0xA1, 0x20], {u"A": 0x8C},
      {0x21: 0x06, 0x22: 0x05, 0x0506: 0x8C}),
    C(u"LDA (zp),Y", [0xA0, 0x02, 0xB1, 0x20, 0x00], {u"A": 0x8D},
      {0x20: 0x08, 0x21: 0x05, 0x0508: 0x8D}),
    C(u"STA zp", [0xA9, 0x66, 0x85, 0x11], None, None, {0x11: 0x66}),
    C(u"STA abs", [0xA9, 0x67, 0x8D, 0x10, 0x05], None, None, {0x0510: 0x67}),
    C(u"STX zp", [0xA2, 0x68, 0x86, 0x12], None, None, {0x12: 0x68}),
    C(u"STY zp", [0xA0, 0x69, 0x84, 0x13], None, None, {0x13: 0x69}),
    # ---------------- пересылки между регистрами
    C(u"TAX", [0xA9, 0x11, 0xAA], {u"A": 0x11, u"X": 0x11}),
    C(u"TAY", [0xA9, 0x12, 0xA8], {u"A": 0x12, u"Y": 0x12}),
    C(u"TXA", [0xA2, 0x22, 0x8A], {u"A": 0x22, u"X": 0x22}),
    C(u"TYA", [0xA0, 0x33, 0x98], {u"A": 0x33, u"Y": 0x33}),
    C(u"TSX", [0xBA], {u"X": 0xFF}),
    C(u"TXS", [0xA2, 0x77, 0x9A], {u"SP": 0x77}),
    # ---------------- инкремент/декремент
    C(u"INX", [0xA2, 0x05, 0xE8], {u"X": 0x06}),
    C(u"DEX", [0xA2, 0x05, 0xCA], {u"X": 0x04}),
    C(u"INY", [0xA0, 0x05, 0xC8], {u"Y": 0x06}),
    C(u"DEY", [0xA0, 0x05, 0x88], {u"Y": 0x04}),
    C(u"INC zp", [0xE6, 0x14], None, {0x14: 0x10}, {0x14: 0x11}),
    C(u"DEC zp", [0xC6, 0x14], None, {0x14: 0x10}, {0x14: 0x0F}),
    C(u"ASL A", [0xA9, 0x21, 0x0A], {u"A": 0x42}),
    C(u"LSR A", [0xA9, 0x42, 0x4A], {u"A": 0x21}),
    C(u"ROL A", [0xA9, 0x21, 0x2A], {u"A": 0x42}),
    C(u"ROR A", [0xA9, 0x42, 0x6A], {u"A": 0x21}),
    # ---------------- арифметика
    C(u"ADC 10+05", [0xA9, 0x10, 0x18, 0x69, 0x05], {u"A": 0x15}),
    C(u"ADC +carry", [0x38, 0xA9, 0x10, 0x69, 0x05], {u"A": 0x16}),
    C(u"ADC ovf", [0xA9, 0x7F, 0x69, 0x01], {u"A": 0x80}, flags={u"N": True}),
    C(u"ADC zero", [0xA9, 0x00, 0x69, 0x00], {u"A": 0x00}, flags={u"Z": True}),
    C(u"SBC 10-01", [0x38, 0xA9, 0x10, 0xE9, 0x01], {u"A": 0x0F}),
    C(u"SBC 05-05", [0x38, 0xA9, 0x05, 0xE9, 0x05], {u"A": 0x00}, flags={u"Z": True}),
    C(u"AND", [0xA9, 0xF0, 0x29, 0x3C], {u"A": 0x30}),
    C(u"ORA", [0xA9, 0xF0, 0x09, 0x0F], {u"A": 0xFF}),
    C(u"EOR", [0xA9, 0xFF, 0x49, 0x0F], {u"A": 0xF0}),
    C(u"CMP equal->Z", [0xA9, 0x20, 0xC9, 0x20], {u"A": 0x20}, flags={u"Z": True}),
    C(u"CMP less->C", [0xA9, 0x20, 0xC9, 0x30], {u"A": 0x20}, flags={u"C": False}),
    C(u"CMP greater", [0xA9, 0x30, 0xC9, 0x20], {u"A": 0x30}, flags={u"C": True}),
    C(u"CPX", [0xA2, 0x20, 0xE0, 0x20], {u"X": 0x20}, flags={u"Z": True}),
    C(u"CPY", [0xA0, 0x20, 0xC0, 0x20], {u"Y": 0x20}, flags={u"Z": True}),
    # ---------------- флаги
    C(u"SEC", [0x38], flags={u"C": True}),
    C(u"SEC-CLC", [0x38, 0x18], flags={u"C": False}),
    C(u"SEI-CLI", [0x78, 0x58], flags={u"I": False}),
    C(u"CLV", [0xB8], flags={u"V": False}),
    # ---------------- переходы
    C(u"BEQ taken", [0xA9, 0x00, 0xC9, 0x00, 0xF0, 0x02, 0xA9, 0xFF], {u"A": 0x00}),
    C(u"BNE taken", [0xA9, 0x01, 0xC9, 0x00, 0xD0, 0x02, 0xA9, 0xFF], {u"A": 0x01}),
    C(u"BCC taken", [0x18, 0x90, 0x02, 0xA9, 0xEE, 0xA9, 0x55], {u"A": 0x55}),
    C(u"BCS taken", [0x38, 0xB0, 0x02, 0xA9, 0xEE, 0xA9, 0x56], {u"A": 0x56}),
    C(u"JMP abs", [0x4C, 0x20, 0x06], None),
    C(u"JMP ind", [0x6C, 0x0F, 0x0F], None),
    # ---------------- подпрограммы
    C(u"JSR/RTS", [0x20, 0x30, 0x06, 0xA9, 0x77], {u"A": 0x77},
      {0x0630: 0xA9, 0x0631: 0x77, 0x0632: 0x60}),
    # ---------------- стек
    C(u"PHA/PLA", [0xA9, 0x99, 0x48, 0xA9, 0x00, 0x68], {u"A": 0x99}),
    C(u"PHP/PLP", [0xA9, 0x01, 0x48, 0x08, 0xA9, 0x00, 0x68, 0x28],
      None, flags={u"C": True}),
]

# Программы-«парковки» для JMP abs: $0620 -- JMP $0620 (петля), проверяем только PC
JMPPARK = 0x0620


def build_program(case, addr):
    """Байты программы с припаркованным JMP в конце."""
    code = list(case["code"])
    end = addr + len(code)
    code += [0x4C, end & 0xFF, (end >> 8) & 0xFF]
    return code, end


def main():
    f = io.open(LOG, "w", encoding="utf-8")
    f.write(u"")
    f.close()
    log(u"=== RUN_TESTS START ===")
    import scriptengine

    WORK = os.path.join(BUILD, u"tests.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"tests.project"):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    s = io.open(OUTPROJ, "rb")
    d = s.read()
    s.close()
    o = io.open(WORK, "wb")
    o.write(d)
    o.close()

    proj = projects.open(WORK)
    app = proj.active_application
    log(u"проект открыт")

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

    def wr(expr, val):
        oa.set_prepared_value(expr, val)
        oa.write_prepared_values()

    def rd(expr):
        v = u"%s" % oa.read_value(expr)
        try:
            if u"16#" in v:
                return int(v.split(u"16#")[-1], 16)
            if u"#" in v:
                return int(v.split(u"#")[-1])
            if v in (u"TRUE", u"FALSE"):
                return 1 if v == u"TRUE" else 0
            return int(v)
        except Exception:
            return None

    def rd_flag(letter):
        p = rd(u"GVL_CPU.P")
        if p is None:
            return None
        bits = {u"C": 0x01, u"Z": 0x02, u"I": 0x04, u"D": 0x08,
                u"B": 0x10, u"V": 0x40, u"N": 0x80}
        return bool(p & bits[letter])

    # ---- начальная парковка: JMP $0F00
    wr(u"GVL_MEM.Mem[%d]" % PARK, u"16#4C")
    wr(u"GVL_MEM.Mem[%d]" % (PARK + 1), u"16#00")
    wr(u"GVL_MEM.Mem[%d]" % (PARK + 2), u"16#0F")
    wr(u"GVL_MEM.Mem[65534]", u"16#00")
    wr(u"GVL_MEM.Mem[65535]", u"16#0F")
    wr(u"GVL_CPU.PC", u"16#%04X" % PARK)
    wr(u"GVL_CPU.SP", u"16#FF")
    wr(u"GVL_CPU.P", u"16#30")
    time.sleep(0.3)

    t0 = time.time()
    results = []
    for idx, case in enumerate(CASES):
        addr = BASE + idx * SLOT
        code, end = build_program(case, addr)
        name = case["name"]
        try:
            for i, b in enumerate(code):
                wr(u"GVL_MEM.Mem[%d]" % (addr + i), u"16#%02X" % b)
            for a, v in case["mem_in"].items():
                wr(u"GVL_MEM.Mem[%d]" % a, u"16#%02X" % v)
            wr(u"GVL_MEM.Mem[65534]", u"16#%02X" % (addr & 0xFF))
            wr(u"GVL_MEM.Mem[65535]", u"16#%02X" % ((addr >> 8) & 0xFF))
            # переключение через BRK на текущем PC
            p = rd(u"GVL_CPU.PC")
            if p is not None:
                wr(u"GVL_MEM.Mem[%d]" % p, u"16#00")
            # ждём парковки на JMP
            parked = False
            for _ in range(MAXPOLL):
                pc = rd(u"GVL_CPU.PC")
                if pc == end:
                    parked = True
                    break
                time.sleep(POLLSLEEP)
            got = {}
            for reg in case["expect"]:
                got[reg] = rd(u"GVL_CPU.%s" % reg)
            mem = {}
            for a, v in case["mem_out"].items():
                mem[a] = rd(u"GVL_MEM.Mem[%d]" % a)
            flg = {}
            for letter in case["flags"]:
                flg[letter] = rd_flag(letter)
            ok = True
            bad = []
            for r, v in case["expect"].items():
                if got.get(r) != v:
                    ok = False
                    bad.append(u"%s ожид %02X факт %s" % (r, v, got.get(r)))
            for a, v in case["mem_out"].items():
                if mem.get(a) != v:
                    ok = False
                    bad.append(u"Mem[%04X] ожид %02X факт %s" % (a, v, mem.get(a)))
            for letter, v in case["flags"].items():
                if flg.get(letter) != v:
                    ok = False
                    bad.append(u"флаг %s ожид %s факт %s" % (letter, v, flg.get(letter)))
            if not parked:
                ok = False
                bad.append(u"не припарковался (PC=%s, ждали %04X)" % (rd(u"GVL_CPU.PC"), end))
            results.append((name, ok, bad))
            log(u"  %-14s %s%s" % (name, u"PASS" if ok else u"FAIL",
                                   u"" if ok else u"  [" + u"; ".join(bad) + u"]"))
        except Exception:
            results.append((name, False, [u"исключение"]))
            log(u"  %-14s ОШИБКА: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

    npass = sum(1 for r in results if r[1])
    log(u"")
    log(u"ИТОГ: PASS %d из %d  (%.0f с)" % (npass, len(results), time.time() - t0))
    failed = [r[0] for r in results if not r[1]]
    if failed:
        log(u"FAILED: %s" % u", ".join(failed))

    try:
        proj.close()
    except Exception:
        pass
    log(u"=== RUN_TESTS END ===")
    try:
        system.exit()
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
