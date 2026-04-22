from pytest import raises

from jnav.node_path import NodePath


class TestNodePath:
    def test_to_string(self):
        path_str = ".foo.bar[0].baz"

        path = NodePath() / "foo" / "bar" / 0 / "baz"

        assert str(path) == path_str

    def test_resolve(self):
        document = {"foo": {"bar": [{"baz": 42}]}}
        path = NodePath() / "foo" / "bar" / 0 / "baz"

        assert path.resolve(document) == 42

    def test_resolve_list_index_out_of_range(self):
        document: object = {"foo": {"bar": []}}
        path = NodePath() / "foo" / "bar" / 0

        with raises(IndexError):
            path.resolve(document)

    def test_resolve_wrong_type(self):
        document: object = {"foo": {"bar": "not a list"}}
        path = NodePath() / "foo" / "bar" / 0

        with raises(TypeError):
            path.resolve(document)

    def test_resolve_wrong_type_dict(self):
        document: object = {"foo": {"bar": 123}}
        path = NodePath() / "foo" / "bar" / "baz"

        with raises(TypeError):
            path.resolve(document)

    def test_resolve_string_index(self):
        document: object = {"foo": {"bar": ["a", "b", "c"]}}
        path = NodePath() / "foo" / "bar" / "0"

        with raises(TypeError):
            path.resolve(document)
