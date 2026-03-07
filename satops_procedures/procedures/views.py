from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .models import Procedure, ProcedureRun, Satellite, StepExecution, Tag
from .services.procedure_loader import load_procedure, save_procedure
from .services.runner import get_next_step

RUN_SORT_OPTIONS = [
    '-start_time',  # newest first (default)
    'start_time',
    'satellite__name',
    '-satellite__name',
    'procedure__name',
    '-procedure__name',
    'status',
    '-status',
]


def _search_runs(queryset, q, tag_id):
    """Filter runs by search query and/or tag."""
    if q:
        q = q.strip()
        if q:
            queryset = queryset.filter(
                Q(satellite__name__icontains=q)
                | Q(procedure__name__icontains=q)
                | Q(operator_name__icontains=q)
            )
    if tag_id:
        queryset = queryset.filter(procedure__tags__id=tag_id).distinct()
    return queryset


def homepage(request):
    return render(request, 'homepage.html')


def dashboard(request):
    q = request.GET.get('q', '')
    tag_id = request.GET.get('tag', '')
    if tag_id:
        try:
            tag_id = int(tag_id)
        except ValueError:
            tag_id = None
    else:
        tag_id = None
    sort = request.GET.get('sort', '-start_time')
    if sort not in RUN_SORT_OPTIONS:
        sort = '-start_time'
    runs = (
        ProcedureRun.objects
        .select_related('satellite', 'procedure')
        .prefetch_related('procedure__tags')
        .order_by(sort)
    )
    runs = _search_runs(runs, q, tag_id)[:50]
    tags = Tag.objects.all()

    # Summary stats for dashboard
    running_count = ProcedureRun.objects.filter(status='RUNNING').count()
    procedures_count = Procedure.objects.count()
    satellites_count = Satellite.objects.count()
    week_ago = timezone.now() - timedelta(days=7)
    runs_last_7_days = ProcedureRun.objects.filter(start_time__gte=week_ago).count()
    scribe_entries_24h = 0
    recent_scribe_entries = []
    try:
        MissionLogEntry = __import__('scribe.models', fromlist=['MissionLogEntry']).MissionLogEntry
        day_ago = timezone.now() - timedelta(days=1)
        scribe_entries_24h = MissionLogEntry.objects.filter(timestamp__gte=day_ago).count()
        recent_scribe_entries = list(
            MissionLogEntry.objects.select_related('role', 'satellite', 'category')
            .order_by('-timestamp')[:5]
        )
    except Exception:
        pass

    active_anomalies_count = 0
    recent_anomalies = []
    fleet_health = 'green'
    try:
        Anomaly = __import__('anomalies.models', fromlist=['Anomaly']).Anomaly
        active_anomalies_count = Anomaly.objects.exclude(status=Anomaly.STATUS_RESOLVED).count()
        recent_anomalies = list(
            Anomaly.objects.select_related('satellite')
            .order_by('-detection_time')[:5]
        )
        has_high_critical = Anomaly.objects.exclude(status=Anomaly.STATUS_RESOLVED).filter(
            severity__in=[Anomaly.SEVERITY_CRITICAL, Anomaly.SEVERITY_HIGH]
        ).exists()
        recent_fail_or_cancel = ProcedureRun.objects.filter(
            status__in=[ProcedureRun.STATUS_FAIL, ProcedureRun.STATUS_CANCELLED],
            start_time__gte=week_ago,
        ).exists()
        if has_high_critical:
            fleet_health = 'red'
        elif active_anomalies_count > 0 or recent_fail_or_cancel:
            fleet_health = 'yellow'
    except Exception:
        pass

    return render(request, 'dashboard.html', {
        'runs': runs,
        'search_query': q,
        'tag_id': tag_id,
        'tags': tags,
        'sort': sort,
        'sort_options': RUN_SORT_OPTIONS,
        'running_count': running_count,
        'procedures_count': procedures_count,
        'satellites_count': satellites_count,
        'runs_last_7_days': runs_last_7_days,
        'scribe_entries_24h': scribe_entries_24h,
        'recent_scribe_entries': recent_scribe_entries,
        'active_anomalies_count': active_anomalies_count,
        'recent_anomalies': recent_anomalies,
        'fleet_health': fleet_health,
    })


