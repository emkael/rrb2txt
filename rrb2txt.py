# coding=utf-8

import sys
import os
import re
import urlparse

from bs4 import BeautifulSoup, Comment
from glob import glob
from itertools import chain, cycle

directory = sys.argv[1] if len(sys.argv) > 1 else '.'
filepath = os.path.join(directory, 'pary.txt')

content = None
with open(filepath, 'r') as file_content:
    content = BeautifulSoup(file_content.read())

pdf_fixed = False
comments = content.findAll(text=lambda t: isinstance(t, Comment))
for comment in comments:
    if comment == 'fixpdf.py':
        pdf_fixed = True
        break

if not pdf_fixed:
    header = content.select('thead tr')[0]
    body = content.select('tbody tr')

    if not header.find_all(text='+/-'):
        tag = content.new_tag('td', style='display:none')
        tag.string = '+/-'
        header.find(lambda n: n.text[0:5] == 'wynik').insert_before(tag)
        for row in body:
            tag = content.new_tag('td', style='display:none', rowspan=2)
            score_cell = row.select('td.right')
            if score_cell:
                score_cell[0].insert_before(tag)

    extra_headers = ['PKL', 'PDF', 'nagroda']
    extra_headers_present = [bool(header.find_all(text=h))
                             for h in extra_headers]

    extra_headers_offset = 8

    for i in range(0, len(extra_headers)):
        if not extra_headers_present[i]:
            tag = content.new_tag('td', style='display:none')
            tag.string = extra_headers[i]
            header.select('td')[extra_headers_offset].insert_after(tag)
            for row in body:
                cells = row.find_all('td')
                if len(cells) >= extra_headers_offset:
                    tag = content.new_tag(
                        'td', style='display:none', rowspan=2)
                    cells[extra_headers_offset].insert_after(tag)
        extra_headers_offset += 1

    def get_points_count(row):
        try:
            return row.find_all('td')[10].text.count('|')
        except IndexError:
            return 0

    max_points_count = max([get_points_count(row) for row in body]) + 1

    header.find_all('td')[10]['colspan'] = max_points_count

    for row in body:
        cells = row.find_all('td')
        if len(cells) >= extra_headers_offset:
            span = max_points_count
            points = cells[10].text.split('|')
            new_cells = []
            for point in points:
                tag = content.new_tag('td', rowspan=2)
                tag.string = point
                new_cells.append(tag)
                span -= 1
            if span > 0:
                new_cells[-1]['colspan'] = span + 1
            for new_cell in new_cells:
                cells[11].insert_before(new_cell)
            cells[10].extract()

    content.body.append(content.new_string('fixpdf.py', Comment))

    content.body.p.extract()
    new_content = content.find('body').decode_contents()
    new_length = len(new_content) + 1

    output = open(filepath.name, 'wb')
    output.write('%012d' % new_length)
    output.write('\n')
    output.write(new_content.encode('utf-8'))
    output.write('\n')


def format_boards(rows):
    rows = rows[1:4]
    header = rows[0][0].split(os.linesep)
    rows[0][0] = '/'.join(reversed(header[1]
                                   .replace('obie przed', 'NIKT')
                                   .replace('obie po', 'OBIE')
                                   .split(' / ')))
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
    header = 'ROZDANIE NR ' + header[0]
    output = [header, '']
    output.append('{:10s}{:6s}{:10s}'.format(*rows.pop(0)))
    for row in rows:
        output.append('  {:8s}{:6s}{:10s}'.format(*row))
    output.append('')
    return output


def format_protocols(rows):
    output = ['                          ZAPIS      WYNIK',
              ' NS  EW  KONTRAKT  WIST  NS   EW    NS    EW']
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
        elif len(row) != 4 and len(row) != 8:
            print 'protocols: row of unexpected length'
            print row
    output.append('')
    return output


