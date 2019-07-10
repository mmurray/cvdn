import argparse

import torch
import torch.nn as nn
from torch.autograd import Variable
from torch import optim
import torch.nn.functional as F

import os
import time
import numpy as np
import pandas as pd
from collections import defaultdict

from utils import read_vocab,write_vocab,build_vocab,Tokenizer,padding_idx,timeSince
from env import R2RBatch
from model import EncoderLSTM, AttnDecoderLSTM, ConcatEncoderLSTM
from agent import Seq2SeqAgent
from eval import Evaluation


TRAIN_VOCAB = 'tasks/NDH_NavHistConcat/data/train_vocab.txt'
TRAINVAL_VOCAB = 'tasks/NDH_NavHistConcat/data/trainval_vocab.txt'
RESULT_DIR = 'tasks/NDH_NavHistConcat/results/'
SNAPSHOT_DIR = 'tasks/NDH_NavHistConcat/snapshots/'
PLOT_DIR = 'tasks/NDH_NavHistConcat/plots/'

IMAGENET_FEATURES = 'img_features/ResNet-152-imagenet.tsv'

# Training settings.
agent_type = 'seq2seq'

# Fixed params from MP.
features = IMAGENET_FEATURES
feature_size = 2048
batch_size = 100
word_embedding_size = 256
action_embedding_size = 32
target_embedding_size = 32
hidden_size = 512
bidirectional = False
dropout_ratio = 0.5
learning_rate = 0.0001
weight_decay = 0.0005

def train(train_env, encoder, decoder, n_iters, path_type, history, feedback_method, max_episode_len, MAX_INPUT_LENGTH, model_prefix,
    log_every=100, val_envs=None):
    ''' Train on training set, validating on both seen and unseen. '''
    if val_envs is None:
        val_envs = {}

    if agent_type == 'seq2seq':
        agent = Seq2SeqAgent(train_env, "", encoder, decoder, max_episode_len)
    else:
        sys.exit("Unrecognized agent_type '%s'" % agent_type)
    print 'Training a %s agent with %s feedback' % (agent_type, feedback_method)
    encoder_optimizer = optim.Adam(encoder.parameters(), lr=learning_rate, weight_decay=weight_decay)
    decoder_optimizer = optim.Adam(decoder.parameters(), lr=learning_rate, weight_decay=weight_decay) 

    data_log = defaultdict(list)
    start = time.time()

    best_success = {}
   
    for idx in range(0, n_iters, log_every):

        interval = min(log_every,n_iters-idx)
        iter = idx + interval
        data_log['iteration'].append(iter)

        # Train for log_every interval
        agent.train(encoder_optimizer, decoder_optimizer, interval, feedback=feedback_method)
        train_losses = np.array(agent.losses)
        assert len(train_losses) == interval
        train_loss_avg = np.average(train_losses)
        data_log['train loss'].append(train_loss_avg)
        loss_str = 'train loss: %.4f' % train_loss_avg

        # Run validation
        for env_name, (env, evaluator) in val_envs.iteritems():
            agent.env = env
            agent.results_path = '%s%s_%s_iter_%d.json' % (RESULT_DIR, model_prefix, env_name, iter)
            # Get validation loss under the same conditions as training
            agent.test(use_dropout=True, feedback=feedback_method, allow_cheat=True)
            val_losses = np.array(agent.losses)
            val_loss_avg = np.average(val_losses)
            data_log['%s loss' % env_name].append(val_loss_avg)
            # Get validation distance from goal under test evaluation conditions
            agent.test(use_dropout=False, feedback='argmax')
            agent.write_results()
            score_summary, _ = evaluator.score(agent.results_path)
            loss_str += ', %s loss: %.4f' % (env_name, val_loss_avg)
            for metric, val in score_summary.iteritems():
                data_log['%s %s' % (env_name, metric)].append(val)
                if metric in ['success_rate', 'oracle success_rate', 'oracle path_success_rate', 'dist_to_end_reduction']:
                    loss_str += ', %s: %.3f' % (metric, val)
                    if env_name not in best_success or best_success[env_name] < val:
                        best_success[env_name] = val

        agent.env = train_env

        print('%s (%d %d%%) %s' % (timeSince(start, float(iter)/n_iters),
                                             iter, float(iter)/n_iters*100, loss_str))
        df = pd.DataFrame(data_log)
        df.set_index('iteration')
        df_path = '%s%s-log.csv' % (PLOT_DIR, model_prefix)
        df.to_csv(df_path)
        
        split_string = "-".join(train_env.splits)
        enc_path = '%s%s_%s_enc_iter_%d' % (SNAPSHOT_DIR, model_prefix, split_string, iter)
        dec_path = '%s%s_%s_dec_iter_%d' % (SNAPSHOT_DIR, model_prefix, split_string, iter)
        agent.save(enc_path, dec_path)

    print("best success: " + str(best_success))


