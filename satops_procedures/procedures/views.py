from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Satellite, Procedure, ProcedureRun, StepExecution
from .services.procedure_loader import load_procedure
from .services.runner import get_next_step


def dashboard(request):
    runs = ProcedureRun.objects.select_related('satellite', 'procedure').order_by('-start_time')[:50]
    return render(request, 'dashboard.html', {'runs': runs})


def start(request):
    if request.method == 'POST':
        satellite_name = request.POST.get('satellite', '').strip()
        operator_name = request.POST.get('operator', '').strip()
        if not operator_name and request.user.is_authenticated:
            operator_name = request.user.get_username()
        operator_name = operator_name or 'Anonymous'
        procedure_id = request.POST.get('procedure')
        if not satellite_name or not procedure_id:
            satellites = Satellite.objects.all()
            procedures = Procedure.objects.all()
            return render(request, 'start.html', {
                'satellites': satellites,
                'procedures': procedures,
                'error': 'Satellite and procedure are required.',
            })
        satellite, _ = Satellite.objects.get_or_create(name=satellite_name, defaults={'name': satellite_name})
        procedure = get_object_or_404(Procedure, pk=procedure_id)
        run = ProcedureRun.objects.create(
            satellite=satellite,
            procedure=procedure,
            operator=request.user if request.user.is_authenticated else None,
            operator_name=operator_name,
            status=ProcedureRun.STATUS_RUNNING,
        )
        return redirect(reverse('run', kwargs={'run_id': run.pk}) + '?step=0')
    satellites = Satellite.objects.all()
    procedures = Procedure.objects.all()
    return render(request, 'start.html', {'satellites': satellites, 'procedures': procedures})


def run_procedure(request, run_id):
    run = get_object_or_404(ProcedureRun.objects.select_related('satellite', 'procedure'), pk=run_id)
    step_index = int(request.GET.get('step', 0))
    proc = load_procedure(run.procedure.yaml_file)
    step = get_next_step(proc, step_index)
    if request.method == 'POST':
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
        return redirect(reverse('run', kwargs={'run_id': run_id}) + f'?step={step_index + 1}')
    if step is None:
        from django.utils import timezone
        if run.end_time is None:
            run.end_time = timezone.now()
            run.status = ProcedureRun.STATUS_PASS
            run.save()
        return redirect('dashboard')
    return render(request, 'run.html', {
        'request': request,
        'procedure': proc,
        'run': run,
        'satellite': run.satellite.name,
        'step': step,
        'step_index': step_index,
        'total_steps': len(proc.get('steps', [])),
    })


def history(request):
    runs = ProcedureRun.objects.select_related('satellite', 'procedure').order_by('-start_time')[:100]
    return render(request, 'history.html', {'runs': runs})
