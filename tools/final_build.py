# -*- coding: utf-8 -*-
"""
final_build.py -- polnaya sborka iz shablona + progon T-LDA-1 v TOJ ZHE sessii.

Pochemu tak: sohranennyy proekt okazalsya povrezhden (process ubili vo vremya
zapisi), i `projects.open` na nem molcha roняet CODESYS. Poetomu kazhdyy raz
sobiraem s chistogo shablona.

Shagi:
  1) kopiya shablona OVEN PLK210 -> rabochiy fayl;
  2) progrev (create+close), zatem open;
  3) sozdanie GVL_CPU i GVL_TABLE;
  4) udalenie pustoy ST-programmy PLC_PRG i import 38 POU + FBD-programmy;
  5) sborka; pri 0 oshibok -- save_as final;
  6) v toj zhe sessii: simulяciя, zagruzka programmy LDA #$42 v pamyat,
     start cherez vektor BRK, chtenie A/PC.
"""
import io
import os
import sys
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "final_build.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
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
log(u"=== FINAL_BUILD START ===")

# --- podtyanut' deklaracii GVL iz build_full.py, ne zapuskaya ego main()
src = io.open(os.path.join(ROOT, "tools", "build_full.py"), "rb").read().decode("utf-8")
head = src.split(u"\ndef main()")[0]
env = {}
exec(compile(head, "build_full_head", "exec"), env)
gvl_text = env["gvl_text"]
table_text = env["table_text"]
log(u"декларации GVL получены")

# --- 1) kopiya shablona
WORK = os.path.join(BUILD, u"final.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"final.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(TPL, "rb")
_d = _s.read()
_s.close()
_o = io.open(WORK, "wb")
_o.write(_d)
_o.close()
log(u"копия шаблона: %d байт" % len(_d))

import scriptengine

# --- 2) progrev + open
try:
    warm = os.path.join(BUILD, u"final_warm.project")
    for junk in os.listdir(BUILD):
        if junk.startswith(u"final_warm.project"):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    _w = projects.create(warm)
    _w.save()
    _w.close()
    # vtoroy progrev: otkryt' malenkiy proekt (inache pervyy open krupnogo padaet)
    _w2 = projects.open(warm)
    _w2.close()
    log(u"прогрев ок (create+save+open tiny)")
except Exception:
    log(u"прогрев: %s" % traceback.format_exc().strip().splitlines()[-1])

t0 = time.time()
proj = projects.open(WORK)
app = proj.active_application
log(u"шаблон открыт за %.1f с" % (time.time() - t0))

# --- 3) GVL
for nm, txt in ((u"GVL_CPU", gvl_text()), (u"GVL_TABLE", table_text())):
    try:
        o = app.create_gvl(nm)
        o.textual_declaration.replace(txt)
        log(u"%s создан (%d байт)" % (nm, len(txt)))
    except Exception:
        log(u"%s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))

# --- 4) udalit' pustuyu ST-programmu PLC_PRG i importirovat' vse
try:
    for o in (app.find(u"PLC_PRG", True) or []):
        try:
            if o.textual_declaration is not None and o.textual_declaration.text:
                o.remove()
                log(u"пустая ST-программа PLC_PRG удалена")
                break
        except Exception:
            continue
except Exception:
    log(u"удаление PLC_PRG: %s" % traceback.format_exc().strip().splitlines()[-1])

ok = imp = 0
for nm in ORDER:
    p = os.path.join(PLCOPEN, u"%s.xml" % nm)
    if not os.path.exists(p):
        log(u"  %-16s НЕТ ФАЙЛА" % nm)
        continue
    try:
        app.import_xml(p, False)
        imp += 1
    except Exception:
        log(u"  импорт %s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))
log(u"импортировано POU: %d" % imp)

try:
    app.import_xml(os.path.join(PLCOPEN, u"PRG_PLC.xml"), False)
    log(u"FBD-программа PLC_PRG импортирована")
except Exception:
    log(u"PRG_PLC: %s" % traceback.format_exc().strip().splitlines()[-1])

# --- 5) sborka
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
        log(u"проект сохранён: %s" % OUTPROJ)
    except Exception:
        log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

    # --- 6) T-LDA-1
    log(u"")
    log(u"--- T-LDA-1 ---")
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
        log(u"онлайн-приложение создано")
        oa.login(scriptengine.OnlineChangeOption.Try, False)
        log(u"login ок")
        oa.start()
        log(u"start ок")
    except Exception:
        log(u"ОНЛАЙН ОШИБКА: %s" % traceback.format_exc())

    if oa is not None:
        try:
            prog = [(0x0200, 0xA9), (0x0201, 0x42), (0x0202, 0x4C),
                    (0x0203, 0x02), (0x0204, 0x02),
                    (0xFFFE, 0x00), (0xFFFF, 0x02)]
            for addr, val in prog:
                oa.set_prepared_value(u"GVL_MEM.Mem[%d]" % addr, u"16#%02X" % val)
            oa.write_prepared_values()
            log(u"память загружена")
            time.sleep(0.6)
            res = {}
            for expr in (u"GVL_CPU.A", u"GVL_CPU.PC", u"GVL_CPU.SP", u"GVL_CPU.P",
                         u"GVL_CPU.OPs", u"GVL_CPU.LD_A_E", u"GVL_CPU.REG_WR",
                         u"GVL_CPU.WDATA", u"GVL_CPU.EFF"):
                try:
                    v = oa.read_value(expr)
                    res[expr] = u"%s" % v
                    log(u"  %-18s = %s" % (expr, v))
                except Exception:
                    log(u"  %-18s ошибка чтения" % expr)

            def num(e):
                s = res.get(e, u"")
                try:
                    return int(s.split(u"#")[-1], 16) if u"#" in s else int(s)
                except Exception:
                    return None

            a = num(u"GVL_CPU.A")
            pc = num(u"GVL_CPU.PC")
            log(u"РЕЗУЛЬТАТ T-LDA-1: A=%s (ожид 66) PC=%s (ожид 514) -> %s"
                % (a, pc, u"PASS" if (a == 0x42 and pc == 0x202) else u"FAIL"))
        except Exception:
            log(u"ТЕСТ ОШИБКА: %s" % traceback.format_exc())
        try:
            oa.stop()
            oa.logout()
        except Exception:
            pass

try:
    proj.close()
except Exception:
    pass
log(u"=== FINAL_BUILD END ===")
try:
    system.exit()
except Exception:
    pass
