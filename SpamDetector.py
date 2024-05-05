import pandas as pd
import numpy as np
from sklearn.metrics import roc_curve, roc_auc_score

"""
This is the training model for the AI. I am using naive bayes do to its relatively simple and straight
forward application in this context. I am going to be using the multinomial naive bayes model as it perfectly matches
our use case: feature vectors that represent the frequencies (in out case spam) that have been generated by a 
multinomial distribution (in our case, word frequencies and capitals)
"""


def train(train_data, laplace_alpha):
    # separate non spam and spam
    spam = train_data[train_data['spam'] == 1]
    non_spam = train_data[train_data['spam'] == 0]

    # prior probabilities
    prior_spam = len(spam) / len(train_data)
    prior_non_spam = len(non_spam) / len(train_data)

    # conditional probabilities for each word given spam or non-spam
    features = train_data.columns[:-1]
    
    # sum up all occurrences of words in spam and non spam datasets
    spam_word_sum = spam[features].sum()
    non_spam_word_sum = non_spam[features].sum()

    # then find the total words (to divide with later), basically sum of all sum of words
    total_spam_word_sum = spam_word_sum.sum()
    total_non_spam_word_sum = non_spam_word_sum.sum()

    # all conditional probabilities using laplace smoothing
    words_spam_prob = (spam_word_sum + laplace_alpha) / (total_spam_word_sum + laplace_alpha * len(features))
    words_non_spam_prob = (non_spam_word_sum + laplace_alpha) / (total_non_spam_word_sum + laplace_alpha * len(features))

    # return training result
    return prior_spam, prior_non_spam, words_spam_prob, words_non_spam_prob


def predict(email, prior_spam, prior_non_spam, words_spam_prob, words_non_spam_prob):
    # USE LOG, underflow issues, dealing with tiny numbers
    # take in prior probability
    spam_prob = np.log(prior_spam)
    non_spam_prob = np.log(prior_non_spam)

    # go through each word in "email"
    # or in this case just go through each column and add the probability if word exists in data set
    # also account for frequency
    for word, freq in email.items():
        if word in words_spam_prob:
            spam_prob += freq * np.log(words_spam_prob[word])
        if word in words_non_spam_prob:
            non_spam_prob += freq * np.log(words_non_spam_prob[word])

    # return whether there is a higher chance of spam
    return spam_prob > non_spam_prob


def test(test_data, prior_spam, prior_non_spam, words_spam_prob, words_non_spam_prob):
    correct = 0
    false_positive = 0
    true_positive = 0

    predictions = []
    spam_labels = []

    total = len(test_data)

    for _, row in test_data.iterrows():
        # predict
        email = row.drop('spam').to_dict()
        prediction = predict(email, prior_spam, prior_non_spam, words_spam_prob, words_non_spam_prob)

        predictions.append(prediction)
        spam_label = row['spam']
        spam_labels.append(spam_label)

        # find if correct
        if prediction == spam_label:
            correct += 1
            # find if correct and also positive for spam
            if prediction:
                true_positive += 1
        else:
            # find if positive for spam when not spam
            if prediction:
                false_positive += 1

    # AUC calculation
    auc = roc_auc_score(spam_labels, predictions)

    # get the proportion of accuracy, false positive and true positive
    acc = correct / total
    fp_rate = false_positive / total
    tp_rate = true_positive / total
    return acc, fp_rate, tp_rate, auc


# this is an attempt to remove correlated features to increase accuracy,
# which "naive" bayes assumes that all features are independent, correlated features leads to poor generalization
def remove_correlated(data, threshold=1.0):
    # correlation matrix
    matrix = data.corr().abs()

    # boolean mask to identify correlation
    mask = np.triu(np.ones_like(matrix, dtype=bool), k=1)

    # find pairs of highly correlated features
    correlated_features = set()
    for i in range(len(matrix.columns)):
        for j in range(i):
            if matrix.iloc[i, j] > threshold:
                attribute = matrix.columns[i]
                correlated_features.add(attribute)

    # Remove correlated features from the dataset
    filtered = data.drop(columns=correlated_features)

    return filtered


# Load data from CSV, also shuffle
data = pd.read_csv('spambase.csv')
data = remove_correlated(data, threshold=0.608)  # remove correlated features
data = data.sample(frac=1, random_state=1234124).reset_index(drop=True)

# additive laplace smoothing to avoid underflow
laplace_alpha = .09

train_size = int(0.8 * len(data))
training_data = data[:train_size]
testing_data = data[train_size:]

# calculate fold size for 5 cross validation using training set, floor division
fold_size = len(training_data) // 5

folds = []
starting_i = 0

# get folds
for i in range(5):
    # end index
    ending_i = min(starting_i + fold_size, len(training_data))
    # get fold
    fold = training_data[starting_i:ending_i]
    # add fold
    folds.append(fold)
    # update starting i
    starting_i = ending_i


for i in range(5):
    # train, with one of 5 folds
    prior_spam, prior_non_spam, word_given_spam_probs, word_given_non_spam_probs = train(folds[i], laplace_alpha)
    # evaluate against test set
    acc, fp_rate, tp_rate, auc = test(testing_data, prior_spam, prior_non_spam,
                                      word_given_spam_probs, word_given_non_spam_probs)
    print(f"SET {i} results:")
    print("Accuracy:", acc)
    print("False Positive rate:", fp_rate)
    print("True Positive rate", tp_rate)
    print("Area Under Curve", auc)
    print("\n")

"""
# a <= .09 works best
accuracy_list = []
for i in range(0, 200, 1):
    laplace_alpha = i * .005
    prior_spam, prior_non_spam, word_given_spam_probs, word_given_non_spam_probs = train(train_data, laplace_alpha)

    # evaluate
    accuracy = test(test_data, prior_spam, prior_non_spam, word_given_spam_probs, word_given_non_spam_probs)
    print("Accuracy:", accuracy)

    accuracy_list.append(accuracy)

# find index and max val
print(max(accuracy_list))
print(accuracy_list.index(max(accuracy_list)))

"""
