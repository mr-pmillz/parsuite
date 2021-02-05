from parsuite.core.argument import Argument,DefaultArguments
from parsuite import helpers
from parsuite.core.suffix_printer import *
import argparse
import re

LEAD_RE=re.compile('\$\*(.+(:[0-9]{1,5})?)\*\$')
HASH_RE=re.compile('[a-z0-9]{1000,}.+:(.+)',re.I)

help='Iterate over each cracked credential in an output file ' \
'generated by HashCat that contains cracked Kerberos tickets and ' \
'return each record in <spn>:<password> format' \


args = [
    DefaultArguments.input_files,
]

def parse(input_files=None, **kwargs):

    # =====================
    # PARSE EACH INPUT FILE
    # =====================

    for input_file in input_files:

        with open('kerb_cracked.txt') as infile:
        
            for line in infile:
        
                line = line.strip()
        
                # ================
                # EXTRACT THE USER
                # ================
        
                user_match = re.search(LEAD_RE, line)
        
                if not user_match:
                    esprint('Failed to get username from: {line}')
                    esprint('Skipping')
                    continue
        
                # =============================
                # EXTRACT THE HASH AND PASSWORD
                # =============================
        
                hash_match = re.search(HASH_RE, line)
        
                if not hash_match:
                    esprint('Failed to get hash/password from: {line}')
                    esprint('Skipping')
                    continue

                print('{}:{}'.format(
                    user_match.groups()[0].lower(),
                    hash_match.groups()[0])
                )

    esprint('Finished!')