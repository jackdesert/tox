from asyncio.windows_utils import BUFSIZE, PipeHandle
from typing import IO, Callable

import _overlapped  # type: ignore # noqa

from .read_via_thread import ReadViaThread


class ReadViaThreadWindows(ReadViaThread):
    def __init__(self, stream: IO[bytes], handler: Callable[[bytes], None]) -> None:
        super().__init__(stream, handler)
        self.closed = False
        assert isinstance(stream, PipeHandle)

    def _read_stream(self) -> None:
        ov = None
        while not self.stop.is_set():
            if ov is None:
                ov = _overlapped.Overlapped(0)
                try:
                    ov.ReadFile(self.stream.handle, 1)  # type: ignore
                except BrokenPipeError:
                    self.closed = True
                    return
            data = ov.getresult(10)  # wait for 10ms
            ov = None
            self.handler(data)

    def _drain_stream(self) -> bytes:
        length, result = 1 if self.closed else 1, b""
        while length:
            ov = _overlapped.Overlapped(0)
            try:
                ov.ReadFile(self.stream.handle, BUFSIZE)  # type: ignore
                data = ov.getresult()
            except BrokenPipeError:
                length = 0
            else:
                result += data
                length = len(data)
        return result