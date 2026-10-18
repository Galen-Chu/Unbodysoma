import pytest

from unbodysoma.core import BusPort, Engine, Module, SignalBus


class Counter(Module):
    def __init__(self, rate_hz: float, key: str = "test.count") -> None:
        self.name = key
        self.rate_hz = rate_hz
        self.writes = (key,)
        self.count = 0
        self.dts: list[float] = []

    def step(self, dt: float, port: BusPort) -> None:
        self.count += 1
        self.dts.append(dt)
        port.write(self.writes[0], self.count)


class Reader(Module):
    name = "test.reader"
    rate_hz = 100.0
    reads = ("test.count",)

    def __init__(self) -> None:
        self.seen: list[float] = []

    def step(self, dt: float, port: BusPort) -> None:
        self.seen.append(port.read("test.count"))


def test_writes_are_invisible_until_commit():
    bus = SignalBus()
    bus.write("a", 1.0)
    assert bus.read("a", -1.0) == -1.0
    bus.commit()
    assert bus.read("a") == 1.0


def test_port_rejects_undeclared_writes():
    port = BusPort(SignalBus(), "owner", ("allowed",))
    port.write("allowed", 1.0)
    with pytest.raises(PermissionError):
        port.write("forbidden", 1.0)


def test_modules_run_at_their_own_rate():
    engine = Engine(base_dt=0.01)
    fast, slow = Counter(100.0), Counter(2.0, key="test.slow")
    engine.add(fast)
    engine.add(slow)
    engine.run(1.0)
    assert fast.count == 100
    assert slow.count == 2
    assert slow.dts == pytest.approx([0.5, 0.5])


def test_reader_sees_previous_tick_regardless_of_order():
    for order in ("reader_first", "writer_first"):
        engine = Engine(base_dt=0.01)
        writer, reader = Counter(100.0), Reader()
        modules = (reader, writer) if order == "reader_first" else (writer, reader)
        for m in modules:
            engine.add(m)
        engine.run(0.05)
        assert reader.seen == [0.0, 1.0, 2.0, 3.0, 4.0], order


def test_duplicate_writer_is_rejected():
    engine = Engine()
    engine.add(Counter(10.0))
    rival = Counter(10.0)
    rival.name = "test.rival"
    with pytest.raises(ValueError, match="already written"):
        engine.add(rival)


def test_duplicate_module_name_is_rejected():
    engine = Engine()
    engine.add(Counter(10.0, key="test.a"))
    twin = Counter(10.0, key="test.b")
    twin.name = "test.a"
    with pytest.raises(ValueError, match="already registered"):
        engine.add(twin)


def test_unwired_read_is_rejected_in_strict_mode():
    engine = Engine()
    engine.add(Reader())
    assert engine.unwired_reads() == {"test.count": ["test.reader"]}
    with pytest.raises(ValueError, match="never written"):
        engine.step()
