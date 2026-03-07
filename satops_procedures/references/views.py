import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import ReferenceEntry, Subsystem


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def reference_list(request):
    if request.GET.get('clear'):
        if 'reference_filters' in request.session:
            del request.session['reference_filters']
        return redirect('reference_list')

    SORT_OPTIONS = [
        'subsystem__name',
        'title',
        '-title',
        'document_type',
        '-updated_at',
    ]
    saved = request.session.get('reference_filters') or {}
    subsystem_id = request.GET.get('subsystem', saved.get('subsystem', ''))
    document_type = request.GET.get('document_type', saved.get('document_type', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', 'subsystem__name'))
    if sort not in SORT_OPTIONS:
        sort = 'subsystem__name'

    has_filters = any([subsystem_id, document_type, q])
    if has_filters or sort != 'subsystem__name':
        request.session['reference_filters'] = {
            'subsystem': subsystem_id or '',
            'document_type': document_type or '',
            'q': q or '',
            'sort': sort,
        }

    entries = ReferenceEntry.objects.select_related('subsystem').order_by(sort)

    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            entries = entries.filter(subsystem_id=sid)
    if document_type:
        entries = entries.filter(document_type=document_type)
    if q:
        entries = entries.filter(
            Q(title__icontains=q)
            | Q(section__icontains=q)
            | Q(location__icontains=q)
            | Q(user_notes__icontains=q)
        )

    entries = entries[:200]

    context = {
        'entries': entries,
        'subsystems': Subsystem.objects.all(),
        'filter_subsystem_id': _int_or_none(subsystem_id),
        'filter_document_type': document_type or None,
        'search_query': q,
        'sort': sort,
        'type_choices': ReferenceEntry.TYPE_CHOICES,
    }
    return render(request, 'references/reference_list.html', context)


def reference_detail(request, entry_id):
    entry = get_object_or_404(
        ReferenceEntry.objects.select_related('subsystem'),
        pk=entry_id,
    )
    return render(request, 'references/reference_detail.html', {'entry': entry})


@login_required
def reference_create(request):
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        document_type = request.POST.get('document_type') or ReferenceEntry.TYPE_REFERENCE
        subsystem_id = request.POST.get('subsystem')
        section = (request.POST.get('section') or '').strip()
        version = (request.POST.get('version') or '').strip()
        location = (request.POST.get('location') or '').strip()
        user_notes = (request.POST.get('user_notes') or '').strip()

        if not title or not subsystem_id or not location:
            messages.error(request, 'Title, subsystem, and location are required.')
            return render(request, 'references/reference_form.html', {
                'subsystems': Subsystem.objects.all(),
                'type_choices': ReferenceEntry.TYPE_CHOICES,
                'form': {
                    'title': title,
                    'document_type': document_type,
                    'subsystem_id': _int_or_none(subsystem_id),
                    'section': section,
                    'version': version,
                    'location': location,
                    'user_notes': user_notes,
                },
            })

        subsystem = get_object_or_404(Subsystem, pk=subsystem_id)

        entry = ReferenceEntry.objects.create(
            title=title,
            document_type=document_type,
            subsystem=subsystem,
            section=section,
            version=version,
            location=location,
            user_notes=user_notes,
        )
        messages.success(request, f'Reference "{entry.title}" created.')
        return redirect('reference_detail', entry_id=entry.pk)

    context = {
        'subsystems': Subsystem.objects.all(),
        'type_choices': ReferenceEntry.TYPE_CHOICES,
        'form': {
            'title': '',
            'document_type': ReferenceEntry.TYPE_REFERENCE,
            'subsystem_id': None,
            'section': '',
            'version': '',
            'location': '',
            'user_notes': '',
        },
    }
    return render(request, 'references/reference_form.html', context)


@login_required
def reference_edit(request, entry_id):
    entry = get_object_or_404(ReferenceEntry, pk=entry_id)
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        document_type = request.POST.get('document_type') or ReferenceEntry.TYPE_REFERENCE
        subsystem_id = request.POST.get('subsystem')
        section = (request.POST.get('section') or '').strip()
        version = (request.POST.get('version') or '').strip()
        location = (request.POST.get('location') or '').strip()
        user_notes = (request.POST.get('user_notes') or '').strip()

        if not title or not subsystem_id or not location:
            messages.error(request, 'Title, subsystem, and location are required.')
            return render(request, 'references/reference_form.html', {
                'entry': entry,
                'subsystems': Subsystem.objects.all(),
                'type_choices': ReferenceEntry.TYPE_CHOICES,
                'form': {
                    'title': title,
                    'document_type': document_type,
                    'subsystem_id': _int_or_none(subsystem_id),
                    'section': section,
                    'version': version,
                    'location': location,
                    'user_notes': user_notes,
                },
            })

        subsystem = get_object_or_404(Subsystem, pk=subsystem_id)

        entry.title = title
        entry.document_type = document_type
        entry.subsystem = subsystem
        entry.section = section
        entry.version = version
        entry.location = location
        entry.user_notes = user_notes
        entry.save()
        messages.success(request, f'Reference "{entry.title}" updated.')
        return redirect('reference_detail', entry_id=entry.pk)

    context = {
        'entry': entry,
        'subsystems': Subsystem.objects.all(),
        'type_choices': ReferenceEntry.TYPE_CHOICES,
        'form': {
            'title': entry.title,
            'document_type': entry.document_type,
            'subsystem_id': entry.subsystem_id,
            'section': entry.section,
            'version': entry.version,
            'location': entry.location,
            'user_notes': entry.user_notes,
        },
    }
    return render(request, 'references/reference_form.html', context)


@login_required
def reference_delete(request, entry_id):
    entry = get_object_or_404(ReferenceEntry, pk=entry_id)
    if request.method == 'POST':
        name = entry.title
        entry.delete()
        messages.success(request, f'Reference "{name}" has been deleted.')
        return redirect('reference_list')
    return render(request, 'references/reference_confirm_delete.html', {'entry': entry})


@login_required
def reference_csv_import(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return redirect('reference_list')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a CSV.')
            return redirect('reference_list')

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception:
            messages.error(request, 'Could not read the CSV file. Check encoding and format.')
            return redirect('reference_list')

        EXPECTED = {'Title', 'Document Type', 'Subsystem', 'Location'}
        if not EXPECTED.issubset(set(reader.fieldnames or [])):
            messages.error(
                request,
                f'CSV must contain columns: {", ".join(sorted(EXPECTED))}. '
                f'Found: {", ".join(reader.fieldnames or [])}',
            )
            return redirect('reference_list')

        created = 0
        skipped = 0
        for row in reader:
            title = (row.get('Title') or '').strip()
            doc_type = (row.get('Document Type') or '').strip()
            subsystem_name = (row.get('Subsystem') or '').strip()
            section = (row.get('Section') or row.get('Section / Topic') or '').strip()
            version = (row.get('Version') or '').strip()
            location = (row.get('Location') or row.get('Location / Link') or '').strip()
            user_notes = (row.get('User Notes') or row.get('Notes') or '').strip()

            if not title or not subsystem_name or not location:
                skipped += 1
                continue

            valid_types = [c[0] for c in ReferenceEntry.TYPE_CHOICES]
            if doc_type not in valid_types:
                doc_type = ReferenceEntry.TYPE_REFERENCE

            subsystem, _ = Subsystem.objects.get_or_create(name=subsystem_name)

            ReferenceEntry.objects.create(
                title=title,
                document_type=doc_type,
                subsystem=subsystem,
                section=section,
                version=version,
                location=location,
                user_notes=user_notes,
            )
            created += 1

        msg = f'Imported {created} reference(s).'
        if skipped:
            msg += f' Skipped {skipped} row(s) with missing required fields.'
        messages.success(request, msg)
        return redirect('reference_list')

    return redirect('reference_list')


def reference_csv_export(request):
    entries = ReferenceEntry.objects.select_related('subsystem').order_by('subsystem__name', 'title')

    subsystem_id = request.GET.get('subsystem')
    document_type = request.GET.get('document_type')
    q = (request.GET.get('q') or '').strip()

    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            entries = entries.filter(subsystem_id=sid)
    if document_type:
        entries = entries.filter(document_type=document_type)
    if q:
        entries = entries.filter(
            Q(title__icontains=q)
            | Q(section__icontains=q)
            | Q(location__icontains=q)
            | Q(user_notes__icontains=q)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="references.csv"'
    response['X-Content-Type-Options'] = 'nosniff'

    writer = csv.writer(response)
    writer.writerow(['Title', 'Document Type', 'Subsystem', 'Section', 'Version', 'Location', 'User Notes'])
    for e in entries:
        writer.writerow([
            e.title,
            e.document_type,
            e.subsystem.name,
            e.section,
            e.version,
            e.location,
            e.user_notes,
        ])

    return response
