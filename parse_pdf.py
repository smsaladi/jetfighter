"""Convert pdf a dataframe of color counts by page
"""

import os.path
import argparse

import tempfile
import subprocess
import glob

import numpy as np
import pandas as pd
import skimage.io

def convert_to_img(fn):
    with tempfile.TemporaryDirectory() as td:
        basen = os.path.basename(fn)
        basen = os.path.splitext(basen)[0] # .replace('.pdf', '')
        outpre = os.path.join(td, basen)

        subprocess.check_call(['pdftoppm', '-png', fn, outpre])
        for pg in glob.iglob(outpre + '*'):
            yield pg

    return

def parse_img(fn):
    im = skimage.io.imread(fn)

    # Check that we have an RGB array (as opposed to grayscale/RGBA)
    assert im.shape[2] == 3

    # Remove white first (large reduction in size of array)
    # NOTE: assumes an 8-bit image
    im = im[np.sum(im, axis=2) != 255*3]

    # im = im.reshape(im.shape[0] * im.shape[1], 3)
    im = pd.DataFrame.from_records(im, columns=['R', 'G', 'B'])

    # count occurrences of each color and then clean up columns
    col = im.groupby(im.columns.tolist()).size()
    col = col.reset_index().rename(columns={0: 'count'})

    col['fn'], _ = os.path.splitext(os.path.basename(fn))

    return col


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_file')

    args = parser.parse_args()

    df = pd.concat([parse_img(p) for p in convert_to_img(args.pdf_file)],
        ignore_index=True, copy=False)

    name, _ = os.path.splitext(args.pdf_file)
    df.to_csv(name + '_colors.csv', index=False)

    return

if __name__ == '__main__':
    main()
