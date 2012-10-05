import re
import sys

ABBREV_DIRECTIONS = {
    'N': 'North',
    'S': 'South',
    'E': 'East',
    'W': 'West',
    'Ctrl': 'Central',
    'Ext': 'Extension',
    'Lwr': 'Lower',
    'Upr': 'Upper',
    'Extn': 'Extension',
    'Access': 'Access',
    }

ABBREV_DIRECTIONS_VALUES = ABBREV_DIRECTIONS.values()

ABBREV_STREET_TYPES = {
    'Accs': 'Access',
    'Ave': 'Avenue',
    'Bch': 'Beach',
    'Blvd': 'Boulevard',
    'Bnd': 'Bend',
    'Brg': 'Bridge',
    'By-pass': 'Bypass',
    'Cir': 'Circle',
    'Cl': 'Close',
    'Cmn': 'Common',
    'Crcs': 'Circus',
    'Cres': 'Crescent',
    'Crst': 'Crest',
    'Crt': 'Court',
    'Ctr': 'Centre',
    'Dr': 'Drive',
    'Dve': 'Drive',
    'Esp': 'Esplanade',
    'Exit': 'Exit',
    'Fawy': 'Fairway',
    'Gdns': 'Gardens',
    'Gld': 'Glade',
    'Gln': 'Glen',
    'Gr': 'Grove',
    'Grn': 'Green',
    'Grv': 'Grove',
    'Hts': 'Heights',
    'Hwy': 'Highway',
    'Ledr': 'Leader',
    'Ln': 'Lane',
    'Lwr': 'Lower',
    'Mwy': 'Motorway',
    'Pde': 'Parade',
    'Pk': 'Park',
    'Pl': 'Place',
    'Prom': 'Promenade',
    'Pt': 'Point',
    'Qy': 'Quay',
    'Rd': 'Road',
    'Rds': 'Roads',
    'Sq': 'Square',
    'St': 'Street',
    'Strd': 'Strand',
    'Tce': 'Terrace',
    'Tk': 'Track',
    'Trk': 'Track',
    'Vis': 'Vista',
    'Vlg': 'Village',
    'Vly': 'Valley',
    'Walkay': 'Walkway',
    'Walway': 'Walway',
    'Wlk': 'Walk',
    'Wy': 'Way',
    }

ABBREV_GENERAL = {
    '4wd': '4WD',
    'Mtb': 'Mountain Bike',
    'Statehighway': 'State Highway',
    'Mountainbike': 'Mountain Bike',
    'Hwy': 'Highway',
    'Mwy': 'Motorway',
    }

ABBREV_START = {
    'Qe': 'Queen Elizabeth',
    'Pt': 'Point',
    'No': 'Number',
    'Mt': 'Mount',
    'St': 'Saint',
    'Sh': 'State Highway',
}

SH_NO = re.compile('^Sh(?P<number>[0-9]+[A-Za-z]*)$')
NUMBERISH = re.compile('^(?P<number>[0-9]+[A-Za-z]*)$')
A_C_R_O_N_Y_M = re.compile('^(?P<acro>([A-Za-z]\\.)+([A-Za-z])?)$')

def clean_token(token_arg):
    token = token_arg.strip()
    m = SH_NO.match(token)
    if m:
        return "State Highway %s" % m.group('number')
    m = NUMBERISH.match(token)
    if m:
        return m.group('number').upper()
    m = A_C_R_O_N_Y_M.match(token)
    if m:
        return token.upper()
    if token.capitalize() in ABBREV_GENERAL:
        return ABBREV_GENERAL[token.capitalize()]
    
    return token

def unmangle_tokens(tokens):
    encountered_name = False
    pass_one = []
    for t in tokens:
        if not encountered_name:
            if t in ABBREV_START:
                pass_one.append(ABBREV_START[t])
                continue
            encountered_name = True
        pass_one.append(t)

    pass_two = []
    pass_one.reverse()
    directions_completed = len(pass_one) <= 2
    types_completed = len(pass_one) <= 1
    for t in pass_one:
        if not directions_completed:
            if t in ABBREV_DIRECTIONS:
                pass_two.append(ABBREV_DIRECTIONS[t])
                continue
            elif t in ABBREV_DIRECTIONS_VALUES:
                pass_two.append(t)
                continue
            else:
                directions_completed = True
                
        if not types_completed:
            if t in ABBREV_STREET_TYPES:
                pass_two.append(ABBREV_STREET_TYPES[t])
                continue
            else:
                types_completed = True
        
        pass_two.append(clean_token(t))

    pass_two.reverse()
        
    return " ".join(pass_two)
    
def unmangle_exit_tokens(tokens):
    return " ".join([clean_token(t) for t in tokens])

EXIT_TO = re.compile('^(?P<pre>.*)(?P<exit>Exit (?P<number>[0-9]+[a-z]? )?To)(?P<post>.*)$')
EXIT_NO = re.compile('^(?P<pre>.*)(?P<exit>Exit(?P<number> [0-9]+[a-z]?)?( [A-Za-z]-*[A-Za-z])?)$')

def interpret_label(label_passed):
    result = {}
    if isinstance(label_passed, str):
        label = label_passed.strip()
        m = EXIT_TO.match(label)
        if m:
            pre_unmangled = unmangle_tokens(m.group('pre').split())
            exit_unmangled = unmangle_exit_tokens(m.group('exit').split())
            post_unmangled = unmangle_tokens(m.group('post').split())
            result['label'] = str(pre_unmangled + " " +
                                  exit_unmangled + " " +
                                  post_unmangled).strip()
            if m.group('number'):
                result['exit_ref'] = clean_token(m.group('number'))
            result['exit_name'] = post_unmangled
            return result
        m = EXIT_NO.match(label)
        if m:
            pre_unmangled = unmangle_tokens(m.group('pre').split())
            exit_unmangled = unmangle_exit_tokens(m.group('exit').split())
            result['label'] = str(pre_unmangled + " " +
                                  exit_unmangled).strip()
            if m.group('number'):
                result['exit_ref'] = clean_token(m.group('number'))
            result['exit_name'] = pre_unmangled
            return result
        return {'label': unmangle_tokens(label.split())}
    else:
        return {'label': label_passed}

if __name__ == '__main__':
    for line in sys.stdin:
        q = line.strip()
        if q:
            u = interpret_label(q)
            if q != u['label'] or u.get('exit_ref') or u.get('exit_name'):
                result = "%50s -> %s" % (q, u.get('label'))
                if u.get('exit_ref'):
                    result += (" ::ref-->:: %s" % u.get('exit_ref'))
                if u.get('exit_name'):
                    result += (" ::name-->:: %s" % u.get('exit_name'))
                print result
            else:
                print "%50s" % q
        
