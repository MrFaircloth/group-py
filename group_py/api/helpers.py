
def param_filter(params: dict):
    filtered_params = {key: value for key, value in params.items() if value is not None}
    return filtered_params
