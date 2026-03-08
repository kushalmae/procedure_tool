from django.core.management.base import BaseCommand

from fdir.models import FDIREntry, Subsystem
from missions.models import Mission

DEFAULT_SUBSYSTEMS = [
    'ADCS',
    'Power',
    'Thermal',
    'Communications',
    'Payload',
    'Other',
]

SAMPLE_ENTRIES = [
    {
        'name': 'Reaction wheel speed anomaly',
        'fault_code': 'FDIR-RW-001',
        'subsystem': 'ADCS',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'sensor',
        'triggering_conditions': (
            'Wheel speed telemetry exceeds nominal range or tachometer fault. '
            'The fault is declared when the wheel controller reports a speed outside the valid envelope '
            'or when the tachometer count is invalid for a sustained period.'
        ),
        'detection_thresholds': (
            'Speed > 6000 rpm or < 0 for > 2 s; or tach count invalid for > 1 s. '
            'Debounce: 2 consecutive samples required before fault is latched.'
        ),
        'onboard_automated_response': (
            'Fault flag set in housekeeping; FSW may reduce wheel torque or request momentum unload. '
            'No automatic safehold. Wheel may be deselected from control loop if configured. '
            'Ground should assess telemetry and run Reaction Wheel Recovery procedure if needed.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Battery undervoltage',
        'fault_code': 'FDIR-PWR-001',
        'subsystem': 'Power',
        'severity': FDIREntry.SEVERITY_CRITICAL,
        'fault_type': 'limit',
        'triggering_conditions': (
            'Battery voltage below threshold for configured duration. '
            'Indicates insufficient charge or high load; can lead to bus undervoltage if not corrected.'
        ),
        'detection_thresholds': (
            'Vbat < 24 V for > 30 s. '
            'Critical threshold: Vbat < 22 V for > 10 s. '
            'Debounce: 5 s to avoid transients.'
        ),
        'onboard_automated_response': (
            'Enter power safehold: shed non-essential loads, reduce charge current, enable survival heaters as configured. '
            'Solar array pointed to sun if in sunlight. Battery heater enabled. '
            'Ground should run Power Recovery procedure and assess state of charge and load profile.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Star tracker lost fix',
        'fault_code': 'FDIR-ADCS-002',
        'subsystem': 'ADCS',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'sensor',
        'triggering_conditions': (
            'Star tracker loses attitude solution (no valid quaternion or lost-in-space). '
            'Can occur during eclipse, stray light, or tracker fault.'
        ),
        'detection_thresholds': (
            'No valid attitude output for > 5 s. Persistence: 3 consecutive cycles. '
            'Fallback to gyro-only propagation if available.'
        ),
        'onboard_automated_response': (
            'Switch to backup star tracker if configured. Gyro-only mode enabled. '
            'No safehold. Ground should verify tracker health and run Star Tracker Recovery if needed.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Solar array drive stall',
        'fault_code': 'FDIR-PWR-002',
        'subsystem': 'Power',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'actuator',
        'triggering_conditions': (
            'Solar array drive mechanism reports stall or excessive current. '
            'Array may be stuck or obstructed.'
        ),
        'detection_thresholds': (
            'Motor current > 2 A for > 10 s or position error > 5 deg for > 30 s. '
            'Debounce: 5 s to reject transients.'
        ),
        'onboard_automated_response': (
            'Drive disabled; array held at last position. Fault flag in telemetry. '
            'No automatic safehold. Ground to assess and run SADM Recovery procedure.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Bus overvoltage',
        'fault_code': 'FDIR-PWR-003',
        'subsystem': 'Power',
        'severity': FDIREntry.SEVERITY_CRITICAL,
        'fault_type': 'limit',
        'triggering_conditions': (
            'Main bus voltage exceeds upper limit. Risk to payload and bus units. '
            'Often caused by regulator fault or load dump.'
        ),
        'detection_thresholds': (
            'Vbus > 36 V for > 3 s. Critical: > 38 V for > 1 s. '
            'Persistence: 2 samples at 1 Hz.'
        ),
        'onboard_automated_response': (
            'Shed non-essential loads; disable battery charge if source of overvoltage. '
            'Enter power safehold. Ground run Bus Overvoltage Recovery and inspect regulator telemetry.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Panel temperature limit exceeded',
        'fault_code': 'FDIR-THM-001',
        'subsystem': 'Thermal',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'limit',
        'triggering_conditions': (
            'Solar panel or component temperature exceeds warning limit. '
            'Prolonged exposure may reduce life or trigger further FDIR.'
        ),
        'detection_thresholds': (
            'T_panel > 65 C for > 60 s. Critical: > 75 C for > 30 s. '
            'Debounce: 20 s to avoid eclipse exit transients.'
        ),
        'onboard_automated_response': (
            'Fault flag set. Optional: reduce charge rate or adjust array angle if in control. '
            'No automatic safehold. Ground monitor trend and run Thermal Anomaly procedure if critical.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Heater fault',
        'fault_code': 'FDIR-THM-002',
        'subsystem': 'Thermal',
        'severity': FDIREntry.SEVERITY_INFO,
        'fault_type': 'actuator',
        'triggering_conditions': (
            'Survival or trim heater circuit reports open circuit, short, or out-of-range current. '
            'Component may be underheated in cold case.'
        ),
        'detection_thresholds': (
            'Heater current < 0.1 A or > 2 A when commanded on for > 120 s. '
            'Persistence: 4 samples at 30 s interval.'
        ),
        'onboard_automated_response': (
            'Fault flag set; backup heater enabled if configured. No safehold. '
            'Ground assess thermal margins and run Heater Anomaly procedure if needed.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Transmitter power drop',
        'fault_code': 'FDIR-COMM-001',
        'subsystem': 'Communications',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'sensor',
        'triggering_conditions': (
            'RF transmitter output power below expected level. '
            'May indicate amplifier fault or antenna mismatch.'
        ),
        'detection_thresholds': (
            'Pout < 80% of nominal for > 30 s. Persistence: 3 samples. '
            'Exclude during mode transitions (first 60 s after TX on).'
        ),
        'onboard_automated_response': (
            'Fault flag set; switch to backup transmitter if configured. No safehold. '
            'Ground verify link budget and run Transmitter Recovery procedure.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Receiver lock lost',
        'fault_code': 'FDIR-COMM-002',
        'subsystem': 'Communications',
        'severity': FDIREntry.SEVERITY_INFO,
        'fault_type': 'sensor',
        'triggering_conditions': (
            'Command receiver loses carrier or symbol lock. '
            'Expected during eclipse or off-pointing; can indicate ground or receiver issue.'
        ),
        'detection_thresholds': (
            'Lock lost for > 300 s (configurable). Persistence: 2 consecutive checks at 60 s. '
            'No debounce on re-acquisition.'
        ),
        'onboard_automated_response': (
            'Fault flag set. Autonomy continues per mission rules; no automatic safehold. '
            'Ground verify pass geometry and command link; run Comm Loss procedure if prolonged.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Payload processor watchdog',
        'fault_code': 'FDIR-PLD-001',
        'subsystem': 'Payload',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'processor',
        'triggering_conditions': (
            'Payload processor fails to respond to watchdog within timeout. '
            'Indicates hang, crash, or bus fault.'
        ),
        'detection_thresholds': (
            'No heartbeat for > 10 s. Persistence: 2 missed heartbeats. '
            'Watchdog period: 5 s.'
        ),
        'onboard_automated_response': (
            'Payload processor reset; payload mode set to safe. Fault flag in housekeeping. '
            'No bus safehold. Ground run Payload Recovery procedure and inspect logs.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Payload data gap',
        'fault_code': 'FDIR-PLD-002',
        'subsystem': 'Payload',
        'severity': FDIREntry.SEVERITY_INFO,
        'fault_type': 'data',
        'triggering_conditions': (
            'Expected payload data product missing or incomplete for a configured interval. '
            'May indicate sensor fault, storage full, or downlink issue.'
        ),
        'detection_thresholds': (
            'No valid data product for > 2 orbits (configurable). Persistence: 1 sample per orbit. '
            'Exclude during planned payload off periods.'
        ),
        'onboard_automated_response': (
            'Fault flag set. No automatic response; payload continues per mode. '
            'Ground assess data availability and run Payload Data Anomaly procedure if needed.'
        ),
        'version': '1.0',
    },
    {
        'name': 'Unknown or unclassified fault',
        'fault_code': 'FDIR-OTH-001',
        'subsystem': 'Other',
        'severity': FDIREntry.SEVERITY_WARNING,
        'fault_type': 'general',
        'triggering_conditions': (
            'Fault code or event not mapped to a specific FDIR rule. '
            'Used for catch-all or newly discovered anomalies.'
        ),
        'detection_thresholds': (
            'As defined by fault source. Persistence per source. '
            'Log raw event and timestamp for ground analysis.'
        ),
        'onboard_automated_response': (
            'Fault logged; no automatic safehold unless combined with other rules. '
            'Ground review event log and mission logs; assign to specific FDIR or create new rule.'
        ),
        'version': '1.0',
    },
]


class Command(BaseCommand):
    help = 'Seed FDIR Handbook subsystems and optional sample FDIR entries.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entries',
            action='store_true',
            help='Also create sample FDIR entries.',
        )

    def handle(self, *args, **options):
        mission = Mission.objects.filter(is_sandbox=False).first() or Mission.objects.first()

        for name in DEFAULT_SUBSYSTEMS:
            _, created = Subsystem.objects.get_or_create(
                name=name,
                mission=mission,
                defaults={'name': name, 'mission': mission},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subsystem: {name}'))

        if options.get('entries'):
            for data in SAMPLE_ENTRIES:
                subsystem = Subsystem.objects.get(name=data['subsystem'], mission=mission)
                entry, created = FDIREntry.objects.get_or_create(
                    name=data['name'],
                    subsystem=subsystem,
                    mission=mission,
                    defaults={
                        'fault_code': data['fault_code'],
                        'severity': data['severity'],
                        'fault_type': data['fault_type'],
                        'triggering_conditions': data['triggering_conditions'],
                        'detection_thresholds': data['detection_thresholds'],
                        'onboard_automated_response': data['onboard_automated_response'],
                        'version': data['version'],
                        'mission': mission,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created FDIR entry: {data["name"]}'))
                else:
                    # Update existing sample entry so full response text is visible
                    entry.triggering_conditions = data['triggering_conditions']
                    entry.detection_thresholds = data['detection_thresholds']
                    entry.onboard_automated_response = data['onboard_automated_response']
                    entry.save()

        self.stdout.write(self.style.SUCCESS('FDIR seed complete.'))
