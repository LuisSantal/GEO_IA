import json
from pathlib import Path
import pandas as pd


def find_json_file():
    base = Path('docs/relatorios')
    if not base.exists():
        return None
    files = list(base.rglob('*.json'))
    return files[0] if files else None


def load_json_to_df(path: Path) -> pd.DataFrame:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return pd.json_normalize(data)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return pd.json_normalize(v)
        return pd.json_normalize(data)
    raise ValueError('Unsupported JSON structure')


def summarize(df: pd.DataFrame):
    print('Shape:', df.shape)
    print('Columns:', ', '.join(df.columns[:30]))
    print('\nHead:')
    print(df.head(5).to_string(index=False))
    print('\nMissing values (top 20):')
    print(df.isna().sum().sort_values(ascending=False).head(20))


def main():
    p = find_json_file()
    if not p:
        print('No JSON file found under docs/relatorios')
        return
    print('Using file:', p)
    try:
        df = load_json_to_df(p)
    except Exception as e:
        print('Error loading JSON:', e)
        return
    summarize(df)


if __name__ == '__main__':
    main()
