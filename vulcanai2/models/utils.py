"""Define utility functions used by models."""
import numpy as np
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import LabelBinarizer


def round_list(raw_list, decimals=4):
    """
    Return the same list with each item rounded off.

    Parameters
    ----------
    raw_list : float list
        float list to round.
    decimals : int
        How many decimal points to round to.

    Returns
    -------
    rounded_list : float list
        The rounded list in the same shape as raw_list.

    """
    return [round(item, decimals) for item in raw_list]


def get_confusion_matrix(predictions, targets):
    """
    Calculate the confusion matrix for classification network predictions.

    Parameters
    ----------
    predictions : numpy.ndarray
        The classes predicted by the network. Does not take one hot vectors.
    targets : numpy.ndarray
        the classes of the ground truth. Does not take one hot vectors.

    Returns
    -------
    confusion_matrix : numpy.ndarray
        The confusion matrix.

    """
    if len(predictions.shape) == 2:
        predictions = predictions[:, 0]
    if len(targets.shape) == 2:
        targets = targets[:, 0]
    return confusion_matrix(y_true=targets,
                            y_pred=predictions)


def get_one_hot(in_matrix):
    """
    Reformat truth matrix to same size as the output of the dense network.

    Parameters
    ----------
    in_matrix : numpy.ndarray
        The categorized 1D matrix

    Returns
    -------
    one_hot : numpy.ndarray
        A one-hot matrix representing the categorized matrix

    """
    if in_matrix.dtype.name == 'category':
        custom_array = in_matrix.cat.codes

    elif isinstance(in_matrix, np.ndarray):
        custom_array = in_matrix

    else:
        raise ValueError("Input matrix cannot be converted.")

    lb = LabelBinarizer()
    return np.array(lb.fit_transform(custom_array), dtype='float32')
