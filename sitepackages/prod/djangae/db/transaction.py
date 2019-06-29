import copy
import functools
import threading

from google.appengine.api.datastore import (
    CreateTransactionOptions,
    _GetConnection,
    _PushConnection,
    _PopConnection,
    _SetConnection,
    IsInTransaction
)
from google.appengine.datastore.datastore_rpc import TransactionOptions

from djangae.db.backends.appengine import caching


def in_atomic_block():
    # At the moment just a wrapper around App Engine so that
    # users don't have to use two different APIs
    return IsInTransaction()


# Because decorators are only instantiated once per function, we need to make sure any state
# stored on them is both thread-local (to prevent function calls in different threads
# interacting with each other) and safe to use recursively (by using a stack of state)

class ContextState(object):
    "Stores state per-call of the ContextDecorator"
    pass


class ContextDecorator(object):
    """
        A thread-safe ContextDecorator. Subclasses should implement classmethods
        called _do_enter(state, decorator_args) and _do_exit(state, decorator_args, exception)

        state is a thread.local which can store state for each enter/exit. Decorator args holds
        any arguments passed into the decorator or context manager when called.
    """
    VALID_ARGUMENTS = ()

    def __init__(self, func=None, **kwargs):
        # Func will be passed in if this has been called without parenthesis
        # as a @decorator

        # Make sure only valid decorator arguments were passed in
        if len(kwargs) > len(self.__class__.VALID_ARGUMENTS):
            raise ValueError("Unexpected decorator arguments: {}".format(
                set(kwargs.keys()) - set(self.__class__.VALID_ARGUMENTS))
            )

        self.func = func
        self.decorator_args = { x: kwargs.get(x) for x in self.__class__.VALID_ARGUMENTS }
        # Add thread local state for variables that change per-call rather than
        # per insantiation of the decorator
        self.state = threading.local()
        self.state.stack = []

    def __get__(self, obj, objtype=None):
        """ Implement descriptor protocol to support instance methods. """
        # Invoked whenever this is accessed as an attribute of *another* object
        # - as it is when wrapping an instance method: `instance.method` will be
        # the ContextDecorator, so this is called.
        # We make sure __call__ is passed the `instance`, which it will pass onto
        # `self.func()`
        return functools.partial(self.__call__, obj)

    def __call__(self, *args, **kwargs):
        # Called if this has been used as a decorator not as a context manager

        def decorated(*_args, **_kwargs):
            decorator_args = self.decorator_args.copy()
            exception = False
            self.__class__._do_enter(self._push_state(), decorator_args)
            try:
                return self.func(*_args, **_kwargs)
            except:
                exception = True
                raise
            finally:
                self.__class__._do_exit(self._pop_state(), decorator_args, exception)

        if not self.func:
            # We were instantiated with args
            self.func = args[0]
            return decorated
        else:
            return decorated(*args, **kwargs)

    def _push_state(self):
        "We need a stack for state in case a decorator is called recursively"
        # self.state is a threading.local() object, so if the current thread is not the one in
        # which ContextDecorator.__init__ was called (e.g. is not the thread in which the function
        # was decorated), then the 'stack' attribute may not exist
        if not hasattr(self.state, 'stack'):
            self.state.stack = []

        self.state.stack.append(ContextState())
        return self.state.stack[-1]

    def _pop_state(self):
        return self.state.stack.pop()

    def __enter__(self):
        self.__class__._do_enter(self._push_state(), self.decorator_args.copy())

    def __exit__(self, exc_type, exc_value, traceback):
        self.__class__._do_exit(self._pop_state(), self.decorator_args.copy(), exc_type)


class TransactionFailedError(Exception):
    pass


class AtomicDecorator(ContextDecorator):
    VALID_ARGUMENTS = ("xg", "independent", "mandatory")

    @classmethod
    def _do_enter(cls, state, decorator_args):
        mandatory = decorator_args.get("mandatory", False)
        independent = decorator_args.get("independent", False)
        xg = decorator_args.get("xg", False)

        # Reset the state
        state.conn_stack = []
        state.transaction_started = False
        state.original_stack = None

        if independent:
            # Unwind the connection stack and store it on the state so that
            # we can replace it on exit
            while in_atomic_block():
                state.conn_stack.append(_PopConnection())
            state.original_stack = copy.deepcopy(caching.get_context().stack)

        elif in_atomic_block():
            # App Engine doesn't support nested transactions, so if there is a nested
            # atomic() call we just don't do anything. This is how RunInTransaction does it
            return
        elif mandatory:
            raise TransactionFailedError("You've specified that an outer transaction is mandatory, but one doesn't exist")

        options = CreateTransactionOptions(
            xg=xg,
            propagation=TransactionOptions.INDEPENDENT if independent else None
        )

        conn = _GetConnection()
        new_conn = conn.new_transaction(options)
        _PushConnection(new_conn)

        assert(_GetConnection())

        # Clear the context cache at the start of a transaction
        caching.get_context().stack.push()
        state.transaction_started = True

    @classmethod
    def _do_exit(cls, state, decorator_args, exception):
        independent = decorator_args.get("independent", False)
        context = caching.get_context()
        try:
            if state.transaction_started:
                if exception:
                    _GetConnection().rollback()
                else:
                    if not _GetConnection().commit():
                        raise TransactionFailedError()
        finally:
            if state.transaction_started:
                _PopConnection()

                 # Clear the context cache at the end of a transaction
                if exception:
                    context.stack.pop(discard=True)
                else:
                    context.stack.pop(apply_staged=True, clear_staged=True)

            # If we were in an independent transaction, put everything back
            # the way it was!
            if independent:
                while state.conn_stack:
                    _PushConnection(state.conn_stack.pop())

                # Restore the in-context cache as it was
                context.stack = state.original_stack


atomic = AtomicDecorator
commit_on_success = AtomicDecorator  # Alias to the old Django name for this kinda thing


class NonAtomicDecorator(ContextDecorator):
    @classmethod
    def _do_enter(cls, state, decorator_args):
        state.conn_stack = []
        context = caching.get_context()

        # We aren't in a transaction, do nothing!
        if not in_atomic_block():
            return

        # Store the current in-context stack
        state.original_stack = copy.deepcopy(context.stack)

        # Similar to independent transactions, unwind the connection statck
        # until we aren't in a transaction
        while in_atomic_block():
            state.conn_stack.append(_PopConnection())

        # Unwind the in-context stack
        while len(context.stack.stack) > 1:
            context.stack.pop(discard=True)

    @classmethod
    def _do_exit(cls, state, decorator_args, exception):
        if not state.conn_stack:
            return

        # Restore the connection stack
        while state.conn_stack:
            _PushConnection(state.conn_stack.pop())

        caching.get_context().stack = state.original_stack


non_atomic = NonAtomicDecorator
