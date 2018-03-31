"""Convert pdf a dataframe of color counts by page
"""

import os.path
import argparse

import tempfile
import subprocess
import glob
import itertools

try:
    import numpy as np
    import pandas as pd
    from sklearn.neighbors import NearestNeighbors

    import skimage.io
    import matplotlib.pyplot as plt
    from colorspacious import cspace_convert
except:
    print("Calculations will fail if this is a worker")


def convert_to_img(fn):
    with tempfile.TemporaryDirectory() as td:
        basen = os.path.basename(fn)
        basen = os.path.splitext(basen)[0]
        outpre = os.path.join(td, basen)

        subprocess.check_call(['pdftoppm', '-png', fn, outpre])
        for pg in glob.iglob(outpre + '*'):
            yield pg

    return

def parse_img(fn):
    im = skimage.io.imread(fn)

    # Check that we have an RGB array (as opposed to grayscale/RGBA)
    assert im.shape[2] == 3

    # Remove white and black first (large reduction in size of array)
    # NOTE: assumes an 8-bit image
    im = im[np.sum(im, axis=2) != 255*3]
    im = im[np.sum(im, axis=1) != 0]

    # im = im.reshape(im.shape[0] * im.shape[1], 3)
    im = pd.DataFrame.from_records(im, columns=['R', 'G', 'B'])

    # count occurrences of each color and then clean up columns
    col = im.groupby(im.columns.tolist()).size()
    col = col.reset_index().rename(columns={0: 'count'})

    col['fn'], _ = os.path.splitext(os.path.basename(fn))

    return col


# Have colormaps separated into categories:
# http://matplotlib.org/examples/color/colormaps_reference.html
cmap_names = [('Perceptually Uniform Sequential', [
            'viridis', 'plasma', 'inferno', 'magma']),
         ('Sequential', [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']),
         ('Sequential (2)', [
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper']),
         ('Diverging', [
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
         ('Qualitative', [
            'Pastel1', 'Pastel2', 'Paired', 'Accent',
            'Dark2', 'Set1', 'Set2', 'Set3',
            'tab10', 'tab20', 'tab20b', 'tab20c']),
         ('Miscellaneous', [
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg', 'hsv',
            'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'])]

def build_cmap_knn(n=256):
    # matplotlib.cm.ScalarMappable(cmap=plt.get_cmap('jet')).to_rgba([.1, 0.5, .9], alpha=False, bytes=True)
    cmaps = {}
    cm_names = [cat[1] for cat in cmap_names]
    for name in itertools.chain.from_iterable(cm_names):
        cm = plt.get_cmap(name)
        cmaps[name] = cm(np.linspace(0, 1, n))[:,:3]
        cmaps[name] = cspace_convert(cmaps[name], "sRGB1", "CAM02-UCS")
        cmaps[name] = NearestNeighbors(n_neighbors=1, metric='euclidean').fit(cmaps[name])
    return cmaps

try:
    cmap_knn = build_cmap_knn()
except:
    print("Calculations will fail if this is a worker")



def convert_to_jab(df):
    arr_tmp = cspace_convert(df[['R', 'G', 'B']], "sRGB255", "CAM02-UCS")
    df[['J', 'a', 'b']] = pd.DataFrame(arr_tmp, index=df.index)

    df.drop(columns=['R', 'G', 'B'], inplace=True)
    return df


def find_cm_dists(df, max_diff=1.0):
    """Expects counts of colors in jab format

    find closest color in cm (in jab space):
    if diff < max_diff:
        then assume thats the mapping
        calculate difference with each remaining page color
        if less than `max_diff`,
            then assume they correspond
    calculate a % of colormap accounted data,
                % of data accounted for by colormap
    """

    cm_stats = pd.DataFrame(index=cmap_knn.keys(),
                            columns=['pct_cm', 'pct_page'])
    cm_stats.index.name = 'cm'

    for cm_name, cm_knn in cmap_knn.items():
        dist, idx = cm_knn.kneighbors(df[['J', 'a', 'b']])

        idx = idx[dist < max_diff]
        dist = dist[dist < max_diff]

        cm_colors = np.unique(idx)

        cm_stats.loc[cm_name, ['pct_cm', 'pct_page']] = [
            cm_colors.size / 256,
            idx.size / df.shape[0]
        ]

    cm_stats.sort_values('pct_cm', ascending=False, inplace=True)

    return cm_stats

def has_rainbow(df_cmap):
    return True


def paper_has_rainbow(fn):
    """Full paper processing code
    """

    df = pd.concat([parse_img(p) for p in convert_to_img(fn)],
        ignore_index=True, copy=False)

    # Write out RGB colors found
    name, _ = os.path.splitext(fn)
    df.to_csv(name + '_colors.csv', index=False)


    # Find nearest color for each page
    df = convert_to_jab(df)
    df_cmap = df.groupby('fn').apply(find_cm_dists)

    # filter output before writing
    df_cmap = df_cmap[df_cmap['pct_cm'] > 0.5]
    df_cmap.to_csv(name + '_cm.csv')

    return has_rainbow(df_cmap)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_file')

    args = parser.parse_args()

    df = pd.concat([parse_img(p) for p in convert_to_img(args.pdf_file)],
        ignore_index=True, copy=False)

    # Write out RGB colors found
    name, _ = os.path.splitext(args.pdf_file)
    df.to_csv(name + '_colors.csv', index=False)


    # Find nearest color for each page
    df = convert_to_jab(df)
    df_cmap = df.groupby('fn').apply(find_cm_dists)

    # filter output before writing
    df_cmap = df_cmap[df_cmap['pct_cm'] > 0.5]
    df_cmap.to_csv(name + '_cm.csv')

    return

if __name__ == '__main__':
    main()
