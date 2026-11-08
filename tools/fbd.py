# -*- coding: utf-8 -*-
"""
fbd.py -- построитель FBD-схем и упаковка их в PLCopen XML (tc6_0200).

Зачем: рисовать сотни блоков руками в CODESYS — недели. Здесь схема описывается
кодом на Python: колонки слева-направо, блоки с пинами, связи по идентификаторам.
На выходе — XML, который CODESYS импортирует в виде нормальной редактируемой
FBD-схемы (со всеми блоками, проводами и координатами).

Терминология раскладки:
  колонка (col) — вертикальная полоса листа, X = 40 + col * COLW
  внутри колонки элементы автоматически укладываются сверху вниз
"""

import re

COLW = 260          # шаг колонок по X
ROWGAP = 20         # вертикальный зазор между элементами
TOPY = 40           # верхняя граница листа
PINSTEP = 20        # шаг пинов на блоке по вертикали

# ГЛОБАЛЬНЫЙ счетчик localId. Нужен потому, что CODESYS допускает в <body>
# только ОДИН элемент <FBD>, поэтому несколько сетей одного POU сливаются в
# один лист -- и их идентификаторы обязаны быть уникальны между собой.
_ID = [0]
# Явный порядок исполнения блоков (атрибут executionOrderId). Флаг вынесен
# наружу, потому что это единственный подозреваемый атрибут, который может
# объяснять молчаливый отказ CODESYS создавать часть POU.
USE_EXECUTION_ORDER = True

# Настоящие имена ВЫХОДНЫХ контактов наших собственных ПОУ. У стандартных блоков
# (ADD, SEL, EQ, ...) выход называется OUT, у функций проекта -- иначе. Если
# объявить в схеме несуществующий контакт, CODESYS выдаёт
# "Идентификатор 'OUT' не задан" и не типизирует выражение.
OUT_PIN = {
    u"F_Join16": u"Q",
    u"F_UnpackByte": u"B",
    u"F_PackByte": u"OUT",
    u"F_Add16": u"Q_LO",
    u"F_Split16": u"LO",
}

# Разрыв связей компараторов именованными переменными (Sheet.gate).
#
# ОПЫТ probe_add16 и партийных сборок: единого правила нет.
#   * с разрывом создаются FB_Decoder6502 (524 блока) и FB_PC_Update;
#   * без разрыва создаётся F_Add16, но теряются эти две.
# Поэтому режим включён глобально (крупные схемы важнее), а для F_Add16
# он отключается точечно прямо в генераторе.
USE_WRAP_CMP = True


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


# ======================================================================
#  Булева логика через SEL
#
#  Экспериментально установлено (см. docs/05_ТЕХНИЧЕСКИЕ_ЗАМЕТКИ_ИМПОРТА.md):
#  POU, где блоки OR/AND соединяют ВЫХОДЫ других блоков типа BOOL, CODESYS
#  молча не создаёт при импорте -- без исключения, детерминированно и
#  независимо от порядка импорта. При этом OR над BYTE (дерево суммирования
#  в F_PackByte) работает штатно, а SEL работает всегда.
#
#  Поэтому вся булева логика строится на SEL, который проверен:
#      OR (a,b) = SEL(a, b, TRUE)
#      AND(a,b) = SEL(a, FALSE, b)
# ======================================================================
def or_bool(s, a, b, col):
    return s.blk(u"SEL", [(u"G", a), (u"IN0", b), (u"IN1", s.const(u"TRUE", col))], col)


def and_bool(s, a, b, col):
    return s.blk(u"SEL", [(u"G", a), (u"IN0", s.const(u"FALSE", col)), (u"IN1", b)], col)


def or_tree_bool(s, ids, col):
    """Дерево OR для BOOL, собранное на SEL."""
    ids = [i for i in ids if i is not None]
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    cur = list(ids)
    c = col
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur) - 1, 2):
            nxt.append(or_bool(s, cur[j], cur[j + 1], c))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur = nxt
        c += 1
    return cur[0]


