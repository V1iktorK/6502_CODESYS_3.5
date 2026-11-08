# -*- coding: utf-8 -*-
"""
gen_fetch.py -- FB_Fetch: STADIYA VYBORKI 6502 (pilot dekompozicii yadra).

Vyhod iz tupika s odnim gigantskim listom (sm. docs/05_...): yadro delitsya na
nezavisimye POU. Zdes pervyy iz nih.

FB_Fetch -- funkciya chetvertogo klasса cherez kontakty (kak prinyato v FBD):

  vhody :  PCs : WORD        -- schetchik komand na nachalo takta
  vyhody:  OPs, OP1, OP2 : BYTE  -- kod operacii i dva bajta operanda
           PC1, PC2     : WORD  -- PCs+1, PCs+2
           PCL, PCH     : BYTE  -- mladshiy/starshiy bajt PC2

Pamyat ne peredaetsya cherez kontakt (ona globalnaya po TZ): chtenie idet
napryamuyu iz GVL_MEM.Mem.

Dopolnitelno stroitsya FB_CorePilot -- kompozitnaya shema, gde EKZEMPLYAR
FB_Fetch podklyuchen kontaktami. Eto proveryaet vsyu arhitekturu
dekompozicii na malom ob"eme, prezhde chem perepisyvat vse 6 POU.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")

MEM = u"GVL_MEM"

INPUTS = [(u"PCs", u"WORD")]
OUTPUTS = [(u"OPs", u"BYTE"), (u"PC1", u"WORD"), (u"PC2", u"WORD")]

# Отдельный ПОУ для чтения операндов. Причина (конспект 2.5): внутри одного ПОУ
# чтение ячейки, записанной в этой же схеме, даёт СТАРОЕ значение. Поэтому адрес
# PC1/PC2 считается в FB_Fetch, а память по нему читает уже ДРУГОЙ ПОУ --
# в том же скане, но на следующем уровне композиции.
IN_OP = [(u"PC1", u"WORD"), (u"PC2", u"WORD")]
OUT_OP = [(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"PCL", u"BYTE"), (u"PCH", u"BYTE")]


def build_fetchop():
    """FB_FetchOp: байты операнда по уже вычисленным адресам PC1 / PC2."""
    s = Sheet(u"FB_FetchOp: чтение двух байт операнда")
    s.add_comment(u"OP1 := Mem[PC1];  OP2 := Mem[PC2];  PCL/PCH := байты PC2")
    s.assign(u"OP1", s.ref(MEM + u".Mem[PC1]", 0), 2)
    s.assign(u"OP2", s.ref(MEM + u".Mem[PC2]", 0), 2)
    pc2 = s.ref(u"PC2", 0)
    # Младший байт: результат AND имеет тип WORD, поэтому обязателен WORD_TO_BYTE
    # (иначе CODESYS пишет "Невозможно конвертировать тип 'UINT' в тип 'BYTE'").
    lo = s.blk(u"AND", [(u"IN1", pc2), (u"IN2", s.const(u"WORD#255", 2))], 3)
    s.assign(u"PCL", s.blk(u"WORD_TO_BYTE", [(u"IN", lo)], 4), 5)
    hi = s.blk(u"SHR", [(u"IN1", pc2), (u"IN2", s.const(u"WORD#8", 2))], 3)
    s.assign(u"PCH", s.blk(u"WORD_TO_BYTE", [(u"IN", hi)], 4), 5)
    return s


def build_fetch():
    s = Sheet(u"FB_Fetch: чтение кода операции и адресов операнда")
    s.add_comment(u"ВЫБОРКА: OP := Mem[PC];  PC1 := PC+1;  PC2 := PC+2")

    # ---- колонка 0: адреса следующ их байтов
    pcs = s.ref(u"PCs", 0)
    pc1 = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(u"WORD#1", 0))], 2, width=90)
    s.assign(u"PC1", pc1, 3)

    pc2 = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(u"WORD#2", 0))], 2, width=90, anchor=pc1)
    s.assign(u"PC2", pc2, 3)

    # ---- колонка 4: чтение кода операции по адресу PC
    op = s.ref(MEM + u".Mem[PCs]", 4)
    s.assign(u"OPs", op, 5)

    return s


def build_pilot():
    """Композитная схема: экземпляр FB_Fetch, подключённый контактами."""
    s = Sheet(u"FB_CorePilot: композиция стадии выборки (проверка архитектуры)")
    s.add_comment(u"Экземпляр FB_Fetch подключён контактами: PC -> FB, выходы -> GVL_CPU")

    pc = s.ref(u"GVL_CPU.PC", 0)
    inst = s.blk(u"FB_Fetch", [(u"PCs", pc)], 2, width=90, inst=u"Fetch")
    # у экземпляра несколько выходов -- каждый берём по имени
    s.assign(u"GVL_CPU.OP", inst, 6, src_pin=u"OPs")
    s.assign(u"GVL_CPU.PC1", inst, 6, src_pin=u"PC1")
    s.assign(u"GVL_CPU.PC2", inst, 6, src_pin=u"PC2")
    return s


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-16s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_fetch ===")

    sf = build_fetch()
    xf = pou_xml(u"FB_Fetch", u"functionBlock",
                 interface(inputs=INPUTS, outputs=OUTPUTS), [sf],
                 comment=u"Стадия выборки MOS 6502")
    write(u"FB_Fetch", xf)

    so = build_fetchop()
    xo = pou_xml(u"FB_FetchOp", u"functionBlock",
                 interface(inputs=IN_OP, outputs=OUT_OP), [so],
                 comment=u"Стадия выборки: байты операнда")
    write(u"FB_FetchOp", xo)

    sp = build_pilot()
    xp = pou_xml(u"FB_CorePilot", u"functionBlock", interface(locals_=[(u"Fetch", u"FB_Fetch")]), [sp],
                 comment=u"Пилот: композиция через экземпляр FB_Fetch")
    write(u"FB_CorePilot", xp)

    print(u"готово")


main()
