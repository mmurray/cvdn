''' Utils for io, language, connectivity graphs etc '''

import os
import sys
import re
import string
import json
import time
import math
from collections import Counter
import numpy as np
import networkx as nx


# padding, unknown word, end of sentence
base_vocab = ['<PAD>', '<UNK>', '<EOS>', '<NAV>', '<ORA>', '<TAR>']
padding_idx = base_vocab.index('<PAD>')

def load_nav_graphs(scans):
    ''' Load connectivity graph for each scan '''

    def distance(pose1, pose2):
        ''' Euclidean distance between two graph poses '''
        return ((pose1['pose'][3]-pose2['pose'][3])**2\
          + (pose1['pose'][7]-pose2['pose'][7])**2\
          + (pose1['pose'][11]-pose2['pose'][11])**2)**0.5

    graphs = {}
    for scan in scans:
        with open('connectivity/%s_connectivity.json' % scan) as f:
            G = nx.Graph()
            positions = {}
            data = json.load(f)
            for i,item in enumerate(data):
                if item['included']:
                    for j,conn in enumerate(item['unobstructed']):
                        if conn and data[j]['included']:
                            positions[item['image_id']] = np.array([item['pose'][3], 
                                    item['pose'][7], item['pose'][11]]);
                            assert data[j]['unobstructed'][i], 'Graph should be undirected'
                            G.add_edge(item['image_id'],data[j]['image_id'],weight=distance(item,data[j]))
            nx.set_node_attributes(G, values=positions, name='position')
            graphs[scan] = G
    return graphs


def load_datasets(splits):
    data = []
    for split in splits:
        assert split in ['train', 'val_seen', 'val_unseen', 'test']
        with open('tasks/NDH_NavHistConcat/data/%s.json' % split) as f:
            data += json.load(f)
    return data


class Tokenizer(object):
    ''' Class to tokenize and encode a sentence. '''
    SENTENCE_SPLIT_REGEX = re.compile(r'(\W+)')  # Split on any non-alphanumeric character
  
    def __init__(self, vocab=None, encoding_length=20):
        self.encoding_length = encoding_length
        self.vocab = vocab
        self.word_to_index = {}
        if vocab:
            for i,word in enumerate(vocab):
                self.word_to_index[word] = i

    def split_sentence(self, sentence):
        ''' Break sentence into a list of words and punctuation '''
        toks = []
        for word in [s.strip().lower() for s in self.SENTENCE_SPLIT_REGEX.split(sentence.strip()) if len(s.strip()) > 0]:
            # Break up any words containing punctuation only, e.g. '!?', unless it is multiple full stops e.g. '..'
            if all(c in string.punctuation for c in word) and not all(c in '.' for c in word):
                toks += list(word)
            else:
                toks.append(word)
        return toks

    def encode_sentence(self, sentences, seps=None):
        if len(self.word_to_index) == 0:
            sys.exit('Tokenizer has no vocab')
        encoding = []
        if type(sentences) is not list:
            sentences = [sentences]
            seps = [seps]
        for sentence, sep in zip(sentences, seps):
            if sep is not None:
                encoding.append(self.word_to_index[sep])
            for word in self.split_sentence(sentence)[::-1]:  # reverse input sentences
                if word in self.word_to_index:
                    encoding.append(self.word_to_index[word])
                else:
                    encoding.append(self.word_to_index['<UNK>'])
        encoding.append(self.word_to_index['<EOS>'])
        if len(encoding) < self.encoding_length:
            encoding += [self.word_to_index['<PAD>']] * (self.encoding_length-len(encoding))

        # cut off the LHS of the encoding if it's over-size (e.g., words from the end of an individual command,
        # favoring those at the beginning of the command (since inst word order is reversed) (e.g., cut off the early
        # instructions in a dialog if the dialog is over size, preserving the latest QA pairs).
        prefix_cut = max(0, len(encoding) - self.encoding_length)
        return np.array(encoding[prefix_cut:])

    def decode_sentence(self, encoding):
        sentence = []
        for ix in encoding:
            if ix == self.word_to_index['<PAD>']:
                break
            else:
                sentence.append(self.vocab[ix])
        return " ".join(sentence[::-1]) # unreverse before output
    
    def pad_or_trunc_sequence(self, seq, enc_len, padding):
        if len(seq) < enc_len:
            seq += [padding] * (enc_len-len(seq))
        prefix_cut = max(0, len(seq) - enc_len)
        return np.array(seq[prefix_cut:])


def build_vocab(splits=['train'], min_count=5, start_vocab=base_vocab):
    ''' Build a vocab, starting with base vocab containing a few useful tokens. '''
    count = Counter()
    t = Tokenizer()
    data = load_datasets(splits)
    for item in data:
        for turn in item['dialog_history']:
            count.update(t.split_sentence(turn['message']))
    vocab = list(start_vocab)

    # Add words that are object targets.
    targets = set()
    for item in data:
        target = item['target']
        targets.add(target)
    vocab.extend(list(targets))

    # Add words above min_count threshold.
    for word, num in count.most_common():
        if word in vocab:  # targets strings may also appear as regular vocabulary.
            continue
        if num >= min_count:
            vocab.append(word)
        else:
            break
    return vocab


def write_vocab(vocab, path):
    print 'Writing vocab of size %d to %s' % (len(vocab),path)
    with open(path, 'w') as f:
        for word in vocab:
            f.write("%s\n" % word)


def read_vocab(path):
    with open(path) as f:
        vocab = [word.strip() for word in f.readlines()]
    return vocab


def asMinutes(s):
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)


def timeSince(since, percent):
    now = time.time()
    s = now - since
    es = s / percent
    rs = es - s
    return '%s (- %s)' % (asMinutes(s), asMinutes(rs))

