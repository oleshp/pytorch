from torch.utils.data import IterDataPipe
from torch.utils.data.datapipes.utils.common import validate_pathname_binary_tuple
from typing import Iterable, Iterator, Tuple, IO, cast
from io import BufferedIOBase

import os
import sys
import zipfile
import warnings

class ZipArchiveReaderIterDataPipe(IterDataPipe[Tuple[str, BufferedIOBase]]):
    r""" :class:`ZipArchiveReaderIterDataPipe`.

    Iterable data pipe to extract zip binary streams from input iterable which contains tuples of
    pathname and zip binary stream, yields pathname and extracted binary stream in a tuple.
    args:
        datapipe: Iterable datapipe that provides pathname and zip binary stream in tuples
        length: a nominal length of the datapipe

    Note:
        The opened file handles will be closed automatically if the default DecoderDataPipe
        is attached. Otherwise, user should be responsible to close file handles explicitly
        or let Python's GC close them periodly.
    """
    def __init__(
            self,
            datapipe : Iterable[Tuple[str, BufferedIOBase]],
            length : int = -1):
        super().__init__()
        self.datapipe : Iterable[Tuple[str, BufferedIOBase]] = datapipe
        self.length : int = length


    def __iter__(self) -> Iterator[Tuple[str, BufferedIOBase]]:
        if not isinstance(self.datapipe, Iterable):
            raise TypeError("datapipe must be Iterable type but got {}".format(type(self.datapipe)))
        for data in self.datapipe:
            validate_pathname_binary_tuple(data)
            pathname, data_stream = data
            try:
                # typing.cast is used here to silence mypy's type checker
                zips = zipfile.ZipFile(cast(IO[bytes], data_stream))
                for zipinfo in zips.infolist():
                    # major version should always be 3 here.
                    if sys.version_info[1] >= 6:
                        if zipinfo.is_dir():
                            continue
                    elif zipinfo.filename.endswith('/'):
                        continue

                    extracted_fobj = zips.open(zipinfo)
                    inner_pathname = os.path.normpath(os.path.join(pathname, zipinfo.filename))
                    # Add a reference of the source zipfile into extracted_fobj, so the source
                    # zipfile handle won't be released until all the extracted file objs are destroyed.
                    extracted_fobj.source_ref = zips  # type: ignore[attr-defined]
                    # typing.cast is used here to silence mypy's type checker
                    yield (inner_pathname, cast(BufferedIOBase, extracted_fobj))
            except Exception as e:
                warnings.warn(
                    "Unable to extract files from corrupted zipfile stream {} due to: {}, abort!".format(pathname, e))
                raise e


    def __len__(self):
        if self.length == -1:
            raise TypeError("{} instance doesn't have valid length".format(type(self).__name__))
        return self.length
