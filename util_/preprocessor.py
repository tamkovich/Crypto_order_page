def remove_prefix_b(bin_dict):
    """
    :param bin_dict: dict where keys and values are binary strings
    :return: decoded dict with 'ascii' encoding
    """
    dictionary = {}
    for b_item in bin_dict.items():
        b_item = b_item[0].decode('ascii'), b_item[1].decode('ascii')
        dictionary[b_item[0]] = b_item[1]
    return dictionary
