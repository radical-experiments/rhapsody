#!/usr/bin/env python3

import copy
import glob
import math
import os
import pprint
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import radical.analytics as ra
import radical.pilot as rp
import radical.utils as ru
from matplotlib.colors import BoundaryNorm
from radical.analytics.utils import to_latex

# Add parent directory to path to import plot_config
sys.path.insert(0, str(Path(__file__).parent.parent))
import warnings

import plot_config

warnings.simplefilter(action='ignore', category=FutureWarning)

# Configure matplotlib with consistent settings (LARGE size for \linewidth)
plot_config.configure_matplotlib(size='large')

DEBUG = False

# # sid = 'rp.session.frontier00110.matitov.020261.0000'  # 1024 nodes
# sid   = 'rp.session.frontier00123.matitov.020260.0000'  #  256 nodes
# group_type  = 'resource'
#
# session = ra.Session(sid, 'radical.pilot')
# pilot   = session.get(etype='pilot')[0]
# n_nodes = pilot.cfg['requested_nodes']
#
# CPU = 'cpu'
# GPU = 'gpu'
# CPU_MPI = 'cpu+mpi'
# GPU_MPI = 'gpu+mpi'
#
# resources_mapping = {
#     'cpu': CPU,
#     'gpu': GPU,
#     'cpu+mpi': CPU_MPI,
#     'gpu+mpi': GPU_MPI,
#
#     'amber0': CPU,  # work_tree
#     'amber1': CPU,  # antechamber
#     'amber2': CPU,  # tleap
#     'amber3': CPU,  # mmpbsa
#     'amber4': CPU,  # mmpbsa_esmacs
#     'amber5': CPU,  # tleap_pose
#     'amber6': CPU,  # tleap_mmpbsa
#     'amber7': CPU,  # post_mmpbsa
#     'amber8': CPU,  # post_mmpbsa_esmacs
#     'mldocking0': CPU,  # preprocessing
#     'mldocking1': GPU_MPI,  # training
#     'mldocking2': GPU_MPI,  # screening
#     'esmacs0': CPU,  # work_tree
#     'esmacs1': GPU,  # eq0
#     'esmacs2': GPU,  # eq1
#     'esmacs3': GPU,  # sim1
#     'namd0': GPU,  # eq0
#     'openeye0': CPU_MPI,  # docking
#     'openeye1': CPU_MPI,  # pose
#     'reinvent0': CPU,  # preparation
#     'reinvent1': GPU,  # preprocessing
#     'reinvent2': GPU,  # reinvent
#     'reinvent3': GPU,  # postprocessing
# }
#
# def get_task_groups(group_type, tasks):
#     """
#     Return a `dict{task_group: [task_uids]}`.
#     """
#     group_types = {# parts of the task UID
#                    'module': [3, 4],
#                    'step': [2],
#                    'member': [0],
#                    'resource': [3, 4],
#                    'debug': [1]}
#     assert group_type in group_types, 'not supported group type'
#
#     pilot_stop  = pilot.timestamps(event={ru.EVENT: 'bootstrap_0_stop'})[0]
#     task_groups = dict()
#     task_info   = dict()
#     skipped     = list()
#     for task in tasks:
# # ---
#         times = task.timestamps(event=[{ru.EVENT: 'exec_start'}])
#         if not times:
#             del task.events[:]
#             print('skip ', task.uid)
#             task.ts_start = None
#             task.ts_stop  = None
#             skipped.append(task)
#             continue
#
#         task.events.append([min(times), 'exec_0_start', '', '', task.uid, '', '', ''])
#         task.ts_start = min(times)
#
#         # if task hasn't been finished ("exec_stop"/"FAILED") or terminated ("task_timeout"),
#         # then it was running until the whole pilot was terminated
#         exec_stop_time = pilot_stop
#         times = task.timestamps(event=[{ru.EVENT: 'exec_stop'}])
#         if times:
#             exec_stop_time = max(times)
#         else:
#             for event in [{ru.STATE: 'FAILED'}, {ru.EVENT: 'task_timeout'}]:
#                 times = task.timestamps(event=[event])
#                 if times:
#                     exec_stop_time = min(times)
#                     break
#             task.events.append([exec_stop_time, 'exec_stop', '', '', task.uid, '', '', ''])
#         task.events.append([exec_stop_time, 'exec_n_stop', '', '', task.uid, '', '', ''])
#         task.ts_stop = exec_stop_time
#
#         # check that task has been "unscheduled" (use related STATE)
#         times = task.timestamps(event=[{ru.STATE: 'AGENT_STAGING_OUTPUT_PENDING'}])
#         if not times:
#             task.events.append([exec_stop_time, 'state', '', '', task.uid, 'AGENT_STAGING_OUTPUT_PENDING', '', ''])
# # ---
#         # print(task)
#         t_uid_parts = task.uid.split('.')
#
#         # DEBUG
#         if len(t_uid_parts) < 5:
#             t_uid_parts += ['x'] * 5
#
#         group_key = ''.join([t_uid_parts[idx] for idx in group_types[group_type]])
#
#         if group_type in ['resource', 'debug']:
#             # print('map %s to %s' % (group_key, resources_mapping.get(group_key)))
#             group_key = resources_mapping.get(group_key)
#             if not group_key:
#                 # print('no group key for %s' % task.uid)
#                 continue
#
#         task_groups.setdefault(group_key, []).append(task.uid)
#
#     import copy
#     copy_c = dict()
#     copy_g = dict()
#     task_info = dict()
#     for tg in task_groups:
#         uids = task_groups[tg]
#         tasks = session.get(uid=uids)
#         for task in tasks:
#             td    = task.description
#             elems = (td['ranks'], td['cores_per_rank'], td['gpus_per_rank'])
#             key   = '%05d_%05d_%05d' % elems
#             task.het = elems
#             task.key = key
#             if key not in task_info: task_info[key] = list()
#             if key not in copy_c   : copy_c[key]    = list()
#             if key not in copy_g   : copy_g[key]    = list()
#
#             task_info[key].append(task.uid)
#             if elems[2]:
#                 copy_g[key].append(task.uid)
#             else:
#                 copy_c[key].append(task.uid)
#
#     for task in skipped:
#         td    = task.description
#         elems = (td['ranks'], td['cores_per_rank'], td['gpus_per_rank'])
#         key   = '%05d_%05d_%05d' % elems
#         if key not in copy_c: copy_c[key] = list()
#         if key not in copy_g: copy_g[key] = list()
#
#         task_info[key].append(task.uid)
#         if elems[2]: copy_g[key].append(task.uid)
#         else       : copy_c[key].append(task.uid)
#
#     # pprint.pprint(tinfo)
#
#     x = list()
#     y = list()
#     z = list()
#     for key in sorted(copy_c.keys()):
#         elems = tuple([int(x) for x in key.split('_')])
#         # print('    %4d ranks  %4d cpr  %4d gpr : %d tasks' % tuple(elems + (len(task_info[key]),)))
#         x.append(elems[0])
#         y.append(len(copy_c[key]))
#         z.append(len(copy_g[key]))
#     # print
#
#     plt.style.use("seaborn-v0_8-whitegrid")
#     fig, ax = plt.subplots(figsize=(3.5, 3), dpi=300)
#
#     # plt.hist(x, weights=y, bins=len(x), color='red', linewidth=3.5)
#
#     plt.hist(
#         [x, x],                 # same bins
#         weights=[y, z],         # two contributions
#         bins=len(x),
#         stacked=True,
#         color=['blue', 'red'],
#         label=['cpu', 'gpu'],
#         linewidth=3.5
#         )
#
#   # plt.xscale('log')
#     plt.yscale('log')
#
#     xlabel = '#ranks'
#     ylabel = '#tasks'
#     ax.set_xlabel(xlabel, fontweight="bold", fontsize=10, labelpad=8)
#     ax.set_ylabel(ylabel, fontweight="bold", fontsize=10)
#     ax.grid(alpha=0.4, linestyle="--")
#     ax.tick_params(axis='both', which='major', labelsize=9)
#     ax.legend(fontsize=9, loc="best")
#     # ax.legend(fontsize=9, loc="best")
#
#     title = 'Distribution of Task Heterogeneity'
#     fig.text(0.5, 0.91, title, ha='center', va='center', fontweight="bold", fontsize=11)
#
#     # fig.suptitle('%s Tasks - %s Nodes' % (100, 256))
#     fname = '%s_task_het.pdf' % sid
#     fig.savefig(fname, dpi=600, bbox_inches='tight')
#     fname = '%s_task_het.png' % sid
#     fig.savefig(fname, dpi=600, bbox_inches='tight')
#
#     # pprint.pprint(task_info)
#     # pprint.pprint(task_groups)
#
#     return task_groups, task_info
#
#
# def get_tsessions(session, task_groups):
#     """
#     From the given session, derive sessions with the same pilot but only
#     with tasks from a given task group.
#     Return a dict `{task_type: session}`
#     """
#     tsessions = dict()
#     for ttype in sorted(task_groups.keys()):
#         tsession = session.filter(uid=task_groups[ttype], inplace=False)
#         tsessions[ttype] = tsession
#         print('task group %s: %d' % (ttype, len(tsession.get())))
#     return tsessions
#
#
# def plot_utilization(session):
#
#     # pick and choose what contributions to plot
#     metrics = [  # metric        , [color    , alpha]]
#                 ['bootstrap'    , ['#66FF66',  0.4 ]],
#                 [CPU            , ['#0000FF',  0.3 ]],
#                 [CPU_MPI        , ['#000099',  0.6 ]],
#                 [GPU            , ['#3300FF',  0.3 ]],
#                 [GPU_MPI        , ['#9900FF',  0.6 ]],
#             #   ['exec_rp'      , ['#00FF99',  1.0 ]],
#             #   ['exec_task'    , ['#0000FF',  0.2 ]],
#             #   ['exec_launch'  , ['#99FF00',  0.4 ]],
#             #   ['term'         , ['#00FF00',  0.3 ]],
#                 ['idle'         , ['#66FF66',  0.1 ]]
#     ]
#
# #bootstrap         0.000000
# #exec_rp          50.000000
# #cpu              50.000000
# #cpu+mpi         100.000000
# #gpu             100.000000
# #gpu+mpi         100.000000
# #exec_launch      50.000000
# #idle            100.000000
#
#     # metrics to stack and to plot
#     to_stack = [m[0]       for m in metrics]
#     to_plot  = {m[0]: m[1] for m in metrics}
#
#     # Use to set Y-axes to % of resource utilization
#     use_percent = True
#
#     p_trans = [
#         [{1: 'bootstrap_0_start'} , 'system'        , 'bootstrap'    ] ,
#         [{5: 'PMGR_ACTIVE'}       , 'bootstrap'     , 'idle'         ] ,
#         [{6: 'cancel_pilot'}      , 'idle'          , 'system'       ] ,
#         [{1: 'bootstrap_0_stop'}  , 'idle'          , 'system'       ] ,
#     ]
#
#     t_trans = [
#         [{1: 'schedule_ok'}       , 'idle'          , 'exec_rp'      ] ,
#         [{1: 'launch_start'}      , 'exec_rp'       , 'exec_launch'  ] ,
#         [{1: 'exec_start'}        , 'exec_launch'   , 'exec_task'    ] ,
#         [{1: 'exec_stop'}         , 'exec_task'     , 'exec_launch'  ] ,
#         [{1: 'launch_stop'}       , 'exec_launch'   , 'exec_rp'      ] ,
#         [{1: 'unschedule_stop'}   , 'exec_rp'       , 'idle'         ]
#     ]
#
#     t_trans = [
#         [{1: 'schedule_ok'}       , 'idle'          , 'exec_rp'      ] ,
#         [{1: 'launch_start'}      , 'exec_rp'       , 'exec_launch'  ] ,
#         [{1: 'exec_start'}        , 'exec_launch'   , 'exec_task'    ] ,
#         [{1: 'exec_stop'}         , 'exec_task'     , 'exec_launch'  ] ,
#         [{1: 'launch_stop'}       , 'exec_launch'   , 'exec_rp'      ] ,
#         [{1: 'unschedule_stop'}   , 'exec_rp'       , 'idle'         ]
#     ]
#
#     t_trans = [
#         [{5: 'AGENT_EXECUTING_PENDING'}     , 'idle'        , 'exec_rp'      ] ,
#         [{1: 'task_mkdir'}                  , 'exec_rp'     , 'exec_launch'  ] ,
#        #[{1: 'launch_start'}                , 'exec_rp'     , 'exec_launch'  ] ,
#        #[{1: 'task_create_exec_start'}      , 'exec_rp'     , 'exec_launch'  ] ,
#         [{1: 'exec_0_start'}                , 'exec_launch' , 'exec_task'    ] ,
#         [{1: 'exec_n_stop'}                 , 'exec_task'   , 'idle'  ] ,
#        #[{1: 'exec_n_stop'}                 , 'exec_task'   , 'exec_launch'  ] ,
#        #[{1: 'launch_stop'}                 , 'exec_launch' , 'exec_rp'      ] ,
#        #[{5: 'AGENT_STAGING_OUTPUT_PENDING'}, 'exec_rp'     , 'idle'         ]
#     ]
#
#     t_trans = [
#         [{1: 'exec_0_start'}                , 'idle'        , 'exec_task'    ] ,
#         [{1: 'exec_n_stop'}                 , 'exec_task'   , 'idle'  ] ,
#     ]
#
#     labels = [
#               [CPU, CPU_MPI, GPU, GPU_MPI, 'idle'],
#     ]
#
#
#
#     # what entity maps to what transition table
#     tmap = {
#         'pilot': p_trans,
#         'task' : t_trans,
#     }
#
#     rtypes = ['cpu', 'gpu']
#
#     # Get transition data for the complete session.
#     # We plan to use most of it - but we exchange the `rp_task` part later -
#     # that is switched out with the equivalent data from filtered sessions,
#     # each containing only certain task types.
#     p_resrc, series, x = ra.get_pilot_series(session, pilot, tmap, rtypes, use_percent)
#
#     if False:
#         for task in session.get(etype='task'):
#             print('========= events %s' % task.uid)
#             for e in task.events:
#                 print(e)
#
#
#
#     # empty out the `exec_task` part of the series
#     for rtype in rtypes:
#         del series[rtype]['exec_task']
#
#     # print('p_resrc')
#     # pprint.pprint(p_resrc)
#     # print('series')
#     # pprint.pprint(series)
#     # print('x')
#     # pprint.pprint(x)
#
#     # FIXME: optimized
#     # get transition data for each task category
#     # tsessions = get_tsessions(session)
#
#     # print('tsession types', list(tsessions.keys()))
#     for ttype,tsession in tsessions.items():
#         # print("\n\n=============================\n")
#         # print('=== ttype %s' % ttype)
#         t_resrc, t_series, t_x = ra.get_pilot_series(tsession, pilot, tmap, rtypes, use_percent)
#         # pprint.pprint(t_resrc)
#         # pprint.pprint(t_series)
#         # pprint.pprint(t_x)
#
#         for rtype in t_series:
#             # print('==== rtype reassign exec_task', rtype, ttype)
#             series[rtype][ttype] = t_series[rtype]['exec_task']
#
#     # now we have the patched data series and can create the plot primitives
#     r_areas = dict()
#     for plot_id, r in enumerate(rtypes):
#
#         if not p_resrc[r]:
#             continue
#
#         print('=================================== plot %d %s' % (plot_id, r))
#         # stack timeseries for each metrics into areas
#         # print(r)
#         # print(sorted(list(series[r].keys())))
#         # print(sorted(to_stack))
#         # pprint.pprint(series)
#
#         areas = ra.stack_transitions(series, r, to_stack)
#         # print('===================================== areas')
#         # pprint.pprint(areas)
#
#         if len(areas) <= 3:
#             print('skip %s, not enough data' % r)
#         else:
#             r_areas[r] = areas
# # ---------------
#     # print(r_areas)
#     flat = [x for row in labels for x in row]
#
#     cf = r_areas['cpu']
#     gf = r_areas['gpu']
#
#     times  = set()
#     ctimes = list()
#     gtimes = list()
#     for idx, row in cf.iterrows():
#         times.add(row['time'])
#         ctimes.append(row['time'])
#     for idx, row in gf.iterrows():
#         times.add(row['time'])
#         gtimes.append(row['time'])
#
#     print('===', len(times), len(ctimes), len(gtimes))
#
#     # print(labels)
#     count = 0
#     hets  = list()
#     # check heterogeneity for all timestamps
#     for t in sorted(list(times)):
#         if t in ctimes:
#             row  = cf[cf['time'] == t]
#             vals = row.values.tolist()[0]
#             keys = list(row.columns)
#             flat.insert(0, 'time')
#             #if count == 0:
#             #    count += 1
#             #    print('flat', flat)
#             #    print('keys', keys)
#             ucc = vals[3] - vals[2]
#             ucm = vals[4] - vals[3]
#             ugg = vals[5] - vals[4]
#             ugm = vals[6] - vals[5]
#             cutil = [ucc, ucm, ugg, ugm]
#             cutil = [0 if x < 0.001 else x for x in cutil]
#             cont  = len([x for x in cutil if x])
#             utot  = sum(cutil)
#             cutil = [round(x,3) for x in cutil]
#             hets.append([t, cont, round(utot, 1), cutil])
#
#     # pprint.pprint(hets)
#
#     # only use hets on max heterogeneity (cmax)
#     cmax = max(x[1] for x in hets)
#     umax = max(x[2] for x in hets)
#     hets = [x for x in hets if x[1] == cmax]
#     # hets = [x for x in hets if x[2] == umax]
#
#     print('cmax, umax', cmax, umax)
#
#     # pprint.pprint(hets)
#
#     # for all timestamps with max heterogenity in cpu, also derive gpu utilization
#     for het in hets:
#         t = het[0]
#         if True:
#             # no data for GPU
#             # het += [round(utot, 1), 0.,0.,0.,0.]
#         #else:
#             # get DF closest to timestamp
#           # row  = gf[gf['time'] == t]
#             idx  = (gf['time'] - t).abs().argmin()
#             row  = gf.iloc[[idx]]
#             vals = row.values.tolist()[0]
#             # print(round(t,2), vals)
#             ucc  = vals[3] - vals[2]
#             ucm  = vals[4] - vals[3]
#             ugg  = vals[5] - vals[4]
#             ugm  = vals[6] - vals[5]
#             gutil = [ucc, ucm, ugg, ugm]
#             gutil = [0 if x < 0.001 else x for x in gutil]
#             cont  = len([x for x in gutil if x])
#             utot  = sum(gutil)
#             gutil = [round(x,3) for x in gutil]
#             het  += [round(utot, 1)] + [gutil]
#
#     # find largest gutil:
#     gmax = max([x[4] for x in hets])
#     print('gmax', gmax)
#
#     # get hets at that gmax
#     hets = [x for x in hets if x[4] == gmax]
#
#     # convert time to float
#     for het in hets:
#         het[0] = round(float(het[0]),3)
#
#     #for het in hets:
#     #    print('het', het)
#     # ------------------
#
#     # print red lines at those data points
#     checkpoints = [x[0] for x in hets]
#
#     # #plots = #resource_types (e.g., ['cpu', 'gpu'] = 2 resource types = 2 plots)
#     n_plots = len(r_areas)
#
#     # sub-plots for each resource type, legend on first, x-axis shared
#     # fig = plt.figure(figsize=(ra.get_plotsize(500)))
#     # gs  = mpl.gridspec.GridSpec(n_plots, 1)
#
#     plt.style.use("seaborn-v0_8-whitegrid")
#     fig, axes = plt.subplots(2, 1, figsize=(6, 6), dpi=600)
#
#     for plot_id, r in enumerate(rtypes):
#
#         ax = axes[plot_id]
#
#         areas = r_areas.get(r)
#         if areas is None:
#             continue
#
#         # plot individual metrics
#         prev_m  = None
#         patches = dict()
#         legend  = dict()
#         for m in areas:
#
#             if m not in to_plot:
#                 if m != 'time':
#                     print('skip', m)
#                 continue
#
#             pcol   = to_plot[m][0]
#             palpha = to_plot[m][1]
#
#             # plot the (stacked) areas
#             # fill first metric toward 0, all others towards previous line
#             if not prev_m:
#                 patch = ax.fill_between(areas['time'], areas[m],
#                                         step='post', label=m, linewidth=0.0,
#                                         color=pcol, alpha=palpha)
#
#             else:
#                 patch = ax.fill_between(areas['time'], areas[m], areas[prev_m],
#                                         step='post', label=m, linewidth=0.0,
#                                         color=pcol, alpha=palpha)
#
#             # remember patches for legend
#             legend[m]  = to_latex(m)
#             patches[m] = patch
#
#             # remember this line to fill against
#             prev_m = m
#
#         ax.set_xlim([x['min'], x['max']])
#         if use_percent:
#             ax.set_ylim([0, 100])
#         else:
#             ax.set_ylim([0, p_resrc[r]])
#
#         xlabel = 'time (s)'
#         ylabel = '%s (%%)' % r
#
#         if plot_id:
#             ax.set_xlabel(xlabel, fontweight="bold", fontsize=10, labelpad=8)
#         ax.set_ylabel(ylabel, fontweight="bold", fontsize=10)
#
#         ax.grid(alpha=0.4, linestyle="--")
#         ax.tick_params(axis='both', which='major', labelsize=9)
#
#         # resort the legend to list entries from left to right
#         ncol = len(labels[0])
#         label_order = list()
#         for i in range(ncol):
#             for row in labels:
#                 if len(row) > i:
#                     label_order.append(row[i])
#         legend_sorted  = list()
#         patches_sorted = list()
#         for label in label_order:
#             legend_sorted.append(legend[label])
#             patches_sorted.append(patches[label])
#
#         # first sub-plot gets legend
#         if plot_id == 0:
#             ax.legend(patches_sorted, legend_sorted, loc='upper center',
#                     ncol=ncol, bbox_to_anchor=(0.5, 1.15), fancybox=True,
#                     shadow=True, fontsize=9)
#
#         # print('--', checkpoints)
#         # plt.vlines(x=checkpoints, ymin=0, ymax=100, color='red', linestyle='--', transform=plt.gca().get_xaxis_transform())
#
#   # ax.legend(fontsize=9, loc="best")
#
#     title = "Resource Utilization per Task Class"
#     fig.text(0.5, 0.95, title, ha='center', va='center', fontweight="bold", fontsize=11)
#
#     # fig.suptitle(title)
#     fig.savefig('%s_util.pdf' % sid, dpi=600, bbox_inches='tight')
#
#     for cp in checkpoints:
#         print("\n===================\nCheckpoint %7.1f\n" % cp)
#         for r, areas in r_areas.items():
#             row = areas.iloc[(areas['time'] - cp).abs().argmin()]
#             print(row)
#             print("\n===================\n\n")
#
#
# task_groups, task_info = get_task_groups(group_type, session.get(etype='task'))
# tsessions = get_tsessions(session, task_groups)
#
# tasks = session.get(etype='task')
#
# e_start = {ru.STATE: None, ru.EVENT: 'exec_0_start'}
# e_stop  = {ru.STATE: None, ru.EVENT: 'exec_n_stop'}
#
# # find the timestamps for which we want to cound task types (whenever a task starts or stops)
# times = set()
# for t in tasks:
#
#     t_start = t.timestamps(event=e_start)
#     t_stop  = t.timestamps(event=e_stop)
#
#     if not t_start or not t_stop:
#         print('skip', t.uid, t_start, t_stop)
#         continue
#
#     times.add(t_start[0])
#     times.add(t_stop[0])
#
#
# # at those points, cound tasks and task types
# data = list()
# print('id m0.i0.s1.openeye.0.0000 127020456968848')
# for ts in sorted(times):
#
#     count = set()
#     for t in tasks:
#         if not t.ts_start:
#             continue
#         if t.ts_start <= ts and ts <= t.ts_stop:
#             count.add(t.het)
#
#     data.append([ts, len(count)])
#
#
# checkpoints = plot_utilization(session)
# print('checkpoints: ', len(checkpoints))


