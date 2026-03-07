from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from anomalies.models import Anomaly, AnomalyTimelineEntry
from procedures.models import Satellite

SAMPLE_ANOMALIES = [
    {
        'satellite': 'SAT-021',
        'title': 'Bus voltage dip during eclipse exit',
        'subsystem': Anomaly.SUBSYSTEM_POWER,
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
        'subsystem': Anomaly.SUBSYSTEM_THERMAL,
        'severity': Anomaly.SEVERITY_L2,
        'status': Anomaly.STATUS_NEW,
        'description': 'Panel temperature sensor T4 reading 3°C above predicted model. All other sensors nominal. May be sun angle or seasonal effect.',
        'timeline': [],
    },
    {
        'satellite': 'SAT-021',
        'title': 'UHF beacon loss during pass 2847',
        'subsystem': Anomaly.SUBSYSTEM_COMM,
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
        'subsystem': Anomaly.SUBSYSTEM_GNC,
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
        'subsystem': Anomaly.SUBSYSTEM_PAYLOAD,
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
        'subsystem': Anomaly.SUBSYSTEM_CDH,
        'severity': Anomaly.SEVERITY_L2,
        'status': Anomaly.STATUS_NEW,
        'description': 'Routine memory scrub reported single-bit error in sector 0x1A. ECC corrected. No impact to current operations.',
        'timeline': [],
    },
    {
        'satellite': 'SAT-021',
        'title': 'Imager safe mode during pass',
        'subsystem': Anomaly.SUBSYSTEM_PAYLOAD,
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
        'subsystem': Anomaly.SUBSYSTEM_GNC,
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
            '--anomalies',
            action='store_true',
            help='Create sample anomalies with timeline entries. Ensures sample satellites exist.',
        )

    def handle(self, *args, **options):
        if not options.get('anomalies'):
            self.stdout.write('Use --anomalies to create sample data.')
            return

        now = timezone.now()

        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))

        for i, data in enumerate(SAMPLE_ANOMALIES):
            satellite = Satellite.objects.get(name=data['satellite'])
            detected_time = now - timedelta(hours=3 * i, minutes=20 * i)

            anomaly, created = Anomaly.objects.get_or_create(
                title=data['title'],
                satellite=satellite,
                defaults={
                    'subsystem': data['subsystem'],
                    'severity': data['severity'],
                    'status': data['status'],
                    'description': data['description'],
                    'detected_time': detected_time,
                    'root_cause': data.get('root_cause', ''),
                    'resolution_actions': data.get('resolution_actions', ''),
                    'recommendations': data.get('recommendations', ''),
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created anomaly: {anomaly.title}'))
                for j, (entry_type, body) in enumerate(data['timeline']):
                    AnomalyTimelineEntry.objects.create(
                        anomaly=anomaly,
                        entry_type=entry_type,
                        body=body,
                        created_at=detected_time + timedelta(minutes=30 * (j + 1)),
                    )
                    self.stdout.write(f'  Added timeline entry: {body[:50]}…')
            else:
                self.stdout.write(f'Anomaly already exists: {data["title"]}')

        self.stdout.write(self.style.SUCCESS('Anomalies seed complete.'))
