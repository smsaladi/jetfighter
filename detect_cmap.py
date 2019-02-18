"""Convert pdf a dataframe of color counts by page
"""

import os.path
import argparse
import urllib

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
    print('Calculations will fail if this is a worker')

def convert_to_img(fn, format='png', other_opt=[], outdir=None):
    """Converts each page of the pdf to a png file.
        If `out` is None, make one for the meantime
    """
    if outdir:
        td = None
    else:
        td = tempfile.TemporaryDirectory()
        outdir = td.name

    basen = os.path.basename(fn)
    basen = os.path.splitext(basen)[0]
    outpre = os.path.join(outdir, basen)

    #other_opt = ['-' + k, v for k, v in kwargs.items()]
    if format == 'png':
        ext = format
    elif format == 'jpeg':
        ext = 'jpg'
    else:
        raise ValueError("Only jpg, png supported by pdftoppm")

    # TODO: check if/which images to rerender
    subprocess.check_call(['pdftoppm', '-' + format, *other_opt, fn, outpre])

    for pg in glob.iglob(outpre + '*.' + ext):
        yield pg

    # If tempdir was created, then clean it up
    if td:
        td.cleanup()


def parse_img(fn, name=None):
    """Parses an image file into a dataframe of R, G, B color counts
        Pure white and black are removed to reduce the size of the calculation
    """
    try:
        im = skimage.io.imread(fn)
    except urllib.error.HTTPError as e:
        print(fn, name)
        raise e

    # Check that we have an RGB array (as opposed to grayscale/RGBA)
    assert im.shape[2] == 3

    # Remove white and black first (large reduction in size of array)
    # NOTE: assumes an 8-bit image
    im = im[np.sum(im, axis=2) != 255*3]
    im = im[np.sum(im, axis=1) != 0]

    if im.size == 0:
        return None

    # im = im.reshape(im.shape[0] * im.shape[1], 3)
    im = pd.DataFrame.from_records(im, columns=['R', 'G', 'B'])

    # count occurrences of each color and then clean up columns
    col = im.groupby(im.columns.tolist()).size()
    col = col.reset_index().rename(columns={0: 'count'})

    if name is None:
        col['fn'], _ = os.path.splitext(os.path.basename(fn))
    else:
        col['fn'] = name

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

# don't keep grey colormaps
drop_maps = ['Greys', 'binary', 'gist_yarg', 'gist_gray', 'gray']

def build_cmap_knn(n=256):
    """Builds a nearest neighbor graph for each colormap in matplotlib
    """
    # matplotlib.cm.ScalarMappable(cmap=plt.get_cmap('jet')).to_rgba([.1, 0.5, .9], alpha=False, bytes=True)
    cmaps = {}
    cm_names = [cat[1] for cat in cmap_names]
    for name in itertools.chain.from_iterable(cm_names):
        if name not in drop_maps:
            cm = plt.get_cmap(name)
            cmaps[name] = cm(np.linspace(0, 1, n))[:,:3]
            cmaps[name] = cspace_convert(cmaps[name], "sRGB1", "CAM02-UCS")
            cmaps[name] = NearestNeighbors(n_neighbors=1, metric='euclidean').fit(cmaps[name])
    return cmaps

try:
    cmap_knn = build_cmap_knn()
except:
    print("Calculations will fail if this is a worker")


def convert_to_jab(df, from_cm='sRGB255', from_cols=['R', 'G', 'B']):
    """Converts a dataframe inplace from one color map to JCAM02-UCS
        Will delete originating columns
    """
    arr_tmp = cspace_convert(df[from_cols], from_cm, 'CAM02-UCS')
    df[['J', 'a', 'b']] = pd.DataFrame(arr_tmp, index=df.index)

    df.drop(columns=from_cols, inplace=True)
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

rainbow_maps = ['prism', 'hsv', 'gist_rainbow',
                'rainbow', 'nipy_spectral', 'gist_ncar', 'jet']

def detect_rainbow_from_colors(df_colors, cm_thresh=0.5, debug=None):
    """Returns a tuple of pages determined to have rainbow and
    results of colormap detection
    """
    # Write out RGB colors found
    if isinstance(debug, str):
        df_colors.to_csv(debug + '_colors.csv', index=False)

    # Find nearest color for each page
    df_colors = convert_to_jab(df_colors)
    df_cmap = df_colors.groupby('fn').apply(find_cm_dists)
    if isinstance(debug, str):
        df_cmap.to_csv(debug + '_cm.csv')

    df_cmap = df_cmap[df_cmap['pct_cm'] > cm_thresh]
    df_rainbow = df_cmap[df_cmap.index.get_level_values('cm').isin(rainbow_maps)]
    if df_rainbow.size == 0:
        return [], df_cmap

    pgs_w_rainbow = df_rainbow.index.get_level_values('fn').unique()
    if pgs_w_rainbow.str.contains('-').any():
        pgs_w_rainbow = pgs_w_rainbow.str.rsplit('-', 1).str[1]
    pgs_w_rainbow = pgs_w_rainbow.astype(int)

    return pgs_w_rainbow.tolist(), df_cmap


def test_detect_rainbow_from_file():
    pgs, _ = detect_rainbow_from_file('test/172627_short.pdf')
    assert np.array_equal(pgs, [3, 7, 8, 9])
    if 1 in pgs:
        print("FYI, the jet image on page 1 is successfully detected."
              "Change this assertion!")
    else:
        print("FYI, the jet image on page 1 isn't detected")


def detect_rainbow_from_file(fn, debug=False):
    """Full paper processing code (from file to detection)
    """

    df = pd.concat([parse_img(p) for p in convert_to_img(fn)],
        ignore_index=True, copy=False)

    return detect_rainbow_from_colors(df)


def test_detect_rainbow_from_iiif():
    # actually 37 pages, but it takes a long time, just test through 10
    pgs, _ = detect_rainbow_from_iiif('172627v1', 10)
    assert np.array_equal(pgs, [9])
    if 1 in pgs:
        print("FYI, the jet image on page 1 is successfully detected."
              "Change this assertion!")
    else:
        print("FYI, the jet image on page 1 isn't detected")

def detect_rainbow_from_iiif(paper_id, pages, debug=False):
    """Pull images from iiif server
    """

    print(paper_id, pages)

    url = "https://iiif-biorxiv.saladi.org/iiif/2/biorxiv:{}.full.pdf/full/full/0/default.png?page={}"
    data = [parse_img(url.format(paper_id, pg), str(pg)) for pg in range(1, pages+1)]
    df = pd.concat(data, ignore_index=True, copy=False)

    return detect_rainbow_from_colors(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_file')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    has_rainbow, data = detect_rainbow_from_file(args.pdf_file, args.debug)
    print('Has rainbow:', has_rainbow)

    return

if __name__ == '__main__':
    main()
