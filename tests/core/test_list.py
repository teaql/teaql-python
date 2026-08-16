from teaql.core.list import SmartList, TeaQLPage


def test_smart_list_is_a_typed_native_sequence_with_metadata():
    items: SmartList[int] = SmartList([1, 2], total_count=5)

    assert list(items) == [1, 2]
    assert items.data is items
    assert items.total_count == 5
    assert list(items.map(str)) == ["1", "2"]
    assert list(items.filter(lambda value: value > 1)) == [2]


def test_page_carries_a_smart_list():
    items = SmartList([1, 2], total_count=5)
    page = TeaQLPage(data=items, total_count=5, offset=0, limit=2)

    assert page.data is items
