# -*- coding: utf-8 -*-
"""
build_batches.py -- sborka shem PARTIYAMI s pereotkrytiem proekta.

Zachem: ustanovleno eksperimentalno (docs/05_...), chto sessiya importa CODESYS
nakoplivaet nestabilnost: posle 10-11 importov podryad sleduyushchiy import
ronyaet process. Odnim session nelzya zagruzit vse 16 shem.

Reshenie: partii po BATCH shtuk. Mezhdu partiyami proekt sohranyaetsya i
zakryvaetsya, zatem otkryvaetsya zanovo -- sessiya importa nachinaetsya s chistogo
sostoyaniya, a uzhe sozdannye POU ostayutsya v fayle proekta.

Dopolnitelno: v kazhdoy partii delayutsya povtornye popytki dlya teh, kto
ne sozdalsya s pervogo raza -- inogda pomogaet chistaya sessiya.

Rezultat -> log/build_batches.log
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
# Резервная папка: сюда генератор кладёт схему, если файл в OneDrive
# заблокирован зависшим процессом CODESYS.
PLCOPEN_ALT = r"C:\CPM6502_build\plcopen"


def xml_path(name):
    """Путь к схеме: сначала основная папка, затем резервная."""
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if os.path.exists(p):
        return p
    a = os.path.join(PLCOPEN_ALT, u"%s.xml" % name)
    if os.path.exists(a):
        return a
    return p
LOG = os.path.join(ROOT, "log", "build_batches.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\Standard.project"
PROJECT = os.path.join(os.getcwd(), u"Emu6502.project")
BATCH = 4
ROUNDS = 6          # сколько раз пройти по всем схемам (для упрямых)


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()

log(u"=== BUILD_BATCHES START ===")
log(u"cwd: %s" % os.getcwd())

ALL = [
    u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16",
    u"F_Add16", u"F_PtrGen",
    u"FB_Reg8", u"FB_Reg16", u"FB_FlagsReg", u"FB_ALU_6502",
    u"FB_Stack", u"FB_PC_Update", u"FB_Branch", u"FB_Memory64K",
    u"FB_Decoder6502",
    # FB_AddrGen ИСКЛЮЧЁН из общего списка: его импорт не просто не создаёт POU,
    # а роняет процесс CODESYS целиком, из-за чего не выполняются круги добора
    # остальных схем. Им занимаемся отдельным прогоном.
    u"FB_AddrGen",
]

OS_VARS = set()


def open_project(first):
    """Открыть проект: при первом запуске -- из шаблона, далее -- уже собранный."""
    if first:
        for junk in os.listdir(os.getcwd()):
            if junk.startswith(u"base_batch.project") or junk.startswith(u"Emu6502.project"):
                try:
                    os.remove(os.path.join(os.getcwd(), junk))
                except Exception:
                    pass
        _s = io.open(TPL, "rb")
        _d = _s.read()
        _s.close()
        _o = io.open(os.path.join(os.getcwd(), u"base_batch.project"), "wb")
        _o.write(_d)
        _o.close()
        return projects.open(os.path.join(os.getcwd(), u"base_batch.project"))
    return projects.open(PROJECT)


def children(app):
    names = []
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.append(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        log(traceback.format_exc())
    return names


created = set()
rounds_used = 0

for rnd in range(1, ROUNDS + 1):
    todo = [n for n in ALL if n not in created]
    if not todo:
        break
    rounds_used = rnd
    # Партии ПО ОДНОЙ схеме на сессию, и проект сохраняется после каждого
    # импорта: импорт отдельной схемы может уронить процесс CODESYS целиком,
    # поэтому цена падения не должна превышать одну схему.
    batch_size = 1
    log(u"")
    log(u"=========== КРУГ %d: осталось %d схем, партии по %d ==========="
        % (rnd, len(todo), batch_size))

    for start in range(0, len(todo), batch_size):
        batch = todo[start:start + batch_size]
        if not batch:
            continue
        log(u"")
        log(u"--- партия: %s" % u", ".join(batch))
        proj = None
        app = None
        try:
            proj = open_project(first=(rnd == 1 and start == 0))
            app = proj.active_application
        except Exception:
            log(u"!!! не удалось открыть проект:")
            log(traceback.format_exc())
            continue

        for name in batch:
            xp = xml_path(name)
            try:
                app.import_xml(xp, False)
            except Exception:
                log(u"  %-16s ИСКЛЮЧЕНИЕ: %s"
                    % (name, traceback.format_exc().strip().splitlines()[-1]))
                continue
            if name in children(app):
                created.add(name)
                log(u"  %-16s -> создан" % name)
            else:
                log(u"  %-16s -> НЕ СОЗДАН" % name)

        try:
            proj.save_as(PROJECT, u"")
        except Exception:
            log(u"!!! ошибка сохранения:")
            log(traceback.format_exc())
        try:
            proj.close()
        except Exception:
            pass

log(u"")
log(u"=========== ИТОГ ===========")
log(u"создано %d из %d за %d круг(а)" % (len(created), len(ALL), rounds_used))
log(u"СОЗДАНЫ   : %s" % u", ".join(sorted(created)))
log(u"НЕ СОЗДАНЫ: %s" % (u", ".join([n for n in ALL if n not in created]) or u"(нет)"))

# ---------------------------------------------------------------- финальная компиляция
if created:
    log(u"")
    log(u"--- финальная компиляция ---")
    proj = None
    try:
        proj = projects.open(PROJECT)
        app = proj.active_application
        try:
            app.build()
            log(u"app.build() -- без исключения")
        except Exception:
            log(u"app.build() -- ИСКЛЮЧЕНИЕ")
            log(traceback.format_exc())
        try:
            msgs = system.get_messages()
            log(u"сообщений компилятора: %d" % len(msgs))
            for m in msgs[:50]:
                try:
                    log(u"  [%s] %s" % (getattr(m, "severity", u"?"), getattr(m, "text", m)))
                except Exception:
                    log(u"  %r" % (m,))
        except Exception:
            log(traceback.format_exc())
        try:
            proj.save()
        except Exception:
            pass
        try:
            proj.close()
        except Exception:
            pass
    except Exception:
        log(u"!!! финальное открытие не удалось:")
        log(traceback.format_exc())

log(u"")
log(u"=== BUILD_BATCHES END ===")
try:
    system.exit()
except Exception:
    pass
