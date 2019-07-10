''' Plotting losses etc.  '''


import numpy as np
import pandas as pd
import os

PLOT_DIR = 'tasks/NDH/plots/'
dfs = {}
# val-seq2seq-all-planner_path-sample-imagenet-log
summary = {"val_seen": {}, "val_unseen": {}, "test": {}}
for path_type, path_len in [['planner_path', 20], ['player_path', 80], ['trusted_path', 80]]:
    print(path_type)
    for eval_type in ['val', 'test']:
        print('\t%s (%d)' % (eval_type, path_len))
        for feedback in ['sample']:
            print('\t\t%s' % feedback)
            for history in ['none', 'target', 'oracle_ans', 'nav_q_oracle_ans', 'all']:
                for blind in [True, False]:
                    print('\t\t\t%s (%s)' % (history, 'blind' if blind else 'vision'))
                    if path_len is None:
                        if blind:
                            log = '%s-seq2seq-%s-%s-%s-imagenet-blind-log.csv' % (eval_type, history,
                                                                                  path_type, feedback)
                        else:
                            log = '%s-seq2seq-%s-%s-%s-imagenet-log.csv' % (eval_type, history, path_type, feedback)
                    else:
                        if blind:
                            log = '%s-seq2seq-%s-%s-%d-%s-imagenet-blind-log.csv' % (eval_type, history,
                                                                                     path_type, path_len, feedback)
                        else:
                            log = '%s-seq2seq-%s-%s-%d-%s-imagenet-log.csv' % (eval_type, history,
                                                                               path_type, path_len, feedback)
                    fn = os.path.join(PLOT_DIR, log)
                    if os.path.isfile(fn):
                        dfs[log] = pd.read_csv(fn)
                        print('\t\t\t\t%d' % len(dfs[log]))
                        metrics = [
                            'val_seen success_rate',
                            'val_seen oracle path_success_rate',
                            'val_seen dist_to_end_reduction',
                            'val_unseen success_rate',
                            'val_unseen oracle path_success_rate',
                            'val_unseen dist_to_end_reduction'] if eval_type == 'val' else [
                            'test success_rate',
                            'test oracle path_success_rate',
                            'test dist_to_end_reduction']
                        for metric in metrics:
                            v = max(dfs[log][metric])
                            print('\t\t\t\t%s\t%.3f' % (metric, v))

                        # Populate summary.
                        if len(dfs[log]) == 200:
                            for cond in ['val_seen', 'val_unseen', 'test']:
                                abl = history + "-%s" % ('blind' if blind else 'vis')
                                if abl not in summary[cond]:
                                    summary[cond][abl] = {"if": {}, "gd": {}}
                                ifm = '%s oracle path_success_rate' % cond
                                if ifm in dfs[log]:
                                    summary[cond][abl]["if"][path_type] = list(dfs[log][ifm])
                                gdm = '%s dist_to_end_reduction' % cond
                                if gdm in dfs[log]:
                                    summary[cond][abl]["gd"][path_type] = list(dfs[log][gdm])

# Print partial table rows for easy copy/paste to latex.
print('')
for cond in ['val_seen', 'val_unseen', 'test']:
    for history in ['none', 'target', 'oracle_ans', 'nav_q_oracle_ans', 'all']:
        for blind in [True, False]:
            abl = history + "-%s" % ('blind' if blind else 'vis')
            if abl not in summary[cond]:
                continue
            l = '%s\t%s\t' % (cond, abl)
            ns = []
            for metric in ['if', 'gd']:
                for sup in ['planner_path', 'player_path', 'trusted_path']:
                    if sup in summary[cond][abl][metric]:
                        if cond == 'test':  # performance is at epoch of best val_seen GD performance.
                            if sup not in summary["val_unseen"][abl]["gd"]:
                                print("val_unseen not yet finished for %s" % abl)
                                ns.append(-2)
                            else:
                                b = max(summary["val_unseen"][abl]["gd"][sup])
                                best_idx = summary["val_unseen"][abl]["gd"][sup].index(b)
                                ns.append(summary[cond][abl][metric][sup][best_idx])
                        else:
                            ns.append(max(summary[cond][abl][metric][sup]))
                    else:
                        ns.append(-1)
            l += ' & '.join(["$%.1f$" % (n*100) for n in ns[:3]]) + ' & ' + \
                 ' & '.join(["$%.2f$" % n for n in ns[3:]])
            print(l)
