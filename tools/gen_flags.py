# -*- coding: utf-8 -*-
"""
gen_flags.py -- registr P konveyerom korotkih stupeney.

Pochemu ne odnim POU: pravilo 2.1 (fan-out) zastavlyaet dvazhdy chitat' bayt,
i kazhdoe takoe mesto KLONIRUET vsyu vhodnuyu cepochku. Na semi bitah
poluchalos' 2^7 kopiy vethvey, i CODESYS takuyu skhemu ne sobiral (zapis' P
ne privodila ni k chemu).

Reshenie: kazhdyy bit -- otdel'naya kroshechnaya stupen'. Stupeni idut
posledovatel'no v sloe FB_CPU_AluFlags i peredayut sostoyanie cherez
GVL_CPU.P_WORK. Vidimost' zapisi GVL dlya sleduyuschego POU v TOM ZHE skane
proverena otdel'no (test_pipe), poetoму registr P sobiраetsya za odin takt.

Forma kazhdoy stupeni (chitaetsya tolko VHODNAYA peremennaya, poetoму
klonirovanie bezopasno):
    P_WORK := uslovie ? novoe-znachenie : P_WORK
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
CPU = u"GVL_CPU"
P = CPU + u".P_WORK"


def B(m):
    return u"BYTE#16#%02X" % m


def orlist(s, names, col):
    """OR из нескольких булевых сигналов (по имени)."""
    ids = [s.ref(n, col) for n in names]
    cur = ids[0]
    for nid in ids[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", nid)], col + 1)
    return cur


def andlist(s, names, col):
    ids = [s.ref(n, col) for n in names]
    cur = ids[0]
    for nid in ids[1:]:
        cur = s.blk(u"AND", [(u"IN1", cur), (u"IN2", nid)], col + 1)
    return cur


def stage(name, cmt, keep, value, inputs, src=P, dst=P):
    """dst := keep ? value(src) : src.

    keep -- список имён BOOL-сигналов, объединяемых по ИЛИ (любая из причин
    обновить бит). Всё это дополнительно умножается по И на GVL_CPU.Enable:
    пока такт не разрешён (Run=FALSE / нет пошагового импульса), регистр P
    меняться не должен. Без этого бит B защёлкивался на самом первом скане
    (в памяти нули, код $00 = BRK, а BRK ставит B), и дальше P был неверным
    до конца сессии.
    """
    s = Sheet(name)
    s.add_comment(cmt)
    p = s.ref(src, 0)
    v = value(s, p)
    cond = s.blk(u"AND", [(u"IN1", s.ref(CPU + u".Enable", 1)),
                          (u"IN2", orlist(s, list(keep), 2))], 4)
    r = s.blk(u"SEL", [(u"G", cond), (u"IN0", p), (u"IN1", v)], 9)
    s.assign(dst, r, 11)
    return s, inputs


def setform(cond, mask, others_clear):
    """Собрать «бит mask по cond, остальные биты сохранить»."""
    def f(s, p):
        cleared = s.blk(u"AND", [(u"IN1", p), (u"IN2", s.const(B(others_clear), 4))], 4)
        bitv = s.blk(u"SEL", [(u"G", s.ref(cond, 0)), (u"IN0", s.const(B(0), 5)),
                              (u"IN1", s.const(B(mask), 5))], 5)
        return s.blk(u"OR", [(u"IN1", cleared), (u"IN2", bitv)], 6)
    return f


def main():
    print(u"=== gen_flags ===")
    made = []

    # --- NZF: откуда берутся флаги N и Z.
    # Флаги N/Z на 6502 -- это свойство ЗАПИСЫВАЕМОГО значения, а не результата
    # АЛУ: у TAX/TAY/TXA/TYA/PLA и у загрузок АЛУ вообще не участвует
    # (ALU_R там = 0 + мусор операнда), поэтому Z ставился ложно. Отдельная
    # ступень считает N_F2/Z_F2 из GVL_CPU.REG_WR -- значения, которое реально
    # уходит в регистр.
    sn = Sheet(u"SL_NZF")
    sn.add_comment(u"N_F2 := старший бит REG_WR;  Z_F2 := REG_WR = 0")
    rw = sn.ref(CPU + u".REG_WR", 0)
    sn.assign(CPU + u".N_F2",
              sn.blk(u"NE", [(u"IN1", sn.blk(u"AND", [(u"IN1", rw),
                                                      (u"IN2", sn.const(B(0x80), 2))], 2)),
                             (u"IN2", sn.const(B(0), 2))], 3), 4)
    sn.assign(CPU + u".Z_F2",
              sn.blk(u"EQ", [(u"IN1", sn.ref(CPU + u".REG_WR", 4)),
                             (u"IN2", sn.const(B(0), 4))], 5), 6)
    made.append((u"SL_NZF", sn, []))

    # --- VSEL: источник флага V (при вычитании -- V_SUB, иначе V_ADD).
    # Отдельная ступень, потому что выбор должен быть виден следующей ступени
    # через GVL, а не вычисляться в том же ПОУ (правило 2.5).
    sv = Sheet(u"SL_VSEL: источник флага V")
    sv.add_comment(u"VSEL := F_SUB ? V_SUB : V_ADD")
    sv.assign(CPU + u".VSEL",
              sv.blk(u"SEL", [(u"G", sv.ref(u"GVL_CPU.F_SUB", 0)),
                              (u"IN0", sv.ref(u"GVL_CPU.V_ADD", 0)),
                              (u"IN1", sv.ref(u"GVL_CPU.V_SUB", 0))], 2), 3)
    made.append((u"SL_VSEL", sv, []))

    # --- N (бит 7)
    # ВАЖНО: первая ступень читает сам регистр P, а не P_WORK, и пишет P_WORK.
    # Иначе запись «P_WORK := P» и её же чтение оказались бы в одном ПОУ, а
    # CODESYS в этом случае отдаёт старое значение (правило 2.5).
    s, ins = stage(u"SL_FLG_N", u"P_WORK := SET_NZ ? (N в N_F) : N",
                   [u"SET_NZ"], setform(u"N_F2", 0x80, 0x7F),
                   [(u"SET_NZ", u"BOOL"), (u"N_F2", u"BOOL")],
                   src=CPU + u".P")
    made.append((u"SL_FLG_N", s, ins))

    # --- Z (бит 1)
    s, ins = stage(u"SL_FLG_Z", u"Z := SET_NZ ? Z_F : Z",
                   [u"SET_NZ"], setform(u"Z_F2", 0x02, 0xFD),
                   [(u"SET_NZ", u"BOOL"), (u"Z_F2", u"BOOL")])
    made.append((u"SL_FLG_Z", s, ins))

    # --- C (бит 0): вычисленный перенос, затем CLC (снять) и SEC (поставить)
    def cval(s, p):
        cleared = s.blk(u"AND", [(u"IN1", p), (u"IN2", s.const(B(0xFE), 4))], 4)
        bitv = s.blk(u"SEL", [(u"G", s.ref(u"CARRY", 0)), (u"IN0", s.const(B(0), 5)),
                              (u"IN1", s.const(B(0x01), 5))], 5)
        r = s.blk(u"OR", [(u"IN1", cleared), (u"IN2", bitv)], 6)
        r = s.blk(u"SEL", [(u"G", s.ref(u"CMD_CLC", 0)),
                           (u"IN0", r),
                           (u"IN1", s.blk(u"AND", [(u"IN1", r),
                                                   (u"IN2", s.const(B(0xFE), 6))], 7))], 7)
        r = s.blk(u"SEL", [(u"G", s.ref(u"CMD_SEC", 0)),
                           (u"IN0", r),
                           (u"IN1", s.blk(u"OR", [(u"IN1", r),
                                                  (u"IN2", s.const(B(0x01), 7))], 8))], 8)
        return r
    s, ins = stage(u"SL_FLG_C", u"C := SET_C ? CARRY : C; CLC снимает, SEC ставит",
                   [u"SET_C", u"CMD_CLC", u"CMD_SEC"], cval,
                   [(u"SET_C", u"BOOL"), (u"CARRY", u"BOOL"),
                    (u"CMD_CLC", u"BOOL"), (u"CMD_SEC", u"BOOL")])
    made.append((u"SL_FLG_C", s, ins))

    # --- V (бит 6)
    s, ins = stage(u"SL_FLG_V", u"V := SET_V ? V(АЛУ) : V",
                   [u"SET_V"], setform(u"VSEL", 0x40, 0xBF),
                   [(u"SET_V", u"BOOL")])
    made.append((u"SL_FLG_V", s, ins))

    # --- I (бит 2): SEI ставит, CLI снимает
    def ival(s, p):
        r = s.blk(u"SEL", [(u"G", s.ref(u"CMD_SEI", 0)), (u"IN0", p),
                           (u"IN1", s.blk(u"OR", [(u"IN1", p),
                                                  (u"IN2", s.const(B(0x04), 5))], 5))], 6)
        r = s.blk(u"SEL", [(u"G", s.ref(u"CMD_CLI", 0)), (u"IN0", r),
                           (u"IN1", s.blk(u"AND", [(u"IN1", r),
                                                   (u"IN2", s.const(B(0xFB), 6))], 7))], 7)
        return r
    s, ins = stage(u"SL_FLG_I", u"I: SEI ставит, CLI снимает",
                   [u"CMD_SEI", u"CMD_CLI"], ival,
                   [(u"CMD_SEI", u"BOOL"), (u"CMD_CLI", u"BOOL")])
    made.append((u"SL_FLG_I", s, ins))

    # --- B (бит 4)
    s, ins = stage(u"SL_FLG_B", u"B := SET_B ? 1 : B", [u"SET_B"],
                   lambda s, p: s.blk(u"OR", [(u"IN1", p),
                                              (u"IN2", s.const(B(0x10), 5))], 5),
                   [(u"SET_B", u"BOOL")])
    made.append((u"SL_FLG_B", s, ins))

    # --- бит 5 всегда 1 (без условия)
    s5 = Sheet(u"SL_FLG5")
    s5.add_comment(u"P_WORK := P_WORK OR 16#20 -- бит 5 всегда единица")
    s5.assign(P, s5.blk(u"OR", [(u"IN1", s5.ref(P, 0)),
                                (u"IN2", s5.const(B(0x20), 1))], 2), 3)
    made.append((u"SL_FLG5", s5, []))

    for nm, sheet, ins in made:
        x = pou_xml(nm, u"functionBlock", interface(inputs=ins), [sheet],
                    comment=u"ступень регистра P")
        p = os.path.join(OUT, u"%s.xml" % nm)
        with io.open(p, "wb") as f:
            f.write(x.encode("utf-8"))
        print(u"  %-10s %8d байт, входы: %s"
              % (nm, os.path.getsize(p), u", ".join(i for i, _t in ins) or u"(нет)"))
    print(u"готово")


if __name__ == u"__main__":
    main()
