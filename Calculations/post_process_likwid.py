import re
import os
import argparse
from matplotlib.pyplot import figure, show
import matplotlib.pyplot as plt
import matplotlib as mp
import numpy as np
import fileinput
from matplotlib.ticker import MaxNLocator

def remove_creation_date(file_name):
    for line in fileinput.input(file_name, inplace=True):
        if not 'CreationDate' in line:
            print line,


# define command line arguments
parser = argparse.ArgumentParser(
    description='Post-Process timing/memory info and plot figures.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('prefix', metavar='prefix', default='LIKWID_Emmy_RRZE', nargs='?',
                    help='A folder to look for benchmark results')
args = parser.parse_args()

prefix = args.prefix if args.prefix.startswith('/') else os.path.join(os.getcwd(), args.prefix)

files = []
for root, dirs, files_ in os.walk(prefix):
    for f in files_:
        if f.endswith(".toutput"):
            files.append(os.path.join(root, f))

print 'Gather data from {0}'.format(prefix)
print 'found {0} files'.format(len(files))

pattern = r'[+\-]?(?:[0-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?'

# Sections to pick up from
#|                 Metric                 |     Sum    |    Min    |     Max    |    Avg    |  %ile 25  |  %ile 50  |  %ile 75  |
# table:
sections = [
    'MFLOP/s STAT',
    'Memory bandwidth [MBytes/s] STAT',
    'Operational intensity STAT'
]

# NODE data:
# memory bandwidth
B=50   # 50 GB/s single socket
# peak performance
P=176  # 176 Gflop/s single socket

table_names = [
    'Event',
    'Metric'
]

likwid_data = []

for f in files:
    # guess parameters from the file name:
    fname = os.path.basename(f)
    strings = fname.split('_')
    dim = int(re.findall(pattern,strings[2])[0])
    p   = int(re.findall(pattern,strings[3])[0])
    q   = int(re.findall(pattern,strings[3])[1])
    region = 'vmult_MF' if 'MF_CG' in f else 'vmult_Trilinos'
    label = ''
    color = ''  # use colors consistent with post_process.py
    if 'MF_CG' in fname:
        if '_scalar' in fname:
            label = 'MF scalar'
            color = 'b'
        elif '_tensor2' in fname:
            label = 'MF tensor2'
            color = 'g'
        elif '_tensor4' in fname:
            label = 'MF tensor4'
            color = 'c'
    else:
        label = 'Trilinos'
        color = 'r'

    print 'dim={0} p={1} q={2} region={3} label={4} color={5} file={6}'.format(dim,p,q,region,label,color,fname)

    fin = open(f, 'r')

    # store data for each requested section here:
    timing = [np.nan for i in range(len(sections))]

    found_region = False
    found_table = False
    for line in fin:
        # Check if we found the right region:
        if 'Region:' in line:
            found_region = (region in line)

        # Reset the table if found any table:
        for t in table_names:
            if t in line:
                found_table = False

        # Now check if the table is actually what we need
        if found_region and ('Metric' in line) and ('Sum' in line):
            found_table = True
            print '-- Region {0}'.format(region)

        # Only if we are inside the table of interest and region of interest, try to match the line:
        if found_table and found_region:
            columns = [s.strip() for s in line.split('|')]
            if len(columns) > 1:
                for idx, s in enumerate(sections):
                    if s == columns[1]:
                        val = float(columns[2])
                        print '   {0} {1}'.format(s,val)
                        # we should get here only once:
                        assert np.isnan(timing[idx])
                        timing[idx] = val

    # finish processing the file, put the data
    tp = tuple((dim,p,q,label,color,timing))
    likwid_data.append(tp)

# now we have lists of tuples ready
# first, sort by label:
likwid_data.sort(key=lambda tup: tup[3])

#####################
#       PLOT        #
#####################

params = {'legend.fontsize': 20,
          'font.size': 20}
plt.rcParams.update(params)

# Roofline model
# p = min (P, b I)
# where I is measured intensity (Flops/byte)
x = [0.05*i for i in range(200)]
y = [min(P,B*i) for i in x]

plt.grid(True, which="both",color='grey', linestyle=':')

plt.loglog(x,y, 'r-', label='Roofline')


# map degrees to point labels:
degree_to_points = {
    2:'s',
    4:'o',
    6:'^',
    8:'v'
}

# Now plot each measured point:
for d in likwid_data:
  f = d[5][0]
  b = d[5][1]
  x = [f/b]
  y = [f/1000]  # MFLOP->GFLOP
  style = d[4] + degree_to_points[d[1]]
  label = '{0} (p={1})'.format(d[3],d[1])
  plt.loglog(x,y, style, label=label)

plt.xlabel('intensity (Flop/byte)')
plt.ylabel('performance (GFlop/s)')

leg = plt.legend(loc='upper left', ncol=1, labelspacing=0.2)


# file location
fig_prefix = os.path.join(os.getcwd(), '../doc/' + os.path.basename(os.path.normpath(prefix)) + '_')

fig_file = fig_prefix + 'roofline.pdf'

print 'Saving figure in: {0}'.format(fig_file)

plt.tight_layout()
plt.savefig(fig_file, format='pdf')

# plt.savefig(fig_prefix + 'timing2d.eps', format='eps')
# remove_creation_date(fig_prefix + 'timing2d.eps')