sid = 'rp.session.frontier00123.matitov.020260.0000'  #  256 nodes null
sid = 'rp.session.frontier00110.matitov.020261.0000'  # 1024 nodes null

datfile = '%s.het.dat' % sid

if os.path.exists(datfile):
    data = list()
    with open(datfile, 'r') as fin:
        for line in fin.readlines():
            data.append([int(x) for x in line.split()])


data_x = [p[0] for p in data]
data_y = [p[1] for p in data]

xlabel = 'time (s)'
ylabel = '#task types'
title  = "Task Heterogenity"

plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(3.5, 1.5), dpi=300)

ax.step(data_x, data_y, color='red', linewidth=1.2)

ax.set_ylim(0, 25)
ax.set_xlabel(xlabel, fontweight="bold", fontsize=10, labelpad=8)
ax.set_ylabel(ylabel, fontweight="bold", fontsize=10)
ax.grid(alpha=0.4, linestyle="--")
ax.tick_params(axis='both', which='major', labelsize=9)
# ax.legend(fontsize=9, loc="best")

fig.text(0.5, 0.94, title, ha='center', va='center', fontweight="bold", fontsize=11)

# fig.suptitle('%s Tasks - %s Nodes' % (100, 256))
fname = '%s_task_types.pdf' % sid
fig.savefig(fname, dpi=600, bbox_inches='tight')

