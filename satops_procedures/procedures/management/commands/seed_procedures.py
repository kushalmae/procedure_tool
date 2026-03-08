from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from missions.models import Mission
from procedures.models import Procedure, ProcedureRun, Satellite, StepExecution, Subsystem, Tag
from procedures.services.procedure_loader import load_procedure

PROCEDURES = [
    {
        'yaml_file': 'bus_checkout',
        'name': 'Bus Checkout',
        'version': '1.0',
        'description': 'Full spacecraft bus health check covering power, thermal, telemetry, and operator signoff. Run after every contact gap or anomaly recovery.',
        'tags': ['checkout', 'bus'],
    },
    {
        'yaml_file': 'payload_init',
        'name': 'Payload Initialization',
        'version': '2.1',
        'description': 'Power-up and configure the payload subsystem from safe mode through full operational readiness, including RF chain activation and telemetry verification.',
        'tags': ['payload', 'commissioning'],
    },
    {
        'yaml_file': 'thermal_safehold',
        'name': 'Thermal Safehold Procedure',
        'version': '1.2',
        'description': 'Assess and maintain spacecraft thermal state during safehold events. Covers heater configuration, battery and propellant temps, and radiator checks.',
        'tags': ['thermal', 'safehold'],
    },
    {
        'yaml_file': 'orbit_maneuver',
        'name': 'Orbit Correction Maneuver',
        'version': '3.0',
        'description': 'Plan, upload, arm, and execute an orbit correction burn with pre- and post-burn verification of propulsion, attitude, and ephemeris.',
        'tags': ['orbit', 'maneuver', 'propulsion'],
    },
    {
        'yaml_file': 'solar_array_deploy',
        'name': 'Solar Array Deployment',
        'version': '1.0',
        'description': 'Command and verify deployment of solar array panels after launch vehicle separation. Includes pre-deploy health checks, actuator firing, and post-deploy power confirmation.',
        'tags': ['commissioning', 'power', 'deployment'],
    },
    {
        'yaml_file': 'adcs_calibration',
        'name': 'ADCS Calibration',
        'version': '2.0',
        'description': 'Calibrate the Attitude Determination and Control System sensors (star trackers, sun sensors, magnetometers) and actuators (reaction wheels, magnetorquers).',
        'tags': ['adcs', 'calibration'],
    },
    {
        'yaml_file': 'comm_link_test',
        'name': 'Communication Link Test',
        'version': '1.5',
        'description': 'End-to-end verification of uplink and downlink communication chains. Tests command reception, telemetry encoding, carrier lock, and bit-error rate across multiple data rates.',
        'tags': ['comms', 'checkout'],
    },
    {
        'yaml_file': 'battery_conditioning',
        'name': 'Battery Conditioning Cycle',
        'version': '1.1',
        'description': 'Controlled deep-discharge and recharge cycle for Li-ion battery packs to recalibrate state-of-charge estimation and assess long-term cell health.',
        'tags': ['power', 'battery', 'maintenance'],
    },
    {
        'yaml_file': 'momentum_dump',
        'name': 'Momentum Dump',
        'version': '2.3',
        'description': 'Desaturate reaction wheels by firing thrusters to offload accumulated angular momentum. Includes wheel speed assessment, thruster priming, and post-dump verification.',
        'tags': ['adcs', 'propulsion', 'maintenance'],
    },
    {
        'yaml_file': 'safe_mode_recovery',
        'name': 'Safe Mode Recovery',
        'version': '1.0',
        'description': 'Step-by-step recovery of a spacecraft from autonomous safe mode, including root cause triage, subsystem re-enable sequence, and return to nominal operations.',
        'tags': ['safehold', 'recovery'],
    },
    {
        'yaml_file': 'firmware_upload',
        'name': 'Firmware Upload',
        'version': '3.1',
        'description': 'Upload, verify, and activate new flight software on the onboard computer. Covers image staging, checksum verification, activation, and rollback contingency.',
        'tags': ['software', 'maintenance'],
    },
    {
        'yaml_file': 'ground_station_handoff',
        'name': 'Ground Station Handoff',
        'version': '1.4',
        'description': 'Transfer active satellite tracking and commanding between ground stations during a pass. Ensures seamless telemetry continuity and command authority transfer.',
        'tags': ['comms', 'ground'],
    },
    {
        'yaml_file': 'deorbit_plan',
        'name': 'Deorbit Planning & Execution',
        'version': '1.0',
        'description': 'End-of-life disposal procedure including passivation planning, final orbit lowering burns, propellant depletion, and battery safing for controlled reentry.',
        'tags': ['orbit', 'end-of-life', 'propulsion'],
    },
    {
        'yaml_file': 'antenna_pattern_test',
        'name': 'Antenna Pattern Test',
        'version': '2.0',
        'description': 'Characterize the deployed antenna gain pattern by performing controlled attitude slews while measuring received signal strength at the ground station.',
        'tags': ['comms', 'calibration', 'commissioning'],
    },
]


