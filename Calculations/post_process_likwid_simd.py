import argparse
import numpy as np

# own functions
from utilities import *

# define command line arguments
parser = argparse.ArgumentParser(
    description='Post-Process timing/memory info and create a table.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--prefix', metavar='prefix', default='LIKWID_Emmy_RRZE',
                    help='A folder prefix to look for benchmark results')
parser.add_argument('--dim', metavar='dim', default=2, type=int,
                    help='Dimension (2 or 3)')

args = parser.parse_args()


# serial | MPI | SIMD | MPI+SIMD
suffixes = [
    '_1proc_novec',
    '_novec',
    '_1proc',
    ''
]

# FIXME: hard-code polynomial orders
poly_to_row = {
    2 : 0,
    4 : 1,
    6 : 2
}

prefix = args.prefix if args.prefix.startswith('/') else os.path.join(os.getcwd(), args.prefix)

# We will generate a table similar to Table 1 in Kronbichler 2012
n_rows = 3 if args.dim == 2 else 2
table_data = [ [ np.nan for i in range(12)] for i in range(n_rows)]

# Go through all the suffixes and parse the data
for idx, s in enumerate(suffixes):
    this_prefix = prefix + s
    files = collection_toutput_files(prefix + s)

    print 'Gather data from {0}'.format(this_prefix)
    print 'found {0} files'.format(len(files))

    # no go through the files:
    for f in files:
        # guess parameters from the file name:
        fname = os.path.basename(f)
        strings = fname.split('_')
        dim = int(re.findall(get_regex_pattern(),strings[2])[0])
        p   = int(re.findall(get_regex_pattern(),strings[3])[0])
        q   = int(re.findall(get_regex_pattern(),strings[3])[1])

        # we are only interested in tensor2 (Algorithm 3) for the currently chosen dimension
        if not (dim == args.dim and '_tensor4' in fname):
            continue

        print 'dim={0} p={1} q={2} file={3}'.format(dim,p,q,fname)

        # these files contain a single region
        result = parse_likwid_file(f,'LIKWID_MARKER_CLOSE')['vmult_MF']

        # depending on the run, the LIKWID output may not have Sum table
        if 'Metric_Sum' not in result:
            data = result['Metric']
            flops = data['MFLOP/s'][0]
            runtime = data['Runtime (RDTSC) [s]'][0]
        else:
            data = result['Metric_Sum']
            flops = data['MFLOP/s STAT'][0]                # take Sum
            runtime = data['Runtime (RDTSC) [s] STAT'][2]  # take Max

        runtime = float(runtime) / 10  # FIXME: hard-code that we run 10 times
        flops = float(flops) / 1000  # MFLOP/s -> GFLOP/s

        print '  {0}'.format(flops)
        print '  {0}'.format(runtime)

        row = poly_to_row[p]
        # first column
        col = 1 if idx==0 else 3 * idx
        # fill in the table
        table_data[row][0] = p
        table_data[row][col] = runtime
        table_data[row][col+1] = flops
        if idx > 0:
            # FIXME: assume that fully serial runs are already in the table
            table_data[row][col+2] = table_data[row][1] / runtime

# Finally write out a latex multicolumn table
file_name = os.path.join(os.getcwd(), '../doc/parallelization_{0}d.tex'.format(args.dim))
print 'Saving table in ' + file_name

with open(file_name, 'w') as f:
    # start with the header
    f.write("""\
\\begin{table}
\centering
\\resizebox{\\textwidth}{!}{
\\begin{tabular}{|c|cc|ccc|ccc|ccc|}
\hline
              & \multicolumn{2}{c|}{serial} & \multicolumn{3}{c|}{MPI} & \multicolumn{3}{c|}{SIMD} & \multicolumn{3}{c|}{MPI+SIMD}  \\\\
\hline
p             & time  & GFlop/s              & time & GFlop/s & speedup & time & GFlop/s & speedup & time & GFlop/s & speedup \\\\
\hline
""")

    # now print the gathered data:
    for row in table_data:
        line = '{0}'.format(int(row[0]))
        for i in range(1, len(row)):
            line = line + '& \pgfmathprintnumber{' + '{0}'.format(row[i]) + '} '
        line = line + '\\\\\n'
        f.write(line)

    # now footer:
    f.write("""\
\hline
\end{tabular}
}
\caption{Wall-clock time in seconds and performance in GFlops of Algorithm \\ref{alg:mf_tensor4} in 2D for various combinations of polynomial degrees,
vectorization and parallelization.}
\label{tab:numbers_2d}
\end{table}
""")