def setup():
    torch.manual_seed(1)
    torch.cuda.manual_seed(1)
    # Check for vocabs
    if not os.path.exists(TRAIN_VOCAB):
        write_vocab(build_vocab(splits=['train']), TRAIN_VOCAB)
    if not os.path.exists(TRAINVAL_VOCAB):
        write_vocab(build_vocab(splits=['train', 'val_seen', 'val_unseen']), TRAINVAL_VOCAB)


def test_submission(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix):
    ''' Train on combined training and validation sets, and generate test submission. '''
  
    setup()

    # Create a batch training environment that will also preprocess text
    vocab = read_vocab(TRAINVAL_VOCAB)
    tok = Tokenizer(vocab=vocab, encoding_length=MAX_INPUT_LENGTH)
    train_env = R2RBatch(features, batch_size=batch_size, splits=['train', 'val_seen', 'val_unseen'], tokenizer=tok,
                         path_type=path_type, history=history)
    
    # Build models and train
    enc_hidden_size = hidden_size//2 if bidirectional else hidden_size
    encoder = EncoderLSTM(len(vocab), word_embedding_size, enc_hidden_size, padding_idx, 
                  dropout_ratio, bidirectional=bidirectional).cuda()
    decoder = AttnDecoderLSTM(Seq2SeqAgent.n_inputs(), Seq2SeqAgent.n_outputs(),
                  action_embedding_size, hidden_size, dropout_ratio).cuda()
    train(train_env, encoder, decoder, n_iters, path_type, history, feedback_method, max_episode_len, MAX_INPUT_LENGTH, model_prefix)

    # Generate test submission
    test_env = R2RBatch(features, batch_size=batch_size, splits=['test'], tokenizer=tok,
                        path_type=path_type, history=history)
    agent = Seq2SeqAgent(test_env, "", encoder, decoder, max_episode_len)
    agent.results_path = '%s%s_%s_iter_%d.json' % (RESULT_DIR, model_prefix, 'test', 20000)
    agent.test(use_dropout=False, feedback='argmax')
    agent.write_results()


# NOTE: only available to us, now, for writing the paper.
def train_test(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix):
    ''' Train on the training set, and validate on the test split. '''

    setup()
    # Create a batch training environment that will also preprocess text
    vocab = read_vocab(TRAINVAL_VOCAB)
    tok = Tokenizer(vocab=vocab, encoding_length=MAX_INPUT_LENGTH)
    train_env = R2RBatch(features, batch_size=batch_size, splits=['train', 'val_seen', 'val_unseen'], tokenizer=tok,
                         path_type=path_type, history=history)

    # Creat validation environments
    val_envs = {split: (R2RBatch(features, batch_size=batch_size, splits=[split],
                                 tokenizer=tok, path_type=path_type, history=history),
                        Evaluation([split], path_type=path_type)) for split in ['test']}

    # Build models and train
    enc_hidden_size = hidden_size // 2 if bidirectional else hidden_size
    encoder = EncoderLSTM(len(vocab), word_embedding_size, enc_hidden_size, padding_idx,
                          dropout_ratio, bidirectional=bidirectional).cuda()
    decoder = AttnDecoderLSTM(Seq2SeqAgent.n_inputs(), Seq2SeqAgent.n_outputs(),
                              action_embedding_size, hidden_size, dropout_ratio).cuda()
    train(train_env, encoder, decoder, n_iters, path_type, history, feedback_method, max_episode_len, MAX_INPUT_LENGTH,
          model_prefix, val_envs=val_envs)


