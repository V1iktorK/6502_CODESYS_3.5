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
        prog = [(512, 0xA9), (513, 0x42), (514, 0x4C), (515, 0x00), (516, 0x02)]
        for addr, val in prog:
            oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % val)
        # Запись в GVL_CPU izvne ne prizhivaetsya (programma perezapisyvaet kazhdyy
        # skan), a zapis v pamyat -- rabotaet. Poetomu startovyy adres zadаem
        # cherez vektor BRK: $FFFE/$FFFF = $0200. Yadro v etot moment krutit BRK
        # po adresu 0 i samo perejdet na nashu programmu.
        oa.set_prepared_value(u"GVL_MEM.Mem[65534]", u"16#00")
        oa.set_prepared_value(u"GVL_MEM.Mem[65535]", u"16#02")
        oa.write_prepared_values()
        log(u"программа записана после старта")
    except Exception:
        log(u"ошибка записи: %s" % traceback.format_exc().strip().splitlines()[-1])

    # контроль: приживается ли запись PC
    try:
        log(u"  сразу после записи: PC=%s A=%s" % (oa.read_value(u"GVL_CPU.PC"),
                                                   oa.read_value(u"GVL_CPU.A")))
    except Exception:
        log(u"  чтение сразу: ошибка")
    try:
        import time
        for i in range(6):
            time.sleep(0.05)
            log(u"  шаг %d: PC=%s A=%s OPs=%s LD_A_E=%s"
                % (i, oa.read_value(u"GVL_CPU.PC"), oa.read_value(u"GVL_CPU.A"),
                   oa.read_value(u"GVL_CPU.OPs"), oa.read_value(u"GVL_CPU.LD_A_E")))
    except Exception:
        pass

    log(u"")
    log(u"--- состояние ---")
    res = {}
    for expr in (u"GVL_CPU.A", u"GVL_CPU.X", u"GVL_CPU.Y", u"GVL_CPU.P",
                 u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.OPs",
                 u"GVL_CPU.ADDR_MODE", u"GVL_CPU.LEN", u"GVL_CPU.SRC",
                 u"GVL_CPU.PC_MODE", u"GVL_CPU.EFF", u"GVL_CPU.WDATA",
                 u"GVL_CPU.ALU_R", u"GVL_CPU.P_NEW", u"GVL_CPU.REG_WR", u"GVL_CPU.RW7", u"GVL_CPU.LD_A", u"GVL_CPU.SET_NZ", u"GVL_CPU.ALU_AX",
                 u"GVL_CPU.LD_A_E", u"GVL_MEM.Mem[512]", u"GVL_MEM.Mem[513]",
                 u"GVL_MEM.Mem[65534]", u"GVL_MEM.Mem[65535]", u"GVL_CPU.BRKV",
                 u"GVL_CPU.P_BRK", u"GVL_CPU.PC_NEW"):
        try:
            v = oa.read_value(expr)
            res[expr] = v
            log(u"  %-18s = %s" % (expr, v))
        except Exception:
            log(u"  %-18s ошибка чтения" % expr)

    # ---- проверка
    def num(expr):
        v = res.get(expr)
        try:
            return int(str(v).split(u"#")[-1], 16) if u"#" in str(v) else int(v)
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
