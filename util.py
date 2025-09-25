
import json




def map_dict(d, func, should_ignore_key=None, print_progress=False):
    def count_leaves(dictionary):
        count = 0
        for k, v in dictionary.items():
            if should_ignore_key and should_ignore_key(k):
                continue
            if isinstance(v, dict):
                count += count_leaves(v)
            elif isinstance(v, str):
                count += 1
        return count

    total_items = count_leaves(d)
    processed = 0

    def map_internal(dictionary):
        nonlocal processed
        result = {}
        for k, v in dictionary.items():
            if should_ignore_key and should_ignore_key(k):
                continue
            if isinstance(v, dict):
                result[k] = map_internal(v)
            elif isinstance(v, str):
                result[k] = func(v)
                processed += 1
                if print_progress:
                    print(f"{(processed / total_items)*100:1f}% done.")


        return result

    return map_internal(d)


def read_json(file):
    with open(file,"r") as f:
        return json.loads(f.read())


def write_json(file, data):
    with open(file,"w+") as f:
        f.write(json.dumps(data))



