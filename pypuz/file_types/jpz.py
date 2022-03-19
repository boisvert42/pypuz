import json
import re
from collections import OrderedDict, defaultdict
import xml.etree.ElementTree as ET
import zipfile

# courtesy of https://stackoverflow.com/a/32842402
def etree_to_ordereddict(t):
    
    # helper function to remove the namespace
    def remove_ns(s):
        return re.sub(r'^\{http.*?\}', '', s)
    
    d = OrderedDict()
    t_tag = remove_ns(t.tag)
    d[remove_ns(t_tag)] = OrderedDict() if t.attrib else None
    children = list(t)
    if children:
        dd = OrderedDict()
        for dc in map(etree_to_ordereddict, children):
            for k, v in dc.items():
                k1 = remove_ns(k)
                if k1 not in dd:
                    dd[k1] = list()
                dd[k1].append(v)
        d = OrderedDict()
        d[t_tag] = OrderedDict()
        for k, v in dd.items():
            k1 = remove_ns(k)
            if len(v) == 1:
                d[t_tag][k1] = v[0]
            else:
                d[t_tag][k1] = v
    if t.attrib:
        d[t_tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t_tag]['#text'] = text
        else:
            d[t_tag] = text
    return d


def read_jpzfile(f):
    """
    Read in a JPZ file, return a dictionary of data
    """
    ret = dict()
    # Try to open as a zip file
    try:
        with zipfile.ZipFile(f, 'r') as myzip:
            this_file = myzip.namelist()[0]
            with myzip.open(this_file) as fid:
                xml = fid.read()
    except zipfile.BadZipFile:
        with open(f, 'r') as fid:
            xml = fid.read()
    tree = ET.XML(xml)
    jpzdata = etree_to_ordereddict(tree)
    # Take the root node (whatever it is)
    jpzdata = jpzdata[list(jpzdata.keys())[0]]
    jpzdata = jpzdata['rectangular-puzzle']
    
    CROSSWORD_TYPES = ['crossword', 'coded', 'acrostic']
    crossword_type = 'crossword'
    for ct in CROSSWORD_TYPES:
        if ct in jpzdata.keys():
            crossword_type = ct
            break
    
    # Collect metadata
    kind = crossword_type
    metadata = jpzdata['metadata']
    ret['metadata'] = {
      'kind': kind
    , 'author': metadata.get('creator')
    , 'title': metadata.get('title')
    , 'copyright': metadata.get('copyright')
    , 'notes': metadata.get('description')
    }
    
    puzzle = jpzdata[crossword_type]
    grid1 = puzzle['grid']
    width = int(grid1['@width'])
    height = int(grid1['@height'])
    ret['metadata']['width'] = width
    ret['metadata']['height'] = height
    
    # Get the grid
    grid = []
    for c in grid1['cell']:
        y = int(c['@y'])
        x = int(c['@x'])
        cell = {'x': x, 'y': y}
        value = c.get('@solve-state')
        solution = c.get('@solution')
        number = c.get('@number')
        if value:
            cell['value'] = value
        if solution:
            cell['solution'] = solution
        if number:
            cell['number'] = number
        
        # black squares
        if c.get('@type') == 'block':
            cell['isBlock'] = True
        elif c.get('@type') == 'void':
            cell['isEmpty'] = True
        ## STYLE ##
        # lots of possibilities for style, these are TODO
        # for now, just focus on a few
        style = {}
        # circle
        if c.get('@background-shape') == 'circle':
             style["shapebg"] = "circle"
        # color
        if c.get('@background-color'):
            style['color'] = c.get('@background-color').replace('#', '')
        # bars
        bar_string = ''
        for letter, side in {'T': 'top', 'B': 'bottom', 'L': 'left', 'R': 'right'}.items():
            if c.get(f'@{side}-bar'):
                bar_string += letter
        if bar_string:
            style['barred'] = bar_string
        # top right numbers
        if c.get('@top-right-number'):
            style['mark'] = {"TR": c.get('@top-right-number')}
        
        cell['style'] = style
             
        grid.append(cell)
    ret['grid'] = grid

    ## Clues ##
    # in a jpz, "clues" are separate from "words"
    # so we'll have to handle both
    words = dict()
    for w in puzzle['word']:
        _id = w['@id']
        cells = []
        for c in w['cells']:
            
    ret_clues = [{'title': 'Across', 'clues': []}, {'title': 'Down', 'clues': []}]
    for c in cfpdata.get('WORDS', {}).get('WORD', []):
        # {'number': number, 'clue': clue}
        clue = {'number': c.get('@num', ''), 'clue': c.get('#text', '')}
        this_ix = int(c['@dir'].lower() == 'down')
        ret_clues[this_ix]['clues'].append(clue)
    ret['clues'] = ret_clues
    return ret