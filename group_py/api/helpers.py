
def param_filter(params: dict):
    ''' Removes None values from params '''
    filtered_params = {key: value for key, value in params.items() if value is not None}
    return filtered_params
