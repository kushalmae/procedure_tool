"""Dashboard widget registry and default configuration."""

WIDGETS = {
    'summary_cards': {
        'label': 'Summary Cards',
        'description': 'Fleet health, running count, procedures, satellites, runs, log entries, anomalies',
        'default_enabled': True,
        'default_order': 0,
        'zone': 'top',
    },
    'runs_table': {
        'label': 'Recent Runs',
        'description': 'Filterable table of recent procedure runs with status and actions',
        'default_enabled': True,
        'default_order': 1,
        'zone': 'main',
    },
    'recent_anomalies': {
        'label': 'Recent Anomalies',
        'description': 'Latest anomalies with severity, status, and links',
        'default_enabled': True,
        'default_order': 2,
        'zone': 'sidebar',
    },
    'recent_scribe': {
        'label': 'Recent Mission Log',
        'description': 'Latest Mission Scribe entries with role and category',
        'default_enabled': True,
        'default_order': 3,
        'zone': 'sidebar',
    },
    'fleet_status': {
        'label': 'Fleet Status',
        'description': 'Per-satellite health at a glance: last run, open anomalies',
        'default_enabled': False,
        'default_order': 4,
        'zone': 'main',
    },
    'sme_requests': {
        'label': 'Active SME Requests',
        'description': 'Open SME requests awaiting action',
        'default_enabled': False,
        'default_order': 5,
        'zone': 'sidebar',
    },
    'my_runs': {
        'label': 'My Recent Runs',
        'description': 'Procedure runs started by you in the last 7 days',
        'default_enabled': False,
        'default_order': 6,
        'zone': 'sidebar',
    },
    'procedure_stats': {
        'label': 'Procedure Pass Rates',
        'description': 'Pass/fail breakdown for procedures run in the last 30 days',
        'default_enabled': False,
        'default_order': 7,
        'zone': 'main',
    },
}

DEFAULT_LAYOUT = [
    {'widget': key, 'enabled': cfg['default_enabled'], 'order': cfg['default_order']}
    for key, cfg in WIDGETS.items()
]


def get_layout(layout_data):
    """Merge saved layout with the widget registry, filling in any new widgets."""
    if not layout_data:
        return DEFAULT_LAYOUT

    known = {item['widget'] for item in layout_data}
    merged = list(layout_data)
    for key, cfg in WIDGETS.items():
        if key not in known:
            merged.append({
                'widget': key,
                'enabled': cfg['default_enabled'],
                'order': cfg.get('default_order', 99),
            })
    merged.sort(key=lambda x: x.get('order', 99))
    return merged