with open(datfile, 'w') as fout:
    for p in data:
        fout.write('%d %d\n' % (p[0], p[1]))


s1 = 'rp.session.frontier00123.matitov.020260.0000'  #  256 nodes null
s2 = 'rp.session.frontier00110.matitov.020261.0000'  # 1024 nodes null

# Create figure using plot_config for consistent styling
fig, axes = plot_config.create_figure(1, 2, figsize=(7.0, 2.5))

xlabel = 'time (s)'
ylabel = '#task types'
title  = "Task Heterogenity"

for i,sid in enumerate([s1, s2]):

    data = list()
    with open('%s.het.dat' % sid, 'r') as fin:
        for line in fin.readlines():
            data.append([int(x) for x in line.split()])

    data_x = [p[0] for p in data]
    data_y = [p[1] for p in data]

    ax   = axes[i]
    ax.step(data_x, data_y, color='red', linewidth=1.5)

    ax.set_ylim(0, 25)
    ax.set_xlabel(xlabel, labelpad=8)
    if not i:
        ax.set_ylabel(ylabel)
    ax.grid(alpha=0.4, linestyle="--")

    if i == 0:
        label = ' 256 nodes'
        ax.set_title(title, loc='left', pad=15, fontweight='bold')
    else:
        label = '1024 nodes'
    ax.legend(labels=[label], loc="best")

plt.tight_layout()

plot_config.save_figure(fig, 'impeccable_task_types.pdf')
plot_config.save_figure(fig, 'impeccable_task_types.png')

