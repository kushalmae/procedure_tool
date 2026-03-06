from django.core.management.base import BaseCommand
from handbook.models import Subsystem, AlertDefinition


DEFAULT_SUBSYSTEMS = [
    'Power',
    'ADCS',
    'Thermal',
    'Communications',
    'Payload',
    'Other',
]

SAMPLE_ALERTS = [
    # Thermal
    {
        'parameter': 'Battery Temperature',
        'subsystem': 'Thermal',
        'description': 'Battery pack temperature out of nominal range. Prolonged exposure may reduce battery life or trigger safehold.',
        'alert_conditions': 'Triggered when battery temperature exceeds warning or critical limits.',
        'warning_threshold': '> 45 C',
        'critical_threshold': '> 55 C',
        'recommended_response': 'Monitor trend. If rising, consider reducing charge rate or activating thermal control. See Thermal Safehold procedure if critical.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Panel Temperature',
        'subsystem': 'Thermal',
        'description': 'Solar panel or structure temperature outside design range. Can affect power output and structural margins.',
        'alert_conditions': 'Triggered when panel temp exceeds limits in sun or eclipse.',
        'warning_threshold': '< -20 C or > 80 C',
        'critical_threshold': '< -30 C or > 90 C',
        'recommended_response': 'Verify attitude and sun exposure. If in eclipse, monitor for recovery. Document for thermal analysis.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Payload Bay Temperature',
        'subsystem': 'Thermal',
        'description': 'Payload compartment temperature out of range. May impact instrument performance or calibration.',
        'alert_conditions': 'Triggered when payload bay temp exceeds limits.',
        'warning_threshold': 'Outside 10–35 C',
        'critical_threshold': 'Outside 5–40 C',
        'recommended_response': 'Check heater/radiator telemetry. Consider safehold or instrument standby if critical.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    # Power
    {
        'parameter': 'Bus Voltage',
        'subsystem': 'Power',
        'description': 'Main power bus voltage outside nominal range. May indicate solar array or battery regulator issue.',
        'alert_conditions': 'Triggered when bus voltage falls below or rises above limits.',
        'warning_threshold': '< 26 V or > 34 V',
        'critical_threshold': '< 24 V or > 36 V',
        'recommended_response': 'Check solar array telemetry and load. If critical, consider safehold.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Battery State of Charge',
        'subsystem': 'Power',
        'description': 'Battery state of charge (SOC) below or above expected range. Low SOC risks loss of power in eclipse.',
        'alert_conditions': 'Triggered when SOC falls below warning or critical level.',
        'warning_threshold': '< 30%',
        'critical_threshold': '< 15%',
        'recommended_response': 'Reduce non-essential loads. Prepare for eclipse; consider payload standby. If critical, execute power-safe procedure.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Solar Array Current',
        'subsystem': 'Power',
        'description': 'Solar array output current below expected for sun angle. May indicate partial failure or shadowing.',
        'alert_conditions': 'Triggered when array current is below limit for given beta angle.',
        'warning_threshold': '< 80% of expected',
        'critical_threshold': '< 60% of expected',
        'recommended_response': 'Verify attitude and array drive. Check for partial short or shadow. Plan for reduced power margin.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    # ADCS
    {
        'parameter': 'Wheel Speed',
        'subsystem': 'ADCS',
        'description': 'Reaction wheel speed outside nominal operating range. May indicate saturation or fault.',
        'alert_conditions': 'Triggered when any wheel speed exceeds limit (RPM or Nms).',
        'warning_threshold': '> 85% max speed',
        'critical_threshold': '> 95% max speed or < 10 RPM',
        'recommended_response': 'Monitor momentum. Consider momentum unload or thruster dump. Check for stuck wheel.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Pointing Error',
        'subsystem': 'ADCS',
        'description': 'Attitude pointing error exceeds mission requirement. Affects payload pointing and power.',
        'alert_conditions': 'Triggered when pointing error (e.g. roll/pitch/yaw) exceeds threshold.',
        'warning_threshold': '> 0.5 deg',
        'critical_threshold': '> 2.0 deg',
        'recommended_response': 'Check star tracker and gyro health. Consider safehold if critical or persistent.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Magnetometer Range',
        'subsystem': 'ADCS',
        'description': 'Magnetometer reading saturated or out of expected range. May affect attitude determination.',
        'alert_conditions': 'Triggered when any magnetometer axis is at limit.',
        'warning_threshold': 'Any axis at ±80% range',
        'critical_threshold': 'Any axis saturated',
        'recommended_response': 'Verify orbit and magnetic model. Consider redundant sensor or safehold if used for control.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    # Communications
    {
        'parameter': 'RF Power Output',
        'subsystem': 'Communications',
        'description': 'Transmitter RF power outside nominal. Low power may cause link loss; high may indicate fault.',
        'alert_conditions': 'Triggered when TX power telemetry is outside limits.',
        'warning_threshold': '< 90% or > 110% nominal',
        'critical_threshold': '< 70% or > 120% nominal',
        'recommended_response': 'Check amplifier telemetry and temperature. Verify link budget. Consider redundant chain if critical.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Link Margin',
        'subsystem': 'Communications',
        'description': 'Command or telemetry link margin below requirement. Risk of loss of link.',
        'alert_conditions': 'Triggered when computed link margin falls below threshold.',
        'warning_threshold': '< 3 dB',
        'critical_threshold': '< 1 dB',
        'recommended_response': 'Verify antenna pointing and station. Increase data rate or reduce range if possible. Prepare for possible LOS.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Receiver Lock',
        'subsystem': 'Communications',
        'description': 'Uplink receiver has lost lock. Command capability may be degraded or lost.',
        'alert_conditions': 'Triggered when receiver lock status goes false.',
        'warning_threshold': 'Lock lost',
        'critical_threshold': 'Lock lost > 5 min',
        'recommended_response': 'Check antenna pointing, frequency, and power. Verify no interference. Re-acquire when in view.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    # Payload
    {
        'parameter': 'Detector Temperature',
        'subsystem': 'Payload',
        'description': 'Payload detector or focal plane temperature out of operating range. Affects data quality and lifetime.',
        'alert_conditions': 'Triggered when detector temp is outside limits.',
        'warning_threshold': 'Outside -40 to -20 C',
        'critical_threshold': 'Outside -50 to -10 C',
        'recommended_response': 'Check cooler and thermal control. Put instrument in standby if critical. Document for calibration.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Data Buffer Fill',
        'subsystem': 'Payload',
        'description': 'Onboard data buffer fill level high. Risk of overflow and data loss if not dumped.',
        'alert_conditions': 'Triggered when buffer fill exceeds threshold.',
        'warning_threshold': '> 75%',
        'critical_threshold': '> 95%',
        'recommended_response': 'Schedule or prioritize downlink. Reduce collection rate if possible. Monitor dump progress.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Payload Power',
        'subsystem': 'Payload',
        'description': 'Payload subsystem power draw outside nominal. May indicate fault or mode change.',
        'alert_conditions': 'Triggered when payload power telemetry exceeds limits.',
        'warning_threshold': '< 90% or > 110% nominal',
        'critical_threshold': '< 70% or > 130% nominal',
        'recommended_response': 'Verify payload mode and configuration. If over-current, consider safe mode or power cycle per procedure.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    # Additional alerts
    {
        'parameter': 'Charge Current',
        'subsystem': 'Power',
        'description': 'Battery charge current outside expected range. May indicate BCR fault or cell imbalance.',
        'alert_conditions': 'Triggered when charge current exceeds or falls below limits for mode.',
        'warning_threshold': '> 5 A in float or < 0.5 A in bulk',
        'critical_threshold': '> 8 A or negative (discharge during charge)',
        'recommended_response': 'Check BCR and battery telemetry. If critical, consider isolating battery and safehold.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Sun Vector Residual',
        'subsystem': 'ADCS',
        'description': 'Difference between measured and expected sun vector exceeds limit. May indicate sun sensor fault or eclipse.',
        'alert_conditions': 'Triggered when sun vector residual exceeds threshold (deg or magnitude).',
        'warning_threshold': '> 2 deg',
        'critical_threshold': '> 5 deg in sun',
        'recommended_response': 'Verify sun sensor health and obscuration. Consider switching to backup sensor or safehold.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Star Tracker Valid',
        'subsystem': 'ADCS',
        'description': 'Star tracker has lost valid solution. Attitude knowledge may be degraded.',
        'alert_conditions': 'Triggered when star tracker valid flag goes false.',
        'warning_threshold': 'Valid lost',
        'critical_threshold': 'Valid lost > 2 min',
        'recommended_response': 'Check for bright object or contamination. Wait for re-acquisition. Consider sun-safe or inertially hold.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'TX Temperature',
        'subsystem': 'Communications',
        'description': 'Transmitter or PA temperature out of range. May cause power roll-off or shutdown.',
        'alert_conditions': 'Triggered when TX temp telemetry exceeds limits.',
        'warning_threshold': '> 60 C',
        'critical_threshold': '> 75 C',
        'recommended_response': 'Reduce power or duty cycle if possible. Check thermal path. Prepare for possible link loss.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Bit Error Rate',
        'subsystem': 'Communications',
        'description': 'Downlink or uplink bit error rate above acceptable level. Data integrity at risk.',
        'alert_conditions': 'Triggered when BER exceeds threshold over averaging window.',
        'warning_threshold': '> 1e-6',
        'critical_threshold': '> 1e-4',
        'recommended_response': 'Check link margin and interference. Reduce data rate or improve geometry. Retransmit critical data.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Optics Temperature',
        'subsystem': 'Payload',
        'description': 'Optical assembly temperature out of range. Affects focus and radiometric accuracy.',
        'alert_conditions': 'Triggered when optics temp is outside limits.',
        'warning_threshold': 'Outside 18–28 C',
        'critical_threshold': 'Outside 15–32 C',
        'recommended_response': 'Check thermal control. Consider recalibration pass. Put in standby if critical.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Safehold Status',
        'subsystem': 'Other',
        'description': 'Spacecraft has entered safehold mode. Requires operator assessment and recovery.',
        'alert_conditions': 'Triggered when safehold mode is asserted.',
        'warning_threshold': 'N/A (event)',
        'critical_threshold': 'N/A',
        'recommended_response': 'Review cause (power, ADCS, command loss). Execute recovery procedure. Document root cause.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Watchdog Reset',
        'subsystem': 'Other',
        'description': 'Processor watchdog timer has triggered a reset. Indicates possible software hang or fault.',
        'alert_conditions': 'Triggered on watchdog reset event.',
        'warning_threshold': 'Single event',
        'critical_threshold': 'Multiple in 24 h',
        'recommended_response': 'Document time and context. Check for pattern. Consider memory dump or safe mode. Report to engineering.',
        'severity': AlertDefinition.SEVERITY_CRITICAL,
    },
    {
        'parameter': 'Propellant Tank Pressure',
        'subsystem': 'Other',
        'description': 'Propellant tank pressure outside nominal. May indicate leak or thermal effect.',
        'alert_conditions': 'Triggered when tank pressure exceeds limits.',
        'warning_threshold': '< 90% or > 110% nominal',
        'critical_threshold': '< 70% or > 130% nominal',
        'recommended_response': 'Verify thermal environment and isolation. If leak suspected, limit maneuvers and report.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
    {
        'parameter': 'Eclipse Duration',
        'subsystem': 'Power',
        'description': 'Upcoming or current eclipse longer than design margin. Battery may not support full load.',
        'alert_conditions': 'Triggered when eclipse duration exceeds threshold for current SOC.',
        'warning_threshold': '> 35 min at current load',
        'critical_threshold': '> 45 min at current load',
        'recommended_response': 'Shed non-essential loads. Put payload in standby. Monitor SOC; execute power-safe if needed.',
        'severity': AlertDefinition.SEVERITY_WARNING,
    },
]


class Command(BaseCommand):
    help = 'Seed Handbook subsystems and optional sample alert definitions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alerts',
            action='store_true',
            help='Also create sample alert definitions.',
        )

    def handle(self, *args, **options):
        for name in DEFAULT_SUBSYSTEMS:
            _, created = Subsystem.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subsystem: {name}'))

        if options.get('alerts'):
            for data in SAMPLE_ALERTS:
                subsystem = Subsystem.objects.get(name=data['subsystem'])
                _, created = AlertDefinition.objects.get_or_create(
                    parameter=data['parameter'],
                    subsystem=subsystem,
                    defaults={
                        'description': data['description'],
                        'alert_conditions': data['alert_conditions'],
                        'warning_threshold': data['warning_threshold'],
                        'critical_threshold': data['critical_threshold'],
                        'recommended_response': data['recommended_response'],
                        'severity': data['severity'],
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created alert: {data["parameter"]}'))

        self.stdout.write(self.style.SUCCESS('Handbook seed complete.'))
