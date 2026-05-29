import threading
import time
from dataclasses import dataclass


EPOCH_MS = 1735689600000


@dataclass(slots=True)
class SnowflakeConfig:
    datacenter_id: int = 1
    worker_id: int = 1


class SnowflakeGenerator:
    def __init__(self, config: SnowflakeConfig) -> None:
        self._datacenter_id = config.datacenter_id & 0x1F
        self._worker_id = config.worker_id & 0x1F
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def next_id(self) -> int:
        with self._lock:
            timestamp = self._current_millis()
            if timestamp < self._last_timestamp:
                timestamp = self._wait_until(self._last_timestamp)

            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & 0xFFF
                if self._sequence == 0:
                    timestamp = self._wait_until(self._last_timestamp + 1)
            else:
                self._sequence = 0

            self._last_timestamp = timestamp
            return (
                ((timestamp - EPOCH_MS) << 22)
                | (self._datacenter_id << 17)
                | (self._worker_id << 12)
                | self._sequence
            )

    @staticmethod
    def _current_millis() -> int:
        return int(time.time() * 1000)

    def _wait_until(self, target_timestamp: int) -> int:
        timestamp = self._current_millis()
        while timestamp < target_timestamp:
            time.sleep(0.001)
            timestamp = self._current_millis()
        return timestamp
