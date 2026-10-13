from teaql.core.projection_properties import ProjectionProperties


def test_computed_properties_do_not_shadow_model_or_methods_and_missing_returns_null():
    values = {'id': 1, 'itemCount': 7, 'save': {'unsafe': ['original']}}
    properties = ProjectionProperties(values, ['id'])
    assert properties.get('id') is None
    assert properties.get('missing') is None
    assert properties.get('itemCount') == 7
    values['save']['unsafe'].append('changed')
    extracted = properties.get('save')
    extracted['unsafe'].append('another change')
    assert properties.get('save') == {'unsafe': ['original']}
