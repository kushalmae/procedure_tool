import csv
from datetime import timedelta

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from anomalies.models import Anomaly
from procedures.models import ProcedureRun, Satellite
from scribe.models import MissionLogEntry


def _parse_filters(request):
    """Extract common date-range and satellite filters from GET params."""
    now = timezone.now()
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    satellite_id = request.GET.get('satellite')

    if date_from:
        try:
            from datetime import datetime
            dt_from = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
        except (ValueError, TypeError):
            dt_from = now - timedelta(days=30)
    else:
        dt_from = now - timedelta(days=30)

    if date_to:
        try:
            from datetime import datetime
            dt_to = timezone.make_aware(
                datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            )
        except (ValueError, TypeError):
            dt_to = now
    else:
        dt_to = now

    sat = None
    if satellite_id:
        try:
            sat = Satellite.objects.filter(mission=request.mission, id=int(satellite_id)).first()
        except (ValueError, TypeError):
            pass

    return dt_from, dt_to, sat


def _filter_qs(request):
    """Return the parsed filters plus the available satellite list for the mission."""
    dt_from, dt_to, sat = _parse_filters(request)
    satellites = Satellite.objects.filter(mission=request.mission)
    return dt_from, dt_to, sat, satellites


def _query_string(request, report_name):
    """Build the query-string portion for CSV export links."""
    parts = [f'report={report_name}']
    if request.GET.get('from'):
        parts.append(f"from={request.GET['from']}")
    if request.GET.get('to'):
        parts.append(f"to={request.GET['to']}")
    if request.GET.get('satellite'):
        parts.append(f"satellite={request.GET['satellite']}")
    return '&'.join(parts)


def reports_dashboard(request, mission_slug):
    reports = [
        {
            'title': 'Procedure Performance',
            'url_name': 'report_procedure_performance',
            'description': 'Pass/fail/cancelled rates, average duration, and per-procedure breakdown.',
            'icon_path': 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
        },
        {
            'title': 'Anomaly Summary',
            'url_name': 'report_anomaly_summary',
            'description': 'Anomaly counts by severity and status, mean time to resolution, satellite breakdown.',
            'icon_path': 'M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
        },
        {
            'title': 'Operator Workload',
            'url_name': 'report_operator_workload',
            'description': 'Runs per operator, unique procedures executed, and total active hours.',
            'icon_path': 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
        },
        {
            'title': 'Mission Activity',
            'url_name': 'report_mission_activity',
            'description': 'Day-by-day activity: procedure runs, scribe entries, and anomalies over time.',
            'icon_path': 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
        },
    ]
    return render(request, 'reports/reports_dashboard.html', {'reports': reports})


def procedure_performance_report(request, mission_slug):
    dt_from, dt_to, sat, satellites = _filter_qs(request)
    mission = request.mission

    runs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
    if sat:
        runs = runs.filter(satellite=sat)

    stats = (
        runs
        .values('procedure__name')
        .annotate(
            total=Count('id'),
            pass_count=Count('id', filter=Q(status=ProcedureRun.STATUS_PASS)),
            fail_count=Count('id', filter=Q(status=ProcedureRun.STATUS_FAIL)),
            cancelled_count=Count('id', filter=Q(status=ProcedureRun.STATUS_CANCELLED)),
        )
        .order_by('-total')
    )

    completed_runs = runs.filter(end_time__isnull=False, start_time__isnull=False)
    avg_duration = completed_runs.annotate(
        duration=F('end_time') - F('start_time')
    ).aggregate(avg=Avg('duration'))['avg']

    avg_duration_minutes = None
    if avg_duration:
        avg_duration_minutes = round(avg_duration.total_seconds() / 60, 1)

    total_runs = runs.count()

    procedure_data = []
    for s in stats:
        total = s['total']
        pass_pct = round(s['pass_count'] / total * 100) if total else 0
        fail_pct = round(s['fail_count'] / total * 100) if total else 0
        cancel_pct = round(s['cancelled_count'] / total * 100) if total else 0
        procedure_data.append({
            'name': s['procedure__name'] or '—',
            'total': total,
            'pass_count': s['pass_count'],
            'fail_count': s['fail_count'],
            'cancelled_count': s['cancelled_count'],
            'pass_pct': pass_pct,
            'fail_pct': fail_pct,
            'cancel_pct': cancel_pct,
        })

    csv_qs = _query_string(request, 'procedure_performance')

    return render(request, 'reports/procedure_performance.html', {
        'procedures': procedure_data,
        'total_runs': total_runs,
        'avg_duration_minutes': avg_duration_minutes,
        'dt_from': dt_from,
        'dt_to': dt_to,
        'satellites': satellites,
        'selected_satellite': sat,
        'csv_qs': csv_qs,
    })


