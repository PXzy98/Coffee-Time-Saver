import io
import pandas as pd
from modules.file_processing.parsers.base import FileParser


class XlsxParser(FileParser):
    async def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            df_map = {"Sheet1": pd.read_csv(io.BytesIO(file_bytes))}
        else:
            df_map = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

        parts = []
        for sheet_name, df in df_map.items():
            parts.append(f"=== {sheet_name} ===")
            parts.append(df.to_string(index=False))
        return "\n\n".join(parts)
