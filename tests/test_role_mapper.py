import pytest
import pytest_asyncio

from jnav.field_detector import FieldDiscovery
from jnav.field_mapping import RoleBinding, RoleMapping, TimeRoleBinding
from jnav.json_model import JsonValue
from jnav.log_entry_item import format_timestamp
from jnav.node_path import walk
from jnav.role_mapper import RoleMapper

from .conftest import make_signal_collector


def _discovery(entry: JsonValue) -> FieldDiscovery:
    return FieldDiscovery(entry=entry, new_fields=[p for _, p in walk(entry)])


@pytest_asyncio.fixture
async def role_mapper() -> RoleMapper:
    return RoleMapper()


class TestDiscoverMappingDetection:
    @pytest.mark.asyncio
    async def test_populates_mapping_from_known_names(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.detect_roles(
            _discovery({"ts": "2025-01-01T00:00:00", "level": "INFO", "message": "hi"})
        )

        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".ts", format="iso8601"
        )
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".message"

    @pytest.mark.asyncio
    async def test_keeps_filling_missing_roles_across_batches(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.detect_roles(_discovery({"level": "INFO"}))
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.timestamp is None

        await role_mapper.detect_roles(
            _discovery({"level": "WARN", "ts": "2025-01-01T00:00:00"})
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".ts", format="iso8601"
        )

    @pytest.mark.asyncio
    async def test_lower_priority_candidate_does_not_demote(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "@timestamp": "2025-01-01T00:00:00",
                "level": "INFO",
                "message": "hi",
            })
        )

        events, collect = make_signal_collector()
        await role_mapper.on_change.subscribe_async(collect)

        await role_mapper.detect_roles(
            _discovery({
                "ts": "2025-01-02T00:00:00",
                "severity": "WARN",
                "msg": "ho",
            })
        )

        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression='.["@timestamp"]', format="iso8601"
        )
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".message"
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_complete_set_overrides_suppresses_detection(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.set_overrides(
            RoleMapping(
                timestamp=TimeRoleBinding(expression=".ts", format="iso8601"),
                level=RoleBinding(expression=".level"),
                message=RoleBinding(expression=".message"),
            )
        )

        events, collect = make_signal_collector()
        await role_mapper.on_change.subscribe_async(collect)

        await role_mapper.detect_roles(
            _discovery({
                "ts": "2025-01-01T00:00:00",
                "level": "INFO",
                "message": "hi",
                "@timestamp": "2025-01-01T00:00:00",
            })
        )

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_partial_set_overrides_replaces_active_mapping(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.set_overrides(
            RoleMapping(level=RoleBinding(expression=".level"))
        )

        await role_mapper.detect_roles(
            _discovery({
                "ts": "2025-01-01T00:00:00",
                "level": "INFO",
                "message": "hi",
            })
        )

        assert role_mapper.mapping.timestamp is None
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.message is None

    @pytest.mark.asyncio
    async def test_fires_on_change_when_detection_updates_mapping(
        self, role_mapper: RoleMapper
    ) -> None:
        events, collect = make_signal_collector()
        await role_mapper.on_change.subscribe_async(collect)

        await role_mapper.detect_roles(_discovery({"level": "INFO"}))

        assert len(events) == 1


class TestSetOverrides:
    @pytest.mark.asyncio
    async def test_set_overrides_fires_on_change(self, role_mapper: RoleMapper) -> None:
        events, collect = make_signal_collector()
        await role_mapper.on_change.subscribe_async(collect)

        await role_mapper.set_overrides(
            RoleMapping(
                timestamp=TimeRoleBinding(expression=".ts", format="iso8601"),
                level=RoleBinding(expression="level"),
                message=RoleBinding(expression="message"),
            )
        )

        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".ts", format="iso8601"
        )
        assert len(events) == 1


class TestKnownFormats:
    @pytest.mark.asyncio
    async def test_logstash_style(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "@timestamp": "2025-01-01T00:00:00",
                "level": "INFO",
                "message": "hello",
            })
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression='.["@timestamp"]', format="iso8601"
        )
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".message"

    @pytest.mark.asyncio
    async def test_bunyan_style(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "time": "2025-01-01T00:00:00",
                "level": 30,
                "msg": "hi",
            })
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".time", format="iso8601"
        )
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".msg"

    @pytest.mark.asyncio
    async def test_pino_epoch_ms(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "time": 1_700_000_000_000,
                "level": 30,
                "msg": "hi",
            })
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".time", format="epoch_ms"
        )

    @pytest.mark.asyncio
    async def test_zap_ts(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "ts": "2025-01-01T00:00:00",
                "level": "info",
                "msg": "hi",
            })
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression=".ts", format="iso8601"
        )

    @pytest.mark.asyncio
    async def test_serilog_style(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "@t": "2025-01-01T00:00:00",
                "@l": "Warning",
                "@m": "hi",
            })
        )
        assert role_mapper.mapping.timestamp == TimeRoleBinding(
            expression='.["@t"]', format="iso8601"
        )
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == '.["@l"]'
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == '.["@m"]'

    @pytest.mark.asyncio
    async def test_priority_prefers_earlier_candidate(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.detect_roles(
            _discovery({
                "@timestamp": "2025-01-01T00:00:00",
                "ts": "2025-01-01T00:00:00",
                "time": "2025-01-01T00:00:00",
                "level": "INFO",
                "message": "hi",
            })
        )
        # @timestamp has higher priority than ts/time
        assert role_mapper.mapping.timestamp is not None
        assert role_mapper.mapping.timestamp.expression == '.["@timestamp"]'

    @pytest.mark.asyncio
    async def test_unknown_format_sets_message(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(_discovery({"weird": "2025-01-01", "value": 42}))
        assert role_mapper.mapping == RoleMapping(message=RoleBinding(expression="."))

    @pytest.mark.asyncio
    async def test_named_message_field_upgrades_root(
        self, role_mapper: RoleMapper
    ) -> None:
        await role_mapper.detect_roles(_discovery({"weird": "value"}))
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == "."

        await role_mapper.detect_roles(_discovery({"message": "hi"}))
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".message"

    @pytest.mark.asyncio
    async def test_message_field_upgrades_msg(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(_discovery({"msg": "hi"}))
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".msg"

        await role_mapper.detect_roles(_discovery({"message": "hello"}))
        assert role_mapper.mapping.message is not None
        assert role_mapper.mapping.message.expression == ".message"

    @pytest.mark.asyncio
    async def test_level_field_upgrades_severity(self, role_mapper: RoleMapper) -> None:
        await role_mapper.detect_roles(_discovery({"severity": "WARN"}))
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".severity"

        await role_mapper.detect_roles(_discovery({"level": "INFO"}))
        assert role_mapper.mapping.level is not None
        assert role_mapper.mapping.level.expression == ".level"


class TestDetectTimestampFormat:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (1_700_000_000, "epoch_s"),
            (1_700_000_000_000, "epoch_ms"),
            (1_700_000_000_000_000, "epoch_us"),
            (1_700_000_000_000_000_000, "epoch_ns"),
        ],
    )
    @pytest.mark.asyncio
    async def test_epoch_magnitude(
        self,
        role_mapper: RoleMapper,
        value: int,
        expected: str,
    ) -> None:
        await role_mapper.detect_roles(_discovery({"ts": value}))
        assert role_mapper.mapping.timestamp is not None
        assert role_mapper.mapping.timestamp.format == expected


class TestFormatTimestamp:
    def test_iso8601(self) -> None:
        assert format_timestamp("2025-01-01T10:30:45.123456", "iso8601") == (
            "10:30:45.123"
        )

    def test_epoch_s(self) -> None:
        # 2023-11-14 22:13:20 UTC
        assert format_timestamp(1_700_000_000, "epoch_s") == "22:13:20.000"

    def test_epoch_ms(self) -> None:
        assert format_timestamp(1_700_000_000_500, "epoch_ms") == "22:13:20.500"

    def test_epoch_us(self) -> None:
        assert format_timestamp(1_700_000_000_500_000, "epoch_us") == "22:13:20.500"

    def test_epoch_ns(self) -> None:
        assert format_timestamp(1_700_000_000_500_000_000, "epoch_ns") == (
            "22:13:20.500"
        )

    def test_invalid_iso8601_falls_back_to_string(self) -> None:
        assert format_timestamp("not a date", "iso8601") == "not a date"

    def test_invalid_epoch_value(self) -> None:
        assert format_timestamp("not a number", "epoch_s") == "not a number"


class TestFieldMappingRoundtrip:
    def test_full_roundtrip(self) -> None:
        mapping = RoleMapping(
            timestamp=TimeRoleBinding(expression='.["@timestamp"]', format="iso8601"),
            level=RoleBinding(expression="severity"),
            message=RoleBinding(expression="msg"),
        )
        assert RoleMapping.model_validate(mapping.model_dump()) == mapping

    def test_empty_roundtrip(self) -> None:
        assert RoleMapping.model_validate(RoleMapping().model_dump()) == RoleMapping()

    def test_partial_roundtrip(self) -> None:
        mapping = RoleMapping(level=RoleBinding(expression="level"))
        assert RoleMapping.model_validate(mapping.model_dump()) == mapping

    def test_missing_roles(self) -> None:
        assert RoleMapping().missing_roles() == ["timestamp", "level", "message"]
        assert RoleMapping(level=RoleBinding(expression="level")).missing_roles() == [
            "timestamp",
            "message",
        ]
