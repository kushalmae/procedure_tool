from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.text import slugify

from .models import Satellite, Tag, Procedure, ProcedureRun, StepExecution
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


def dashboard(request):
    from django.utils import timezone
    from datetime import timedelta

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
    try:
        MissionLogEntry = __import__('scribe.models', fromlist=['MissionLogEntry']).MissionLogEntry
        day_ago = timezone.now() - timedelta(days=1)
        scribe_entries_24h = MissionLogEntry.objects.filter(timestamp__gte=day_ago).count()
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
    return render(request, 'start.html', {
        'satellites': satellites,
        'procedures': procedures,
        'tags': tags,
        'filter_tag_id': filter_tag_id,
        'preselected_procedure_id': preselected_procedure_id,
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
            Q(name__icontains=q) | Q(version__icontains=q)
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
    return render(request, 'procedure_review.html', {
        'procedure': procedure,
        'proc': proc,
        'steps': steps,
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
                'form_steps': steps,
            })
        if not steps:
            return render(request, 'procedure_create.html', {
                'error': 'At least one step (id and description) is required.',
                'form_name': name,
                'form_version': version,
                'form_steps': [],
            })
        proc_dict = {'name': name, 'version': version, 'steps': steps}
        yaml_stem = _unique_yaml_stem(name)
        try:
            save_procedure(proc_dict, yaml_stem)
        except OSError as e:
            return render(request, 'procedure_create.html', {
                'error': f'Could not save procedure file: {e}',
                'form_name': name,
                'form_version': version,
                'form_steps': steps,
            })
        procedure = Procedure.objects.create(name=name, version=version, yaml_file=yaml_stem)
        return redirect(reverse('procedure_review') + f'?procedure={procedure.id}')
    return render(request, 'procedure_create.html', {
        'form_name': '',
        'form_version': '1.0',
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
    form_steps = [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in steps]
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        version = request.POST.get('version', '1.0').strip() or '1.0'
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
                'form_steps': [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in (new_steps or [{}])] or [{'id': '', 'description': '', 'input': ''}],
            })
        if not new_steps:
            return render(request, 'procedure_edit.html', {
                'procedure': procedure,
                'error': 'At least one step (id and description) is required.',
                'form_name': name,
                'form_version': version,
                'form_steps': [{'id': '', 'description': '', 'input': ''}],
            })
        proc_dict = {'name': name, 'version': version, 'steps': new_steps}
        try:
            save_procedure(proc_dict, procedure.yaml_file)
        except OSError as e:
            return render(request, 'procedure_edit.html', {
                'procedure': procedure,
                'error': f'Could not save procedure file: {e}',
                'form_name': name,
                'form_version': version,
                'form_steps': [{'id': s.get('id', ''), 'description': s.get('description', ''), 'input': s.get('input', '')} for s in new_steps] or [{'id': '', 'description': '', 'input': ''}],
            })
        procedure.name = name
        procedure.version = version
        procedure.save()
        messages.success(request, f'Procedure "{name}" updated.')
        return redirect(reverse('procedure_review') + f'?procedure={procedure.id}')
    return render(request, 'procedure_edit.html', {
        'procedure': procedure,
        'form_name': procedure.name,
        'form_version': procedure.version,
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
        'has_prev': has_prev,
        'has_next': has_next,
        'view_all': view_all,
        'steps_with_execution': steps_with_execution,
    })


def run_summary(request, run_id):
    """All steps in one view, print-friendly."""
    run = get_object_or_404(
        ProcedureRun.objects.select_related('satellite', 'procedure'),
        pk=run_id,
    )
    proc = load_procedure(run.procedure.yaml_file)
    executed_list = list(run.step_executions.order_by('timestamp'))
    steps = proc.get('steps', [])
    steps_with_execution = []
    for i, step in enumerate(steps):
        ex = executed_list[i] if i < len(executed_list) else None
        steps_with_execution.append({'step': step, 'execution': ex})
    return render(request, 'run_summary.html', {
        'run': run,
        'procedure': proc,
        'steps_with_execution': steps_with_execution,
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
