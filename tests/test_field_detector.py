import pytest
import pytest_asyncio

from jnav.field_detector import FieldDetector, FieldDiscovery
from jnav.node_path import NodePath


@pytest_asyncio.fixture
async def field_detector() -> FieldDetector:
    return FieldDetector()


class TestDetectFields:
    @pytest.mark.asyncio
    async def test_populates_all_fields(self, field_detector: FieldDetector) -> None:
        await field_detector.detect_fields({
            "level": "INFO",
            "message": "hi",
            "extra": 1,
        })

        assert ".level" in field_detector.all_fields
        assert ".message" in field_detector.all_fields
        assert ".extra" in field_detector.all_fields

    @pytest.mark.asyncio
    async def test_grows_incrementally(self, field_detector: FieldDetector) -> None:
        await field_detector.detect_fields({"a": 1})

        assert field_detector.all_fields == {".", ".a"}

        await field_detector.detect_fields({"a": 2, "b": 3})

        assert field_detector.all_fields == {".", ".a", ".b"}

    @pytest.mark.asyncio
    async def test_scalar_entry_reports_root(
        self, field_detector: FieldDetector
    ) -> None:
        discoveries: list[FieldDiscovery] = []

        async def collect(discovery: FieldDiscovery) -> None:
            discoveries.append(discovery)

        await field_detector.on_discovery.subscribe_async(collect)

        await field_detector.detect_fields(42)

        assert field_detector.all_fields == {"."}
        assert discoveries == [FieldDiscovery(42, [NodePath()])]

    @pytest.mark.asyncio
    async def test_array_entry_reports_root_and_indices(
        self, field_detector: FieldDetector
    ) -> None:
        await field_detector.detect_fields([1, "x"])

        assert field_detector.all_fields == {".", ".[0]", ".[1]"}
