''' Plotting losses etc.  '''


import numpy as np
import pandas as pd
# import matplotlib as mpl
from eval import Evaluation
# mpl.use('Agg')
# import matplotlib.pyplot as plt

logs = {
  'seq2seq-oracle_ans-planner_path-sample-imagenet-log.csv': 'A-Planner-Student-forcing',
  'seq2seq-oracle_ans-planner_path-teacher-imagenet-log.csv': 'A-Planner-Teacher-forcing',
  'seq2seq-oracle_ans-player_path-sample-imagenet-log.csv': 'A-Player-Student-forcing',
  'seq2seq-oracle_ans-player_path-teacher-imagenet-log.csv': 'A-Player-Teacher-forcing',
  'seq2seq-nav_q_oracle_ans-planner_path-teacher-imagenet-log.csv': 'QA-Planner-Teacher-forcing',
  'seq2seq-nav_q_oracle_ans-planner_path-sample-imagenet-log.csv': 'QA-Planner-Student-forcing',
  'seq2seq-nav_q_oracle_ans-player_path-teacher-imagenet-log.csv': 'QA-Planner-Teacher-forcing',
  'seq2seq-nav_q_oracle_ans-player_path-sample-imagenet-log.csv': 'QA-Player-Student-forcing',
  'seq2seq-all-planner_path-teacher-imagenet-log.csv': 'All-Teacher-forcing',
  'seq2seq-all-planner_path-sample-imagenet-log.csv': 'All-Student-forcing',
}

RESULT_DIR = 'tasks/instruction_following_MP_baseline/results/'
PLOT_DIR = 'tasks/instruction_following_MP_baseline/plots/'

def plot_training_curves():
    ''' Plot the validation loss, navigation error and success rate during training. '''

    font = {
      'size'   : 12
    }
    # mpl.rc('font', **font)

    dfs = {}
    for log in logs:
        dfs[log] = pd.read_csv('tasks/instruction_following_MP_baseline/plots/'+log)
        for metric in ['val_seen oracle success_rate', 'val_seen success_rate', 'val_seen spl',
                       'val_unseen oracle success_rate', 'val_unseen success_rate', 'val_unseen spl']:
            v = max(dfs[log][metric])
            print("%s\t%s\t%.3f" % (log, metric, v))

    plots = [
        ('Loss', 'loss',['val_seen loss', 'val_unseen loss', 'train loss']),
        ('Navigation Error', 'm', ['val_seen nav_error', 'val_unseen nav_error']),
        ('Success', '%', ['val_seen success_rate', 'val_unseen success_rate'])
    ]

    colors = {
      'Student-forcing Val Seen': 'C0',
      'Student-forcing Val Unseen': 'C2',
      'Student-forcing Train': 'C4',
      'Teacher-forcing Val Seen': 'C1',
      'Teacher-forcing Val Unseen': 'C3',
      'Teacher-forcing Train': 'C5'
    }
    
    fig, axes = plt.subplots(ncols=3, squeeze=True, figsize=(13,3.25))
    handles = []
    labels = []
    for i,(title, ylabel, x_vars) in enumerate(plots):
        for log in logs:
            df = dfs[log]
            x = df['iteration']
            for col_name in x_vars:
                y = df[col_name]
                label = ' Train'
                if 'unseen' in col_name:
                    label = ' Val Unseen'
                elif 'seen' in col_name:
                    label = ' Val Seen'
                if i == 0:
                    label = logs[log]+label
                    labels.append(labels)
                    handles.append(axes[i].plot(x,y, colors[label], label=label))
                else:
                    axes[i].plot(x,y, colors[logs[log]+label], label=logs[log]+label)
        axes[i].set_title(title)
        axes[i].set_xlabel('Iteration')
        axes[i].set_ylabel(ylabel)

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.4)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[1].legend(handles = handles, labels=labels, loc='upper center', 
             bbox_to_anchor=(0.5, -0.35), fancybox=False, shadow=False, ncol=3)
    plt.setp(axes[1].get_legend().get_texts(), fontsize='12')
    plt.savefig('%s/training.png' % (PLOT_DIR))

        
def plot_final_scores():
    ''' Plot the scores '''
    font = {
      'size'   : 12
    }
    mpl.rc('font', **font)
    fig, ax = plt.subplots( nrows=1, ncols=1, figsize=(7,4) )  # create figure & 1 axis
    outfiles = [
        RESULT_DIR + 'seq2seq_sample_imagenet_%s_iter_20000.json',
        RESULT_DIR + 'seq2seq_teacher_imagenet_%s_iter_5000.json',
        RESULT_DIR + '%s_stop_agent.json',
        RESULT_DIR + '%s_random_agent.json'
    ]
    for split in ['val_seen']:
        ev = Evaluation([split])
        for i,outfile in enumerate(outfiles):
            score_summary,scores = ev.score(outfile % split)
            if i == 1:
                method = 'Teacher-forcing'
                ax.hist(scores['nav_errors'], bins=range(0,30,3), label=method, normed=True, histtype = 'step', linewidth=2.5, color='C1')
            elif i == 0:
                method = 'Student-forcing'
                ax.hist(scores['nav_errors'], bins=range(0,30,3), label=method, alpha=0.7, normed=True, color='C0')
            elif i == 2:
                method = 'Start locations'
                ax.hist(scores['nav_errors'], bins=range(0,30,3), label=method, normed=True, histtype = 'step', linewidth=2.5, color='C3')
            elif i == 3:
                method = 'Random agent'
                ax.hist(scores['nav_errors'], bins=range(0,30,3), label=method, normed=True, histtype = 'step', linewidth=2.5, color='C2')
    ax.set_title('Val Seen Navigation Error')
    ax.set_xlabel('Error (m)')
    ax.set_ylabel('Frequency')
    ax.set_ylim([0,0.14])
    ax.set_xlim([0,30])
    plt.axvline(x=3, color='black', linestyle='--')
    legend = ax.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig('%s/val_seen_error.png' % (PLOT_DIR))
    plt.close(fig)


if __name__ == '__main__':
    plot_training_curves()
    plot_final_scores()







