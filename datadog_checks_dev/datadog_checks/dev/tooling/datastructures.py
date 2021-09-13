#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)


class JSONDict(dict):
    """Subclass of dict which adds jsonpointer-like access methods"""

    def _resolve(self, path):
        parts = path.lstrip('/').split('/')

        obj = self
        for p in parts:
            # first, try to convert integer refs
            try:
                p = int(p)
            except Exception:
                pass

            try:
                obj = obj[p]
            except KeyError:
                return None

        return obj

    def get_path(self, path):
        return self._resolve(path)

    def set_path(self, path, value):
        # resolve the containing object

        # Note: more elegantly handled in python3 via:
        # *obj_path, tail = path.lstrip('/').split('/')
        parts = path.lstrip('/').split('/')
        if len(parts) > 1:
            obj_path, tail = parts[:-1], parts[-1]
        elif len(parts) == 1:
            obj_path, tail = None, parts[0]
        else:
            raise Exception('Unable to parse path successfully: {}'.format(path))

        obj = self
        if obj_path:
            obj = self._resolve('/'.join(obj_path))

        try:
            tail = int(tail)
        except Exception:
            pass

        obj[tail] = value
