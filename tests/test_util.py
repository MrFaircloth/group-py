from group_py.api.util import param_filter

# CHATGPT generated tests.


def test_param_filter_removes_none_values():
    params = {'name': 'John', 'age': None, 'city': 'New York', 'email': None}

    filtered_params = param_filter(params)

    assert 'name' in filtered_params
    assert 'age' not in filtered_params
    assert 'city' in filtered_params
    assert 'email' not in filtered_params


def test_param_filter_preserves_non_none_values():
    params = {'name': 'Alice', 'age': 25, 'city': 'San Francisco'}

    filtered_params = param_filter(params)

    assert 'name' in filtered_params
    assert 'age' in filtered_params
    assert 'city' in filtered_params


def test_param_filter_empty_input():
    params = {}

    filtered_params = param_filter(params)

    assert len(filtered_params) == 0
