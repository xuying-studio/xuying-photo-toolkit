"""本地 XMP 属性仓库。"""

from pathlib import Path

from xuying_toolbox.domain.services.xmp import XmpProperties
from xuying_toolbox.infrastructure.metadata.xmp_file import read


class LocalXmpRepository:
    def read(self, path: Path) -> XmpProperties:
        return read(path)
