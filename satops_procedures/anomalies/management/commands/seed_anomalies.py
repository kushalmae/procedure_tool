from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from procedures.models import Satellite
from anomalies.models import Subsystem, AnomalyType, Anomaly, AnomalyNote


DEFAULT_SUBSYSTEMS = [
    'Power',
    'Thermal',
    'C&DH',
    'Comm',
    'GNC',
    'Payload',
    'Ground',
]

DEFAULT_ANOMALY_TYPES = [
    'Fault',
    'Performance Degradation',
    'Unexpected Behavior',
]

# Sample anomalies: (satellite_name, subsystem_name, type_name, severity, impact, status, description, notes_list)
SAMPLE_ANOMALIES = [
    ('SAT-021', 'Power', 'Fault', Anomaly.SEVERITY_HIGH, Anomaly.IMPACT_MODERATE, Anomaly.STATUS_INVESTIGATING,
     'Bus voltage dip during eclipse exit. Voltage recovered to nominal within 2 minutes. Logging for trend analysis.',
     ['Checked battery state of charge; within limits.', 'Requesting telemetry dump for next pass.']),
    ('SAT-034', 'Thermal', 'Performance Degradation', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MINOR, Anomaly.STATUS_NEW,
     'Panel temp sensor T4 reading 3°C above predicted. Other sensors nominal. May be sun angle / seasonal.',
     []),
    ('SAT-021', 'Comm', 'Fault', Anomaly.SEVERITY_CRITICAL, Anomaly.IMPACT_MAJOR, Anomaly.STATUS_MITIGATED,
     'UHF beacon lost for 8 minutes during pass 2847. Reacquired on next AOS. Ground station reported no local issues.',
     ['Switched to backup TX per procedure.', 'Monitoring next 3 passes.']),
    ('SAT-012', 'GNC', 'Unexpected Behavior', Anomaly.SEVERITY_LOW, Anomaly.IMPACT_NONE, Anomaly.STATUS_RESOLVED,
     'Single momentum wheel speed spike during maneuver. Auto recovery nominal. No recurrence over 5 days.',
     ['Closed as nominal variant; no procedure change.']),
    ('SAT-034', 'Payload', 'Performance Degradation', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MINOR, Anomaly.STATUS_INVESTIGATING,
     'Elevated dark current on detector channel 2. Within spec but trending up. Calibration still valid.',
     []),
    ('SAT-012', 'C&DH', 'Fault', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MODERATE, Anomaly.STATUS_NEW,
     'Memory scrub reported single-bit error in sector 0x1A. ECC corrected. No impact to operations.',
     []),
    # 10 more sample anomalies
    ('SAT-034', 'Ground', 'Fault', Anomaly.SEVERITY_LOW, Anomaly.IMPACT_NONE, Anomaly.STATUS_RESOLVED,
     'Pass 2901: antenna pointing error 0.2 deg for 30 sec. Autotrack reacquired. No data loss.',
     ['Verified ground config; no repeat on next pass.']),
    ('SAT-021', 'Thermal', 'Performance Degradation', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MINOR, Anomaly.STATUS_INVESTIGATING,
     'Heater H3 duty cycle 12% above baseline for 24h. Box temps nominal. Possible sensor drift.',
     []),
    ('SAT-012', 'Power', 'Fault', Anomaly.SEVERITY_HIGH, Anomaly.IMPACT_MODERATE, Anomaly.STATUS_NEW,
     'Solar array current drop on string B during sunrise. String A nominal. Monitoring next eclipse.',
     ['Will compare with SAT-034 string B telemetry.']),
    ('SAT-034', 'Comm', 'Unexpected Behavior', Anomaly.SEVERITY_LOW, Anomaly.IMPACT_NONE, Anomaly.STATUS_RESOLVED,
     'One duplicate frame in downlink session. CRC ok. Attributed to ground retry; closed.',
     []),
    ('SAT-021', 'Payload', 'Fault', Anomaly.SEVERITY_CRITICAL, Anomaly.IMPACT_MAJOR, Anomaly.STATUS_MITIGATED,
     'Imager safe mode at T+120s into pass. Auto-recovery at T+180s. Science loss for that pass only.',
     ['Root cause under review.', 'Updated watchdog threshold per vendor note.']),
    ('SAT-012', 'Thermal', 'Performance Degradation', Anomaly.SEVERITY_LOW, Anomaly.IMPACT_NONE, Anomaly.STATUS_NEW,
     'Radiator temp 1C below prediction. All other zones nominal. Seasonal; no action.',
     []),
    ('SAT-034', 'GNC', 'Fault', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MINOR, Anomaly.STATUS_INVESTIGATING,
     'Star tracker lost lock for 5s during terminator. Coarse sun sensor kept attitude. No maneuver.',
     []),
    ('SAT-021', 'C&DH', 'Unexpected Behavior', Anomaly.SEVERITY_LOW, Anomaly.IMPACT_NONE, Anomaly.STATUS_RESOLVED,
     'Time tag jump +1s in one HK packet. Subsequent packets correct. Likely ground timestamp; closed.',
     []),
    ('SAT-012', 'Payload', 'Performance Degradation', Anomaly.SEVERITY_MEDIUM, Anomaly.IMPACT_MODERATE, Anomaly.STATUS_NEW,
     'Detector bias voltage 2% high on channel 4. Calibration run scheduled. Data still usable with correction.',
     []),
    ('SAT-034', 'Power', 'Fault', Anomaly.SEVERITY_HIGH, Anomaly.IMPACT_MODERATE, Anomaly.STATUS_MITIGATED,
     'Battery cell 2 voltage spread 45 mV. Balancing commanded; next pass to verify.',
     ['Balancing cycle completed.', 'Spread reduced to 12 mV.']),
]


