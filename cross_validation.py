import math
import random
import csv
import sys
import getopt
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
from copy import deepcopy
from tqdm import tqdm, trange
from scipy import stats

#sklearn library
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn import svm
from sklearn import metrics

# Import pytorch
import torch
import torch.nn as nn
import torch.nn.functional as func

from data_loading import *


# Neural network implementations
# ----------------------------------

# NN definition using PyTorch
class Net(nn.Module):

    def __init__(self, m):

        super(Net, self).__init__()

        self.fc1 = nn.Linear(m, 30)
        self.bn1 = nn.BatchNorm1d(30)
        self.drop1 = nn.Dropout(0.1)

        self.fc2 = nn.Linear(30, 30)
        self.bn2 = nn.BatchNorm1d(30)
        self.drop2 = nn.Dropout(0.1)

        self.fc3 = nn.Linear(30,2)

    def forward(self, x):

        x = self.fc1(x)
        x = self.bn1(x)
        x = Func.relu(x)
        x = self.drop1(x)

        x = self.fc2(x)
        x = self.bn2(x)
        x = Func.relu(x)
        x = self.drop2(x)

        x = self.fc3(x)

        return x


# Train neural network
def train(X_train, y_train, X_val, y_val , epochs=35, lr=0.1):

    X_train = torch.Tensor(X_train)#.cuda()
    y_train = torch.Tensor(y_train)#.cuda()
    X_val = torch.Tensor(X_val)#.cuda()
    y_val = torch.Tensor(y_val)#.cuda()

    net = Net(X_train.shape[1])#.cuda()

    losses_train = []
    losses_val = []
    acc = []
    nets = []

    criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.Adam(net.parameters(), lr=0.005)

    for _ in range(epochs):

        y_pred = net(X_train)

        loss_train = criterion(y_pred, y_train.long())

        losses_train.append(loss_train)
        
        y_pred_val = net(X_val)
        loss_val = criterion(y_pred_val, y_val.long())
        losses_val.append(loss_val)
        test_acc = y_val[y_val.long()==torch.argmax(y_pred_val,axis=1)].shape[0]/y_val.shape[0]
        acc.append(test_acc)

        nets.append(deepcopy(net))

        optimizer.zero_grad()
        loss_train.backward()
        optimizer.step()

    return max(acc), nets[np.argmax(np.asarray(acc))]
    


# Model Training Process
# ----------------------------------

def cross_validation_net(X, y, num_splits = 5, epochs=35, lr=0.1):

    kf = StratifiedKFold(n_splits = num_splits)

    total_acc = 0

    for train_index, val_index in kf.split(X, y):
        X_train, X_val = X[train_index], X[val_index]
        y_train, y_val = y[train_index], y[val_index]

        acc, model = train(X_train, y_train, X_val, y_val, epochs=epochs, lr=lr)
        total_acc += acc


    return total_acc / num_splits


def get_accuracy_net(X_train, y_train, X_test, y_test, num_splits=5, epochs=35, lrs=[0.1]): 

    best_acc = 0
    best_lr = lrs[0]
    for lr in lrs:

        acc = cross_validation_net(X_train, y_train, num_splits = num_splits, epochs=epochs, lr=lr)

        if(acc > best_acc):
            best_acc = acc
            best_lr = lr

    X_training, X_val, y_training, y_val = train_test_split(X_train, y_train, test_size=0.1, random_state=0) 

    acc, net = train(X_training, y_training, X_val, y_val, epochs=epochs, lr=best_lr)

    X_test = torch.Tensor(X_test)#.cuda()
    y_test = torch.Tensor(y_test)#.cuda()

    y_pred_test = net(X_test)

    test_acc = y_test[y_test.long()==torch.argmax(y_pred_test,axis=1)].shape[0]/y_test.shape[0]
    test_acc_0 = y_test[y_test==0][y_test.long()[y_test==0]==torch.argmax(y_pred_test[y_test==0],axis=1)].shape[0]/y_test[y_test==0].shape[0]
    test_acc_1 = y_test[y_test==1][y_test.long()[y_test==1]==torch.argmax(y_pred_test[y_test==1],axis=1)].shape[0]/y_test[y_test==1].shape[0]


    return test_acc, test_acc_0, test_acc_1


