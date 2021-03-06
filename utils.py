import os
import sys 
import json
import torch
import shutil
import numpy as np 
from config import config
from torch import nn
import torch.nn.functional as F 
from sklearn.metrics import f1_score
from torch.autograd import Variable
import pandas as pd


# Code referenced from https://gist.github.com/gyglim/1f8dfb1b5c82627ae3efcfbbadb9f514
import tensorflow as tf
import scipy.misc
from io import BytesIO  # Python 3.x

# Early stopping
class EarlyStopping:
    """Early stops the training if validation loss dosen't improve after a given patience."""
    def __init__(self, patience=7, verbose=False):
        """
        Args:
            patience (int): How long to wait after last time validation loss improved.
                            Default: 7
            verbose (bool): If True, prints a message for each validation loss improvement.
                            Default: False
        """
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.val_loss_min = np.Inf

    def __call__(self, val_loss, model):

        score = -val_loss

        # this is for f1_score
        # score = val_loss

        if self.best_score is None:
            self.best_score = score
        elif score < self.best_score:
            self.counter += 1
            print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.update_loss_min(val_loss, model)
            self.counter = 0



    def update_loss_min(self, val_loss, model):
        '''Saves model when validation loss decrease.'''
        if self.verbose:
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}) ...')
        # torch.save(model.state_dict(), 'checkpoint.pt')
        self.val_loss_min = val_loss


# save best model
def save_checkpoint(state, is_best_loss,is_best_f1,fold, kfold):
    filename = '{0}{1}/fold_{2}/checkpoint_{3}_fold{4}.pth.tar'.format(
        config.weights, config.model_name, str(fold), state['epoch'], kfold)
    # filename = config.weights + config.model_name + os.sep +str(fold) + os.sep + "checkpoint.pth.tar"
    torch.save(state, filename)
    # if is_best_loss:
    #     shutil.copyfile(filename,"%s/%s_fold_%s_model_best_loss.pth.tar"%(config.best_models,config.model_name,str(fold)))
    # if is_best_f1:
    #     shutil.copyfile(filename,"%s/%s_fold_%s_model_best_f1.pth.tar"%(config.best_models,config.model_name,str(fold)))

# evaluate meters
class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

# print logger
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout  #stdout
        self.file = None

    def open(self, file, mode=None):
        if mode is None: mode ='w'
        self.file = open(file, mode)

    def write(self, message, is_terminal=1, is_file=1 ):
        if '\r' in message: is_file=0

        if is_terminal == 1:
            self.terminal.write(message)
            self.terminal.flush()
            #time.sleep(1)

        if is_file == 1:
            self.file.write(message)
            self.file.flush()

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass

class TFLogger(object):

    def __init__(self, log_dir):
        """Create a summary writer logging to log_dir."""
        self.writer = tf.summary.FileWriter(log_dir)

    def scalar_summary(self, tag, value, step):
        """Log a scalar variable."""
        summary = tf.Summary(value=[tf.Summary.Value(tag=tag, simple_value=value)])
        self.writer.add_summary(summary, step)

    def image_summary(self, tag, images, step):
        """Log a list of images."""

        img_summaries = []
        for i, img in enumerate(images):
            # Write the image to a string
            try:
                s = StringIO()
            except:
                s = BytesIO()
            scipy.misc.toimage(img).save(s, format="png")

            # Create an Image object
            img_sum = tf.Summary.Image(encoded_image_string=s.getvalue(),
                                       height=img.shape[0],
                                       width=img.shape[1])
            # Create a Summary value
            img_summaries.append(tf.Summary.Value(tag='%s/%d' % (tag, i), image=img_sum))

        # Create and write Summary
        summary = tf.Summary(value=img_summaries)
        self.writer.add_summary(summary, step)

    def histo_summary(self, tag, values, step, bins=1000):
        """Log a histogram of the tensor of values."""

        # Create a histogram using numpy
        counts, bin_edges = np.histogram(values, bins=bins)

        # Fill the fields of the histogram proto
        hist = tf.HistogramProto()
        hist.min = float(np.min(values))
        hist.max = float(np.max(values))
        hist.num = int(np.prod(values.shape))
        hist.sum = float(np.sum(values))
        hist.sum_squares = float(np.sum(values ** 2))

        # Drop the start of the first bin
        bin_edges = bin_edges[1:]

        # Add bin edges and counts
        for edge in bin_edges:
            hist.bucket_limit.append(edge)
        for c in counts:
            hist.bucket.append(c)

        # Create and write Summary
        summary = tf.Summary(value=[tf.Summary.Value(tag=tag, histo=hist)])
        self.writer.add_summary(summary, step)
        self.writer.flush()

# class FocalLoss(nn.Module):
#     def __init__(self, alpha=0.25,gamma=2):
#         super(FocalLoss, self).__init__()
#         self.alpha = alpha
#         self.gamma = gamma
#
#     def forward(self, x, y):
#         '''Focal loss.
#         Args:
#           x: (tensor) sized [N,D].
#           y: (tensor) sized [N,].
#         Return:
#           (tensor) focal loss.
#         '''
#         t = Variable(y).cuda()  # [N,20]
#
#         p = x.sigmoid()
#         pt = p*t + (1-p)*(1-t)         # pt = p if t > 0 else 1-p
#         w = self.alpha*t + (1-self.alpha)*(1-t)  # w = alpha if t > 0 else 1-alpha
#         w = w * (1-pt).pow(self.gamma)
#         return F.binary_cross_entropy_with_logits(x, t, w, size_average=False)

