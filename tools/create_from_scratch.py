# -*- coding: utf-8 -*-
"""
create_from_scratch.py -- sozdat' proekt C NULYA s ustroystvom i sobrat' yadro.

Pochemu: posle zhestkih snyatiy processov CODESYS perestal otkryvat' lyubye
sushchestvuyushchie proekty (molcha padает na projects.open), no
projects.create rabotaet i repozitoriy ustroystv dostupen (776 zapisey).
Znachit mozhno ne otkryvat' fayl, a sozdat' proekt i dobavit' device cherez API.

Shagi: create -> najti device -> add -> GVL -> import POU -> build -> save.
"""
import io
import os
import time
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "create_from_scratch.log")
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
log(u"=== CREATE_FROM_SCRATCH START ===")

import scriptengine


def attrs(obj, names):
    out = []
    for n in names:
        try:
            out.append((n, u"%s" % getattr(obj, n)))
        except Exception:
            pass
    return out


# --- 1) najti device
cand = []
try:
    rep = scriptengine.device_repository
    devs = rep.get_all_devices()
    log(u"устройств: %d" % len(devs))
    for d in devs:
        info = dict(attrs(d, (u"name", u"device_id", u"version", u"vendor",
                              u"id", u"device_version", u"type")))
        nm = info.get(u"name", u"")
        if (u"Control Win" in nm) or (u"210" in nm) or (u"PLK" in nm):
            cand.append((d, info))
    for d, info in cand[:12]:
        log(u"  кандидат: %s" % info)
except Exception:
    log(u"repo: %s" % traceback.format_exc().strip().splitlines()[-1])

# --- 2) create
WORK = os.path.join(BUILD, u"scratch.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"scratch.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
proj = projects.create(WORK)
log(u"projects.create OK")

# --- 3) dobavit' device raznymi sposobami
added = False
if cand:
    d, info = cand[0]
    dev_name = info.get(u"name", u"Device")
    dev_id = info.get(u"device_id") or info.get(u"id") or u""
    dev_ver = info.get(u"version") or info.get(u"device_version") or u""
    log(u"пробую добавить: name=%s id=%s ver=%s" % (dev_name, dev_id, dev_ver))
    attempts = []
    try:
        obj = proj.add(dev_name, dev_id, dev_ver)
        attempts.append((u"add(name,id,ver)", obj))
    except Exception as e:
        attempts.append((u"add(name,id,ver)", u"ERR %s" % e))
    if not isinstance(attempts[-1][1], (u"", type(None))) and not (u"ERR" in u"%s" % attempts[-1][1]):
        added = True
    log(u"  результат: %s" % (attempts[-1][1],))

log(u"добавлено устройство: %s" % added)

# --- 4) chto est' v proekte
try:
    app = proj.active_application
    log(u"active_application: %s" % app)
except Exception:
    log(u"active_application: %s" % traceback.format_exc().strip().splitlines()[-1])
    app = None

if app is not None:
    src = io.open(os.path.join(ROOT, "tools", "build_full.py"), "rb").read().decode("utf-8")
    head = src.split(u"\ndef main()")[0]
    env = {}
    exec(compile(head, "bf", "exec"), env)
    for nm, txt in ((u"GVL_CPU", env["gvl_text"]()), (u"GVL_TABLE", env["table_text"]())):
        try:
            g = app.create_gvl(nm)
            g.textual_declaration.replace(txt)
            log(u"%s создан" % nm)
        except Exception:
            log(u"%s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))
    imp = 0
    for nm in ORDER:
        p = os.path.join(PLCOPEN, u"%s.xml" % nm)
        if not os.path.exists(p):
            continue
        try:
            app.import_xml(p, False)
            imp += 1
        except Exception:
            log(u"  импорт %s: %s" % (nm, traceback.format_exc().strip().splitlines()[-1]))
    log(u"импортировано POU: %d" % imp)
    try:
        app.import_xml(os.path.join(PLCOPEN, u"PRG_PLC.xml"), False)
        log(u"PRG импортирована")
    except Exception:
        log(u"PRG: %s" % traceback.format_exc().strip().splitlines()[-1])
    try:
        app.build()
    except Exception:
        pass
    errs = 0
    for c in system.get_message_categories():
        try:
            for m in system.get_messages(c):
                try:
                    t = u"%s" % (m,)
                except Exception:
                    continue
                low = t.lower()
                if (u"ошибк" in low or u"неизвестн" in low or u"не задан" in low) and u"0 ошибки" not in t:
                    errs += 1
                    log(u"  !! %s" % t)
        except Exception:
            pass
    log(u"ошибок компиляции: %d" % errs)
    if errs == 0:
        try:
            proj.save_as(OUTPROJ)
            log(u"проект сохранён: %s" % OUTPROJ)
        except Exception:
            log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

try:
    proj.close()
except Exception:
    pass
log(u"=== CREATE_FROM_SCRATCH END ===")
try:
    system.exit()
except Exception:
    pass
