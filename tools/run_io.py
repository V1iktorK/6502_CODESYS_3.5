# -*- coding: utf-8 -*-
"""run_io.py -- testy TZ-2 (okno $F000-$F0FF, konsol, disk) v odnu sessiyu.

Kazhdyy keys -- programma na 6502 (mini-assembler) + proverki GVL/OKZU.
Rezhim -- poshagovyy (odin impuls = odna komanda): tak yadro ostanavlivaetsya
i sostoyanie chitaetsya tochno.
"""
import io, os, sys, time, traceback
ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import asm6502

LOG = os.path.join(ROOT, "log", "run_io.log")
BUILD = r"C:\CPM6502_build"
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8"); f.write(u"%s\n" % (m,)); f.close()


def C(name, src, setup=None, checks=None, pulses=24):
    return {"name": name, "src": src, "setup": setup or [], "checks": checks or [], "pulses": pulses}


def echo(where, port):
    return """
ORG $0200
        LDA %s
        STA %s
        HLT
""" % (where, port)


def imm_lda(val):
    return "LDA #$%02X" % val


CASES = [
    C("T-IO-1 консоль: вывод строки", """
ORG $0200
start:  LDX #$00
loop:   LDA msg,X
        BEQ done
        STA $F000
        INX
        JMP loop
done:   HLT
msg:    DB $43,$50,$2F,$4D,$00
""", checks=[(u"GVL_IO.ConPtr", 4), (u"MEM:0xF100", 0x43), (u"MEM:0xF101", 0x50),
         (u"MEM:0xF102", 0x2F), (u"MEM:0xF103", 0x4D)]),
    C("T-IO-2 дискретный выход", echo(imm_lda(0xA5), "$F000"),
      checks=[(u"GVL_IO.Io_Out", 0xA5)]),
    C("T-IO-3 дискретный вход", echo("$F000", "$0300"),
      setup=[(u"GVL_IO.Io_In", u"16#3C")], checks=[(u"MEM:0x0300", 0x3C)]),
    C("T-IO-4 аналоговый выход (ст/мл)", """
ORG $0200
        LDA #$12
        STA $F002
        LDA #$34
        STA $F003
        HLT
""", checks=[(u"GVL_IO.Ao0", 0x1234)]),
    C("T-IO-5 аналоговый вход", echo("$F002", "$0300"),
      setup=[(u"GVL_IO.Ai0", u"16#5678")], checks=[(u"MEM:0x0300", 0x78)]),
    C("T-IO-6 маска прерываний", echo(imm_lda(0x0F), "$F001"),
      checks=[(u"GVL_IO.IrqMask", 0x0F)]),
    C("T-IO-7 диск: сектор->номер", """
ORG $0200
        LDA #$05
        STA $F010
        LDA #$00
        STA $F011
        LDA #$03
        STA $F012
        HLT
""", checks=[(u"GVL_DISK.Sector", 5), (u"GVL_DISK.Offset", 3)]),
    C("T-IO-8 окно отдельно от ОЗУ", """
ORG $0200
        LDA #$77
        STA $0100
        LDA #$88
        STA $F000
        HLT
""", checks=[(u"MEM:0x0100", 0x77), (u"GVL_IO.Io_Out", 0x88)]),
    C("T-IO-9 (ключевой) чтение DI процессором", """
ORG $0200
        LDA $F000
        STA $0300
        LDA $F003
        STA $0301
        HLT
""", setup=[(u"GVL_IO.Io_In", u"16#C3"), (u"GVL_IO.Ai0", u"16#ABCD")],
      checks=[(u"MEM:0x0300", 0xC3), (u"MEM:0x0301", 0xAB)]),
    C("T-IO-10 консоль: эхо символов", """
ORG $0200
        LDX #$00
loop:   LDA msg,X
        BEQ done
        STA $F000
        INX
        JMP loop
done:   HLT
msg:    DB $4F,$4B,$00
""", checks=[(u"GVL_IO.ConPtr", 2), (u"MEM:0xF100", 0x4F), (u"MEM:0xF101", 0x4B)]),
]


