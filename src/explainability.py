from math import comb

import numpy as np


def class_contributions(model, sample, reference, class_index):
    """Exact Shapley differences against one reference, for the six sensor inputs."""
    count = len(reference)
    masks = np.arange(1 << count)
    bits = 1 << np.arange(count)
    included = (masks[:, None] & bits) != 0
    hybrids = np.where(included, sample, reference)
    scores = model.predict_proba(hybrids)[:, class_index]
    sizes = included.sum(axis=1)
    contributions = []
    for feature, bit in enumerate(bits):
        without = masks[~included[:, feature]]
        weights = [1 / (count * comb(count - 1, size)) for size in sizes[without]]
        contributions.append(np.dot(weights, scores[without | bit] - scores[without]))
    return scores[0], contributions