class Command(BaseCommand):
    help = 'Seed Procedures, Tags, Subsystems, and sample Satellites.'

    DEFAULT_SUBSYSTEMS = [
        'ADCS', 'Power', 'Comm', 'Payload', 'C&DH',
        'Thermal', 'Propulsion', 'GNC', 'Ground', 'Other',
    ]

    def _get_default_mission(self):
        return Mission.objects.filter(is_sandbox=False).first() or Mission.objects.first()

    def handle(self, *args, **options):
        mission = self._get_default_mission()

        for name in self.DEFAULT_SUBSYSTEMS:
            _, created = Subsystem.objects.get_or_create(name=name, mission=mission)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subsystem: {name}'))

        for p in PROCEDURES:
            proc, created = Procedure.objects.get_or_create(
                yaml_file=p['yaml_file'],
                mission=mission,
                defaults={
                    'name': p['name'],
                    'version': p['version'],
                    'description': p.get('description', ''),
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created procedure: {proc.name}'))
            else:
                updated = False
                if not proc.description and p.get('description'):
                    proc.description = p['description']
                    updated = True
                if updated:
                    proc.save()
                    self.stdout.write(f'Updated procedure: {proc.name}')
                else:
                    self.stdout.write(f'Procedure already exists: {proc.name}')
            for tag_name in p.get('tags', []):
                tag, _ = Tag.objects.get_or_create(name=tag_name, mission=mission)
                proc.tags.add(tag)
        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name, mission=mission, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))

        if ProcedureRun.objects.count() == 0:
            self._create_sample_runs()

        self.stdout.write(self.style.SUCCESS('Seed complete.'))

    def _create_sample_runs(self):
        """Create a few sample procedure runs with step executions."""
        mission = self._get_default_mission()
        now = timezone.now()
        satellites = list(Satellite.objects.filter(mission=mission)[:3])
        procedures = list(Procedure.objects.filter(mission=mission)[:4])
        if not satellites or not procedures:
            return
        proc_bus = next((p for p in procedures if p.yaml_file == 'bus_checkout'), procedures[0])
        sat = next((s for s in satellites if s.name == 'SAT-021'), satellites[0])
        start1 = now - timedelta(days=2, hours=4)
        run1 = ProcedureRun.objects.create(
            mission=mission,
            satellite=sat,
            procedure=proc_bus,
            operator=None,
            operator_name='Ops',
            status=ProcedureRun.STATUS_PASS,
            end_time=start1 + timedelta(minutes=12),
            run_notes='Nominal bus checkout. All limits green.',
        )
        run1.start_time = start1
        run1.save(update_fields=['start_time'])
        self._add_step_executions(run1, proc_bus.yaml_file, start1, status='PASS')
        self.stdout.write(self.style.SUCCESS(f'Created run: {sat.name} — {proc_bus.name} (PASS)'))

        proc_thermal = next((p for p in procedures if p.yaml_file == 'thermal_safehold'), procedures[1])
        sat2 = next((s for s in satellites if s.name == 'SAT-034'), satellites[1])
        start2 = now - timedelta(days=1, hours=2)
        run2 = ProcedureRun.objects.create(
            mission=mission,
            satellite=sat2,
            procedure=proc_thermal,
            operator=None,
            operator_name='Ops',
            status=ProcedureRun.STATUS_PASS,
            end_time=start2 + timedelta(minutes=25),
            run_notes='Thermal safehold verified. Beta angle 12 deg.',
        )
        run2.start_time = start2
        run2.save(update_fields=['start_time'])
        self._add_step_executions(run2, proc_thermal.yaml_file, start2, status='PASS')
        self.stdout.write(self.style.SUCCESS(f'Created run: {sat2.name} — {proc_thermal.name} (PASS)'))

        start3 = now - timedelta(hours=12)
        run3 = ProcedureRun.objects.create(
            mission=mission,
            satellite=next((s for s in satellites if s.name == 'SAT-012'), satellites[2]),
            procedure=proc_bus,
            operator=None,
            operator_name='Ops',
            status=ProcedureRun.STATUS_FAIL,
            end_time=start3 + timedelta(minutes=8),
            run_notes='Step 2 (telemetry) failed — stream dropped for 30 s. Retry passed on next pass.',
        )
        run3.start_time = start3
        run3.save(update_fields=['start_time'])
        self._add_step_executions(run3, proc_bus.yaml_file, start3, fail_at_step_index=1)
        self.stdout.write(self.style.SUCCESS(f'Created run: SAT-012 — {proc_bus.name} (FAIL)'))

        proc_payload = next((p for p in procedures if p.yaml_file == 'payload_init'), procedures[0])
        start4 = now - timedelta(minutes=30)
        run4 = ProcedureRun.objects.create(
            mission=mission,
            satellite=sat,
            procedure=proc_payload,
            operator=None,
            operator_name='Ops',
            status=ProcedureRun.STATUS_RUNNING,
            run_notes='',
        )
        run4.start_time = start4
        run4.save(update_fields=['start_time'])
        self._add_step_executions(run4, proc_payload.yaml_file, start4, only_first_n=2)
        self.stdout.write(self.style.SUCCESS(f'Created run: {sat.name} — {proc_payload.name} (RUNNING)'))

    def _add_step_executions(self, run, yaml_stem, run_start, status='PASS', fail_at_step_index=None, only_first_n=None):
        """Add step executions for a run. Load steps from YAML."""
        try:
            proc = load_procedure(yaml_stem)
        except (FileNotFoundError, OSError):
            return
        steps = proc.get('steps', [])
        for i, step in enumerate(steps):
            if only_first_n is not None and i >= only_first_n:
                break
            step_status = 'FAIL' if i == fail_at_step_index else status
            step_ts = run_start + timedelta(minutes=i + 1)
            StepExecution.objects.create(
                run=run,
                step_id=step.get('id', ''),
                description=step.get('description', ''),
                status=step_status,
                input_value=None,
                notes='' if step_status == 'PASS' else 'Stream dropped; retry on next pass.' if fail_at_step_index is not None else '',
                timestamp=step_ts,
            )