@login_required
def start(request):
    if request.method == 'POST':
        satellite_name = request.POST.get('satellite', '').strip()
        procedure_id = request.POST.get('procedure')
        if not satellite_name or not procedure_id:
            satellites = Satellite.objects.all()
            procedures = Procedure.objects.prefetch_related('tags').all()
            tags = Tag.objects.all()
            return render(request, 'start.html', {
                'satellites': satellites,
                'procedures': procedures,
                'tags': tags,
                'error': 'Satellite and procedure are required.',
            })
        satellite, _ = Satellite.objects.get_or_create(name=satellite_name, defaults={'name': satellite_name})
        procedure = get_object_or_404(Procedure, pk=procedure_id)
        run = ProcedureRun.objects.create(
            satellite=satellite,
            procedure=procedure,
            operator=request.user,
            operator_name=request.user.get_username(),
            status=ProcedureRun.STATUS_RUNNING,
        )
        return redirect(reverse('run', kwargs={'run_id': run.pk}) + '?step=0')
    satellites = Satellite.objects.all()
    procedures = Procedure.objects.prefetch_related('tags').all()
    filter_tag_id = None
    tag_param = request.GET.get('tag', '')
    if tag_param:
        try:
            filter_tag_id = int(tag_param)
            procedures = procedures.filter(tags__id=filter_tag_id).distinct()
        except ValueError:
            pass
    tags = Tag.objects.all()
    preselected_procedure_id = request.GET.get('procedure', '')
    try:
        preselected_procedure_id = int(preselected_procedure_id) if preselected_procedure_id else None
    except ValueError:
        preselected_procedure_id = None
    preselected_satellite_name = ''
    satellite_id_param = request.GET.get('satellite', '')
    if satellite_id_param:
        try:
            sid = int(satellite_id_param)
            sat = Satellite.objects.filter(pk=sid).first()
            if sat:
                preselected_satellite_name = sat.name
        except ValueError:
            pass
    return render(request, 'start.html', {
        'satellites': satellites,
        'procedures': procedures,
        'tags': tags,
        'filter_tag_id': filter_tag_id,
        'preselected_procedure_id': preselected_procedure_id,
        'preselected_satellite_name': preselected_satellite_name,
    })


PROCEDURE_SORT_OPTIONS = [
    ('name', 'Name A–Z'),
    ('-name', 'Name Z–A'),
    ('version', 'Version'),
    ('-version', 'Version (newest first)'),
]


def procedure_list(request):
    """List all procedures with links to review and start. Filter by tag, sort by name/version."""
    q = request.GET.get('q', '').strip()
    tag_id = request.GET.get('tag', '')
    try:
        filter_tag_id = int(tag_id) if tag_id else None
    except ValueError:
        filter_tag_id = None
    sort = request.GET.get('sort', 'name')
    allowed_sort = [s[0] for s in PROCEDURE_SORT_OPTIONS]
    if sort not in allowed_sort:
        sort = 'name'
    procedures = Procedure.objects.prefetch_related('tags').order_by(sort)
    if filter_tag_id:
        procedures = procedures.filter(tags__id=filter_tag_id).distinct()
    if q:
        procedures = procedures.filter(
            Q(name__icontains=q) | Q(version__icontains=q) | Q(description__icontains=q)
        )
    # Attach step count where YAML is loadable
    for p in procedures:
        try:
            proc = load_procedure(p.yaml_file)
            p.step_count = len(proc.get('steps', []))
        except (FileNotFoundError, OSError):
            p.step_count = None
    tags = Tag.objects.all()
    return render(request, 'procedure_list.html', {
        'procedures': procedures,
        'tags': tags,
        'filter_tag_id': filter_tag_id,
        'search_query': q,
        'sort': sort,
        'sort_options': PROCEDURE_SORT_OPTIONS,
    })


def procedure_review(request):
    """Show procedure steps before starting a run."""
    procedure_id = request.GET.get('procedure', '')
    if not procedure_id:
        return redirect('start')
    try:
        procedure_id = int(procedure_id)
    except ValueError:
        return redirect('start')
    procedure = get_object_or_404(Procedure.objects.prefetch_related('tags'), pk=procedure_id)
    try:
        proc = load_procedure(procedure.yaml_file)
    except FileNotFoundError:
        return redirect('start')
    steps = proc.get('steps', [])
    preconditions = (proc.get('preconditions') or '').strip()
    return render(request, 'procedure_review.html', {
        'procedure': procedure,
        'proc': proc,
        'steps': steps,
        'preconditions': preconditions,
    })


def _unique_yaml_stem(name):
    """Generate a unique yaml_file stem from procedure name."""
    base = (slugify(name) or 'procedure').replace('-', '_').strip('_') or 'procedure'
    stem = base
    n = 0
    while Procedure.objects.filter(yaml_file=stem).exists():
        n += 1
        stem = f"{base}_{n}"
    return stem


