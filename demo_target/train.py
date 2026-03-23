"""
Single editable target file for the local demo.

The search loop mutates only these constants.
"""

ALPHA = 0.725669
BETA = -1.100000
GAMMA = 2.800000
DELTA = 0.249982
def current_params() -> dict[str, float]:
    return {
        "ALPHA": ALPHA,
        "BETA": BETA,
        "GAMMA": GAMMA,
        "DELTA": DELTA,
    }
