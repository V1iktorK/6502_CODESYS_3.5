# -*- coding: utf-8 -*-
"""
run_cases.py -- progon VSEH keysov iz tools/testcases.py v odnu sessiyu CODESYS.

Edinyy istochnik istiny po keysam -- testcases.py (121 keys). Zdes tolko
ispolnenie: zagruzka sostoyaniya, odin progon programmy, snyatie rezultata.

Mehanika keysa:
  1) GVL_CPU.Run := FALSE  -- yadro zamorozheno (ne menyayutsya ni registry,
     ni PC, ni pamyat'), poetomu sostoyanie gruzitsya bez gonki;
  2) zapisyvaem pamyat' (pre), registry A/X/Y/P/SP i kod programmy po pc0;
     v konec programmy -- JMP na sebya (parkovka), a dlya perehodov esche i
     parkovka po ozhidaemomu adresu (chtoby PC pokazyval, kuda realno ushli);
  3) GVL_CPU.Run := TRUE, zhdyom 0.25 s -- programmy koroche pyati komand,
     za eto vremya oni vypolnyayutsya i ustoyatsya na parkovke;
  4) GVL_CPU.Run := FALSE, chitaem registry, P, PC i pamyat' (post).

Vazhno (konspekt 5.5): write_prepared_values() primenyaet tolko POSLEDNEE
znachenie, poetomu kazhdoe znachenie zapisyvaetsya i podtverzhdaetsya otdelno.

Vazhno: chisla CODESYS pechataet v desyatichnom vide ("BYTE#66");
shestnadtsaterichnoe znachenie -- tolko s prefiksom "16#".
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "run_cases.log")
BUILD = r"C:\CPM6502_build"
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
sys.path.insert(0, os.path.join(ROOT, "tools"))

SETTLE = 0.25           # с пауза
ONLY_GROUP = None       # фильтр по группе (отладка)


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def cases():
    import testcases
    return testcases.CASES


def main():
    f = io.open(LOG, "w", encoding="utf-8")
    f.write(u"")
    f.close()
    log(u"=== RUN_CASES START ===")
    import scriptengine

    all_cases = cases()
    log(u"кейсов загружено: %d" % len(all_cases))

    WORK = os.path.join(BUILD, u"cases.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"cases.project"):
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

    def wrb(addr, val):
        wr(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % (val & 0xFF))

    def rd(expr):
        v = u"%s" % oa.read_value(expr)
        try:
            if u"16#" in v:
                return int(v.split(u"16#")[-1], 16)
            if u"#" in v:
                return int(v.split(u"#")[-1])
            if v == u"TRUE":
                return 1
            if v == u"FALSE":
                return 0
            return int(v)
        except Exception:
            return None

    results = []
    t0 = time.time()
    # Ядро стартует остановленным. Тесты гоняют его СВОБОДНО, а останавливает
    # сама программа: в конце стоит команда HLT ($02), которая запрещает
    # обновление PC. Так не нужно ловить «один такт за импульс» по времени
    # (импульс короче цикла задачи проскакивал), а PC после останова равен
    # ровно тому адресу, где стоит HLT -- это и проверяется.
    wr(u"GVL_CPU.Step_On", u"FALSE")
    wr(u"GVL_CPU.Step_Pulse", u"FALSE")
    wr(u"GVL_CPU.Run", u"FALSE")
    time.sleep(0.1)
    HLT = 0x02

    for case in all_cases:
        gid = case["group"]
        if ONLY_GROUP and ONLY_GROUP not in gid:
            continue
        name = u"%s %s" % (case["id"], case["name"])
        code = list(case["code"])
        pc0 = case["pc0"]
        exp = case["exp"]
        end = pc0 + len(code)
        try:
            for a, v in case["pre"]:
                wrb(a, v)
            wr(u"GVL_CPU.A", u"16#%02X" % case["init"]["a"])
            wr(u"GVL_CPU.X", u"16#%02X" % case["init"]["x"])
            wr(u"GVL_CPU.Y", u"16#%02X" % case["init"]["y"])
            wr(u"GVL_CPU.P", u"16#%02X" % case["init"]["p"])
            wr(u"GVL_CPU.SP", u"16#%02X" % case["init"]["sp"])
            for i, b in enumerate(code):
                wrb(pc0 + i, b)
            # останов в конце программы и по ожидаемому адресу перехода
            wrb(end, HLT)
            if exp[u"pc"] != end and end < exp[u"pc"] < end + 0x20:
                wrb(exp[u"pc"], HLT)
            wr(u"GVL_CPU.PC", u"16#%04X" % pc0)
            # Регистры ядра пересчитываются каждый скан, и одна «запоздавшая»
            # запись может затереться. Поэтому пишем и ПРОВЕРЯЕМ: пока чтение
            # не совпало с записью, повторяем (до 30 попыток).
            want = [(u"GVL_CPU.A", u"16#%02X", case["init"]["a"]),
                    (u"GVL_CPU.X", u"16#%02X", case["init"]["x"]),
                    (u"GVL_CPU.Y", u"16#%02X", case["init"]["y"]),
                    (u"GVL_CPU.SP", u"16#%02X", case["init"]["sp"]),
                    (u"GVL_CPU.PC", u"16#%04X", pc0)]
            for _ in range(30):
                off = [k for k, _f, v in want if rd(k) != v]
                if not off:
                    break
                for k, fmt, v in want:
                    if k in off:
                        wr(k, fmt % v)
                time.sleep(0.02)
            wr(u"GVL_CPU.Run", u"TRUE")
            # ждём останова: PC перестал меняться и равен одной из точек останова
            stops = set([end])
            if exp[u"pc"] != end:
                stops.add(exp[u"pc"])
            parked = False
            prev = None
            for _ in range(60):
                time.sleep(0.02)
                pc = rd(u"GVL_CPU.PC")
                if pc in stops and pc == prev:
                    parked = True
                    break
                prev = pc
            wr(u"GVL_CPU.Run", u"FALSE")
            got = {
                u"a": rd(u"GVL_CPU.A"), u"x": rd(u"GVL_CPU.X"),
                u"y": rd(u"GVL_CPU.Y"), u"p": rd(u"GVL_CPU.P"),
                u"sp": rd(u"GVL_CPU.SP"), u"pc": rd(u"GVL_CPU.PC"),
            }
            bad = []
            for k in (u"a", u"x", u"y", u"p", u"sp", u"pc"):
                if got.get(k) != exp[k]:
                    bad.append(u"%s ожид %02X факт %s" % (k.upper(), exp[k], got.get(k)))
            for a, v in case["post"]:
                g = rd(u"GVL_MEM.Mem[%d]" % a)
                if g != v:
                    bad.append(u"Mem[%04X] ожид %02X факт %s" % (a, v, g))
            if not parked and not bad:
                bad.append(u"нет останова (PC=%s)" % got.get(u"pc"))
            ok = not bad
            results.append((name, ok, bad))
            log(u"  %-30s %s%s" % (name, u"PASS" if ok else u"FAIL",
                                   u"" if ok else u"  [" + u"; ".join(bad) + u"]"))
        except Exception:
            results.append((name, False, [u"исключение"]))
            log(u"  %-30s ОШИБКА: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))

    wr(u"GVL_CPU.Run", u"FALSE")
    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

    npass = sum(1 for r in results if r[1])
    log(u"")
    log(u"ИТОГ: PASS %d из %d  (%.0f с)" % (npass, len(results), time.time() - t0))
    groups = {}
    for (nm, ok, _b) in results:
        pass
    failed = [r[0] for r in results if not r[1]]
    if failed:
        log(u"FAILED:")
        for x in failed:
            log(u"   %s" % x)
    try:
        proj.close()
    except Exception:
        pass
    log(u"=== RUN_CASES END ===")
    try:
        system.exit()
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