# class FocalLoss(nn.Module):
#     def __init__(self, gamma=2, alpha=0.25, size_average=False):
#         super(FocalLoss, self).__init__()
#         self.gamma = gamma
#         self.alpha = alpha
#         self.size_average = size_average
#         # if isinstance(alpha, (float, int)):
#         #     if self.alpha > 1:
#         #         raise ValueError('Not supported value, alpha should be small than 1.0')
#         #     else:
#         #         self.alpha = torch.Tensor([alpha, 1.0 - alpha])
#         # if isinstance(alpha, list): self.alpha = torch.Tensor(alpha)
#
#
#     def forward(self, x, y):
#
#         t = Variable(y).cuda()
#         p = x.sigmoid()
#         pt = p*t + (1-p)*(1-t)         # pt = p if t > 0 else 1-p
#         logpt = torch.log(pt + 1e-10)
#
#         # alpha = alpha if t > 0 else 1-alpha
#         alpha = self.alpha *t + (1-self.alpha)*(1-t)
#         loss = -1 * alpha * torch.pow((1 - pt), self.gamma) * logpt
#
#         if self.size_average:
#             return loss.mean()
#         else:
#             return loss.sum()


class FocalLoss(nn.Module):
    def __init__(self, gamma=2):
        super().__init__()
        self.gamma = gamma

    def forward(self, input, target):
        if not (target.size() == input.size()):
            raise ValueError("Target size ({}) must be the same as input size ({})"
                             .format(target.size(), input.size()))

        max_val = (-input).clamp(min=0)
        loss = input - input * target + max_val + \
               ((-max_val).exp() + (-input - max_val).exp()).log()

        invprobs = F.logsigmoid(-input * (target * 2.0 - 1.0))
        loss = (invprobs * self.gamma).exp() * loss

        return loss.sum(dim=1).mean()

# F1_loss
# https://www.kaggle.com/rejpalcz/best-loss-function-for-f1-score-metric
# https://discuss.pytorch.org/t/build-your-own-loss-function-in-pytorch/235/3
# https://www.kaggle.com/c/human-protein-atlas-image-classification/discussion/70225?
class F1_loss(nn.Module):
    def __init__(self):
        super(F1_loss, self).__init__()
        self.__small_value = 1e-6
        self.beta = 1
    def forward(self, logits, labels):
        batch_size = logits.size()[0]
        p = F.sigmoid(logits)
        l = Variable(labels)
        tp = torch.sum(l * p, 1)
        tn = torch.sum((1-l) * (1-p), 1)
        fp = torch.sum((1-l) * p, 1)
        fn = torch.sum(l * (1-p), 1)
        precise = tp / (tp + fp + self.__small_value)
        recall = tp / (tp + fn + self.__small_value)
        fs = (1 + self.beta * self.beta) * precise * recall / (self.beta * self.beta * precise + recall + self.__small_value)
        # loss = fs.sum() / batch_size
        loss = fs.mean()
        return (1 - loss)


def acc(preds,targs,th=0.0):
    preds = (preds > th).int()
    targs = targs.int()
    return (preds==targs).float().mean()

def get_learning_rate(optimizer):
    lr=[]
    for param_group in optimizer.param_groups:
       lr +=[ param_group['lr'] ]

    #assert(len(lr)==1) #we support only one param_group
    lr = lr[0]

    return lr

def time_to_str(t, mode='min'):
    if mode=='min':
        t  = int(t)/60
        hr = t//60
        min = t%60
        return '%2d hr %02d min'%(hr,min)

    elif mode=='sec':
        t   = int(t)
        min = t//60
        sec = t%60
        return '%2d min %02d sec'%(min,sec)


    else:
        raise NotImplementedError


# creating duplicates for rare classes in train set
class Oversampling:
    def __init__(self, path):
        self.train_labels = pd.read_csv(path).set_index('Id')
        self.train_labels['Target'] = [[int(i) for i in s.split()]
                                       for s in self.train_labels['Target']]
        # set the minimum number of duplicates for each class
        self.multi = [1, 1, 1, 1, 1, 1, 1, 1,
                      4, 4, 4, 1, 1, 1, 1, 4,
                      1, 1, 1, 1, 2, 1, 1, 1,
                      1, 1, 1, 4]

    def get(self, image_id):
        labels = self.train_labels.loc[image_id, 'Target'] if image_id \
                                                              in self.train_labels.index else []
        m = 1
        for l in labels:
            if m < self.multi[l]:
                m = self.multi[l]
        return m

if __name__ == '__main__':
    with open(os.path.join("./input/protein-trainval-split", 'tr_names.txt'), 'r') as text_file:
        train_names = text_file.read().split(',')

    s =  Oversampling("./input/train.csv")
    train_names = [idx for idx in train_names for _ in range(s.get(idx))]
    print(len(train_names), flush=True)



