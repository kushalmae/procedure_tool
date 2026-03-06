import yaml
from django.conf import settings


def _yaml_dir():
    yaml_dir = getattr(settings, 'PROCEDURES_YAML_DIR', None)
    if not yaml_dir:
        from pathlib import Path
        yaml_dir = Path(settings.BASE_DIR) / 'procedures_yaml'
    return yaml_dir


def load_procedure(name):
    """Load a procedure by name (yaml_file stem, e.g. 'bus_checkout')."""
    path = _yaml_dir() / f"{name}.yaml"
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_procedure(proc_dict, yaml_stem):
    """Write procedure dict to procedures_yaml/{yaml_stem}.yaml."""
    path = _yaml_dir() / f"{yaml_stem}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(proc_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return path
