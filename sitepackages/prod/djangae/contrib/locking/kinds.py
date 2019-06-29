

class LOCK_KINDS(object):
    """ The different kinds of lock which you can use.
        WEAK is not guaranteed to be robust, but can be used for situations where avoiding
        simultaneous code execution is preferable but not critical.
        STRONG is for where preventing simultaneous code execution is *required*.
    """
    WEAK = 'weak'
    STRONG = 'strong'

