from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from anomalies.models import Anomaly, AnomalyTimelineEntry
from missions.models import Mission
from procedures.models import Satellite, Subsystem

SAMPLE_ANOMALIES = [
    {
        'satellite': 'SAT-021',
        'title': 'Bus voltage dip during eclipse exit',
        'subsystem': 'Power',
        'severity': Anomaly.SEVERITY_L4,
        'status': Anomaly.STATUS_INVESTIGATING,
        'description': 'Bus voltage dropped to 26.1V during eclipse exit cycle. Recovery to nominal 28V within 2 minutes. Logging for trend analysis across upcoming eclipses.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Battery SOC checked — within limits at 82%.'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Requesting telemetry dump for next three passes.'),
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
        ],
    },
    {
        'satellite': 'SAT-034',
        'title': 'Panel temp sensor T4 elevated reading',
        'subsystem': 'Thermal',
        'severity': Anomaly.SEVERITY_L2,
        'status': Anomaly.STATUS_NEW,
        'description': 'Panel temperature sensor T4 reading 3°C above predicted model. All other sensors nominal. May be sun angle or seasonal effect.',
        'timeline': [],
    },
    {
        'satellite': 'SAT-021',
        'title': 'UHF beacon loss during pass 2847',
        'subsystem': 'Comm',
        'severity': Anomaly.SEVERITY_L5,
        'status': Anomaly.STATUS_MITIGATED,
        'description': 'UHF beacon lost for 8 minutes during pass 2847. Reacquired on next AOS. Ground station confirmed no local issues.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
            (AnomalyTimelineEntry.ENTRY_ACTION, 'Switched to backup TX per emergency comm procedure.'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Monitoring next 3 passes for recurrence.'),
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from Investigating to Mitigated'),
        ],
    },
    {
        'satellite': 'SAT-012',
        'title': 'Momentum wheel speed spike during maneuver',
        'subsystem': 'GNC',
        'severity': Anomaly.SEVERITY_L1,
        'status': Anomaly.STATUS_CLOSED,
        'description': 'Single momentum wheel speed spike during planned maneuver. Auto-recovery nominal. No recurrence over 5 days.',
        'root_cause': 'Transient torque disturbance during maneuver initiation. Within design envelope.',
        'resolution_actions': 'Monitored for 5 days with no recurrence. No procedure change required.',
        'recommendations': 'Continue standard monitoring. No design change needed.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Wheel telemetry review complete — single transient spike.'),
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from Investigating to Resolved'),
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Anomaly closed. Root cause: transient torque disturbance.'),
        ],
    },
    {
        'satellite': 'SAT-034',
        'title': 'Elevated dark current on detector channel 2',
        'subsystem': 'Payload',
        'severity': Anomaly.SEVERITY_L3,
        'status': Anomaly.STATUS_INVESTIGATING,
        'description': 'Dark current on detector channel 2 trending upward. Currently within spec but approaching upper limit. Calibration still valid.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Scheduled calibration run for next payload activation window.'),
        ],
    },
    {
        'satellite': 'SAT-012',
        'title': 'Memory scrub single-bit error in sector 0x1A',
        'subsystem': 'C&DH',
        'severity': Anomaly.SEVERITY_L2,
        'status': Anomaly.STATUS_NEW,
        'description': 'Routine memory scrub reported single-bit error in sector 0x1A. ECC corrected. No impact to current operations.',
        'timeline': [],
    },
    {
        'satellite': 'SAT-021',
        'title': 'Imager safe mode during pass',
        'subsystem': 'Payload',
        'severity': Anomaly.SEVERITY_L5,
        'status': Anomaly.STATUS_INVESTIGATING,
        'description': 'Imager entered safe mode at T+120s into imaging pass. Auto-recovery at T+180s. Science data lost for that pass only.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Root cause under review with vendor.'),
            (AnomalyTimelineEntry.ENTRY_ACTION, 'Updated watchdog threshold per vendor technical note TN-2026-003.'),
        ],
    },
    {
        'satellite': 'SAT-034',
        'title': 'Star tracker lost lock at terminator',
        'subsystem': 'GNC',
        'severity': Anomaly.SEVERITY_L3,
        'status': Anomaly.STATUS_MITIGATED,
        'description': 'Star tracker lost lock for 5 seconds during terminator crossing. Coarse sun sensor maintained attitude knowledge. No maneuver impact.',
        'timeline': [
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from New to Investigating'),
            (AnomalyTimelineEntry.ENTRY_NOTE, 'Known behavior near terminator — reviewing exclusion zone parameters.'),
            (AnomalyTimelineEntry.ENTRY_ACTION, 'Updated star tracker exclusion zone from 15° to 20° around Earth limb.'),
            (AnomalyTimelineEntry.ENTRY_STATUS_CHANGE, 'Status changed from Investigating to Mitigated'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed Anomaly Tracker with sample anomalies and timeline entries.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-anomalies',
            action='store_true',
            help='Skip creating sample anomalies (only useful if calling this command directly).',
        )

    def handle(self, *args, **options):
        if options.get('no_anomalies'):
            self.stdout.write('Skipping anomaly creation (--no-anomalies).')
            return

        missions = []
        for slug in ('simulation', 'sandbox'):
            m = Mission.objects.filter(slug=slug).first()
            if m:
                missions.append(m)
        if not missions:
            m = Mission.objects.first()
            if m:
                missions = [m]
        now = timezone.now()

        for mission in missions:
            try:
                self._seed_anomalies_for_mission(mission, now)
            except Exception as e:
                import traceback
                self.stdout.write(self.style.ERROR(f'  Failed for {mission.name}: {e}'))
                if 'FOREIGN KEY' in str(e) or 'IntegrityError' in type(e).__name__:
                    self.stdout.write(self.style.WARNING('  Run seed_procedures first, then seed_anomalies.'))
                    self.stdout.write(traceback.format_exc())

        self.stdout.write(self.style.SUCCESS('Anomalies seed complete.'))

    def _seed_anomalies_for_mission(self, mission, now):
        # Ensure we have a committed mission (refresh from DB to avoid FK issues)
        mission = Mission.objects.get(pk=mission.pk)

        self.stdout.write(self.style.NOTICE(f'Seeding anomalies for mission: {mission.name}'))

        # Ensure procedures.Subsystem and Satellite exist and are committed first (SQLite FK checks at commit)
        PROCEDURE_SUBSYSTEMS = [
            'ADCS', 'Power', 'Comm', 'Payload', 'C&DH',
            'Thermal', 'Propulsion', 'GNC', 'Ground', 'Other',
        ]
        for name in PROCEDURE_SUBSYSTEMS:
            Subsystem.objects.get_or_create(name=name, mission=mission, defaults={'name': name, 'mission': mission})

        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(
                name=name, mission=mission, defaults={'name': name, 'mission': mission}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created satellite: {sat.name}'))

        # Subsystem left None: DB may have subsystem_id FK to anomalies_subsystem while model uses procedures.Subsystem.
        for i, data in enumerate(SAMPLE_ANOMALIES):
            satellite = Satellite.objects.get(name=data['satellite'], mission=mission)
            detected_time = now - timedelta(hours=3 * i, minutes=20 * i)

            with transaction.atomic():
                anomaly, created = Anomaly.objects.get_or_create(
                    title=data['title'],
                    satellite=satellite,
                    mission=mission,
                    defaults={
                        'subsystem': None,
                        'severity': data['severity'],
                        'status': data['status'],
                        'description': data['description'],
                        'detected_time': detected_time,
                        'operational_impact': data.get('operational_impact', ''),
                        'root_cause': data.get('root_cause', ''),
                        'resolution_actions': data.get('resolution_actions', ''),
                        'recommendations': data.get('recommendations', ''),
                        'mission': mission,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  Created anomaly: {anomaly.title}'))
                    for j, (entry_type, body) in enumerate(data['timeline']):
                        AnomalyTimelineEntry.objects.create(
                            anomaly=anomaly,
                            entry_type=entry_type,
                            body=body,
                            created_at=detected_time + timedelta(minutes=30 * (j + 1)),
                        )
                    if data['timeline']:
                        self.stdout.write(f'    Added {len(data["timeline"])} timeline entries')
                else:
                    self.stdout.write(f'  Anomaly already exists: {data["title"]}')
