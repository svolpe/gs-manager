# /* Get extension by id return -1 if not found*/
def get_race(num):
    race = ['Dwarf', 'Elf', 'Gnome', 'Halfling', 'Half-elf', 'Half-orc', 'Human', 'Aberration', 'Animal', 'Beast',
            'Construct', 'Dragon', 'Humanoid, Goblinoid', 'Humanoid, Monstrous', 'Humanoid, Orc',
            'Humanoid, Reptillian', 'Elemental', 'Fey', 'Giant', 'Magical Beast', 'Outsider', 'Unknown', 'Unknown',
            'Shapechanger', 'Undead', 'Vermin', 'Unknown']
    return race[num]

def get_gender(gender):
    """Retrieve the gender based on the provided index.

    This function returns the gender corresponding to the given index. 
    If the index is out of range, it returns "unknown".

    Args:
        gender (int): The index of the gender to retrieve.

    Returns:
        str: The gender as a string, either "Male", "Female", or "unknown".
    """

    gender_opt = ['Male', 'Female']
    return gender_opt[gender] if gender < len(gender_opt) else "unknown"


def extension_id2char(extension_id):
    extension = {2063: 'bik',
                2061: 'ssf',
                2060: 'utw',
                2059: '4pc',
                2056: 'jrl',
                2055: 'utg',
                2054: 'btg',
                2053: 'pwk',
                2052: 'dwk',
                2051: 'utm',
                2050: 'btm',
                2049: 'ccs',
                2048: 'css',
                2047: 'gui',
                2046: 'gic',
                2045: 'dft',
                2044: 'utp',
                2043: 'btp',
                2042: 'utd',
                2041: 'btd',
                2040: 'ute',
                2039: 'bte',
                2038: 'fac',
                2037: 'gff',
                2036: 'ltr',
                2035: 'uts',
                2034: 'bts',
                2033: 'dds',
                2030: 'itp',
                2029: 'dlg',
                2023: 'git',
                2032: 'utt',
                2031: 'btt',
                2027: 'utc',
                2026: 'btc',
                2025: 'uti',
                2024: 'bti',
                9: 'mpg',
                2018: 'tlk',
                2017: '2da',
                2005: 'fnt',
                6: 'plt',
                2016: 'wok',
                2015: 'bic',
                2014: 'ifo',
                2013: 'set',
                2012: 'are',
                2010: 'ncs',
                2009: 'nss',
                2008: 'slt',
                2003: 'thg',
                2007: 'lua',
                2002: 'mdl',
                2001: 'tex',
                2000: 'plh',
                9998: 'bif',
                9999: 'key',
                2022: 'txi',
                10: 'txt',
                7: 'ini',
                4: 'wav',
                3: 'tga',
                2: 'mve',
                1: 'bmp',
                0: 'res',
                }
    return extension[extension_id]


# /* Get extension by name without point return -1 if not found  */
def extension_char2id(extension):
    extension_l = extension.lower()
    char2id = {
        'bik': 2063,
        'ssf': 2061,
        '4pc': 2059,
        'utw': 2060,
        'jrl': 2056,
        'utg': 2055,
        'btg': 2054,
        'pwk': 2053,
        'dwk': 2052,
        'utm': 2051,
        'btm': 2050,
        'ccs': 2049,
        'css': 2048,
        'gui': 2047,
        'gic': 2046,
        'dft': 2045,
        'utp': 2044,
        'btp': 2043,
        'utd': 2042,
        'btd': 2041,
        'ute': 2040,
        'bte': 2039,
        'fac': 2038,
        'gff': 2037,
        'ltr': 2036,
        'uts': 2035,
        'bts': 2034,
        'dds': 2033,
        'itp': 2030,
        'dlg': 2029,
        'git': 2023,
        'utt': 2032,
        'btt': 2031,
        'utc': 2027,
        'btc': 2026,
        'uti': 2025,
        'bti': 2024,
        'mpg': 9,
        'tlk': 2018,
        '2da': 2017,
        'fnt': 2005,
        'plt': 6,
        'wok': 2016,
        'bic': 2015,
        'ifo': 2014,
        'set': 2013,
        'are': 2012,
        'ncs': 2010,
        'nss': 2009,
        'slt': 2008,
        'thg': 2003,
        'lua': 2007,
        'mdl': 2002,
        'tex': 2001,
        'plh': 2000,
        'bif': 9998,
        'key': 9999,
        'txi': 2022,
        'txt': 10,
        'ini': 7,
        'wav': 4,
        'tga': 3,
        'mve': 2,
        'bmp': 1,
        'res': 0
    }
    return char2id[extension_l]