def anomaly_summary_report(request, mission_slug):
    dt_from, dt_to, sat, satellites = _filter_qs(request)
    mission = request.mission

    base_qs = Anomaly.objects.filter(mission=mission)
    period_qs = base_qs.filter(detected_time__gte=dt_from, detected_time__lte=dt_to)
    if sat:
        period_qs = period_qs.filter(satellite=sat)

    by_severity = (
        period_qs
        .values('severity')
        .annotate(total=Count('id'))
        .order_by('severity')
    )

    severity_labels = dict(Anomaly.SEVERITY_CHOICES)
    severity_data = []
    max_sev = max((r['total'] for r in by_severity), default=1) or 1
    for row in by_severity:
        severity_data.append({
            'severity': row['severity'],
            'label': severity_labels.get(row['severity'], row['severity']),
            'total': row['total'],
            'bar_pct': round(row['total'] / max_sev * 100),
        })

    open_count = period_qs.filter(
        status__in=[Anomaly.STATUS_NEW, Anomaly.STATUS_INVESTIGATING, Anomaly.STATUS_MITIGATED]
    ).count()
    closed_count = period_qs.filter(
        status__in=[Anomaly.STATUS_RESOLVED, Anomaly.STATUS_CLOSED]
    ).count()
    new_in_period = period_qs.count()

    resolved_qs = period_qs.filter(
        status__in=[Anomaly.STATUS_RESOLVED, Anomaly.STATUS_CLOSED],
        updated_at__isnull=False,
    )
    mttr_agg = resolved_qs.annotate(
        resolution_time=F('updated_at') - F('detected_time')
    ).aggregate(avg=Avg('resolution_time'))['avg']
    mttr_hours = round(mttr_agg.total_seconds() / 3600, 1) if mttr_agg else None

    by_satellite = (
        period_qs
        .values('satellite__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    max_sat = max((r['total'] for r in by_satellite), default=1) or 1
    satellite_data = []
    for row in by_satellite:
        satellite_data.append({
            'name': row['satellite__name'] or '—',
            'total': row['total'],
            'bar_pct': round(row['total'] / max_sat * 100),
        })

    csv_qs = _query_string(request, 'anomaly_summary')

    return render(request, 'reports/anomaly_summary.html', {
        'severity_data': severity_data,
        'open_count': open_count,
        'closed_count': closed_count,
        'new_in_period': new_in_period,
        'mttr_hours': mttr_hours,
        'satellite_data': satellite_data,
        'dt_from': dt_from,
        'dt_to': dt_to,
        'satellites': satellites,
        'selected_satellite': sat,
        'csv_qs': csv_qs,
    })


def operator_workload_report(request, mission_slug):
    dt_from, dt_to, sat, satellites = _filter_qs(request)
    mission = request.mission

    runs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
    if sat:
        runs = runs.filter(satellite=sat)

    operator_stats = (
        runs
        .values('operator_name')
        .annotate(
            run_count=Count('id'),
            unique_procedures=Count('procedure', distinct=True),
            total_duration=Sum(F('end_time') - F('start_time')),
        )
        .order_by('-run_count')
    )

    operators = []
    max_runs = max((o['run_count'] for o in operator_stats), default=1) or 1
    for o in operator_stats:
        hours = None
        if o['total_duration']:
            hours = round(o['total_duration'].total_seconds() / 3600, 1)
        operators.append({
            'name': o['operator_name'] or '—',
            'run_count': o['run_count'],
            'unique_procedures': o['unique_procedures'],
            'hours': hours,
            'bar_pct': round(o['run_count'] / max_runs * 100),
        })

    csv_qs = _query_string(request, 'operator_workload')

    return render(request, 'reports/operator_workload.html', {
        'operators': operators,
        'dt_from': dt_from,
        'dt_to': dt_to,
        'satellites': satellites,
        'selected_satellite': sat,
        'csv_qs': csv_qs,
    })


def mission_activity_report(request, mission_slug):
    dt_from, dt_to, sat, satellites = _filter_qs(request)
    mission = request.mission

    runs_qs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
    anomaly_qs = Anomaly.objects.filter(mission=mission, detected_time__gte=dt_from, detected_time__lte=dt_to)
    scribe_qs = MissionLogEntry.objects.filter(mission=mission, timestamp__gte=dt_from, timestamp__lte=dt_to)

    if sat:
        runs_qs = runs_qs.filter(satellite=sat)
        anomaly_qs = anomaly_qs.filter(satellite=sat)
        scribe_qs = scribe_qs.filter(satellite=sat)

    runs_by_day = dict(
        runs_qs
        .annotate(day=TruncDate('start_time'))
        .values('day')
        .annotate(count=Count('id'))
        .values_list('day', 'count')
    )

    anomalies_by_day = dict(
        anomaly_qs
        .annotate(day=TruncDate('detected_time'))
        .values('day')
        .annotate(count=Count('id'))
        .values_list('day', 'count')
    )

    scribe_by_day = dict(
        scribe_qs
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(count=Count('id'))
        .values_list('day', 'count')
    )

    all_days = sorted(set(list(runs_by_day.keys()) + list(anomalies_by_day.keys()) + list(scribe_by_day.keys())))

    daily_data = []
    total_runs = total_anomalies = total_scribe = 0
    for day in all_days:
        r = runs_by_day.get(day, 0)
        a = anomalies_by_day.get(day, 0)
        s = scribe_by_day.get(day, 0)
        total_runs += r
        total_anomalies += a
        total_scribe += s
        daily_data.append({'day': day, 'runs': r, 'anomalies': a, 'scribe_entries': s})

    csv_qs = _query_string(request, 'mission_activity')

    return render(request, 'reports/mission_activity.html', {
        'daily_data': daily_data,
        'total_runs': total_runs,
        'total_anomalies': total_anomalies,
        'total_scribe': total_scribe,
        'dt_from': dt_from,
        'dt_to': dt_to,
        'satellites': satellites,
        'selected_satellite': sat,
        'csv_qs': csv_qs,
    })


def report_csv_export(request, mission_slug):
    report_type = request.GET.get('report', '')
    dt_from, dt_to, sat, _ = _filter_qs(request)
    mission = request.mission

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type or "report"}.csv"'
    writer = csv.writer(response)

    if report_type == 'procedure_performance':
        runs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
        if sat:
            runs = runs.filter(satellite=sat)
        stats = (
            runs
            .values('procedure__name')
            .annotate(
                total=Count('id'),
                pass_count=Count('id', filter=Q(status=ProcedureRun.STATUS_PASS)),
                fail_count=Count('id', filter=Q(status=ProcedureRun.STATUS_FAIL)),
                cancelled_count=Count('id', filter=Q(status=ProcedureRun.STATUS_CANCELLED)),
            )
            .order_by('-total')
        )
        writer.writerow(['Procedure', 'Total Runs', 'Pass', 'Fail', 'Cancelled', 'Pass %', 'Fail %', 'Cancelled %'])
        for s in stats:
            total = s['total']
            writer.writerow([
                s['procedure__name'] or '—',
                total,
                s['pass_count'],
                s['fail_count'],
                s['cancelled_count'],
                round(s['pass_count'] / total * 100, 1) if total else 0,
                round(s['fail_count'] / total * 100, 1) if total else 0,
                round(s['cancelled_count'] / total * 100, 1) if total else 0,
            ])

    elif report_type == 'anomaly_summary':
        anomalies = Anomaly.objects.filter(
            mission=mission, detected_time__gte=dt_from, detected_time__lte=dt_to
        )
        if sat:
            anomalies = anomalies.filter(satellite=sat)
        writer.writerow(['ID', 'Title', 'Satellite', 'Severity', 'Status', 'Detected', 'Updated'])
        for a in anomalies:
            writer.writerow([
                f'ANOM-{a.pk}',
                a.title,
                a.satellite.name if a.satellite else '—',
                a.get_severity_display(),
                a.get_status_display(),
                a.detected_time.strftime('%Y-%m-%d %H:%M'),
                a.updated_at.strftime('%Y-%m-%d %H:%M'),
            ])

    elif report_type == 'operator_workload':
        runs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
        if sat:
            runs = runs.filter(satellite=sat)
        stats = (
            runs
            .values('operator_name')
            .annotate(
                run_count=Count('id'),
                unique_procedures=Count('procedure', distinct=True),
                total_duration=Sum(F('end_time') - F('start_time')),
            )
            .order_by('-run_count')
        )
        writer.writerow(['Operator', 'Runs', 'Unique Procedures', 'Total Hours'])
        for o in stats:
            hours = ''
            if o['total_duration']:
                hours = round(o['total_duration'].total_seconds() / 3600, 1)
            writer.writerow([o['operator_name'] or '—', o['run_count'], o['unique_procedures'], hours])

    elif report_type == 'mission_activity':
        runs_qs = ProcedureRun.objects.filter(mission=mission, start_time__gte=dt_from, start_time__lte=dt_to)
        anomaly_qs = Anomaly.objects.filter(mission=mission, detected_time__gte=dt_from, detected_time__lte=dt_to)
        scribe_qs = MissionLogEntry.objects.filter(mission=mission, timestamp__gte=dt_from, timestamp__lte=dt_to)
        if sat:
            runs_qs = runs_qs.filter(satellite=sat)
            anomaly_qs = anomaly_qs.filter(satellite=sat)
            scribe_qs = scribe_qs.filter(satellite=sat)

        runs_by_day = dict(
            runs_qs.annotate(day=TruncDate('start_time'))
            .values('day').annotate(count=Count('id')).values_list('day', 'count')
        )
        anomalies_by_day = dict(
            anomaly_qs.annotate(day=TruncDate('detected_time'))
            .values('day').annotate(count=Count('id')).values_list('day', 'count')
        )
        scribe_by_day = dict(
            scribe_qs.annotate(day=TruncDate('timestamp'))
            .values('day').annotate(count=Count('id')).values_list('day', 'count')
        )

        all_days = sorted(set(list(runs_by_day.keys()) + list(anomalies_by_day.keys()) + list(scribe_by_day.keys())))
        writer.writerow(['Date', 'Procedure Runs', 'Anomalies', 'Scribe Entries'])
        for day in all_days:
            writer.writerow([
                day.strftime('%Y-%m-%d'),
                runs_by_day.get(day, 0),
                anomalies_by_day.get(day, 0),
                scribe_by_day.get(day, 0),
            ])
    else:
        writer.writerow(['Error'])
        writer.writerow(['Unknown report type. Use: procedure_performance, anomaly_summary, operator_workload, mission_activity'])

    return response
