
import json

from typing import Callable, Optional, TypeVar, Any, Union




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
                result[k] = v
            elif isinstance(v, dict):
                result[k] = map_internal(v)
            elif isinstance(v, str):
                result[k] = func(v)
                processed += 1
                if print_progress:
                    print(f"{(processed / total_items)*100:1f}% done.")


        return result

    return map_internal(d)


def read_json(file):
    with open(file,"r",encoding="utf8") as f:
        return json.loads(f.read())


def write_json(file, data):
    with open(file,"w+",encoding="utf8") as f:
        f.write(json.dumps(data))








class NDict:
    def __init__(self, d=None):
        self._data: dict[tuple, str] = {}
        if d:
            self._flatten(d)
    
    def _flatten(self, d, prefix=()):
        for k, v in d.items():
            path = prefix + (k,)
            if isinstance(v, dict):
                self._flatten(v, path)
            else:
                self._data[path] = v
    
    def items(self):
        return self._data.items()
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __repr__(self):
        return repr(self._data)
    
    def to_dict(self):
        result = {}
        for k, v in self._data.items():
            current = result
            for key in k[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[k[-1]] = v
        return result
    
    @staticmethod
    def from_dict(d):
        return NDict(d)
    
    def to_json(self):
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_json(s):
        return NDict.from_dict(json.loads(s))

    @staticmethod
    def from_file(inputfile):
        with open(inputfile,"r") as f:
            return NDict.from_json(f.read())

    def to_file(self, outfile):
        with open(outfile,"w") as f:
            f.write(self.to_json())

    def map(    
        self, 
        func: Callable[[str], str], 
        should_ignore_key: Optional[Callable[[tuple, str], bool]] = None, 
        print_progress: bool = False
    ):
        total_items = 0
        for k in self._data.keys():
            if should_ignore_key:
                strkey = k if isinstance(k, str) else k[-1]
                if should_ignore_key(k, strkey):
                    continue
            total_items += 1

        processed = 0
        result = NDict()
        
        for k, v in self._data.items():
            strkey = k if isinstance(k, str) else k[-1]
            
            if should_ignore_key and should_ignore_key(k,strkey):
                result[k] = v
            else:
                result[k] = func(v)
                processed += 1
                if print_progress:
                    print(f"{(processed / total_items) * 100:.1f}% done.")
        
        return result


