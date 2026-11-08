# -*- coding: utf-8 -*-
"""
test_lda.py -- T-LDA-1: LDA #$42 s ostanovkoy v beskonechnom JMP.

Poryadok raboty s PLC vazhen: snachala start(), ZATEM zapis znacheniy, inache
start perezapisyvaet ih nachalnymi znacheniyami (proverено: PC stanovilsya 0).

Programma:
  $0200: A9 42        LDA #$42
  $0202: 4C 02 02     JMP $0202      (samopovtor: PC stabilen, A sohranyaetsya)

Ozhidaem: A=$42, PC=$0202, Z=0 (A<>0), N=0.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "test_lda.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== TEST_LDA START ===")
import scriptengine

WORK = os.path.join(BUILD, u"lda.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"lda.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(PROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()

proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")

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
    log(u"симуляция запущена (start выполнен ДО записи)")
except Exception:
    log(u"ошибка запуска: %s" % traceback.format_exc().strip().splitlines()[-1])
    oa = None

if oa is not None:
    # ---- загрузка программы ПОСЛЕ старта
    try:
        # ВАЖНО (конспект 5.5): write_prepared_values() применяет ТОЛЬКО последнее
        # значение, поэтому пишем и подтверждаем ПО ОДНОМУ.
        # Регистры A/X/Y/P НЕ пишем: процессор уже работает, и такая запись
        # затирает результат LDA ($42 -> 0). Достаточно памяти и PC.
        writes = [(u"GVL_MEM.Mem[512]", u"16#A9"), (u"GVL_MEM.Mem[513]", u"16#42"),
                  (u"GVL_MEM.Mem[514]", u"16#4C"), (u"GVL_MEM.Mem[515]", u"16#02"),
                  (u"GVL_MEM.Mem[516]", u"16#02"),
                  (u"GVL_MEM.Mem[65534]", u"16#00"), (u"GVL_MEM.Mem[65535]", u"16#02"),
                  (u"GVL_CPU.PC", u"16#0200"), (u"GVL_CPU.SP", u"16#FF")]
        for nm, val in writes:
            try:
                oa.set_prepared_value(nm, val)
                oa.write_prepared_values()
            except Exception:
                log(u"  не записалось: %s" % nm)
        log(u"программа записана после старта")
    except Exception:
        log(u"ошибка записи: %s" % traceback.format_exc().strip().splitlines()[-1])

    # быстрый поскановый след: ловим первые такты
    try:
        import time
        prev = None
        for k in range(60):
            try:
                pc = oa.read_value(u"GVL_CPU.PC")
                op = oa.read_value(u"GVL_CPU.PC_MODE")
                a = oa.read_value(u"GVL_CPU.P_ADV")
            except Exception:
                break
            cur = (str(pc), str(op), str(a))
            if cur != prev:
                log(u"  такт %2d: PC=%s PC_MODE=%s P_ADV=%s" % (k, pc, op, a))
                prev = cur
            time.sleep(0.02)
    except Exception:
        pass
    log(u"")
    log(u"--- состояние ---")
    res = {}
    for expr in (u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.PC_MODE", u"GVL_CPU.SP_MODE",
                 u"GVL_CPU.BRKV", u"GVL_CPU.P_BRK", u"GVL_CPU.PC_NEW",
                 u"GVL_CPU.STK_A0", u"GVL_CPU.STK_A1", u"GVL_CPU.STK_A2",
                 u"GVL_CPU.WR0", u"GVL_CPU.WR1", u"GVL_CPU.WR_EN0", u"GVL_CPU.WRD0",
                 u"GVL_CPU.SPM1", u"GVL_CPU.SPP1", u"GVL_CPU.SP_NEW",
                 u"GVL_MEM.Mem[65534]", u"GVL_MEM.Mem[65535]", u"GVL_CPU.Enable",
                 u"GVL_CPU.A", u"GVL_CPU.Ops", u"GVL_CPU.SRC", u"GVL_CPU.LEN",
                 u"GVL_CPU.ADDR_MODE", u"GVL_CPU.LD_A", u"GVL_CPU.LD_A_E",
                 u"GVL_CPU.REG_WR", u"GVL_CPU.ALU_R", u"GVL_CPU.ADV",
                 u"GVL_CPU.P_EFF", u"GVL_CPU.P_KEEP"):
        try:
            v = oa.read_value(expr)
            res[expr] = v
            log(u"  %-18s = %s" % (expr, v))
        except Exception:
            log(u"  %-18s ошибка чтения" % expr)

    # ---- проверка
    def num(expr):
        # CODESYS печатает BYTE/WORD в десятичном виде ("BYTE#66"); шестнадцатеричное
        # значение приходит только с префиксом "16#". Раньше здесь всё считалось
        # hex-ом, из-за чего $42 превращался в 102 и тест ложно падал.
        v = res.get(expr)
        s = str(v)
        try:
            if u"16#" in s:
                return int(s.split(u"16#")[-1], 16)
            if u"#" in s:
                return int(s.split(u"#")[-1])
            return int(s)
        except Exception:
            return None

    a = num(u"GVL_CPU.A")
    pc = num(u"GVL_CPU.PC")
    log(u"")
    log(u"РЕЗУЛЬТАТ T-LDA-1: A=%s (ожидание 0x42), PC=%s (ожидание 0x202) -> %s"
        % (a, pc, u"PASS" if (a == 0x42 and pc == 0x202) else u"FAIL"))

    try:
        oa.stop()
        oa.logout()
    except Exception:
        pass

try:
    proj.close()
except Exception:
    pass

log(u"=== TEST_LDA END ===")
try:
    system.exit()
except Exception:
    pass
