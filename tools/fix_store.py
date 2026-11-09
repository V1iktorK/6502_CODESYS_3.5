import io, re
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\build_full.py"
t = io.open(p, encoding="utf-8").read()
start = t.index('u"IF NOT Init THEN')
end = t.index('OUT := TRUE;")', start) + len('OUT := TRUE;")')
body = '''u"IF NOT Init THEN\\n\\tpB := ADR(GVL_MEM.Mem[0]);\\n\\tInit := TRUE;\\nEND_IF\\n"
            u"IF NOT DInit THEN\\n\\tpD := ADR(GVL_DISK.Disk);\\n\\tDInit := TRUE;\\nEND_IF\\n"
            u"IF En THEN\\n"
            u"\\tIF Addr >= 16#F000 AND Addr <= 16#F0FF THEN\\n\\t\\tGVL_IO.PortAddr := Addr;\\n\\t\\tGVL_IO.PortWr := Data;\\n"
            u"\\t\\tCASE Addr OF\\n"
            u"\\t\\t16#F000: GVL_IO.Io_Out := Data;\\n"
            u"\\t\\t16#F001: GVL_IO.IrqMask := Data;\\n"
            u"\\t\\t16#F002: GVL_IO.Ao0 := SHL(BYTE_TO_WORD(Data), 8) OR (GVL_IO.Ao0 AND 16#00FF);\\n"
            u"\\t\\t16#F003: GVL_IO.Ao0 := (GVL_IO.Ao0 AND 16#FF00) OR BYTE_TO_WORD(Data);\\n"
            u"\\t\\t16#F009: GVL_IO.Latch := 0;\\n"
            u"\\t\\t16#F010: GVL_DISK.Sector := (GVL_DISK.Sector AND 16#FF00) OR BYTE_TO_WORD(Data);\\n"
            u"\\t\\t16#F011: GVL_DISK.Sector := (GVL_DISK.Sector AND 16#00FF) OR SHL(BYTE_TO_WORD(Data), 8);\\n"
            u"\\t\\t16#F012: GVL_DISK.Offset := Data;\\n"
            u"\\t\\t16#F013:\\n\\t\\t\\tpS := pD + (GVL_DISK.Sector * 128 + BYTE_TO_WORD(GVL_DISK.Offset));\\n"
            u"\\t\\t\\tIF GVL_DISK.RdWr THEN\\n\\t\\t\\t\\tpS^ := Data;\\n\\t\\t\\tELSE\\n\\t\\t\\t\\tGVL_DISK.Data := pS^;\\n\\t\\t\\tEND_IF\\n"
            u"\\t\\tEND_CASE\\n"
            u"\\tELSE\\n\\t\\tpC := pB + Addr;\\n\\t\\tpC^ := Data;\\n\\tEND_IF\\n"
            u"END_IF\\n"
            u"IF HEN THEN\\n\\tpC := pB + HADR;\\n\\tpC^ := HDAT;\\nEND_IF\\n"
            u"IF GVL_CPU.RD_ADR >= 16#F000 AND GVL_CPU.RD_ADR <= 16#F0FF THEN\\n\\tCASE GVL_CPU.RD_ADR OF\\n"
            u"\\t16#F000: GVL_CPU.RD_VAL := GVL_IO.Io_In;\\n"
            u"\\t16#F002: GVL_CPU.RD_VAL := WORD_TO_BYTE(GVL_IO.Ai0);\\n"
            u"\\t16#F003: GVL_CPU.RD_VAL := WORD_TO_BYTE(SHR(GVL_IO.Ai0, 8));\\n"
            u"\\t16#F006: GVL_CPU.RD_VAL := GVL_IO.IrqMask;\\n"
            u"\\t16#F007: GVL_CPU.RD_VAL := GVL_IO.Latch;\\n"
            u"\\t16#F008: GVL_CPU.RD_VAL := GVL_IO.Tick;\\n"
            u"\\t16#F010: GVL_CPU.RD_VAL := WORD_TO_BYTE(GVL_DISK.Sector);\\n"
            u"\\t16#F011: GVL_CPU.RD_VAL := WORD_TO_BYTE(SHR(GVL_DISK.Sector, 8));\\n"
            u"\\t16#F012: GVL_CPU.RD_VAL := GVL_DISK.Offset;\\n"
            u"\\t16#F013: GVL_CPU.RD_VAL := GVL_DISK.Data;\\n"
            u"\\t16#F020: GVL_CPU.RD_VAL := GVL_IO.Key;\\n"
            u"\\tELSE\\n\\t\\tGVL_CPU.RD_VAL := GVL_IO.PortWr;\\n\\tEND_CASE\\n"
            u"ELSE\\n\\tGVL_CPU.RD_VAL := GVL_MEM.Mem[GVL_CPU.RD_ADR];\\nEND_IF\\n"
            u"OUT := TRUE;")'''
t = t[:start] + body + t[end:]
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("store body rewritten")
