import os

import numpy as np
import pandas as pd

def get_maxdist():
    return 1

def allign_alleles(df):
    """Look for reversed alleles and inverts the z-score for one of them.

    Here, we take advantage of numpy's vectorized functions for performance.
    """
    d = {'A': 0, 'C': 1, 'G': 2, 'T': 3}
    a = []  # array of alleles
    for colname in ['A1_ref1', 'A2_ref1', 'A1_ref2', 'A2_ref2', 'A1_x', 'A2_x', 'A1_y', 'A2_y']:
        tmp = np.empty(len(df[colname]), dtype=int)
        for k, v in d.items():
            tmp[np.array(df[colname]) == k] = v
        a.append(tmp)
    matched_alleles_ref = (((a[0] == a[2]) & (a[1] == a[3])) |
        ((a[0] == 3 - a[2]) & (a[1] == 3 - a[3])))
    reversed_alleles_ref = (((a[0] == a[3]) & (a[1] == a[2])) |
        ((a[0] == 3 - a[3]) & (a[1] == 3 - a[2])))
    matched_alleles_x = (((a[0] == a[4]) & (a[1] == a[5])) |
        ((a[0] == 3 - a[4]) & (a[1] == 3 - a[5])))
    reversed_alleles_x = (((a[0] == a[5]) & (a[1] == a[4])) |
        ((a[0] == 3 - a[5]) & (a[1] == 3 - a[4])))
    matched_alleles_y = (((a[0] == a[6]) & (a[1] == a[7])) |
        ((a[0] == 3 - a[6]) & (a[1] == 3 - a[7])))
    reversed_alleles_y = (((a[0] == a[7]) & (a[1] == a[6])) |
        ((a[0] == 3 - a[7]) & (a[1] == 3 - a[6])))
    df['Z_x'] *= -2 * reversed_alleles_x + 1
    df['Z_y'] *= -2 * reversed_alleles_y + 1
    df = df[((matched_alleles_ref|reversed_alleles_ref)&(matched_alleles_x|reversed_alleles_x)&(matched_alleles_y|reversed_alleles_y))]
    reversed_alleles_ref = reversed_alleles_ref[((matched_alleles_ref|reversed_alleles_ref)&(matched_alleles_x|reversed_alleles_x)&(matched_alleles_y|reversed_alleles_y))]
    return df, reversed_alleles_ref


def get_files(file_name):
    if '@' in file_name:
        valid_files = []
        for i in range(1, 23):
            cur_file = file_name.replace('@', str(i))
            if os.path.isfile(cur_file):
                valid_files.append(cur_file)
            else:
                raise ValueError('No file matching {} for chr {}'.format(
                    file_name, i))
        return valid_files
    else:
        if os.path.isfile(file_name):
            return [file_name]
        else:
            ValueError('No files matching {}'.format(file_name))


def prep(bfile1, bfile2, partition, sumstats1, sumstats2, N1, N2):
    bim_files1 = get_files(bfile1 + '.bim')
    bim_files2 = get_files(bfile2 + '.bim')
    bed_files = get_files(partition)
    # read in bim files
    bims1 = [pd.read_csv(f,
                        header=None,
                        names=['CHR', 'SNP', 'CM', 'BP', 'A1', 'A2'],
                        delim_whitespace=True) for f in bim_files1]
    bims2 = [pd.read_csv(f,
                        header=None,
                        names=['CHR', 'SNP', 'CM', 'BP', 'A1', 'A2'],
                        delim_whitespace=True) for f in bim_files2]

    bim1 = pd.concat(bims1, ignore_index=True)
    bim2 = pd.concat(bims2, ignore_index=True)

    # read in bed files
    beds = [pd.read_csv(f,
                        delim_whitespace=True) for f in bed_files]
    bed = pd.concat(beds, ignore_index=True)

    dfs = [pd.read_csv(file, delim_whitespace=True)
        for file in [sumstats1, sumstats2]]

    # rename cols
    bim1.rename(columns={'CHR': 'CHR_ref1', 'CM': 'CM_ref1', 'BP':'BP_ref1', 'A1': 'A1_ref1', 'A2': 'A2_ref1'}, inplace=True)
    bim2.rename(columns={'CHR': 'CHR_ref2', 'CM': 'CM_ref2', 'BP':'BP_ref2', 'A1': 'A1_ref2', 'A2': 'A2_ref2'}, inplace=True)
    dfs[0].rename(columns={'A1': 'A1_x', 'A2': 'A2_x', 'N': 'N_x', 'Z': 'Z_x'},
        inplace=True)
    dfs[1].rename(columns={'A1': 'A1_y', 'A2': 'A2_y', 'N': 'N_y', 'Z': 'Z_y'},
        inplace=True)

    # take overlap between output and ref genotype files
    df = pd.merge(bim1, bim2, on=['SNP']).merge(dfs[1], on=['SNP']).merge(dfs[0], on=['SNP'])
    # flip sign of z-score for allele reversals
    df, reversed_alleles_ref = allign_alleles(df)
    df = df.drop_duplicates(subset='SNP', keep=False)
    if N1 is not None:
        N1 = N1
    else:
        N1 = dfs[0]['N_x'].max()
    if N2 is not None:
        N2 = N2
    else:
        N2 = dfs[1]['N_y'].max()
    df.rename(columns={'CHR_ref1':'CHR'}, inplace=True)
    return (df[['CHR', 'SNP', 'Z_x', 'Z_y']], reversed_alleles_ref, bed, N1, N2)