def main():
    f = io.open(LOG, "w", encoding="utf-8"); f.write(u""); f.close()
    log(u"=== RUN_IO START ===")
    import scriptengine
    WORK = os.path.join(BUILD, u"iotest.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"iotest.project"):
            try: os.remove(os.path.join(BUILD, junk))
            except Exception: pass
    s = io.open(PROJ, "rb"); d = s.read(); s.close()
    o = io.open(WORK, "wb"); o.write(d); o.close()
    proj = projects.open(WORK)
    app = proj.active_application
    node = app
    for i in range(6):
        node = node.parent
        if node is None: break
        try:
            node.set_simulation_mode(True); break
        except Exception: continue
    oa = scriptengine.online.create_online_application(app)
    oa.login(scriptengine.OnlineChangeOption.Try, False)
    oa.start()
    log(u"симуляция запущена")

    def wr(e, v):
        oa.set_prepared_value(e, v); oa.write_prepared_values()

    def rd(e):
        try:
            v = u"%s" % oa.read_value(e)
        except Exception:
            return None
        try:
            if u"16#" in v: return int(v.split(u"16#")[-1], 16)
            if u"#" in v: return int(v.split(u"#")[-1])
            return int(v)
        except Exception:
            return None

    wr(u"GVL_CPU.Run", u"TRUE")
    wr(u"GVL_CPU.Step_On", u"TRUE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    time.sleep(0.2)

    results = []
    for case in CASES:
        name = case["name"]
        try:
            mem, labels = asm6502.assemble(case["src"])
            wr(u"GVL_IO.ConPtr", u"16#00")
            for a in range(0x0200, 0x0280):
                wr(u"GVL_CPU.HADR", u"16#%04X" % a)
                wr(u"GVL_CPU.HDAT", u"16#00")
                wr(u"GVL_CPU.HEN", u"TRUE")
                time.sleep(0.01)
                wr(u"GVL_CPU.HEN", u"FALSE")
            for e, v in case["setup"]:
                wr(e, v)
            for a in sorted(mem):
                wr(u"GVL_CPU.HADR", u"16#%04X" % a)
                wr(u"GVL_CPU.HDAT", u"16#%02X" % mem[a])
                wr(u"GVL_CPU.HEN", u"TRUE")
                time.sleep(0.02)
                wr(u"GVL_CPU.HEN", u"FALSE")
            wr(u"GVL_CPU.PC", u"16#0200")
            wr(u"GVL_CPU.SP", u"16#FF")
            time.sleep(0.1)
            prev = None
            for _ in range(case["pulses"]):
                wr(u"GVL_CPU.Step_Pulse", u"TRUE"); time.sleep(0.09)
                wr(u"GVL_CPU.Step_Pulse", u"FALSE"); time.sleep(0.05)
                pc = rd(u"GVL_CPU.PC")
                if pc == prev:
                    break
                prev = pc
            bad = []
            for expr, exp in case["checks"]:
                if expr.startswith(u"MEM:"):
                    a = int(expr.split(u":")[1], 16)
                    wr(u"GVL_CPU.RD_ADR", u"16#%04X" % a)
                    time.sleep(0.03)
                    got = rd(u"GVL_CPU.RD_VAL")
                else:
                    got = rd(expr)
                if got != exp:
                    bad.append(u"%s ожид %s факт %s" % (expr, exp, got))
            ok = not bad
            results.append((name, ok))
            log(u"  %-34s %s%s" % (name, u"PASS" if ok else u"FAIL",
                                   u"" if ok else u"  [" + u"; ".join(bad) + u"]"))
        except Exception:
            results.append((name, False))
            log(u"  %-34s ОШИБКА: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))

    try:
        oa.stop(); oa.logout()
    except Exception:
        pass
    npass = sum(1 for r in results if r[1])
    log(u"")
    log(u"ИТОГ TZ-2: PASS %d из %d" % (npass, len(results)))
    failed = [r[0] for r in results if not r[1]]
    if failed:
        log(u"FAILED: %s" % u", ".join(failed))
    try:
        proj.close()
    except Exception:
        pass
    log(u"=== RUN_IO END ===")
    try:
        system.exit()
    except Exception:
        pass


if __name__ == u"__main__":
    sys.exit(main())
