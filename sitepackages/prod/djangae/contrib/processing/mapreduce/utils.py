import types

def qualname(func):
    if isinstance(func, types.MethodType):
        return "{cls}.{func}".format(
            cls=func.im_self.__class__,
            func=func.im_func.__name__
        )
    elif isinstance(func, types.BuiltinMethodType):
        if not func.__self__:
            return "{func}".format(
                func=func.__name__
            )
        else:
            return "{type}.{func}".format(
                type=func.__self__,
                func=func.__name__
            )
    elif (isinstance(func, types.ObjectType) and hasattr(func, "__call__")) or\
        isinstance(func, (types.FunctionType, types.BuiltinFunctionType,
                        types.ClassType, types.UnboundMethodType)):
        return "{module}.{func}".format(
            module=func.__module__,
            func=func.__name__
        )
    else:
        raise ValueError("func must be callable")
