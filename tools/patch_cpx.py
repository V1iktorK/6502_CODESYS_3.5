import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\opcodes.py"
t = io.open(p, encoding="utf-8").read()
anchor = '        elif mn in (u"ADC", u"SBC", u"CMP"):'
if "CPX" in t and 'mn in (u"CPX"' in t:
    print("уже есть")
else:
    add = ('        elif mn in (u"CPX", u"CPY"):\n'
           '            # CPX/CPY -- sravnenie indeksnogo registra s operandom.\n'
           '            # RAN\'SHE ih ne bylo v tablitse voobshche: Z/C ne vystavlyalis,\n'
           '            # i cikl "CPX #5 / BNE loop" zazikal navsegda.\n'
           '            set_(op, SET_NZ=True, SET_C=True, SRC=SRC_ALU,\n'
           '                 ALU_A=(ALU_X if mn == u"CPX" else ALU_Y), ALU_B=ALU_B_MDR,\n'
           '                 F_CMP=True, CIN_FORCE=True)\n')
    t = t.replace(anchor, add + anchor, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    print("CPX/CPY добавлены в build_effects")
