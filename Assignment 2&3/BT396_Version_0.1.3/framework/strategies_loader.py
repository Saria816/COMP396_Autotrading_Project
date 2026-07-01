# framework/strategies_loader.py
"""
Loader that lets students write plain Backtrader strategies:

    class TeamStrategy(bt.Strategy):
        params = dict(...)  # or tuple-of-tuples

We return a class that *always* enforces COMP396 rules by wrapping the
student class with (COMP396Base, StudentClass). We do NOT touch/parse
the student's params; we only add ('_comp396', None) on the wrapper,
and let Backtrader's metaclass merge params across bases.
"""

import importlib
import inspect
import backtrader as bt
from framework.strategy_base import COMP396Base


import importlib
import inspect
import backtrader as bt
from framework.strategy_base import COMP396Base

def _wrap_with_comp396(student_cls: type) -> type:
    # capture student hooks
    student_init = getattr(student_cls, "__init__", None)
    student_start = getattr(student_cls, "start", None)
    student_next = getattr(student_cls, "next", None)
    student_notify = getattr(student_cls, "notify_order", None)

    class Wrapped(COMP396Base, student_cls):
        """Dynamic wrapper that injects COMP396Base behavior around the student Strategy to enforce course trading rules transparently."""
        # only add framework param; BT merges with student's params
        params = (("_comp396", None),)

        def __init__(self, *args, **kwargs):
            # Ensure Backtrader + mixins init
            super().__init__(*args, **kwargs)
            # Explicitly run student's __init__ so attributes like _sent/_b are set
            if callable(student_init):
                # Many student __init__ take only self; if they accept params, they
                # already came via cerebro.addstrategy(...). Safe to call with none.
                student_init(self)

        def start(self):
            # COMP396 engine first
            COMP396Base.start(self)
            # then student's start
            if callable(student_start):
                student_start(self)

        def next(self):
            # engine first (bankruptcy, final-day, EOD limit cancels)
            COMP396Base.next(self)
            # then student's trading logic (queues market orders)
            if callable(student_next):
                student_next(self)
            # finally, flush buffered market orders this bar
            if hasattr(self, "_flush_pending_market_orders"):
                self._flush_pending_market_orders()

        def notify_order(self, order):
            # apply slippage on MARKET orders
            COMP396Base.notify_order(self, order)
            # then student's notify
            if callable(student_notify):
                student_notify(self, order)

    Wrapped.__name__ = f"{student_cls.__name__}__COMP396Wrapped"
    return Wrapped



def load_strategy_class(module_name: str, explicit_class: str | None):
    """
    Import strategies.<module_name>, find a Backtrader Strategy class,
    and return a class that is guaranteed to enforce COMP396 rules.

    - If the found class already subclasses COMP396Base, return it as-is.
    - Otherwise, return a dynamic wrapper that injects COMP396Base behavior.
    """
    mod = importlib.import_module(f"strategies.{module_name}")

    # pick the class
    if explicit_class:
        cls = getattr(mod, explicit_class)
    else:
        cls = None
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, bt.Strategy):
                cls = obj
                break
        if cls is None:
            raise ValueError(f"No Backtrader Strategy subclass found in strategies.{module_name}.")

    if issubclass(cls, COMP396Base):
        return cls

    return _wrap_with_comp396(cls)
