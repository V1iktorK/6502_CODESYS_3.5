# -*- coding: utf-8 -*-
"""
build_and_test.py -- odna sessiya: zamenit' POU, sobrat', projti T-LDA-1.

Zachem: otkrytie proekta teper zanimaet minuty, poetomu nelzya delat'
"otdelno sborka, otdelno test". Skript:
  1) kopiruet build/CPM6502_CPU.project;
  2) dlya kazhdogo POU iz ORDER: udalyaet staryy i importiruet svezhiy XML;
  3) sobiraet proekt; pri 0 oshibok sohranyaet;
  4) v toj zhe sessii podnimaet simulyaciyu i prohonyaet T-LDA-1
     (LDA #$42; JMP $0202 -> A=$42, PC=$0202).
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "build_and_test.log")
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")

ORDER = [
    u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
    u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"FB_WriteBack",
    u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
    u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
    u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",
    u"FB_CPU_Addr1", u"FB_CPU_Select", u"FB_CPU_Stack", u"FB_CPU_AluFlags",
    u"FB_CPU_PcWb", u"FB_CPU_Store", u"FB_CPU_Core",
]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== BUILD_AND_TEST START ===")
import scriptengine

WORK = os.path.join(BUILD, u"bat.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"bat.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(OUTPROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()
log(u"копия проекта: %d байт" % len(_d))

# прогрев сессии: create открывает caches быстрее, чем первый open
try:
    warm = os.path.join(BUILD, u"bat_warm.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"bat_warm.project"):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    _w = projects.create(warm)
    _w.close()
    log(u"прогрев выполнен")
except Exception:
    log(u"прогрев: %s" % traceback.format_exc().strip().splitlines()[-1])
proj = projects.open(WORK)
app = proj.active_application
log(u"проект открыт")


def find_textual(name):
    for o in (app.find(name, True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                return o
        except Exception:
            continue
    return None


removed = imp = 0
for nm in ORDER:
    p = os.path.join(PLCOPEN, u"%s.xml" % nm)
    if not os.path.exists(p):
        log(u"  %-16s НЕТ ФАЙЛА" % nm)
        continue
    o = find_textual(nm)
    if o is not None:
        try:
            o.remove()
            removed += 1
        except Exception:
            log(u"  не удалён %s" % nm)
    try:
        app.import_xml(p, False)
        imp += 1
    except Exception:
        log(u"  импорт %s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))
log(u"удалено %d, импортировано %d" % (removed, imp))

# ---------------- сборка
try:
    app.build()
except Exception:
    pass
errs = []
for c in system.get_message_categories():
    try:
        for m in system.get_messages(c):
            try:
                t = u"%s" % (m,)
            except Exception:
                continue
            low = t.lower()
            if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) \
                    and u"0 ошибки" not in t:
                errs.append(t)
    except Exception:
        pass
log(u"ошибок компиляции: %d" % len(errs))
for t in errs[:12]:
    log(u"  !! %s" % t)

if not errs:
    try:
        proj.save_as(OUTPROJ)
        log(u"проект сохранён")
    except Exception:
        log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

# ---------------- T-LDA-1 v toj zhe sessii
if not errs:
    log(u"")
    log(u"--- T-LDA-1 ---")
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
        # startovyy adres zadаem cherez vektor BRK, dannye -- v pamyat
        prog = [(512, 0xA9), (513, 0x42), (514, 0x4C), (515, 0x02), (516, 0x02)]
        for addr, val in prog:
            oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % val)
        oa.set_prepared_value(u"GVL_MEM.Mem[65534]", u"16#00")
        oa.set_prepared_value(u"GVL_MEM.Mem[65535]", u"16#02")
        oa.write_prepared_values()
        log(u"память загружена, старт через вектор BRK")
        try:
            import time
            time.sleep(0.6)
        except Exception:
            pass
        res = {}
        for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.P",
                     u"GVL_CPU.OPs", u"GVL_CPU.LD_A_E", u"GVL_CPU.REG_WR",
                     u"GVL_CPU.WDATA", u"GVL_CPU.EFF"):
            try:
                v = oa.read_value(expr)
                res[expr] = v
                log(u"  %-18s = %s" % (expr, v))
            except Exception:
                log(u"  %-18s ошибка чтения" % expr)

        def num(expr):
            v = res.get(expr)
            s = u"%s" % v
            try:
                base = 16 if u"#" in s else 10
                return int(s.split(u"#")[-1], base)
            except Exception:
                return None

        a = num(u"GVL_CPU.A")
        pc = num(u"GVL_CPU.PC")
        ok = (a == 0x42 and pc == 0x202)
        log(u"РЕЗУЛЬТАТ T-LDA-1: A=%s PC=%s -> %s" % (a, pc, u"PASS" if ok else u"FAIL"))
        try:
            oa.stop()
            oa.logout()
        except Exception:
            pass
    except Exception:
        log(u"онлайн: %s" % traceback.format_exc())

try:
    proj.close()
except Exception:
    pass

log(u"=== BUILD_AND_TEST END ===")
try:
    system.exit()
except Exception:
    pass
