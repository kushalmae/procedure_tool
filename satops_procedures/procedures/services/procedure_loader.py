import yaml
from django.conf import settings


def load_procedure(name):
    """Load a procedure by name (yaml_file stem, e.g. 'bus_checkout')."""
    yaml_dir = getattr(settings, 'PROCEDURES_YAML_DIR', None)
    if not yaml_dir:
        from pathlib import Path
        yaml_dir = Path(settings.BASE_DIR) / 'procedures_yaml'
    path = yaml_dir / f"{name}.yaml"
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)
