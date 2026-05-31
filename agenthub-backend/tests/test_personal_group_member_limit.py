import pytest

from app.services.member_service import create_user_member


class _Q:
    def __init__(self, count_value: int):
        self._count_value = count_value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def count(self):
        return self._count_value


class _DB:
    def __init__(self, group):
        self._group = group

    def query(self, model):
        from app.models.group import Group

        if model is Group:
            class _GQ(_Q):
                def first(self_inner):
                    return self._group

            return _GQ(0)
        return _Q(2)

    def add(self, *args, **kwargs):
        raise AssertionError("Should not add when limit exceeded")

    def commit(self):
        raise AssertionError("Should not commit when limit exceeded")

    def refresh(self, *args, **kwargs):
        raise AssertionError("Should not refresh when limit exceeded")


def test_personal_group_member_limit_blocks_third_member():
    from app.models.group import Group

    g = Group(name="g", description=None, type="personal")
    db = _DB(g)
    with pytest.raises(Exception):
        create_user_member(db, "1", "u3", "3", None)