def train_val(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix):
    ''' Train on the training set, and validate on seen and unseen splits. '''
  
    setup()
    # Create a batch training environment that will also preprocess text
    vocab = read_vocab(TRAIN_VOCAB)
    tok = Tokenizer(vocab=vocab, encoding_length=MAX_INPUT_LENGTH)
    train_env = R2RBatch(features, batch_size=batch_size, splits=['train'], tokenizer=tok,
                         path_type=path_type, history=history)

    # Creat validation environments
    val_envs = {split: (R2RBatch(features, batch_size=batch_size, splits=[split], 
                tokenizer=tok, path_type=path_type, history=history),
                Evaluation([split], path_type=path_type)) for split in ['val_seen', 'val_unseen']}

    # Build models and train
    enc_hidden_size = hidden_size//2 if bidirectional else hidden_size
    # encoder = EncoderLSTM(len(vocab), word_embedding_size, enc_hidden_size, padding_idx, 
    #               dropout_ratio, bidirectional=bidirectional).cuda()
    encoder = ConcatEncoderLSTM(len(vocab), word_embedding_size, feature_size, enc_hidden_size, enc_hidden_size, padding_idx, 
                   dropout_ratio, bidirectional=bidirectional).cuda()
    decoder = AttnDecoderLSTM(Seq2SeqAgent.n_inputs(), Seq2SeqAgent.n_outputs(),
                  action_embedding_size, hidden_size, dropout_ratio).cuda()
    train(train_env, encoder, decoder, n_iters,
          path_type, history, feedback_method, max_episode_len, MAX_INPUT_LENGTH, model_prefix, val_envs=val_envs)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--path_type', type=str, required=True,
                        help='planner_path or player_path')
    parser.add_argument('--history', type=str, required=True,
                        help='oracle_ans, nav_q_oracle_ans, or all')
    parser.add_argument('--feedback', type=str, required=True,
                        help='teacher or sample')
    parser.add_argument('--eval_type', type=str, required=True,
                        help='val or test')
    args = parser.parse_args()

    assert args.path_type in ['planner_path', 'player_path']
    assert args.history in ['target', 'oracle_ans', 'nav_q_oracle_ans', 'all']
    assert args.feedback in ['sample', 'teacher']
    assert args.eval_type in ['val', 'test']

    # Set default args.
    path_type = args.path_type
    # In MP, max_episode_len = 20 while average hop range [4, 7], e.g. ~3x max.
    # max_episode_len has to account for turns; this heuristically allowed for about 1 turn per hop.
    if path_type == 'planner_path':
        max_episode_len = 20  # [1, 6], e.g., ~3x max
    else:
        max_episode_len = 120  # [2, 41], e.g., ~3x max

    # Input settings.
    history = args.history
    # In MP, MAX_INPUT_LEN = 80 while average utt len is 29, e.g., a bit less than 3x avg.
    if history == 'target':
        MAX_INPUT_LENGTH = 3  # [<TAR> target <EOS>] fixed length.
    elif history == 'oracle_ans':
        MAX_INPUT_LENGTH = 70  # 16.16+/-9.67 ora utt len, 35.5 at x2 stddevs. 71 is double that.
    elif history == 'nav_q_oracle_ans':
        MAX_INPUT_LENGTH = 120  # 11.24+/-6.43 [plus Ora avg], 24.1 at x2 std. 71+48 ~~ 120 per QA doubles both.
    else:
        MAX_INPUT_LENGTH = 120 * 6  # 4.93+/-3.21 turns -> 2.465+/-1.605 Q/A. 5.67 at x2 std. Call it 6 (real max 13).

    # Training settings.
    feedback_method = args.feedback
    n_iters = 5000 if feedback_method == 'teacher' else 20000

    # Model prefix to uniquely id this instance.
    model_prefix = '%s-seq2seq-%s-%s-%s-imagenet' % (args.eval_type, history, path_type, feedback_method)

    if args.eval_type == 'val':
        train_val(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix)
    else:
        train_test(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix)

    # test_submission(path_type, max_episode_len, history, MAX_INPUT_LENGTH, feedback_method, n_iters, model_prefix)