def procedure_create(request):
    """Create a new procedure from the UI (writes YAML and creates Procedure record)."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        version = request.POST.get('version', '1.0').strip() or '1.0'
        step_ids = request.POST.getlist('step_id')
        step_descriptions = request.POST.getlist('step_description')
        step_inputs = request.POST.getlist('step_input')
        steps = []
        for i, sid in enumerate(step_ids):
            sid = (sid or '').strip()
            desc = (step_descriptions[i] if i < len(step_descriptions) else '').strip()
            inp = (step_inputs[i] if i < len(step_inputs) else '').strip()
            if sid and desc:
                step = {'id': sid, 'description': desc}
                if inp:
                    step['input'] = inp
                steps.append(step)
        if not name:
            return render(request, 'procedure_create.html', {
                'error': 'Procedure name is required.',
                'form_name': request.POST.get('name'),
                'form_version': request.POST.get('version'),
                'form_description': request.POST.get('description', '').strip(),
                'form_preconditions': request.POST.get('preconditions', '').strip(),
                'form_steps': steps,
            })
        if not steps:
            return render(request, 'procedure_create.html', {
                'error': 'At least one step (id and description) is required.',
                'form_name': name,
                'form_version': version,
                'form_description': request.POST.get('description', '').strip(),
                'form_preconditions': request.POST.get('preconditions', '').strip(),
                'form_steps': [],
            })
        description = (request.POST.get('description') or '').strip()
        preconditions = (request.POST.get('preconditions') or '').strip()
        proc_dict = {'name': name, 'version': version, 'steps': steps}
        if preconditions:
            proc_dict['preconditions'] = preconditions
        yaml_stem = _unique_yaml_stem(name)
        try:
            save_procedure(proc_dict, yaml_stem)
        except OSError as e:
            return render(request, 'procedure_create.html', {
                'error': f'Could not save procedure file: {e}',
                'form_name': name,
                'form_version': version,
                'form_description': description,
                'form_preconditions': preconditions,
                'form_steps': steps,
            })
        procedure = Procedure.objects.create(name=name, version=version, description=description, yaml_file=yaml_stem)
        return redirect(reverse('procedure_review') + f'?procedure={procedure.id}')
    return render(request, 'procedure_create.html', {
        'form_name': '',
        'form_version': '1.0',
        'form_description': '',
        'form_preconditions': '',
        'form_steps': [{'id': '', 'description': '', 'input': ''}],
    })


def procedure_edit(request, procedure_id):
    """Edit an existing procedure (name, version, steps). Keeps same yaml_file."""
    procedure = get_object_or_404(Procedure.objects.prefetch_related('tags'), pk=procedure_id)
    try:
        proc = load_procedure(procedure.yaml_file)
    except (FileNotFoundError, OSError):
        return redirect('procedure_list')
    steps = proc.get('steps', [])
    form_preconditions = (proc.get('preconditions') or '')
    form_steps = [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in steps]
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        version = request.POST.get('version', '1.0').strip() or '1.0'
        description = (request.POST.get('description') or '').strip()
        preconditions = (request.POST.get('preconditions') or '').strip()
        step_ids = request.POST.getlist('step_id')
        step_descriptions = request.POST.getlist('step_description')
        step_inputs = request.POST.getlist('step_input')
        new_steps = []
        for i, sid in enumerate(step_ids):
            sid = (sid or '').strip()
            desc = (step_descriptions[i] if i < len(step_descriptions) else '').strip()
            inp = (step_inputs[i] if i < len(step_inputs) else '').strip()
            if sid and desc:
                step = {'id': sid, 'description': desc}
                if inp:
                    step['input'] = inp
                new_steps.append(step)
        if not name:
            return render(request, 'procedure_edit.html', {
                'procedure': procedure,
                'error': 'Procedure name is required.',
                'form_name': request.POST.get('name'),
                'form_version': request.POST.get('version'),
                'form_description': description,
                'form_preconditions': preconditions,
                'form_steps': [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in (new_steps or [{}])] or [{'id': '', 'description': '', 'input': ''}],
            })
        if not new_steps:
            return render(request, 'procedure_edit.html', {
                'procedure': procedure,
                'error': 'At least one step (id and description) is required.',
                'form_name': name,
                'form_version': version,
                'form_description': description,
                'form_preconditions': preconditions,
                'form_steps': [{'id': '', 'description': '', 'input': ''}],
            })
        proc_dict = {'name': name, 'version': version, 'steps': new_steps}
        if preconditions:
            proc_dict['preconditions'] = preconditions
        try:
            save_procedure(proc_dict, procedure.yaml_file)
        except OSError as e:
            return render(request, 'procedure_edit.html', {
                'procedure': procedure,
                'error': f'Could not save procedure file: {e}',
                'form_name': name,
                'form_version': version,
                'form_description': description,
                'form_preconditions': preconditions,
                'form_steps': [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in new_steps] or [{'id': '', 'description': '', 'input': ''}],
            })
        procedure.name = name
        procedure.version = version
        procedure.description = description
        procedure.save()
        messages.success(request, f'Procedure "{name}" updated.')
        return redirect(reverse('procedure_review') + f'?procedure={procedure.id}')
    return render(request, 'procedure_edit.html', {
        'procedure': procedure,
        'form_name': procedure.name,
        'form_version': procedure.version,
        'form_description': procedure.description,
        'form_preconditions': form_preconditions,
        'form_steps': form_steps or [{'id': '', 'description': '', 'input': ''}],
    })


def procedure_delete(request, procedure_id):
    """Confirm and delete a procedure (and its YAML file). Runs are deleted by CASCADE."""
    procedure = get_object_or_404(Procedure, pk=procedure_id)
    run_count = procedure.procedurerun_set.count()
    if request.method == 'POST':
        name = procedure.name
        yaml_file = procedure.yaml_file
        yaml_dir = getattr(settings, 'PROCEDURES_YAML_DIR', None)
        if yaml_dir:
            yaml_path = yaml_dir / f"{yaml_file}.yaml"
            if yaml_path.exists():
                try:
                    yaml_path.unlink()
                except OSError:
                    pass
        procedure.delete()
        messages.success(request, f'Procedure "{name}" has been deleted.')
        return redirect('procedure_list')
    return render(request, 'procedure_delete_confirm.html', {
        'procedure': procedure,
        'run_count': run_count,
    })


def procedure_clone(request, procedure_id):
    """Clone a procedure: new name, new YAML file, copy steps and tags; redirect to edit."""
    procedure = get_object_or_404(Procedure.objects.prefetch_related('tags'), pk=procedure_id)
    try:
        proc = load_procedure(procedure.yaml_file)
    except (FileNotFoundError, OSError):
        messages.error(request, 'Could not load procedure to clone.')
        return redirect('procedure_list')
    new_name = f"Copy of {procedure.name}"
    new_stem = _unique_yaml_stem(new_name)
    proc_dict = {
        'name': new_name,
        'version': procedure.version,
        'steps': proc.get('steps', []),
    }
    if proc.get('preconditions'):
        proc_dict['preconditions'] = proc['preconditions']
    try:
        save_procedure(proc_dict, new_stem)
    except OSError as e:
        messages.error(request, f'Could not save cloned procedure: {e}')
        return redirect('procedure_list')
    new_procedure = Procedure.objects.create(
        name=new_name,
        version=procedure.version,
        yaml_file=new_stem,
    )
    for tag in procedure.tags.all():
        new_procedure.tags.add(tag)
    messages.success(request, f'Cloned as "{new_name}". Edit the new procedure as needed.')
    return redirect(reverse('procedure_edit', kwargs={'procedure_id': new_procedure.pk}))


def _run_step_context(run, proc, step_index, executed_list):
    """Build step list for sidebar and clamp step_index."""
    steps = proc.get('steps', [])
    total = len(steps)
    num_done = len(executed_list)
    step_index = max(0, min(step_index, num_done))
    step_list = []
    for i, s in enumerate(steps):
        step_list.append({
            'index': i,
            'step': s,
            'done': i < num_done,
            'current': i == step_index,
        })
    return step_index, step_list, total, num_done


@login_required
def run_procedure(request, run_id):
    run = get_object_or_404(
        ProcedureRun.objects.select_related('satellite', 'procedure'),
        pk=run_id,
    )
    if run.status != ProcedureRun.STATUS_RUNNING:
        return redirect('run_summary', run_id=run_id)

    if request.method == 'POST' and request.POST.get('abort') is not None:
        from django.utils import timezone
        run.status = ProcedureRun.STATUS_CANCELLED
        run.end_time = timezone.now()
        run.save()
        messages.success(request, 'Procedure run aborted.')
        return redirect('dashboard')

    executed_list = list(run.step_executions.order_by('timestamp'))
    proc = load_procedure(run.procedure.yaml_file)
    step_index = int(request.GET.get('step', 0))
    step_index, step_list, total_steps, num_done = _run_step_context(run, proc, step_index, executed_list)

    if request.method == 'POST':
        keep_view_all = request.POST.get('view_all') == '1'
        if request.POST.get('save_run_notes') is not None:
            run.run_notes = request.POST.get('run_notes', '').strip()
            run.save()
            messages.success(request, 'Run notes saved.')
            q = '?view=all' if keep_view_all else f'?step={step_index}'
            return redirect(reverse('run', kwargs={'run_id': run_id}) + q)
        step = get_next_step(proc, step_index)
        if step is None:
            return redirect('dashboard')
        status = request.POST.get('status', 'PASS')
        input_value = request.POST.get('value', '').strip() or None
        notes = request.POST.get('notes', '').strip() or None
        StepExecution.objects.create(
            run=run,
            step_id=step['id'],
            description=step.get('description', ''),
            status=status,
            input_value=input_value,
            notes=notes,
        )
        next_step = get_next_step(proc, step_index + 1)
        if next_step is None:
            from django.utils import timezone
            run.end_time = timezone.now()
            run.status = status
            run.save()
            return redirect('dashboard')
        q = '?view=all' if keep_view_all else f'?step={step_index + 1}'
        return redirect(reverse('run', kwargs={'run_id': run_id}) + q)

    if num_done >= total_steps and total_steps > 0:
        from django.utils import timezone
        if run.end_time is None:
            run.end_time = timezone.now()
            run.status = ProcedureRun.STATUS_PASS
            run.save()
        return redirect('dashboard')

    step = get_next_step(proc, step_index)
    if step is None:
        return redirect('dashboard')

    step_is_readonly = step_index < num_done
    execution = executed_list[step_index] if step_is_readonly else None

    has_prev = step_index > 0
    has_next = step_index < total_steps - 1

    view_all = request.GET.get('view') == 'all'
    steps_with_execution = []
    if view_all:
        steps = proc.get('steps', [])
        for i, s in enumerate(steps):
            ex = executed_list[i] if i < len(executed_list) else None
            steps_with_execution.append({
                'step': s,
                'execution': ex,
                'index': i,
                'is_current': i == num_done,
            })

    preconditions = (proc.get('preconditions') or '').strip()
    return render(request, 'run.html', {
        'procedure': proc,
        'run': run,
        'satellite': run.satellite.name,
        'step': step,
        'step_index': step_index,
        'total_steps': total_steps,
        'step_list': step_list,
        'step_is_readonly': step_is_readonly,
        'execution': execution,
        'num_done': num_done,
        'preconditions': preconditions,
        'has_prev': has_prev,
        'has_next': has_next,
        'view_all': view_all,
        'steps_with_execution': steps_with_execution,
    })


def run_summary(request, run_id):
    """All steps in one view, print-friendly."""
    run = get_object_or_404(
        ProcedureRun.objects.select_related('satellite', 'procedure').prefetch_related('linked_anomalies'),
        pk=run_id,
    )
    proc = load_procedure(run.procedure.yaml_file)
    executed_list = list(run.step_executions.order_by('timestamp'))
    steps = proc.get('steps', [])
    steps_with_execution = []
    for i, step in enumerate(steps):
        ex = executed_list[i] if i < len(executed_list) else None
        steps_with_execution.append({'step': step, 'execution': ex})
    preconditions = (proc.get('preconditions') or '').strip()
    return render(request, 'run_summary.html', {
        'run': run,
        'procedure': proc,
        'steps_with_execution': steps_with_execution,
        'preconditions': preconditions,
    })


def history(request):
    q = request.GET.get('q', '')
    tag_id = request.GET.get('tag', '')
    if tag_id:
        try:
            tag_id = int(tag_id)
        except ValueError:
            tag_id = None
    else:
        tag_id = None
    sort = request.GET.get('sort', '-start_time')
    if sort not in RUN_SORT_OPTIONS:
        sort = '-start_time'
    runs = (
        ProcedureRun.objects
        .select_related('satellite', 'procedure')
        .prefetch_related('procedure__tags')
        .order_by(sort)
    )
    runs = _search_runs(runs, q, tag_id)[:100]
    tags = Tag.objects.all()
    return render(request, 'history.html', {
        'runs': runs,
        'search_query': q,
        'tag_id': tag_id,
        'tags': tags,
        'sort': sort,
        'sort_options': RUN_SORT_OPTIONS,
    })


def fleet(request):
    """Fleet-centric single pane of glass: per-satellite last run, open anomalies, last scribe."""
    satellites = list(Satellite.objects.order_by('name'))
    if not satellites:
        return render(request, 'fleet.html', {'fleet_rows': [], 'satellites_count': 0, 'fleet_health': 'green'})

    # Latest run per satellite (one query, then first per satellite in Python)
    runs = (
        ProcedureRun.objects
        .filter(satellite__in=satellites)
        .select_related('satellite', 'procedure')
        .order_by('satellite_id', '-start_time')
    )
    last_run_by_sat = {}
    for r in runs:
        if r.satellite_id not in last_run_by_sat:
            last_run_by_sat[r.satellite_id] = r

    # Open anomaly counts and high/critical flags per satellite (for health)
    open_anomaly_counts = {}
    satellites_with_high_or_critical = set()
    try:
        Anomaly = __import__('anomalies.models', fromlist=['Anomaly']).Anomaly
        open_anomaly_counts = dict(
            Anomaly.objects
            .exclude(status=Anomaly.STATUS_RESOLVED)
            .values('satellite_id')
            .annotate(cnt=Count('id'))
            .values_list('satellite_id', 'cnt')
        )
        satellites_with_high_or_critical = set(
            Anomaly.objects
            .exclude(status=Anomaly.STATUS_RESOLVED)
            .filter(severity__in=[Anomaly.SEVERITY_CRITICAL, Anomaly.SEVERITY_HIGH])
            .values_list('satellite_id', flat=True)
        )
    except Exception:
        pass

    # Last scribe entry per satellite
    last_scribe_by_sat = {}
    try:
        MissionLogEntry = __import__('scribe.models', fromlist=['MissionLogEntry']).MissionLogEntry
        scribe_entries = (
            MissionLogEntry.objects
            .filter(satellite_id__in=[s.id for s in satellites])
            .select_related('satellite', 'role', 'category')
            .order_by('satellite_id', '-timestamp')
        )
        for e in scribe_entries:
            if e.satellite_id and e.satellite_id not in last_scribe_by_sat:
                last_scribe_by_sat[e.satellite_id] = e
    except Exception:
        pass

    # Open events per satellite
    open_event_counts = {}
    satellites_with_critical_events = set()
    try:
        Event = __import__('events.models', fromlist=['Event']).Event
        open_event_counts = dict(
            Event.objects
            .exclude(status__in=[Event.STATUS_RESOLVED, Event.STATUS_CLOSED])
            .values('satellite_id')
            .annotate(cnt=Count('id'))
            .values_list('satellite_id', 'cnt')
        )
        satellites_with_critical_events = set(
            Event.objects
            .exclude(status__in=[Event.STATUS_RESOLVED, Event.STATUS_CLOSED])
            .filter(severity__in=[Event.SEVERITY_L4, Event.SEVERITY_L5])
            .values_list('satellite_id', flat=True)
        )
    except Exception:
        pass

    def _health_for_sat(sat_id, last_run, open_count, has_high_critical):
        if has_high_critical or sat_id in satellites_with_critical_events:
            return 'red'
        open_events = open_event_counts.get(sat_id, 0)
        if open_count > 0 or open_events > 0 or (last_run and last_run.status in (ProcedureRun.STATUS_FAIL, ProcedureRun.STATUS_CANCELLED)):
            return 'yellow'
        return 'green'

    fleet_rows = []
    health_values = []
    for s in satellites:
        last_run = last_run_by_sat.get(s.id)
        open_count = open_anomaly_counts.get(s.id, 0)
        has_high_critical = s.id in satellites_with_high_or_critical
        health = _health_for_sat(s.id, last_run, open_count, has_high_critical)
        health_values.append(health)
        fleet_rows.append({
            'satellite': s,
            'last_run': last_run,
            'open_anomalies_count': open_count,
            'open_events_count': open_event_counts.get(s.id, 0),
            'last_scribe_entry': last_scribe_by_sat.get(s.id),
            'health_status': health,
        })
    fleet_health = 'red' if 'red' in health_values else ('yellow' if 'yellow' in health_values else 'green')

    return render(request, 'fleet.html', {
        'fleet_rows': fleet_rows,
        'satellites_count': len(satellites),
        'fleet_health': fleet_health,
    })


def handover(request):
    """Handover pack: running procedures, open anomalies, latest shift notes, recent runs. Print-friendly."""
    now = timezone.now()

    running_runs = (
        ProcedureRun.objects
        .filter(status=ProcedureRun.STATUS_RUNNING)
        .select_related('satellite', 'procedure')
        .order_by('satellite__name')
    )

    open_anomalies = []
    try:
        Anomaly = __import__('anomalies.models', fromlist=['Anomaly']).Anomaly
        open_anomalies = list(
            Anomaly.objects
            .exclude(status=Anomaly.STATUS_RESOLVED)
            .select_related('satellite', 'subsystem', 'anomaly_type')
            .order_by('-severity', '-detection_time')[:50]
        )
    except Exception:
        pass

    latest_shift = None
    try:
        Shift = __import__('scribe.models', fromlist=['Shift']).Shift
        latest_shift = Shift.objects.order_by('-start_time').first()
    except Exception:
        pass

    recent_runs = (
        ProcedureRun.objects
        .select_related('satellite', 'procedure')
        .exclude(status=ProcedureRun.STATUS_RUNNING)
        .order_by('-start_time')[:15]
    )

    return render(request, 'handover.html', {
        'running_runs': running_runs,
        'open_anomalies': open_anomalies,
        'latest_shift': latest_shift,
        'recent_runs': recent_runs,
        'generated_at': now,
    })


def metrics(request):
    """Ops metrics / KPIs: procedure performance, anomaly metrics, fleet utilization, operator workload."""
    now = timezone.now()
    period_7 = now - timedelta(days=7)
    period_30 = now - timedelta(days=30)

    # Procedure performance (last 30 days): pass/fail/cancelled per procedure
    runs_30 = ProcedureRun.objects.filter(
        start_time__gte=period_30
    ).exclude(status=ProcedureRun.STATUS_RUNNING)
    procedure_stats = (
        runs_30.values('procedure__name', 'procedure_id')
        .annotate(
            total=Count('id'),
            pass_count=Count('id', filter=Q(status=ProcedureRun.STATUS_PASS)),
            fail_count=Count('id', filter=Q(status=ProcedureRun.STATUS_FAIL)),
            cancelled_count=Count('id', filter=Q(status=ProcedureRun.STATUS_CANCELLED)),
        )
        .order_by('-total')
    )

    # Anomaly metrics: open by severity
    open_by_severity = []
    try:
        Anomaly = __import__('anomalies.models', fromlist=['Anomaly']).Anomaly
        open_by_severity = list(
            Anomaly.objects
            .exclude(status=Anomaly.STATUS_RESOLVED)
            .values('severity')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
        )
        resolved_30 = Anomaly.objects.filter(
            status=Anomaly.STATUS_RESOLVED,
            updated_at__gte=period_30,
        ).count()
    except Exception:
        resolved_30 = 0

    # Fleet utilization: runs per satellite (last 7 and 30 days)
    runs_per_satellite_7 = (
        ProcedureRun.objects
        .filter(start_time__gte=period_7)
        .values('satellite__name', 'satellite_id')
        .annotate(run_count=Count('id'))
        .order_by('-run_count')
    )
    runs_per_satellite_30 = (
        ProcedureRun.objects
        .filter(start_time__gte=period_30)
        .values('satellite__name', 'satellite_id')
        .annotate(run_count=Count('id'))
        .order_by('-run_count')
    )

    # Operator workload: runs per operator (last 30 days)
    runs_per_operator = (
        ProcedureRun.objects
        .filter(start_time__gte=period_30)
        .values('operator_name')
        .annotate(run_count=Count('id'))
        .order_by('-run_count')
    )

    return render(request, 'metrics.html', {
        'procedure_stats': procedure_stats,
        'open_by_severity': open_by_severity,
        'resolved_30': resolved_30,
        'runs_per_satellite_7': runs_per_satellite_7,
        'runs_per_satellite_30': runs_per_satellite_30,
        'runs_per_operator': runs_per_operator,
        'period_7': period_7,
        'period_30': period_30,
        'now': now,
    })


def timeline(request):
    """Fused mission timeline: procedure runs, scribe entries, anomalies in one chronological list."""
    satellite_id = request.GET.get('satellite', '')
    event_type = request.GET.get('type', '')  # run, scribe, anomaly or empty = all
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()
    export_csv = request.GET.get('export') == 'csv'

    try:
        sat_id = int(satellite_id) if satellite_id else None
    except ValueError:
        sat_id = None

    events = []
    # Procedure runs: one event per run at start_time (and optionally end for completed)
    runs = ProcedureRun.objects.select_related('satellite', 'procedure').order_by('-start_time')
    if sat_id:
        runs = runs.filter(satellite_id=sat_id)
    if date_from:
        try:
            from datetime import date as date_type
            runs = runs.filter(start_time__date__gte=date_type.fromisoformat(date_from[:10]))
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            from datetime import date as date_type
            runs = runs.filter(start_time__date__lte=date_type.fromisoformat(date_to[:10]))
        except (ValueError, TypeError):
            pass
    if event_type and event_type != 'run':
        runs = runs.none()
    for r in runs[:200]:
        events.append({
            'timestamp': r.start_time,
            'type': 'run',
            'satellite_name': r.satellite.name,
            'run_id': r.id,
            'procedure_name': r.procedure.name,
            'status': r.status,
            'operator_name': r.operator_name or '—',
        })
        if r.end_time and r.status != ProcedureRun.STATUS_RUNNING:
            events.append({
                'timestamp': r.end_time,
                'type': 'run_end',
                'satellite_name': r.satellite.name,
                'run_id': r.id,
                'procedure_name': r.procedure.name,
                'status': r.status,
                'operator_name': r.operator_name or '—',
            })

    try:
        MissionLogEntry = __import__('scribe.models', fromlist=['MissionLogEntry']).MissionLogEntry
        entries = MissionLogEntry.objects.select_related('role', 'satellite', 'category').order_by('-timestamp')
        if sat_id:
            entries = entries.filter(satellite_id=sat_id)
        if date_from:
            try:
                from datetime import date as date_type
                entries = entries.filter(timestamp__date__gte=date_type.fromisoformat(date_from[:10]))
            except (ValueError, TypeError):
                pass
        if date_to:
            try:
                from datetime import date as date_type
                entries = entries.filter(timestamp__date__lte=date_type.fromisoformat(date_to[:10]))
            except (ValueError, TypeError):
                pass
        if event_type and event_type != 'scribe':
            entries = entries.none()
        for e in entries[:200]:
            events.append({
                'timestamp': e.timestamp,
                'type': 'scribe',
                'satellite_name': e.satellite.name if e.satellite else '—',
                'entry_id': e.id,
                'role_name': e.role.name,
                'category_name': e.category.name,
                'description': e.description,
                'severity': getattr(e, 'severity', ''),
            })
    except Exception:
        pass

    try:
        Anomaly = __import__('anomalies.models', fromlist=['Anomaly']).Anomaly
        anomalies = Anomaly.objects.select_related('satellite').order_by('-detection_time')
        if sat_id:
            anomalies = anomalies.filter(satellite_id=sat_id)
        if date_from:
            try:
                from datetime import date as date_type
                anomalies = anomalies.filter(detection_time__date__gte=date_type.fromisoformat(date_from[:10]))
            except (ValueError, TypeError):
                pass
        if date_to:
            try:
                from datetime import date as date_type
                anomalies = anomalies.filter(detection_time__date__lte=date_type.fromisoformat(date_to[:10]))
            except (ValueError, TypeError):
                pass
        if event_type and event_type != 'anomaly':
            anomalies = anomalies.none()
        for a in anomalies[:200]:
            events.append({
                'timestamp': a.detection_time,
                'type': 'anomaly',
                'satellite_name': a.satellite.name,
                'anomaly_id': a.id,
                'severity': a.severity,
                'status': a.status,
                'description': (a.description or '')[:200],
            })
    except Exception:
        pass

    # Events (Event Workflow)
    try:
        EventModel = __import__('events.models', fromlist=['Event']).Event
        evt_qs = EventModel.objects.select_related('satellite').order_by('-detected_time')
        if sat_id:
            evt_qs = evt_qs.filter(satellite_id=sat_id)
        if date_from:
            try:
                from datetime import date as date_type
                evt_qs = evt_qs.filter(detected_time__date__gte=date_type.fromisoformat(date_from[:10]))
            except (ValueError, TypeError):
                pass
        if date_to:
            try:
                from datetime import date as date_type
                evt_qs = evt_qs.filter(detected_time__date__lte=date_type.fromisoformat(date_to[:10]))
            except (ValueError, TypeError):
                pass
        if event_type and event_type != 'event':
            evt_qs = evt_qs.none()
        for ev_obj in evt_qs[:200]:
            events.append({
                'timestamp': ev_obj.detected_time,
                'type': 'event',
                'satellite_name': ev_obj.satellite.name,
                'event_id': ev_obj.id,
                'event_title': ev_obj.title,
                'severity': ev_obj.severity,
                'status': ev_obj.status,
                'description': (ev_obj.description or '')[:200],
            })
    except Exception:
        pass

    events.sort(key=lambda x: x['timestamp'], reverse=True)
    events = events[:300]

    if export_csv:
        import csv

        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mission_timeline.csv"'
        w = csv.writer(response)
        w.writerow(['Timestamp', 'Type', 'Satellite', 'Detail'])
        for ev in events:
            detail = ''
            if ev['type'] in ('run', 'run_end'):
                detail = f"{ev.get('procedure_name', '')} — {ev.get('status', '')} ({ev.get('operator_name', '')})"
            elif ev['type'] == 'scribe':
                detail = f"{ev.get('role_name', '')} — {ev.get('category_name', '')}: {(ev.get('description') or '')[:80]}"
            elif ev['type'] == 'anomaly':
                detail = f"Severity {ev.get('severity', '')} Status {ev.get('status', '')}: {(ev.get('description') or '')[:80]}"
            elif ev['type'] == 'event':
                detail = f"EVT {ev.get('event_title', '')} [{ev.get('severity', '')}] {ev.get('status', '')}: {(ev.get('description') or '')[:80]}"
            w.writerow([
                ev['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(ev['timestamp'], 'strftime') else str(ev['timestamp']),
                ev['type'],
                ev.get('satellite_name', ''),
                detail,
            ])
        return response

    satellites = Satellite.objects.all().order_by('name')
    return render(request, 'timeline.html', {
        'events': events,
        'satellites': satellites,
        'filter_satellite_id': sat_id,
        'filter_type': event_type,
        'filter_from': date_from,
        'filter_to': date_to,
    })