class Command(BaseCommand):
    help = 'Seed Fleet Anomaly Tracker: Subsystems, AnomalyTypes, and optionally sample anomalies (--anomalies).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--anomalies',
            action='store_true',
            help='Also create sample anomalies (and notes). Ensures sample satellites exist.',
        )

    def handle(self, *args, **options):
        for name in DEFAULT_SUBSYSTEMS:
            _, created = Subsystem.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subsystem: {name}'))
        for name in DEFAULT_ANOMALY_TYPES:
            _, created = AnomalyType.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created anomaly type: {name}'))

        if options['anomalies']:
            self._seed_anomalies()

        self.stdout.write(self.style.SUCCESS('Anomalies seed complete.'))

    def _seed_anomalies(self):
        now = timezone.now()
        # Ensure we have satellites (match seed_procedures names)
        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))

        subs = {s.name: s for s in Subsystem.objects.all()}
        types = {t.name: t for t in AnomalyType.objects.all()}

        for i, row in enumerate(SAMPLE_ANOMALIES):
            sat_name, sub_name, type_name, severity, impact, status, description, notes_list = row
            satellite = Satellite.objects.get(name=sat_name)
            subsystem = subs.get(sub_name)
            anomaly_type = types.get(type_name)
            # Stagger detection_time: most recent first
            detection_time = now - timedelta(hours=2 * i, minutes=15 * i)

            anomaly, created = Anomaly.objects.get_or_create(
                satellite=satellite,
                detection_time=detection_time,
                defaults={
                    'subsystem': subsystem,
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'operational_impact': impact,
                    'status': status,
                    'description': description,
                    'reported_by': None,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created anomaly: {satellite.name} — {description[:50]}…'))
                for note_body in notes_list:
                    AnomalyNote.objects.create(anomaly=anomaly, body=note_body, created_by=None)
                    self.stdout.write(f'  Added note: {note_body[:40]}…')
            else:
                self.stdout.write(f'Sample anomaly already exists (e.g. {satellite.name} @ {detection_time})')
