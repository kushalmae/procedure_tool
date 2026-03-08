from django.conf import settings
from django.db import models


class RequestType(models.Model):
    mission = models.ForeignKey(
        'missions.Mission', on_delete=models.CASCADE,
        related_name='request_types', null=True, blank=True,
    )
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SMERequest(models.Model):
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_PENDING_APPROVAL = 'PENDING_APPROVAL'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_NEEDS_CLARIFICATION = 'NEEDS_CLARIFICATION'
    STATUS_QUEUED = 'QUEUED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_PENDING_APPROVAL, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_NEEDS_CLARIFICATION, 'Needs Clarification'),
        (STATUS_QUEUED, 'Queued'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CLOSED, 'Closed'),
    ]

    PRIORITY_LOW = 'LOW'
    PRIORITY_NORMAL = 'NORMAL'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_URGENT = 'URGENT'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    mission = models.ForeignKey(
        'missions.Mission', on_delete=models.CASCADE,
        related_name='sme_requests', null=True, blank=True,
    )
    title = models.CharField(max_length=200)
    satellite = models.ForeignKey(
        'procedures.Satellite',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests',
    )
    subsystem = models.ForeignKey(
        'procedures.Subsystem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests',
    )
    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests',
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )
    description = models.TextField(
        help_text='Describe the data or analysis being requested.',
    )
    time_range_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Start of the time range for requested data.',
    )
    time_range_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text='End of the time range for requested data.',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests_created',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests_assigned',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests_approved',
    )
    linked_event = models.ForeignKey(
        'scribe.MissionLogEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_requests',
        help_text='Optionally link to an operational event from Mission Scribe.',
    )
    result_notes = models.TextField(
        blank=True,
        help_text='Output or results delivered for this request.',
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text='Explanation if request was rejected or needs clarification.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SME request'
        verbose_name_plural = 'SME requests'

    def __str__(self):
        return f"#{self.pk} {self.title}"


class RequestNote(models.Model):
    request = models.ForeignKey(
        SMERequest,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sme_request_notes',
    )
    body = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on #{self.request_id} – {self.created_at}"
