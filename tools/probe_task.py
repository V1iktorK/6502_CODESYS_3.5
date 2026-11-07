# -*- coding: utf-8 -*-
"""
probe_task.py -- kak privyazat POU k zadache i kak chitat znacheniya.

Nuzhno dlya testov:
  1) dobavit programmu s ekzemplyarom FB_CPU_Core v MainTask (ili zamenit PLC_PRG);
  2) sozdat onlajn-prilozhenie, vojti, zapustit i prochitat GVL_CPU.

Sobiraem uzhe gotovyy proekt build/CPM6502_CPU.project i issleduem API.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_task.log")
PROJ = os.path.join(ROOT, "build", u"CPM6502_CPU.project")
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_TASK START ===")
import scriptengine

COPY = os.path.join(BUILD, u"task_probe.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"task_probe.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(PROJ, "rb")
_d = _s.read()
_s.close()
_o = io.open(COPY, "wb")
_o.write(_d)
_o.close()

proj = app = None
try:
    proj = projects.open(COPY)
    app = proj.active_application
    log(u"проект открыт: %s" % app)
except Exception:
    log(traceback.format_exc())

# --- vsyo derevo
log(u"")
log(u"--- дерево проекта ---")


def walk(node, depth):
    try:
        kids = node.get_children()
    except Exception:
        return
    for k in kids:
        try:
            nm = k.get_name()
        except Exception:
            nm = u"?"
        try:
            cls = k.__class__.__name__
        except Exception:
            cls = u"?"
        log(u"  %s%s   [%s]" % (u"  " * depth, nm, cls))
        walk(k, depth + 1)


walk(app, 0)

# --- chto umeet zadacha
log(u"")
log(u"--- объекты задач ---")
for path in (u"Taskkonfiguration", u"MainTask"):
    try:
        o = app.find(path, True)
        log(u"  find(%s) -> %s" % (path, o))
        if o is not None:
            for attr in (u"get_tasks", u"pous", u"add_pou", u"get_pous", u"children",
                         u"get_children", u"set_pous"):
                try:
                    v = getattr(o, attr)
                    log(u"     есть %s -> %s" % (attr, v))
                except Exception:
                    pass
    except Exception:
        log(u"  find(%s) исключение: %s" % (path, traceback.format_exc().strip().splitlines()[-1]))

# --- chto umeet PLC_PRG
log(u"")
log(u"--- PLC_PRG ---")
try:
    p = app.find(u"PLC_PRG", True)
    if p is not None:
        log(u"  найден: %s" % p)
        for attr in (u"remove", u"delete", u"get_children", u"textual_implementation",
                     u"implementation_languages", u"replace"):
            try:
                v = getattr(p, attr)
                log(u"     есть %s -> %s" % (attr, v))
            except Exception:
                pass
        try:
            log(u"  декларация: %s" % p.textual_declaration.text[:300])
        except Exception:
            log(u"  декларация недоступна")
except Exception:
    log(traceback.format_exc())

# --- onlajn
log(u"")
log(u"--- онлайн ---")
for attr in (u"create_online_application", u"online_application", u"build"):
    try:
        v = getattr(app, attr)
        log(u"  app.%s -> %s" % (attr, v))
    except Exception:
        pass

log(u"=== PROBE_TASK END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
