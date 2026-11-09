import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\run_io.py"
t = io.open(p, encoding="utf-8").read()
t = t.replace('''    return """
ORG $0200
        LDA %s
        STA %s
        HLT
""" % (where, port)''', '''    return """
ORG $0200
        LDA %s
        STA %s
        HLT
""" % (where, port)


def imm_lda(val):
    return "LDA #$%02X" % val''')
t = t.replace('C("T-IO-2 дискретный выход", echo("BYTE#16#A5", "$F000"),',
              'C("T-IO-2 дискретный выход", echo(imm_lda(0xA5), "$F000"),')
t = t.replace('C("T-IO-6 маска прерываний", echo("BYTE#16#0F", "$F001"),',
              'C("T-IO-6 маска прерываний", echo(imm_lda(0x0F), "$F001"),')
# ochistka okna programmy pered kazhdym keysom
t = t.replace('''            wr(u"GVL_IO.ConPtr", u"16#00")''',
              '''            wr(u"GVL_IO.ConPtr", u"16#00")
            for a in range(0x0200, 0x0280):
                wr(u"GVL_CPU.HADR", u"16#%04X" % a)
                wr(u"GVL_CPU.HDAT", u"16#00")
                wr(u"GVL_CPU.HEN", u"TRUE")
                time.sleep(0.01)
                wr(u"GVL_CPU.HEN", u"FALSE")''')
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("исправлено")
