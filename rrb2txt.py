# coding=utf-8

import sys
import os
import re
import urlparse

from bs4 import BeautifulSoup, Comment
from glob import glob
from itertools import chain, cycle


class RRBPdfFix(object):

    __filepath = ''
    __content = None

    def __init__(self, directory):
        pair_file = os.path.join(directory, 'pary.txt')
        self.__filepath = pair_file
        with open(self.__filepath, 'r') as file_content:
            content = file_content.read()
        self.__content = BeautifulSoup(content, 'lxml')

    def check_fixpdf(self):
        comments = self.__content.findAll(
            text=lambda t: isinstance(t, Comment))
        for comment in comments:
            if comment == 'fixpdf.py':
                return True
        return False

    def __fix_adjustments_column(self, header, body):
        if not header.find_all(text='+/-'):
            tag = self.__content.new_tag('td', style='display:none')
            tag.string = '+/-'
            header.find(lambda n: n.text[0:5] == 'wynik').insert_before(tag)
            for row in body:
                tag = self.__content.new_tag(
                    'td', style='display:none', rowspan=2)
                score_cell = row.select('td.right')
                if score_cell:
                    score_cell[0].insert_before(tag)

    def __fix_extra_columns(self, header, body, extra_headers):
        extra_headers_present = [bool(header.find_all(text=h))
                                 for h in extra_headers]

        extra_headers_offset = 8

        for i in range(0, len(extra_headers)):
            if not extra_headers_present[i]:
                tag = self.__content.new_tag('td', style='display:none')
                tag.string = extra_headers[i]
                header.select('td')[extra_headers_offset].insert_after(tag)
                for row in body:
                    cells = row.find_all('td')
                    if len(cells) >= extra_headers_offset:
                        tag = self.__content.new_tag(
                            'td', style='display:none', rowspan=2)
                        cells[extra_headers_offset].insert_after(tag)
            extra_headers_offset += 1
        return extra_headers_offset

    def __fix_pdf_columns(self, header, body, extra_headers_offset):

        def get_pdf_count(row):
            try:
                return row.find_all('td')[10].text.count('|')
            except IndexError:
                return 0

        max_points_count = max([get_pdf_count(row) for row in body]) + 1

        header.find_all('td')[10]['colspan'] = max_points_count

        for row in body:
            cells = row.find_all('td')
            if len(cells) >= extra_headers_offset:
                span = max_points_count
                points = cells[10].text.split('|')
                new_cells = []
                for point in points:
                    tag = self.__content.new_tag('td', rowspan=2)
                    tag.string = point
                    new_cells.append(tag)
                    span -= 1
                if span > 0:
                    new_cells[-1]['colspan'] = span + 1
                for new_cell in new_cells:
                    cells[11].insert_before(new_cell)
                cells[10].extract()

    def __fix_table(self):
        content = self.__content

        header = content.select('thead tr')[0]
        body = content.select('tbody tr')

        self.__fix_adjustments_column(header, body)

        extra_headers = ['PKL', 'PDF', 'nagroda']
        extra_headers_offset = self.__fix_extra_columns(
            header, body, extra_headers)

        self.__fix_pdf_columns(header, body, extra_headers_offset)

        return content

    def __write_content(self, content):
        content.body.append(content.new_string('fixpdf.py', Comment))
        content.body.p.extract()
        new_content = content.find('body').decode_contents()
        new_length = len(new_content) + 1

        with open(self.__filepath, 'wb') as output:
            output.write('%012d' % new_length)
            output.write('\n')
            output.write(new_content.encode('utf-8'))
            output.write('\n')

    def fixpdf(self):
        if not self.check_fixpdf():
            self.__write_content(self.__fix_table())


def get_content_with_suits(filepath):
    return re.sub('<img src=".*/(.*).gif" ?/>',
                  lambda img: img.group(1)[0].capitalize(),
                  open(filepath, 'r').read())