def format_results(rows):
    rows.pop(0)
    content = []
    link_regex = re.compile(r'^http://www\.msc\.com\.pl')
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
    output.append('%s %s  %s %s %s' % (
        'M-CE NR',
        ' ' * name_column,
        'WK     CEZAR     +/-   WYNIK PKL',
        ('{:^' + str(3 * pdf_columns) + 's}').format('PDF'),
        'NAGRODA'
    ))
    output.append('-' * len(output[-1]))
    for c in content:
        line = (
            u'{:>3s} {:>3s} {:' + unicode(name_column) +
            u's} {:>4s} {:2s} {:5s} {:2s} {:>5s} {:>6s} {:>3s}').format(
                *(c[0:3] + c[5:7] + c[3:5] + c[8:11]))
        pdf = (
            u' {:' + unicode(3 * pdf_columns) + u's}').format(
                ''.join([u'{:>3s}'.format(cc) for cc in c[11:-1]]))
        line += pdf
        line += u' {:>6s}'.format(c[-1])
        output.append(line)
    output.append(' ' * (8 + name_column) + '-----')
    output.append(
        ('{:>' + str(13 + name_column) + 's}').format(
            'Suma WK = {:.1f}'.format(wk_sum)))
    return output


def format_histories(rows):
    header = rows.pop(0)[0]
    rows.pop(0)
    if ' pauza ' in header:
        return []
    output = ['WYNIKI PARY NR ' + header,
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
        else:
            print 'histories: unexpected row length'
            print row
    column_width = max([len(r[1]) for r in content_rows])
    content_rows = [[
        'RND', 'PRZECIWNIK', 'RZD', ' ', 'KONTRAKT', 'WIST',
        'ZAPIS', 'WYNIK ', u'/ BIEŻĄCY'
    ]] + content_rows
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


def format_rows(rows, rowtype):
    return globals()['format_' + rowtype](rows)


def get_rows(content):
    soup = BeautifulSoup(content)
    output = []
    link_regex = re.compile(r'^http://www\.msc\.com\.pl')
    header = soup.find('h2')
    if header:
        output.append([header.text])
    for table_row in soup.find_all('tr'):
        row = map(lambda t:
                  os.linesep.join(t.stripped_strings),
                  table_row.find_all('td'))
        row = row + map(lambda l:
                        l['href'],
                        table_row.find_all('a', {'href': link_regex}))
        output.append(row)
    return output


def get_content(filepath):
    return re.sub('<img src=".*/(.*).gif" ?/>',
                  lambda img: img.group(1)[0].capitalize(),
                  open(filepath, 'r').read())


def get_header(directory):
    soup = BeautifulSoup(
        open(os.path.join(directory, 'index.html'), 'r').read())
    return [node.text for node in soup.select('#header *')]


def get_files(directory):
    return dict(map(lambda (key, val): (
        key,
        reduce(list.__add__, map(
            lambda v: sorted(glob(os.path.join(directory, v))), val), [])),
                    {
                        'boards': ['d?.txt', 'd??.txt'],
                        'protocols': ['p?.txt', 'p??.txt'],
                        'histories': ['h?.txt', 'h??.txt'],
                        'results': ['pary.txt'],
                    }.items()))


def compile_dir(directory):
    files = get_files(directory)
    return dict(
        map(lambda (key, val):
            (
                key,
                list(
                    chain(
                        *list(
                            i.next() for i in cycle(
                                map(lambda v:
                                    iter(
                                        map(lambda file:
                                            format_rows(
                                                get_rows(
                                                    get_content(file)
                                                ),
                                                v),
                                            files[v])),
                                    val))
                        )
                    )
                )
            ),
            {
                'P': ['boards', 'protocols'],
                'H': ['histories'],
                'W': ['results']
            }.items()))

directory = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath('.')
header = get_header(directory) + ['']
output = compile_dir(directory)
file_prefix = os.path.basename(directory)

for filepath, rows in output.iteritems():
    output_file = open(file_prefix + filepath + '.txt', 'w')
    for line in header:
        output_file.write(line.encode('windows-1250') + '\n')
    for row in rows:
        output_file.write(row.encode('windows-1250') + '\n')