def net_single(X_train, y_train, X_test, y_test, num_splits=5, epochs=35, lrs=[0.1]):

    accuracies = []

    X_test = torch.Tensor(X_test)#.cuda()
    y_test = torch.Tensor(y_test)#.cuda()

    for i in trange(X_train.shape[1]):

        X_single = X_train[:,[i]]

        for lr in lrs:

            best_acc = 0
            best_lr = 0

            acc = cross_validation_net(X_single, y_train, num_splits = num_splits, epochs=epochs, lr=lr)

            if(acc > best_acc):
                best_acc = acc
                best_lr = lrs

        X_training, X_val, y_training, y_val = train_test_split(X_single, y_train, test_size=0.2, random_state=0) 

        acc, net = train(X_training, y_training, X_val, y_val, epochs=epochs, lr=best_lr)

        y_pred_test = net(X_test[:,[i]])
        test_acc = y_test[y_test.long()==torch.argmax(y_pred_test,axis=1)].shape[0]/y_test.shape[0]
        accuracies.append(test_acc)

    return np.asarray(accuracies)


def cross_validation(clf_func, X, y, param, num_splits = 5):
    """
    Given a classifier clf and training data X with labels y, performs
    k-fold cross validation with k=num_splits
    """
    kf = StratifiedKFold(n_splits = num_splits)

    total_acc = 0

    for train_index, val_index in kf.split(X, y):
        X_train, X_val = X[train_index], X[val_index]
        y_train, y_val = y[train_index], y[val_index]
        clf = clf_func(param)
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_val)

        total_acc +=  metrics.accuracy_score(y_val, y_pred)

    return total_acc / num_splits


def select_parameters(X, y, clf_func, params, num_splits = 5):
    """
    Performs hyperparemeter selection on training data.
    clf_func is a function that accepts a parameters from the params list,
    and returns a classifier with that paremeter setting
    """
    best_acc = 0
    best_param = params[0]
    for param in params:

        acc = cross_validation(clf_func, X, y, param, num_splits = num_splits)

        if(acc > best_acc):
            best_acc = acc
            best_param = param

    return best_acc, best_param


def get_accuracy(X_train, y_train, X_test, y_test, clf_func, params, num_splits = 5):

    best_acc, best_param = select_parameters(X_train, y_train, clf_func, params, num_splits=5)

    clf = clf_func(best_param)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = metrics.accuracy_score(y_test, y_pred)
    acc_0 = metrics.accuracy_score(y_test[y_test==0], y_pred[y_test==0])
    acc_1 = metrics.accuracy_score(y_test[y_test==1], y_pred[y_test==1])

    return acc, acc_0, acc_1, best_param


def run_single(X_train, y_train, X_test, y_test, clf_func, params, num_splits=5):

    accuracies = []

    for i in trange(X_train.shape[1]):

        X_single = X_train[:,[i]]

        best_acc, best_param = select_parameters(X_single, y_train, clf_func, params, num_splits=5)

        clf = clf_func(best_param)
        clf.fit(X_single, y_train)

        y_pred = clf.predict(X_test[:,[i]])
        acc = metrics.accuracy_score(y_test, y_pred)
        accuracies.append(acc)

    return np.asarray(accuracies)


def calc_entropy(X, y):

    def entropy(x):

        return stats.entropy(np.bincount(x) / len(x))

    base = entropy(y)
    entropy_gain = []
    for i in range(X.shape[1]):

        new_entropy = 0

        for x in np.unique(X[:,i]):

            y_subset = y[X[:,i]==x]
            new_entropy += entropy(y_subset) * len(y_subset) / len(y)

        entropy_gain.append(base - new_entropy)

    return np.asarray(entropy_gain)


def lin_regression(X, y):

    r2_values = []
    p_values = []

    for i in range(X.shape[1]):
        slope, intercept, r_value, p_value, std_err = stats.linregress(X[:,i],y)
        r2_values.append(r_value**2)
        p_values.append(p_value)

    return np.asarray(r2_values), np.asarray(p_values)


def handle_args(argv):

    clf = ""
    params = ""
    single = False
    time = 48
    threshold = 0

    try:
        opts, args = getopt.getopt(argv,"hc:p:t:s:",["clf=","params=", "time=", "single", "threshold="])
    except getopt.GetoptError:
        print('python3 cross_validation.py --clf <clf> --params <p1,p2,p3> [--time=t --single --threshold=#]')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('python3 cross_validation.py --clf <clf> -params <p1,p2,p3> [--time=t --single]')
            sys.exit()
        elif opt in ("-c", "--clf"):
            clf = arg
        elif opt in ("-p", "--params"):
            params = arg
        elif opt in ("-t", "--time"):
            time = arg
        elif opt in ("-s", "--single"):
            single = True
        elif opt == "--threshold":
            threshold = int(arg)

    if clf == "svm":
        clf_func = lambda x: svm.SVC(kernel='linear', C=x, random_state=1)
    elif clf == "knn":
        clf_func = lambda x: KNeighborsClassifier(n_neighbors = int(x))
    elif clf == "tree":
        clf_func = lambda x: DecisionTreeClassifier(criterion = "entropy", max_depth=int(x), random_state=1)
    elif clf == "entropy":
        clf_func = None 
    elif clf == "linreg":
        clf_func = None
    elif clf == "net":
        clf_func = None
    else:
        print("Classifier options 'svm', 'knn', 'tree', 'linreg', 'net")
        sys.exit(2)

    if(len(params) > 0):
        params = [float(elem) for elem in params.split(',')]

    return clf_func, params, clf, time, single, threshold


