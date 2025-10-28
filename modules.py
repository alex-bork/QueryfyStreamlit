from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class File:
    name: str
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
    def create_dataframe(self):
        df = pd.read_excel(self._file_binary)
        return df
    
class CSVDataExtractor(FileDataExtractorBase):
    def create_dataframe(self):
        df = pd.read_csv(self._file_binary)
        return df