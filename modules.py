from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd
from io import BytesIO


@dataclass(frozen=True)
class File:
    name: str
    type: str
    size: int
    data: bytes


@dataclass()
class RegFile:
    fullname: str
    name: str
    sheetname: str
    type: str
    size: int
    data: bytes
    tabname: str


class FileDataExtractorBase(ABC):
    def __init__(self, file_binary):
        super().__init__()
        self._file_binary = file_binary

    @abstractmethod
    def create_dataframe(self):
        pass


class ExcelDataExtractor(FileDataExtractorBase):
    def __init__(self, file_binary, sheetname: str):
        super().__init__(file_binary)
        self._sheetname = sheetname

    def create_dataframe(self):
        if self._sheetname:
            df = pd.read_excel(self._file_binary, sheet_name=self._sheetname)
        else:
            df = pd.read_excel(self._file_binary)
        return df


class CSVDataExtractor(FileDataExtractorBase):
    def create_dataframe(self):
        df = pd.read_csv(BytesIO(self._file_binary))
        return df
