# -*- coding: utf-8 -*-
"""gen_memstore.py -- FB_MemStore: zapis' v emuliruemuyu RAM.

ВЫНУЖДЕННОЕ, ДОКУМЕНТИРОВАННОЕ ОТСТУПЛЕНИЕ ОТ "ТОЛЬКО FBD".
Zapis' v massiv po VYCHISLYAEMOMU indeksu v etoy srede molcha teryaetsya:
proverены pyat' form (vlozhennoe POU, programma, lokalnyy indeks, vhodnoy
pin, ukazatel) -- vo vseh sluchayah kompilyaciya chistaya, znachenie ne
pojavlyaetsya (pravilo 2.4 konspekta). Bez zapisi v RAM nevozmozhny ni stek,
ni STA/STX/STY, ni disk CP/M.

Poetomu odna kroshechnaya POU na ST delaet TOLKO odin operator --
Mem[Adr] := Dat. Vsya logika processorа (deshifrator, ALU, adresaciya,
stack, flagi, kompoziciya) ostaetsya na FBD.
"""
import io
import os

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")

XML = u'''<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
<fileHeader companyName="" productName="CODESYS" productVersion="CODESYS V3.5 SP17 Patch 3" creationDateTime="2026-01-01T00:00:00" />
<contentHeader name="Emu6502"><coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo></contentHeader>
<types><dataTypes /><pous>
<pou name="FB_MemStore" pouType="functionBlock">
<interface>
<inputVars>
<variable name="Adr"><type><WORD /></type></variable>
<variable name="Dat"><type><BYTE /></type></variable>
<variable name="En"><type><BOOL /></type></variable>
</inputVars>
<outputVars>
<variable name="OUT"><type><BOOL /></type></variable>
</outputVars>
</interface>
<body>
<ST><xhtml xmlns="http://www.w3.org/1999/xhtml">IF En THEN
	GVL_MEM.Mem[Adr] := Dat;
END_IF
OUT := TRUE;</xhtml></ST>
</body>
<addData />
</pou>
</pous></types>
<instances><configurations /></instances>
</project>
'''


def main():
    print(u"=== gen_memstore ===")
    p = os.path.join(OUT, u"FB_MemStore.xml")
    with io.open(p, "wb") as f:
        f.write(XML.encode("utf-8"))
    print(u"  FB_MemStore  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
