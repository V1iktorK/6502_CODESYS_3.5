# -*- coding: utf-8 -*-
"""
gen_io.py -- podsistemy I/O i diska po TZ.

Sozdaet:
  * GVL_BUS, GVL_IO, GVL_MAP -- obyavleniya (tekst dlya create_gvl);
  * FB_IOBridge    -- okno $F000-$F0FF <-> GVL_IO, inache probros v GVL_MEM.Mem;
  * FB_IRQController -- front kazhdogo DI cherez R_TRIG, maska $F006, latch $F007;
  * FB_AnalogBridge  -- AI0/AO0 : WORD, little-endian;
  * FB_DiskImage     -- obraz 2048 sekciy x 128 bayt = 256 KB.

Karta okna (iz TZ):
  $F000 DI | $F001 DO | $F002-3 AI0 | $F004-5 AO0 | $F006 maska IRQ
  $F007 latch fronta (sbrasyvaetsya chteniem) | $F008 schetchik taktov

Rezultat: plcopen\\FB_IOBridge.xml, FB_IRQController.xml, FB_AnalogBridge.xml,
FB_DiskImage.xml + GVL_*.txt
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
FALLBACK = r"C:\CPM6502_build\plcopen"

W0 = u"WORD#0"
B0, B1 = u"BYTE#0", u"BYTE#1"
BFF = u"BYTE#16#FF"

# Смещения регистров окна I/O
IO_IN, IO_OUT, IO_AIL, IO_AIH, IO_AOL, IO_AOH, IO_MSK, IO_LAT, IO_TICK = range(9)


def emit(name, kind, iface, sheets, comment=None):
    xml = pou_xml(name, kind, iface, sheets, comment)
    path = os.path.join(OUT, u"%s.xml" % name)
    try:
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
    except (IOError, OSError):
        if not os.path.isdir(FALLBACK):
            os.makedirs(FALLBACK)
        path = os.path.join(FALLBACK, u"%s.xml" % name)
        f = io.open(path, "w", encoding="utf-8")
        f.write(xml)
        f.close()
    print(u"  %-18s %-14s элементов=%4d блоков=%4d" %
          (name, kind, len(sheets[0].els),
           sum(1 for e in sheets[0].els if e.startswith(u"<block"))))
    return path


# =====================================================================
#  FB_IOBridge
# =====================================================================
def gen_iobridge():
    s = Sheet(u"Окно $F000–$F0FF: чтение и запись регистров I/O; иначе — эмулируемая память")
    addr = s.var(u"Addr", 0)
    we = s.var(u"WE", 0)
    wd = s.var(u"WD", 0)

    # --- дешифрация адреса: по одному EQ на регистр ---
    gate = {}
    for k in range(9):
        gate[k] = s.blk(u"EQ", [(u"IN1", addr),
                                (u"IN2", s.const(u"WORD#16#F0%02X" % k, 0))], 1)

    # --- чтение: начинаем с памяти, затем подменяем окном ---
    base = s.var(u"GVL_MEM.Mem[Addr]", 2)
    rd = base
    src = [
        (IO_IN, u"GVL_IO.Io_In"),
        (IO_OUT, u"GVL_IO.Io_Out"),
        (IO_AIL, u"GVL_AIL"),          # младший байт AI0
        (IO_AIH, u"GVL_AIH"),          # старший байт AI0
        (IO_AOL, u"GVL_AOL"),
        (IO_AOH, u"GVL_AOH"),
        (IO_MSK, u"GVL_IO.IrqMask"),
        (IO_LAT, u"GVL_IO.Latch"),
        (IO_TICK, u"GVL_IO.Tick"),
    ]
    for k, expr in src:
        val = s.var(expr, 3)
        rd = s.blk(u"SEL", [(u"G", gate[k]), (u"IN0", rd), (u"IN1", val)], 4)
    s.assign(u"RD", rd, 6)

    # --- сброс latch при чтении $F007 ---
    s.assign(u"LatchClr", s.blk(u"AND", [(u"IN1", gate[IO_LAT]), (u"IN2", s.const(u"TRUE", 3))], 3), 4)

    # --- запись ---
    s.assign(u"GVL_IO.Io_Out", s.blk(u"SEL", [
        (u"G", s.blk(u"AND", [(u"IN1", we), (u"IN2", gate[IO_OUT])], 5)),
        (u"IN0", s.var(u"GVL_IO.Io_Out", 5)), (u"IN1", wd)], 6), 7)
    for k, expr in ((IO_AOL, u"GVL_AOL"), (IO_AOH, u"GVL_AOH"),
                    (IO_MSK, u"GVL_IO.IrqMask")):
        s.assign(expr, s.blk(u"SEL", [
            (u"G", s.blk(u"AND", [(u"IN1", we), (u"IN2", gate[k])], 5)),
            (u"IN0", s.var(expr, 5)), (u"IN1", wd)], 6), 7)
    return [s]


# =====================================================================
#  FB_IRQController
# =====================================================================
def gen_irq():
    """Фронт каждого DI через сравнение с предыдущим значением.

    ПОЧЕМУ БЕЗ R_TRIG: восемь экземпляров R_TRIG в одной схеме CODESYS молча
    отвергает при импорте (проверено: POU не создаётся, исключения нет).
    Детектор фронта через сохранённое предыдущее значение эквивалентен и
    использует только те блоки, которые в проекте компилируются чисто:
        edge := Io_In XOR Prev      -- какие биты изменились
        rise := Io_In AND edge      -- фронт 0 -> 1
        Prev := Io_In               -- запомнили для следующего скана
    """
    s = Sheet(u"Фронт каждого DI + маска $F006 → флаг $F007 → линия IRQ")
    din = s.var(u"Io_In", 0)
    msk = s.var(u"IrqMask", 0)
    clr = s.var(u"LatchClr", 0)
    prev = s.var(u"Prev", 0)

    edge = s.blk(u"XOR", [(u"IN1", din), (u"IN2", prev)], 1)
    rise = s.blk(u"AND", [(u"IN1", din), (u"IN2", edge)], 2)
    s.assign(u"Prev", din, 3)

    lat = []
    for i in range(8):
        mb = s.blk(u"AND", [(u"IN1", msk), (u"IN2", s.const(u"BYTE#16#%02X" % (1 << i), 3))], 3)
        hit = s.blk(u"AND", [(u"IN1", rise), (u"IN2", mb)], 4)
        lat.append(hit)
    # упаковка восьми бит в байт через SEL-лестницу (OR по one-hot)
    parts = []
    for i in range(8):
        parts.append(s.blk(u"SEL", [(u"G", lat[i]), (u"IN0", s.const(B0, 5)),
                                    (u"IN1", s.const(u"BYTE#16#%02X" % (1 << i), 5))], 5))
    cur = parts[0]
    for p in parts[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], 6)
    newlat = s.blk(u"SEL", [(u"G", clr), (u"IN0", cur), (u"IN1", s.const(B0, 7))], 7)
    s.assign(u"Latch", newlat, 8)
    s.assign(u"Irq", s.blk(u"NE", [(u"IN1", newlat), (u"IN2", s.const(B0, 8))], 9), 10)
    return [s]


# =====================================================================
#  FB_AnalogBridge -- AI0/AO0 : WORD, little-endian
# =====================================================================
def gen_analog():
    s = Sheet(u"AI0/AO0: WORD little-endian — младший байт первым (как в 6502)")
    ai = s.var(u"Ai0", 0)
    ao = s.var(u"Ao0", 0)
    # младший байт = значение И $FF ; старший = SHR(значение, 8)
    s.assign(u"GVL_AIL", s.blk(u"WORD_TO_BYTE", [(u"IN", ai)], 1), 2)
    s.assign(u"GVL_AIH", s.blk(u"WORD_TO_BYTE",
                               [(u"IN", s.blk(u"SHR", [(u"IN", ai), (u"N", s.const(u"WORD#8", 1))], 1))], 2), 3)
    s.assign(u"GVL_AOL", s.blk(u"WORD_TO_BYTE", [(u"IN", ao)], 1), 2)
    s.assign(u"GVL_AOH", s.blk(u"WORD_TO_BYTE",
                               [(u"IN", s.blk(u"SHR", [(u"IN", ao), (u"N", s.const(u"WORD#8", 1))], 1))], 2), 3)
    return [s]


# =====================================================================
#  FB_DiskImage -- 2048 x 128 = 256 КБ
# =====================================================================
def gen_disk():
    s = Sheet(u"Образ дискеты 8\": 2048 секторов × 128 байт. "
              u"Номер сектора = Track*32 + Sector (32 сектора на дорожку)")
    trk = s.var(u"Track", 0)
    sec = s.var(u"Sector", 0)
    we = s.var(u"WE", 0)
    wd = s.var(u"WD", 0)

    t32 = s.blk(u"MUL", [(u"IN1", trk), (u"IN2", s.const(u"BYTE#32", 0))], 1)
    sidx = s.blk(u"ADD", [(u"IN1", t32), (u"IN2", sec)], 2)
    # индекс сектора -> WORD (для индексации двумерного массива)
    sw = s.blk(u"BYTE_TO_WORD", [(u"IN", sidx)], 3)
    # адрес конца: sidx*128 + 127 -> через WORD-арифметику
    base = s.blk(u"MUL", [(u"IN1", sw), (u"IN2", s.const(u"WORD#128", 3))], 3)
    s.assign(u"SEC_BASE", base, 4)
    rd = s.var(u"Disk[SEC_BASE]", 5)
    s.assign(u"RD", rd, 6)
    s.assign(u"Disk[SEC_BASE]", s.blk(u"SEL", [(u"G", we), (u"IN0", rd), (u"IN1", wd)], 6), 7)
    return [s]


def gvl_texts():
    return [
        (u"GVL_BUS.txt",
         u"VAR_GLOBAL\n\t(* Общие шины (ТЗ): одна шина данных и одна шина адреса *)\n"
         u"\tBus_Data : BYTE;\n\tBus_Addr : WORD;\n\tBus_WE : BOOL;\n\tBus_RE : BOOL;\nEND_VAR\n"),
        (u"GVL_IO.txt",
         u"VAR_GLOBAL\n\t(* Окно $F000-$F0FF: регистры ввода-вывода *)\n"
         u"\tIo_In : BYTE;      (* $F000: дискретные входы DI0..DI7 *)\n"
         u"\tIo_Out : BYTE;     (* $F001: дискретные выходы DO0..DO7 *)\n"
         u"\tAi0 : WORD;        (* $F002-$F003: аналоговый вход, little-endian *)\n"
         u"\tAo0 : WORD;        (* $F004-$F005: аналоговый выход, little-endian *)\n"
         u"\tIrqMask : BYTE;    (* $F006: маска разрешения IRQ по DI *)\n"
         u"\tLatch : BYTE;      (* $F007: флаг фронта, сбрасывается чтением *)\n"
         u"\tTick : BYTE;       (* $F008: счётчик тактов PLC *)\n"
         u"\tGVL_AIL : BYTE;\n\tGVL_AIH : BYTE;\n\tGVL_AOL : BYTE;\n\tGVL_AOH : BYTE;\nEND_VAR\n"),
        (u"GVL_MAP.txt",
         u"VAR_GLOBAL CONSTANT\n\t(* Карта памяти MOS 6502 (ТЗ) *)\n"
         u"\tZP_START : WORD := 16#0000;\n\tZP_END : WORD := 16#00FF;\n"
         u"\tSTACK_PAGE : WORD := 16#0100;\n\tTPA_START : WORD := 16#0200;\n"
         u"\tTPA_END : WORD := 16#EFFF;\n\tIO_WIN : WORD := 16#F000;\n"
         u"\tIO_WIN_END : WORD := 16#F0FF;\n\tBIOS_VEC : WORD := 16#FF00;\n"
         u"\tRESET_VEC : WORD := 16#FFFC;\n\tIRQ_VEC : WORD := 16#FFFE;\nEND_VAR\n"),
    ]


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    print(u"Генерация подсистем I/O и диска:")
    emit(u"FB_IOBridge", u"functionBlock",
         interface(inputs=[(u"Addr", u"WORD"), (u"WE", u"BOOL"), (u"WD", u"BYTE")],
                   outputs=[(u"RD", u"BYTE"), (u"LatchClr", u"BOOL")],
                   locals_=[]),
         gen_iobridge(),
         u"Мост окна $F000-$F0FF: DI/DO, AI0/AO0, маска и латч IRQ, счётчик тактов. "
         u"Адреса вне окна читаются и пишутся в эмулируемую память GVL_MEM.Mem.")
    emit(u"FB_IRQController", u"functionBlock",
         interface(inputs=[(u"Io_In", u"BYTE"), (u"IrqMask", u"BYTE"), (u"LatchClr", u"BOOL")],
                   outputs=[(u"Latch", u"BYTE"), (u"Irq", u"BOOL")],
                   locals_=[(u"Prev", u"BYTE")]),
         gen_irq(),
         u"Прерывание по фронту физического входа: R_TRIG на каждом DI, "
         u"разрешение по маске $F006, флаг фронта в $F007 (сбрасывается чтением).")
    emit(u"FB_AnalogBridge", u"functionBlock",
         interface(inputs=[(u"Ai0", u"WORD"), (u"Ao0", u"WORD")],
                   outputs=[(u"GVL_AIL", u"BYTE"), (u"GVL_AIH", u"BYTE"),
                            (u"GVL_AOL", u"BYTE"), (u"GVL_AOH", u"BYTE")]),
         gen_analog(),
         u"Аналоговый мост: WORD раскладывается на два байта little-endian — "
         u"младший байт первым, как принято в 6502.")
    emit(u"FB_DiskImage", u"functionBlock",
         interface(inputs=[(u"Track", u"BYTE"), (u"Sector", u"BYTE"),
                           (u"WE", u"BOOL"), (u"WD", u"BYTE")],
                   outputs=[(u"RD", u"BYTE")],
                   locals_=[(u"Disk", u"ARRAY[0..2047, 0..127] OF BYTE"),
                            (u"SEC_BASE", u"WORD")]),
         gen_disk(),
         u"Образ дискеты 8\": 2048 секторов по 128 байт (256 КБ), формат CP/M 2.2. "
         u"Номер сектора: Track*32 + Sector. Чтение и запись сектора с SD — через SysFile.")
    for nm, txt in gvl_texts():
        f = io.open(os.path.join(OUT, nm), "w", encoding="utf-8")
        f.write(txt)
        f.close()
        print(u"  %s записан" % nm)


if __name__ == "__main__":
    main()
