from jnav.json_model import JsonValue, walk
from jnav.node_path import NodePath


def test_walk_tree():
    document: JsonValue = {
        "foo": {
            "bar": [
                {"baz": 42},
                {"baz": 43},
            ]
        }
    }

    paths = [path for _, path in walk(document)]

    assert paths == [
        NodePath(),
        NodePath() / "foo",
        NodePath() / "foo" / "bar",
        NodePath() / "foo" / "bar" / 0,
        NodePath() / "foo" / "bar" / 0 / "baz",
        NodePath() / "foo" / "bar" / 1,
        NodePath() / "foo" / "bar" / 1 / "baz",
    ]
