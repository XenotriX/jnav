import pytest
import pytest_asyncio

from jnav.field_detector import FieldDetector


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