def main(argv):


    num_shuffles = 10
    clf_func, params, clf_str, time, single, threshold = handle_args(argv)
    edges, features, ind_to_neuron = get_network(time=time) 

    X, y = network_to_mat(edges,features)
  
    # If feature is > 0, set to 1
    # If feature == 0, set to 0
    y[y > threshold] = 1
    # np.random.shuffle(y) to shuffle labels

    Xs = []
    ys = []

    for i in range(num_shuffles):

        idx = np.random.RandomState(seed=i).permutation(X.shape[0])
        X_shuffle, y_shuffle = X[idx], y[idx]

        Xs.append(np.asarray(X_shuffle))
        ys.append(np.asarray(y_shuffle))

    if(clf_str == "entropy"):

        entropies = np.zeros(Xs[0].shape[1])

        for i in range(num_shuffles):
            X = Xs[i]
            y = ys[i]

            ent = calc_entropy(X,y)
            entropies = entropies * (i)/float(i+1) + ent / float(i+1)

        np.savetxt("entropies.txt", entropies, fmt='%10.5f')


    elif clf_str == "linreg":

        if(single):
            r2_values = np.zeros(Xs[0].shape[1])
            p_values = np.zeros(Xs[0].shape[1])

            for i in range(num_shuffles):
                X = Xs[i]
                y = ys[i]

                r2, p = lin_regression(X,y)
                
                r2_values = r2_values * (i)/float(i+1) + r2 / float(i+1)
                p_values = p_values * (i)/float(i+1) + p / float(i+1)

            np.savetxt("r2.txt", r2_values, fmt='%10.5f')
            np.savetxt("p.txt", p_values)

            alpha = 0.05
            threshold = alpha / len(y)
            # TODO: indexing may be off
            i = 0
            cnt = 0
            while i < len(p_values):
                if p_values[i] <= threshold:
                    print("SNP " + str(i) +  " has p-value " + str(p_values[i]))
                    cnt += 1
                i += 1
            print(cnt)

        else:

            r_values = []
            p_values = []
            for  i in range(num_shuffles):
                X, y, = Xs[i], ys[i]

                model = LinearRegression().fit(X,y)
                r_values.append(model.score(X,y))

            print(sum(r_values) / len(r_values))
            #print(sum(p_values) / len(p_values))
            #print(p_values)


    elif clf_str == "net":
        if(single):
            accs = 0
            for i in trange(num_shuffles):
                X = Xs[i]
                y = ys[i]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
                acc = net_single(X_train, y_train, X_test, y_test, lrs=params)
                accs = accs * (i)/float(i+1) + acc / float(i+1)

            np.savetxt("net_single.txt", accs, fmt='%10.5f')


        else:
            accs = 0
            accs_0 = 0
            accs_1 = 0
            for i in trange(num_shuffles):
                X = Xs[i]
                y = ys[i]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

                acc, acc_0, acc_1 = get_accuracy_net(X_train, y_train, X_test, y_test, lrs=params)
                accs += acc
                accs_0 += acc_0
                accs_1 += acc_1

            print("Accuracy overall: ", accs / num_shuffles)
            print("Accuracy non:     ", accs_0 / num_shuffles)
            print("Accuracy high:    ", accs_1 / num_shuffles)

    else:

        if (single):

            accuracies = np.zeros(Xs[0].shape[1])

            print(type(accuracies[0]))
            for i in range(num_shuffles):
                X = Xs[i]
                y = ys[i]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

                acc = run_single(X_train, y_train, X_test, y_test, clf_func, params)
                accuracies = accuracies * (i)/float(i+1) + acc / float(i+1)

            np.savetxt(str(clf_str) + "_single.txt", accuracies, fmt='%10.5f')

        else:
            accs = 0
            accs_0 = 0
            accs_1 = 0
            best_params = []
            for i in trange(num_shuffles):
                X = Xs[i]
                y = ys[i]

                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0, stratify=y)

                acc, acc_0, acc_1, best_param = get_accuracy(X_train, y_train, X_test, y_test, clf_func, params)
                accs += acc
                accs_0 += acc_0
                accs_1 += acc_1
                best_params.append(best_param)

            print("Accuracy overall: ", accs / num_shuffles)
            print("Accuracy non:     ", accs_0 / num_shuffles)
            print("Accuracy high:    ", accs_1 / num_shuffles)
            print(best_params)


if __name__ == '__main__':
    main(sys.argv[1:])
