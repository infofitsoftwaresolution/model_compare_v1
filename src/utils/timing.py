"""Simple timing utilities."""

import time


def now_ms() -> int:
    return int(time.time() * 1000)


class Stopwatch:
    def __enter__(self):
        self.start = now_ms()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.end = now_ms()
        self.elapsed_ms = self.end - self.start


