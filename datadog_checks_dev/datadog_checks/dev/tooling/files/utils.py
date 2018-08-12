# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

from ...utils import ensure_parent_dir_exists, write_file

LICENSE_HEADER = """\
# (C) Datadog, Inc. {year}
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
""".format(year=str(datetime.now().year))


class File(object):
    def __init__(self, file_path, contents=''):
        self.file_path = file_path
        self.contents = LICENSE_HEADER + contents if file_path.endswith('.py') else contents

    def write(self):
        ensure_parent_dir_exists(self.file_path)
        write_file(self.file_path, self.contents)
