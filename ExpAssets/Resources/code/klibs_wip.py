import random
from klibs.KLStructure import FactorSet


class Block(object):
    """Defines a custom block of trials.

    """
    def __init__(self, factors, label=None, trials=None, practice=False):
        self.practice = practice
        self.label = label
        if not isinstance(factors, FactorSet):
            factors = FactorSet(factors)
        self._factors = factors
        self.trialcount = trials if trials else self._factors.set_length
    
    def get_trials(self, full_shuffle=False):
        """Generates a shuffled set of trials from the block.

        """
        trials = []
        while len(trials) < self.trialcount:
            new = self._factors._get_combinations()
            remaining = self.trialcount - len(trials)
            random.shuffle(new)
            if remaining < len(new):
                new = new[:remaining]
            trials += new

        if full_shuffle:
            random.shuffle(trials)

        return trials
        
    @property
    def factors(self):
        """list: The names of all trial factors used in the block."""
        return self._factors.names


def block_to_str(block, trials, num):
    # Generates a string describing the structure and factor levels for each
    # trial in a given block
    out = []
    col_pad = {}
    block_header = "\n=== Block {0} ({1} trials{2}) ===\n"
    factors = block.factors

    # Get max character length for each factor level for sake of alignment
    for f in factors:
        if not f in col_pad.keys():
            col_pad[f] = len(f)
        for level in block._factors._factors[f]:
            if len(str(level)) > col_pad[f]:
                col_pad[f] = len(str(level))

    # Generate a header for the block
    practice = ", practice" if block.practice else ""
    out.append(block_header.format(num, len(trials), practice))
    if len(factors):
        out.append(" ".join([f.ljust(col_pad[f]) for f in factors]))
        out.append(" ".join(["-" * col_pad[f] for f in factors]))

    # Write the factor levels for each trial in the block
    if len(factors):
        for trial in trials:
            out.append(" ".join([str(trial[f]).ljust(col_pad[f]) for f in factors]))

    out.append("")
    return "\n".join(out)
