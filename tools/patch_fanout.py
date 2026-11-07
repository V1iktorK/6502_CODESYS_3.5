# -*- coding: utf-8 -*-
"""
patch_fanout.py -- realizaciya pravila 2.1 konspekta: RAZVERTYVANIE FAN-OUT.

Konspekt: "esli lyuboy vyhod pitает bolshe odnogo vhoda, CODESYS 3.5 SP17
vybrasyvaet POU" i "reshenie -- razvorachivat graf v derevo: dlya kazhdogo
lishnego ispolzovaniya sozdaetsya KOPIYA elementa vmeste so vsey ego vhodnoy
vetvyu". Zashchelka cherez peremennuyu ne goditsya: po (2.5) chtenie yacheyki
v toy zhe seti daet staroe znachenie.

Realizuem v Sheet.xml(): pered vyvodom kazhdaya svyaz, ispolzovannaya vtoroy
i posleduyushchie razy, perenapravlyaetsya na glubokuyu kopiyu istochnika
(so vsemi predkami).
"""
import io
import ast
import re

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\fbd.py"
t = io.open(P, "rb").read().decode("utf-8")

# 1) dobavim metod _clone i novyy xml() s razvorachivaniem
anchor = u'    def xml(self):'
if anchor not in t:
    raise SystemExit(u"не найден xml()")

new_methods = u'''    def _build_index(self):
        self._byid = {}
        for e in self.els:
            m = re.search(u'localId="(\\\\d+)"', e[:200]) if False else None
            m = re.search(u'localId="(\\\\d+)"', e[:200])
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

        body = re.sub(u'refLocalId="(\\\\d+)"', repl, el)
        body = re.sub(u'localId="\\\\d+"', u'localId="%d"' % new_id, body, count=1)
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
            out_els.append(re.sub(u'refLocalId="(\\\\d+)"', repl, e))
        return u"<FBD>" + u"".join(out_els) + u"</FBD>"
'''

# udalyaem staryy xml() (tri stroki)
old_xml = u'''    def xml(self):
        return u"<FBD>" + u"".join(self.els) + u"</FBD>"'''
if old_xml in t:
    t = t.replace(old_xml, new_methods.rstrip(), 1)
    print(u"xml() заменён на версию с развёртыванием fan-out")
else:
    # ishem po signaturam
    i = t.find(u'    def xml(self):')
    j = t.find(u'</FBD>', i)
    j = t.find(u'\n', j)
    t = t[:i] + new_methods.rstrip() + t[j:]
    print(u"xml() заменён (по позиции)")

# nuzhen import re
if u"^import re" not in t and u"\nimport re" not in t:
    t = t.replace(u"import os", u"import os\nimport re", 1)

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис fbd.py OK")
