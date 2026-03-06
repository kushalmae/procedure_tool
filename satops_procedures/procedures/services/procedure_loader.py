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
    """Write procedure dict to procedures_yaml/{yaml_stem}.yaml.
    Supports optional 'preconditions' key (string) for prerequisite notes.
    """
    path = _yaml_dir() / f"{yaml_stem}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure order: name, version, preconditions (if any), steps
    out = {'name': proc_dict.get('name', ''), 'version': proc_dict.get('version', '1.0')}
    if proc_dict.get('preconditions'):
        out['preconditions'] = proc_dict['preconditions']
    out['steps'] = proc_dict.get('steps', [])
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return path
