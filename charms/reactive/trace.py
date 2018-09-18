from charms.reactive import bus


class NullTracer(object):
    def set_flag(self, flag):
        pass

    def clear_flag(self, flag):
        pass


class LogTracer(NullTracer):
    def set_flag(self, flag):
        self._flag("flag {} set".format(flag))

    def clear_flag(self, flag):
        self._flag("flag {} cleared".format(flag))

    def _emit(self, msg):
        print("tracer: {}".format(msg))

    _enabled_handlers = frozenset()

    def _flag(self, msg):
        self._emit(msg)
        prev_handlers = self._enabled_handlers
        next_handlers = set(h for h in bus.Handler.get_handlers() if h.test())

        for h in sorted(h.id() for h in (next_handlers - prev_handlers)):
            self._emit("++ queue   handler {}".format(h))

        for h in sorted(h.id() for h in (prev_handlers - next_handlers)):
            self._emit("-- dequeue handler {}".format(h))

        self._enabled_handlers = next_handlers


_tracer = None


def install_tracer(tracer):
    global _tracer
    _tracer = tracer


def tracer():
    global _tracer
    return _tracer


install_tracer(NullTracer())
