from charmhelpers.core import hookenv

from charms.reactive import bus


class NullTracer(object):
    def set_flag(self, flag):
        pass

    def clear_flag(self, flag):
        pass


class LogTracer(NullTracer):
    LEVEL = hookenv.DEBUG

    def __init__(self):
        self._msgs = []

    def set_flag(self, flag):
        self._flag("flag {} set".format(flag))

    def clear_flag(self, flag):
        self._flag("flag {} cleared".format(flag))

    def _emit(self, msg):
        self._msgs.append("tracer: {}".format(msg))

    def _flush(self):
        if self._msgs:
            if len(self._msgs) > 1:
                self._msgs.insert(0, "tracer>")
            hookenv.log("\n".join(self._msgs), self.LEVEL)
            self._msgs = []

    _active_handlers = frozenset()

    def _flag(self, msg):
        self._emit(msg)
        prev_handlers = self._active_handlers
        next_handlers = set(h for h in bus.Handler.get_handlers() if h.test())

        for h in sorted(h.id() for h in (next_handlers - prev_handlers)):
            self._emit("++   queue handler {}".format(h))

        for h in sorted(h.id() for h in (prev_handlers - next_handlers)):
            self._emit("-- dequeue handler {}".format(h))

        self._flush()

        self._active_handlers = next_handlers


_tracer = None


def install_tracer(tracer):
    global _tracer
    _tracer = tracer
    # Disable tracing when we hit atexit, to avoid spam from layers
    # like the base layer tearing down flags.
    hookenv.atexit(install_tracer, NullTracer())


def tracer():
    global _tracer
    return _tracer


install_tracer(NullTracer())
