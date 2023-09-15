"""
author:     https://github.com/gargolito
"""

import os
from io import BytesIO
from tqdm import tqdm

def copy_dest(source, dest)
fsize = int(os.path.getsize(source))
    with open(dest, 'rb') as f:
        with open(dest, 'ab') as n:
            with tqdm(ncols=60, total=fsize, bar_format='{l_bar}{bar} | Remaining: {remaining}') as pbar:
                buffer = bytearray()
                while True:
                    buf = f.read(8192)
                    n.write(buf)
                    if len(buf) == 0:
                        break
                    buffer += buf
                    pbar.update(len(buf))