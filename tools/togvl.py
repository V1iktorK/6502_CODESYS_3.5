# -*- coding: utf-8 -*-
"""
togvl.py -- preobrazovanie POU-stepeney: VYHODY -> zapis v GVL_CPU.

Pochemu: CODESYS ne prinimaet vybor imennovannogo vyhoda ekzemplyara.
Pri svyazi "vyhod ekzemplyara -> peremennaya" on vozvrashchaet oshibku
    Идентификатор 'OUT' не задан / 'Fch.OUT'
to est ignoriruet formalParameter u vyhoda i bеret pervyy vhod pod imenem OUT.

Reshenie: u stupeney net vyhodnyh kontaktov. Kazhdaya stupen sama zapisyvaet
svoi rezultaty v GVL_CPU (ploskost imen zadana TZ), a kompoziciya prosto
vyzyvaet stupeni po poryadku. Vhody (inputVars) ostayutsya -- oni rabotayut.

Skript beret spisok POU, dlya kazhdogo:
  1) chitaet imena vyhodnyh peremennyh;
  2) v sheme menyaet <expression>ИМЯ</expression> na <expression>GVL_CPU.ИМЯ</expression>;
  3) udalyaet sekciyu <outputVars> iz interfejsa.
"""
import io
import os
import re
import sys

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")

TARGETS = [
    u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"FB_WriteBack",
    u"SL_C1A", u"SL_C1B", u"SL_YW", u"SL_IND2", u"SL_INDP", u"SL_RELA",
    u"SL_RELC", u"SL_BRK", u"SL_SELECT12", u"SL_WDATA2",
    u"SL_STK1", u"SL_STK2", u"SL_STK3", u"SL_STK4", u"SL_SPSEL",
    u"SL_ADV", u"SL_JRET", u"SL_BRNE", u"SL_BRN2", u"SL_PCSEL",
]


def convert(name):
    path = os.path.join(PLCOPEN, u"%s.xml" % name)
    text = io.open(path, "rb").read().decode("utf-8")

    m = re.search(u'<outputVars>(.*?)</outputVars>', text, re.S)
    if not m:
        return None
    all_outs = re.findall(u'<variable name="([^"]+)">', m.group(1))
    # OUT -- служебный контактный выход: он ОСТАЁТСЯ в объявлении и НЕ
    # переводится в GVL_CPU. Именно его читает композиция, и только благодаря
    # этому чтению CODESYS исполняет тело ступени (правило 3 конспекта).
    outs = [o for o in all_outs if o != u"OUT"]
    kept = [o for o in all_outs if o == u"OUT"]
    if not all_outs:
        return None

    new = text
    for o in outs:
        new = new.replace(u'<expression>%s</expression>' % o,
                          u'<expression>GVL_CPU.%s</expression>' % o)
    # удаляем секцию выходных переменных, но сохраняем служебный OUT
    if kept:
        section = u'<outputVars>' + u''.join(
            u'<variable name="OUT"><type><BOOL /></type></variable>' for _ in kept
        ) + u'</outputVars>'
    else:
        section = u''
    new = new[:m.start()] + section + new[m.end():]

    o = io.open(path, "wb")
    o.write(new.encode("utf-8"))
    o.close()
    return outs if not kept else (outs + [u"OUT"])


def main():
    print(u"=== togvl ===")
    total = 0
    for name in TARGETS:
        outs = convert(name)
        if outs is None:
            print(u"  %-16s пропущен (нет выходов)" % name)
            continue
        total += len(outs)
        print(u"  %-16s выходов %d -> GVL_CPU" % (name, len(outs)))
    print(u"всего выходов переведено на GVL: %d" % total)


if __name__ == "__main__":
    main()
