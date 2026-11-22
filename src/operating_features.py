import numpy as np


def operating_features(inputs):
    """Append temperature rise, shaft power in watts, and a wear-load interaction."""
    raw = np.asarray(inputs, dtype=float)
    _, air, process, rpm, torque, wear = raw.T
    return np.column_stack((raw, process - air, torque * rpm * (2 * np.pi / 60), wear * torque))
