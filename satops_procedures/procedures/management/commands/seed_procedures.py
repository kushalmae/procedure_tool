from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from procedures.models import Satellite, Tag, Procedure, ProcedureRun, StepExecution
from procedures.services.procedure_loader import load_procedure


PROCEDURES = [
    {'yaml_file': 'bus_checkout', 'name': 'Bus Checkout', 'version': '1.0', 'tags': ['checkout', 'bus']},
    {'yaml_file': 'payload_init', 'name': 'Payload Initialization', 'version': '2.1', 'tags': ['payload', 'commissioning']},
    {'yaml_file': 'thermal_safehold', 'name': 'Thermal Safehold Procedure', 'version': '1.2', 'tags': ['thermal', 'safehold']},
    {'yaml_file': 'orbit_maneuver', 'name': 'Orbit Correction Maneuver', 'version': '3.0', 'tags': ['orbit', 'maneuver', 'propulsion']},
]


class Command(BaseCommand):
    help = 'Seed Procedures, Tags, and sample Satellites.'

    def handle(self, *args, **options):
        for p in PROCEDURES:
            proc, created = Procedure.objects.get_or_create(
                yaml_file=p['yaml_file'],
                defaults={'name': p['name'], 'version': p['version']},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created procedure: {proc.name}'))
            else:
                self.stdout.write(f'Procedure already exists: {proc.name}')
            for tag_name in p.get('tags', []):
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                proc.tags.add(tag)
        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))

        # Sample procedure runs (only if no runs exist)
        if ProcedureRun.objects.count() == 0:
            self._create_sample_runs()

        self.stdout.write(self.style.SUCCESS('Seed complete.'))

    def _create_sample_runs(self):
        """Create a few sample procedure runs with step executions."""
        now = timezone.now()
        satellites = list(Satellite.objects.all()[:3])
        procedures = list(Procedure.objects.all()[:4])
        if not satellites or not procedures:
            return
        # Run 1: SAT-021, Bus Checkout, completed PASS (2 days ago)
        proc_bus = next((p for p in procedures if p.yaml_file == 'bus_checkout'), procedures[0])
        sat = next((s for s in satellites if s.name == 'SAT-021'), satellites[0])
        start1 = now - timedelta(days=2, hours=4)
        run1 = ProcedureRun.objects.create(
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

        # Run 2: SAT-034, Thermal Safehold, completed PASS (1 day ago)
        proc_thermal = next((p for p in procedures if p.yaml_file == 'thermal_safehold'), procedures[1])
        sat2 = next((s for s in satellites if s.name == 'SAT-034'), satellites[1])
        start2 = now - timedelta(days=1, hours=2)
        run2 = ProcedureRun.objects.create(
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

        # Run 3: SAT-012, Bus Checkout, completed FAIL (12 hours ago) — one step FAIL
        start3 = now - timedelta(hours=12)
        run3 = ProcedureRun.objects.create(
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

        # Run 4: SAT-021, Payload Init, RUNNING (started 30 min ago)
        proc_payload = next((p for p in procedures if p.yaml_file == 'payload_init'), procedures[0])
        start4 = now - timedelta(minutes=30)
        run4 = ProcedureRun.objects.create(
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