class RRBTxtGen(object):

    __vulnerability_replace = {
        'obie przed': 'NIKT',
        'obie po': 'OBIE'
    }
    __board_prefix = 'ROZDANIE NR '

    def format_boards(self, rows):
        rows = rows[1:4]

        header = rows[0][0].split(os.linesep)
        for search, replacement in self.__vulnerability_replace.iteritems():
            header[1] = header[1].replace(search, replacement)

        rows[0][0] = '/'.join(reversed(header[1].split(' / ')))
        rows[1][1] = ''

        def split_hand(hand):
            return hand.split(os.linesep)

        rows[0][1] = split_hand(rows[0][1])
        rows[1][0] = split_hand(rows[1][0])
        rows[1][2] = split_hand(rows[1][2])
        rows[2][1] = split_hand(rows[2][1])

        def side_rows(row):
            ret = [
                [row[0],
                 row[1][0][2:],
                 row[2]]
            ]
            for i in range(1, 4):
                ret.append(['',
                            row[1][i][2:] or '===',
                            ''])
            return ret

        def middle_rows(row):
            ret = []
            for i in range(0, 4):
                ret.append([row[0][i][2:] or '===',
                            row[1],
                            row[2][i][2:] or '==='])
            return ret

        rows = side_rows(rows[0]) + middle_rows(rows[1]) + side_rows(rows[2])

        header = self.__board_prefix + header[0]

        output = [header, '']
        output.append('{:10s}{:6s}{:10s}'.format(*rows.pop(0)))
        for row in rows:
            output.append('  {:8s}{:6s}{:10s}'.format(*row))
        output.append('')
        return output

    __traveller_header = ['                          ZAPIS      WYNIK  ',
                          ' NS  EW  KONTRAKT  WIST  NS   EW    NS    EW']

    def format_protocols(self, rows):
        output = self.__traveller_header
        for row in rows:
            content = []
            if len(row) == 10:
                content = [
                    row[0],
                    row[1],
                    ' ' + row[2] + ' ' + row[3] + ' ' + row[5],
                    row[4] or '',
                    row[6] or '',
                    '-' + row[7] if row[7] else '',
                    '{:.1f}'.format(float(row[8])),
                    '{:.1f}'.format(float(row[9]))
                ]
            elif len(row) == 9:
                content = [
                    row[0],
                    row[1],
                    ' ' + row[2] + ' ' + row[3] + ' ' + row[5],
                    row[4],
                    '0',
                    '',
                    '{:.1f}'.format(float(row[7])),
                    '{:.1f}'.format(float(row[8]))
                ]
            if content:
                output.append(
                    u'{:>3s} {:>3s} {:11s}{:^4s}{:>4s}{:>5s} {:>5s} {:>5s}'.format(
                        *content))
            elif len(row) != 4 and len(row) != 8:  # TODO: make it a warning
                print 'protocols: row of unexpected length'
                print row
        output.append('')
        return output

    __cezar_link_prefix = r'^http://www\.msc\.com\.pl'
    __result_headers = {
        'place': 'M-CE',
        'number': 'NR',
        'rank': 'WK',
        'id': 'CEZAR',
        'adjustments': '+/-',
        'score': 'WYNIK',
        'class_points': 'PKL',
        'points': 'PDF',
        'prize': 'NAGRODA'
    }
    __rank_sum_prefix = 'Suma WK'

    def format_results(self, rows):
        rows.pop(0)
        content = []
        link_regex = re.compile(self.__cezar_link_prefix)
        cezar_ids = [
            '{:05d}'.format(int(
                dict(urlparse.parse_qsl(urlparse.urlparse(row.pop()).query))['r']))
            if re.match(link_regex, row[-1])
            else ''
            for row in rows]
        pdf_columns = max([len(row) for row in rows]) - 11
        for row in rows:
            length = len(row)
            if length > 5:
                content.append(row[0:3] + [cezar_ids.pop(0)] + row[3:])
            elif length == 5:
                content.append([''] * 2 + row[0:1] + [
                    cezar_ids.pop(0)] + row[1:] + [''] * (3 + pdf_columns))
            elif length == 4:
                if len(row[3]) != 2:
                    content.append([''] * 2 + row[0:1] + [cezar_ids.pop(0)] +
                                   row[1:3] + content[-1][6:7] +
                                   row[3:4] + [''] * (3 + pdf_columns))
                else:
                    content.append([''] * 2 + row[0:1] + [
                        cezar_ids.pop(0)] + row[1:4] + [''] * (4 + pdf_columns))
            elif length == 3:
                content.append([''] * 2 + row[0:1] +
                               [cezar_ids.pop(0)] + row[1:3] + content[-1][6:8] +
                               [''] * (3 + pdf_columns))
        wk_sum = sum([float(c[5]) if len(c[5]) else 0.0 for c in content])
        output = []
        name_column = max([len(r[2]) for r in content])
        output.append(
            '{:4s} {:2s} {:s} {:6s} {:9s} {:5s} {:5s} {:3s} {:s} {:7s}'.format(
                self.__result_headers['place'],
                self.__result_headers['number'],
                ' ' * (name_column + 1),
                self.__result_headers['rank'],
                self.__result_headers['id'],
                self.__result_headers['adjustments'],
                self.__result_headers['score'],
                self.__result_headers['class_points'],
                ('{:^' + str(3 * pdf_columns) + 's}').format(
                    self.__result_headers['points']),
                self.__result_headers['prize']))
        output.append('-' * len(output[-1]))
        for col in content:
            line = (
                u'{:>3s} {:>3s} {:' + unicode(name_column) +
                u's} {:>4s} {:2s} {:5s} {:2s} {:>5s} {:>6s} {:>3s}').format(
                    *(col[0:3] + col[5:7] + col[3:5] + col[8:11]))
            pdf = (
                u' {:' + unicode(3 * pdf_columns) + u's}').format(
                    ''.join([u'{:>3s}'.format(cc) for cc in col[11:-1]]))
            line += pdf
            line += u' {:>6s}'.format(col[-1])
            output.append(line)
        output.append(' ' * (8 + name_column) + '-----')
        output.append(
            ('{:>' + str(13 + name_column) + 's}').format(
                self.__rank_sum_prefix + ' = {:.1f}'.format(wk_sum)))
        return output

    __recap_header = 'WYNIKI PARY NR '
    __recap_table_header = ['RND', 'PRZECIWNIK', 'RZD', ' ', 'KONTRAKT',
                            'WIST', 'ZAPIS', 'WYNIK ', u'/ BIEŻĄCY']

    def format_histories(self, rows):
        header = rows.pop(0)[0]
        rows.pop(0)
        if ' pauza ' in header:
            return []
        output = [self.__recap_header + header,
                  '']
        content_rows = []
        add_separator = False
        for row in rows:
            content = []
            if len(row) == 11:
                add_separator = (
                    len(''.join(row[0:9])) == 0) and (
                        (add_separator is False) or (row[-2] == 'miejsce'))
                content = row[0:4] + [
                    row[4] + ' ' + row[5] + ' ' + row[7]
                ] + [row[6]] + row[8:11]
            elif len(row) == 10:
                content = [''] + row[0:3] + [
                    row[3] + ' ' + row[4] + ' ' + row[6]
                ] + [row[5]] + row[7:10]
            elif len(row) == 9:
                content = ['', ''] + row[0:2] + [
                    row[2] + ' ' + row[3] + ' ' + row[5]
                ] + [row[4]] + row[6:9]
            if content:
                if add_separator:
                    content_rows.append(
                        ['', '', '', '', '', '', '', '-------', '--------'])
                content_rows.append(content)
            else:  # TODO: make a warning of it
                print 'histories: unexpected row length'
                print row
        column_width = max([len(r[1]) for r in content_rows])
        content_rows = [self.__recap_table_header] + content_rows
        for content in content_rows:
            if content[6]:
                score_align = u'>' if content[6][0] == u'-' else (
                    u'' if content[6][0] == u'+' else u'^')
            else:
                score_align = u''
            output.append(
                (u'{:>3s} {:' + unicode(column_width) +
                 u's} {:>3s} {:2s} {:9s}{:^4s} {:' +
                 score_align + u'7s} {:>7s}{:>8s}').format(
                     *[c or ' ' for c in content]))
        output.insert(3, '-' * len(output[2]))
        output.append('')
        return output


    def format_rows(self, rows, rowtype):
        return getattr(self, 'format_' + rowtype)(rows)


    def get_rows(self, content):
        soup = BeautifulSoup(content, 'lxml')
        output = []
        link_regex = re.compile(self.__cezar_link_prefix)
        header = soup.find('h2')
        if header:
            output.append([header.text])
        for table_row in soup.find_all('tr'):
            row = [
                os.linesep.join(t.stripped_strings)
                for t in table_row.find_all('td')]
            row = row + [l['href'] for l
                         in table_row.find_all('a', {'href': link_regex})]
            output.append(row)
        return output


    def get_header(self):
        soup = BeautifulSoup(
            open(os.path.join(self.__directory, 'index.html'), 'r').read(), 'lxml')
        return [node.text for node in soup.select('#header *')]


    __file_mapping = {
        'boards': ['d?.txt', 'd??.txt'],
        'protocols': ['p?.txt', 'p??.txt'],
        'histories': ['h?.txt', 'h??.txt'],
        'results': ['pary.txt'],
    }

    def get_files(self):
        return dict(
            [(key, reduce(list.__add__,
                          [sorted(glob(os.path.join(self.__directory, v)))
                           for v in val]))
             for (key, val) in self.__file_mapping.items()])


    __output_mapping = {
        'P': ['boards', 'protocols'],
        'H': ['histories'],
        'W': ['results']
    }

    def compile_dir(self):
        files = self.get_files()
        return dict([(
            key,  # I have no fucking clue about what follows
            list(chain(*list(i.next() for i in cycle([
                iter([self.format_rows(
                    self.get_rows(
                        get_content_with_suits(file)), v)
                      for file in files[v]])
                for v in val]))))
            ) for (key, val) in self.__output_mapping.items()])

    __directory = ''

    def __init__(self, directory):
        self.__directory = directory

    def generate(self):
        file_prefix = os.path.dirname(self.__directory).split('/')[-1]

        header = self.get_header() + ['']
        output = self.compile_dir()

        for filepath, rows in output.iteritems():
            output_file = open(file_prefix + filepath + '.txt', 'w')
            for line in header:
                output_file.write(line.encode('windows-1250') + '\n')
            for row in rows:
                output_file.write(row.encode('windows-1250') + '\n')

def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else '.'

    rrb_pdf = RRBPdfFix(directory)
    rrb_pdf.fixpdf()

    rrb_gen = RRBTxtGen(directory)
    rrb_gen.generate()

if __name__ == '__main__':
    main()