class Sheet(object):
    """Один лист FBD (= одна сеть POU)."""

    def __init__(self, name=u"", order_start=1, dx=0, dy=0):
        self.name = name
        self.els = []            # фрагменты xml
        self._cursor = {}        # col -> следующий свободный Y
        self._ypos = {}          # localId -> Y (для выравнивания блоков)
        self._order = order_start
        self.dx = dx             # сдвиг листа по X (сети одного POU сливаются)
        self.dy = dy             # сдвиг листа по Y
        self.use_execution_order = USE_EXECUTION_ORDER
        self._btype = {}         # localId блока -> имя типа блока
        self.synth = []          # синтетические локальные переменные [(имя, тип)]

    # ---------------------------------------------------------------- служебное
    def nid(self):
        _ID[0] += 1
        return _ID[0]

    def _y(self, col, h):
        y = self._cursor.get(col, TOPY)
        self._cursor[col] = y + h + ROWGAP
        return y + self.dy

    def x(self, col):
        return 40 + self.dx + col * COLW

    def skip(self, col, pixels=40):
        """Вставить вертикальный промежуток в колонке (для читаемости)."""
        self._cursor[col] = self._cursor.get(col, TOPY) + pixels

    def add_comment(self, text):
        """Текстовая рамка НА схеме (PLCopen <comment>).

        Именно так, а не через <documentation>: CODESYS отвергает <documentation>
        внутри <pou> ("недопустимый дочерний элемент interface"). Рамка на листе
        заодно виднее -- читающий схему сразу понимает назначение блока.
        """
        i = self.nid()
        w = max(240, 7 * len(text))
        self.els.insert(0,
            u'<comment localId="%d" height="30" width="%d">'
            u'<position x="%d" y="%d" />'
            u'<content><xhtml xmlns="http://www.w3.org/1999/xhtml">%s</xhtml></content>'
            u'</comment>' % (i, w, self.x(0), self.dy, esc(text)))
        return i

    # ---------------------------------------------------------------- элементы
    def var(self, expr, col, width=None):
        """Входная переменная / выражение. Возвращает localId."""
        i = self.nid()
        w = width or max(70, 9 * len(str(expr)))
        h = 20
        y = self._y(col, h)
        self.els.append(
            u'<inVariable localId="%d" height="%d" width="%d">'
            u'<position x="%d" y="%d" />'
            u'<connectionPointOut><relPosition x="%d" y="%d" /></connectionPointOut>'
            u'<expression>%s</expression></inVariable>'
            % (i, h, w, self.x(col), y, w, h // 2, esc(expr)))
        return i

    def ref(self, src, col):
        """Источник пина: либо уже готовый localId (int), либо выражение (str).

        Строка автоматически превращается в элемент-константу. Это сделано
        специально: иначе легко передать 'BYTE#0' вместо идентификатора и
        получить ошибку форматирования далеко от места ошибки.
        """
        if isinstance(src, int):
            return src
        return self.var(src, col)

    # Блоки-компараторы: их выход типа BOOL, и именно такая связь
    # (компаратор -> вход другого блока) отказывала при импорте чаще всего.
    CMP_BLOCKS = (u"EQ", u"NE", u"LT", u"LE", u"GT", u"GE")

    def gate(self, src, col, typ=u"BOOL"):
        """Разорвать связь «выход блока -> вход блока» именованной переменной.

        Причина в docs/05_ТЕХНИЧЕСКИЕ_ЗАМЕТКИ_ИМПОРТА.md: часть схем CODESYS
        молча не создаёт, и под подозрением именно прямые связки компараторов.
        Побочная польза -- на схеме появляется именованный сигнал вместо провода.
        """
        i = self.nid()
        name = u"G%d" % i
        self.synth.append((name, typ))
        self.assign(name, src, col)
        return self.var(name, col)

    def _wrap(self, src, col):
        """Применить gate к источнику, если это выход компаратора."""
        if not getattr(self, "wrap_cmp", USE_WRAP_CMP):
            return src
        if isinstance(src, int) and self._btype.get(src) in Sheet.CMP_BLOCKS:
            return self.gate(src, col)
        return src

    def const(self, value, col):
        """Константа. В FBD она вводится просто как выражение."""
        return self.var(value, col)

    def blk(self, type_name, pins, col, width=80, out_pin=u"OUT", anchor=None, inst=None):
        """Функциональный блок.

        pins -- список пар (имя_пина, localId_источника). Порядок = порядок сверху вниз.
        anchor -- localId, к которому выровнять блок по вертикали (для читаемости).
        inst -- имя ЭКЗЕМПЛЯРА. Обязательно для вызовов ПОУ (FB): CODESYS требует
                атрибут instanceName, а сам экземпляр должен быть объявлен в
                декларации как переменная с типом <derived name="Тип"/>.
                Для стандартных блоков (ADD, SEL, ...) остаётся None.
        Возвращает localId (единственный выходной пин блока).
        """
        i = self.nid()
        h = max(PINSTEP, PINSTEP * len(pins))
        # ВАЖНО: имя выходного контакта должно СОВПАДАТЬ с настоящим именем
        # выхода вызываемого ПОУ. Иначе CODESYS пишет "Идентификатор 'OUT' не
        # задан": у стандартных блоков (ADD, SEL, EQ, ...) выход действительно
        # называется OUT, а у наших функций -- иначе.
        if out_pin == u"OUT" and type_name in OUT_PIN:
            out_pin = OUT_PIN[type_name]
        # У экземпляров ПОУ (ступени и слои) выход OUT есть, и его надо читать:
        # CODESYS исполняет тело ПОУ только тогда, когда вызов что-то отдаёт
        # (правило 3 конспекта). Поэтому клапан, отнимавший выход, снят.
        if anchor is not None and anchor in self._ypos:
            y = self._ypos[anchor]
            self._cursor[col] = max(self._cursor.get(col, TOPY), y + h + ROWGAP)
        else:
            y = self._y(col, h)
        self._ypos[i] = y
        self._btype[i] = type_name
        head = u'<block localId="%d" typeName="%s"' % (i, esc(type_name))
        if inst:
            head += u' instanceName="%s"' % esc(inst)
        buf = [head + u' height="%d" width="%d"' % (h, width)]
        if self.use_execution_order:
            buf.append(u' executionOrderId="%d"' % self._order)
            self._order += 1
        buf.append(u'>')
        buf.append(u'<position x="%d" y="%d" />' % (self.x(col), y))
        buf.append(u'<inputVariables>')
        for n, (pin, src) in enumerate(pins):
            buf.append(u'<variable formalParameter="%s">' % esc(pin))
            buf.append(u'<connectionPointIn><relPosition x="0" y="%d" />'
                       u'<connection refLocalId="%d" /></connectionPointIn>'
                       % (PINSTEP * n + PINSTEP // 2, self.ref(self._wrap(src, col), col)))
            buf.append(u'</variable>')
        buf.append(u'</inputVariables>')
        # ВНИМАНИЕ: пустой <inOutVariables /> обязателен. XSD CODESYS не помечает
        # этот элемент необязательным, и без него импорт падает с сообщением
        # "недопустимый дочерний элемент outputVariables; ожидается inOutVariables".
        buf.append(u'<inOutVariables />')
        if out_pin is None:
            buf.append(u'<outputVariables />')
        else:
            buf.append(u'<outputVariables><variable formalParameter="%s">'
                       u'<connectionPointOut><relPosition x="%d" y="%d" /></connectionPointOut>'
                       u'</variable></outputVariables>' % (esc(out_pin), width, h // 2))
        buf.append(u'</block>')
        self.els.append(u"".join(buf))
        return i

    def assign(self, expr, src, col, width=None, anchor=None, src_pin=None):
        """Записать выход блока в переменную/элемент массива.

        src_pin -- имя ВЫХОДНОГО пина блока-источника. Нужно, когда у блока
        несколько выходов (например, экземпляр FB_Decoder6502 отдаёт 29 сигналов):
        без formalParameter CODESYS подключает первый выход. Возвращает localId.
        """
        i = self.nid()
        w = width or max(70, 9 * len(str(expr)))
        h = 20
        if anchor is not None and anchor in self._ypos:
            y = self._ypos[anchor]
            self._cursor[col] = max(self._cursor.get(col, TOPY), y + h + ROWGAP)
        else:
            y = self._y(col, h)
        conn = u'<connection refLocalId="%d"' % self.ref(src, col)
        if src_pin:
            conn += u' formalParameter="%s"' % esc(src_pin)
        conn += u' />'
        self.els.append(
            u'<outVariable localId="%d" height="%d" width="%d">'
            u'<position x="%d" y="%d" />'
            u'<connectionPointIn><relPosition x="0" y="%d" />%s</connectionPointIn>'
            u'<expression>%s</expression></outVariable>'
            % (i, h, w, self.x(col), y, h // 2, conn, esc(expr)))
        return i

    def _build_index(self):
        self._byid = {}
        for e in self.els:
            m = re.search(u'localId="(\d+)"', e[:200]) if False else None
            m = re.search(u'localId="(\d+)"', e[:200])
            if m:
                self._byid[int(m.group(1))] = e

    def _clone(self, src_id, mapping):
        """Глубокая копия элемента src_id и всех его предков. Возвращает новый id.

        Нужна для развёртывания fan-out (конспект 2.1): каждый выход должен
        питать ровно один вход, поэтому лишние потребители получают копию
        ветви, а не общую ссылку.
        """
        if src_id in mapping:
            return mapping[src_id]
        el = getattr(self, "_byid", {}).get(src_id)
        if el is None:
            return src_id
        new_id = self.nid()
        mapping[src_id] = new_id

        def repl(m):
            return u'refLocalId="%d"' % self._clone(int(m.group(1)), mapping)

        body = re.sub(u'refLocalId="(\d+)"', repl, el)
        body = re.sub(u'localId="\d+"', u'localId="%d"' % new_id, body, count=1)
        self.els.append(body)
        self._byid[new_id] = body
        return new_id

    def xml(self):
        """Собрать <FBD> с развёрнутым fan-out (каждый выход — ровно одному входу)."""
        self._build_index()
        seen = {}
        out_els = []
        for e in self.els:
            def repl(m):
                src = int(m.group(1))
                n = seen.get(src, 0)
                seen[src] = n + 1
                if n == 0:
                    return m.group(0)
                return u'refLocalId="%d"' % self._clone(src, {})
            out_els.append(re.sub(u'refLocalId="(\d+)"', repl, e))
        return u"<FBD>" + u"".join(out_els) + u"</FBD>"


# ==================================================================== декларации
def vartype(t):
    """Тип переменной -> XML.

    Поддерживает и одномерные, и многомерные массивы: образ дискеты по ТЗ —
    ARRAY[0..2047, 0..127] OF BYTE, то есть 2048 секторов по 128 байт (256 КБ).
    В PLCopen XML каждое измерение — отдельный элемент <dimension>.
    """
    t = str(t).strip()
    if t.startswith("ARRAY"):
        m = re.match(r"ARRAY\s*\[([^\]]+)\]\s*OF\s*(\w+)", t, re.I)
        if not m:
            raise ValueError(u"не разобран тип: %s" % t)
        dims = []
        for d in m.group(1).split(u","):
            mm = re.match(r"\s*(\d+)\s*\.\.\s*(\d+)\s*$", d)
            if not mm:
                raise ValueError(u"не разобрано измерение %r в типе %s" % (d, t))
            dims.append(u'<dimension lower="%s" upper="%s" />' % (mm.group(1), mm.group(2)))
        base = m.group(2).upper()
        return (u'<type><array>' + u"".join(dims)
                + u'<baseType><%s /></baseType></array></type>' % base)
    ELEM = (u"BOOL", u"BYTE", u"WORD", u"DWORD", u"LWORD", u"SINT", u"INT", u"DINT",
            u"LINT", u"USINT", u"UINT", u"UDINT", u"ULINT", u"REAL", u"LREAL",
            u"TIME", u"DATE", u"DT", u"TOD", u"STRING", u"WSTRING")
    if t.upper() in ELEM:
        return u'<type><%s /></type>' % t.upper()
    # Всё остальное — производный тип (экземпляр функционального блока), и его
    # ОБЯЗАТЕЛЬНО писать через <derived>. Иначе CODESYS отвергает импорт с
    # сообщением «недопустимый дочерний элемент R_TRIG; ожидается ... derived».
    return u'<type><derived name="%s" /></type>' % t


def var_decl(name, t, init=None, comment=None):
    s = u'<variable name="%s">' % esc(name)
    s += vartype(t)
    if init is not None:
        s += u'<initialValue><simpleValue value="%s" /></initialValue>' % esc(init)
    if comment:
        s += u'<documentation><xhtml xmlns="http://www.w3.org/1999/xhtml">%s</xhtml></documentation>' % esc(comment)
    s += u'</variable>'
    return s


def interface(inputs=(), outputs=(), locals_=(), in_outs=()):
    """inputs/outputs/locals_/in_outs -- списки (имя, тип[, начальное значение, комментарий])."""
    def block(tag, items):
        if not items:
            return u""
        out = [u"<%s>" % tag]
        for it in items:
            out.append(var_decl(*it))
        out.append(u"</%s>" % tag)
        return u"".join(out)

    return (u"<interface>"
            + block("inputVars", inputs)
            + block("outputVars", outputs)
            + block("inOutVars", in_outs)
            + block("localVars", locals_)
            + u"</interface>")


POU_TYPE_XML = {
    "functionBlock": u"functionBlock",
    "function": u"function",
    "program": u"program",
}


def pou_xml(name, pou_type, iface, sheets, comment=None):
    """Собрать PLCopen XML с одним POU.

    ВАЖНО: CODESYS допускает в <body> РОВНО ОДИН элемент <FBD> (проверено
    импортом: "недопустимый дочерний элемент FBD; ожидается addData,
    documentation"). Поэтому несколько сетей сливаются в один лист, а их
    координаты разводятся сдвигами dx/dy у Sheet.
    """
    if comment:
        sheets[0].add_comment(comment)
    # Синтетические локальные переменные (разрыв связей компараторов) обязаны
    # попасть в объявление POU, иначе схема ссылается на несуществующие имена.
    synth = []
    for s in sheets:
        synth.extend(s.synth)
    if synth:
        decl = u"".join(var_decl(n, t) for n, t in synth)
        if u"<localVars>" in iface:
            iface = iface.replace(u"<localVars>", u"<localVars>" + decl, 1)
        else:
            iface = iface.replace(u"</interface>", u"<localVars>" + decl + u"</localVars></interface>", 1)
    # Ступени и слои (FB_*, SL_*) обязаны иметь контактный выход OUT: CODESYS
    # исполняет тело ПОУ только тогда, когда его вызов что-то читает
    # (правило 3 конспекта). Без этого ALU_R оставался 0 при верных входах.
    needs_out = (pou_type != u"program"
                 and (name.startswith(u"FB_") or name.startswith(u"SL_")))
    if needs_out and u'name="OUT"' not in iface:
        sheets[0].assign(u"OUT", sheets[0].const(u"TRUE", 0), 0)
        out_var = u'<variable name="OUT"><type><BOOL /></type></variable>'
        if u"<outputVars>" in iface:
            iface = iface.replace(u"</outputVars>", out_var + u"</outputVars>", 1)
        else:
            iface = iface.replace(u"</interface>",
                                  u"<outputVars>" + out_var + u"</outputVars></interface>", 1)
    all_els = []
    for s in sheets:
        all_els.extend(s.els)
    merged = Sheet(u"")
    merged.els = all_els
    body = merged.xml()
    doc = u'<?xml version="1.0" encoding="utf-8"?>\n'
    doc += u'<project xmlns="http://www.plcopen.org/xml/tc6_0200">\n'
    doc += (u'<fileHeader companyName="" productName="CODESYS" '
            u'productVersion="CODESYS V3.5 SP17 Patch 3" creationDateTime="2026-01-01T00:00:00" />\n')
    doc += u'<contentHeader name="Emu6502">\n<coordinateInfo>\n'
    doc += u'<fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld>'
    doc += u'<sfc><scaling x="1" y="1" /></sfc>\n</coordinateInfo>\n</contentHeader>\n'
    doc += u'<types><dataTypes /><pous>\n'
    doc += u'<pou name="%s" pouType="%s">\n' % (esc(name), POU_TYPE_XML[pou_type])
    doc += iface + u"\n<body>\n" + body + u"\n</body>\n<addData />\n</pou>\n"
    doc += u'</pous></types>\n<instances><configurations /></instances>\n</project>\n'
    return doc


