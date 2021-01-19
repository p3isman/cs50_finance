def check_for_duplicates(key, value, test_dict):
    for i in range(len(test_dict)):
        if value == test_dict[i][key]:
            return True
    return False