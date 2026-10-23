"""Copy two actual saved receipts into a NEW local replay database. Never deletes data."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pm.models import Project  # noqa: E402
from pm.store import Store  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/portfolio-release.sqlite3')
    args = parser.parse_args()
    target = Path(args.database)
    if target.exists():
        parser.error('Database already exists; choose a new path. No existing data was changed.')
    store = Store(target)
    for name in ['live-haiti-expanded.json', 'live-microgrids.json']:
        project = Project.model_validate_json((Path(__file__).resolve().parents[1] / 'examples' / name).read_text(encoding='utf-8'))
        store.save(project)
    print('Prepared two saved-execution replays in a new local database. No model calls.')


if __name__ == '__main__':
    main()
