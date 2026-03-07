from django.core.management.base import BaseCommand

from cmdtlm.models import (
    CommandDefinition,
    CommandInput,
    TelemetryDefinition,
    TelemetryEnum,
)

SAMPLE_COMMANDS = [
    {
        'name': 'Set Transmitter Power',
        'command_id': '0x0101',
        'subsystem': 'Communications',
        'category': 'RF Control',
        'description': 'Sets the RF transmitter output power level. Affects link margin and power consumption.',
        'inputs': [
            {'name': 'power_level', 'order': 1, 'data_type': 'UINT8', 'description': 'Transmit power level', 'default_value': '5', 'constraints': '0–10 (0=off, 10=max)'},
            {'name': 'ramp_rate', 'order': 2, 'data_type': 'UINT8', 'description': 'Power ramp rate in dB/sec', 'default_value': '2', 'constraints': '1–5'},
        ],
    },
    {
        'name': 'Switch Antenna',
        'command_id': '0x0102',
        'subsystem': 'Communications',
        'category': 'RF Control',
        'description': 'Selects the active antenna (primary or redundant).',
        'inputs': [
            {'name': 'antenna_id', 'order': 1, 'data_type': 'ENUM', 'description': 'Antenna selection', 'constraints': '0=Primary, 1=Redundant'},
        ],
    },
    {
        'name': 'Set Data Rate',
        'command_id': '0x0103',
        'subsystem': 'Communications',
        'category': 'RF Control',
        'description': 'Configures the downlink data rate for the selected channel.',
        'inputs': [
            {'name': 'channel', 'order': 1, 'data_type': 'UINT8', 'description': 'Channel number', 'constraints': '0–3'},
            {'name': 'rate_kbps', 'order': 2, 'data_type': 'UINT32', 'description': 'Data rate in kbps', 'default_value': '128', 'constraints': '32, 64, 128, 256, 512, 1024'},
        ],
    },
    {
        'name': 'Reaction Wheel Speed Set',
        'command_id': '0x0201',
        'subsystem': 'ADCS',
        'category': 'Actuator Control',
        'description': 'Commands a target speed for a specified reaction wheel.',
        'inputs': [
            {'name': 'wheel_id', 'order': 1, 'data_type': 'UINT8', 'description': 'Wheel identifier', 'constraints': '0–3 (X+, X-, Y, Z)'},
            {'name': 'target_rpm', 'order': 2, 'data_type': 'INT16', 'description': 'Target speed in RPM', 'constraints': '-6000 to +6000'},
            {'name': 'ramp_time_ms', 'order': 3, 'data_type': 'UINT16', 'description': 'Ramp duration in milliseconds', 'default_value': '1000', 'constraints': '100–10000'},
        ],
    },
    {
        'name': 'Momentum Dump',
        'command_id': '0x0202',
        'subsystem': 'ADCS',
        'category': 'Momentum Management',
        'description': 'Initiates a magnetic torquer-based momentum dump sequence.',
        'inputs': [
            {'name': 'dump_axis', 'order': 1, 'data_type': 'ENUM', 'description': 'Axis to dump', 'constraints': '0=All, 1=X, 2=Y, 3=Z'},
            {'name': 'max_duration_s', 'order': 2, 'data_type': 'UINT16', 'description': 'Maximum dump duration in seconds', 'default_value': '300', 'constraints': '60–600'},
        ],
    },
    {
        'name': 'Set Attitude Mode',
        'command_id': '0x0203',
        'subsystem': 'ADCS',
        'category': 'Mode Control',
        'description': 'Transitions the ADCS to the specified attitude control mode.',
        'inputs': [
            {'name': 'mode', 'order': 1, 'data_type': 'ENUM', 'description': 'Target attitude mode', 'constraints': '0=Safe, 1=Detumble, 2=Nadir, 3=Sun-Point, 4=Inertial, 5=Target-Track'},
        ],
    },
    {
        'name': 'Battery Charge Control',
        'command_id': '0x0301',
        'subsystem': 'Power',
        'category': 'Power Management',
        'description': 'Sets battery charge parameters including max current and voltage limit.',
        'inputs': [
            {'name': 'max_current_mA', 'order': 1, 'data_type': 'UINT16', 'description': 'Maximum charge current in mA', 'default_value': '2000', 'constraints': '500–5000'},
            {'name': 'voltage_limit_mV', 'order': 2, 'data_type': 'UINT16', 'description': 'Charge voltage limit in mV', 'default_value': '16800', 'constraints': '14000–17000'},
            {'name': 'taper_enable', 'order': 3, 'data_type': 'BOOL', 'description': 'Enable taper charge', 'default_value': '1', 'constraints': '0=disabled, 1=enabled'},
        ],
    },
    {
        'name': 'Load Shed',
        'command_id': '0x0302',
        'subsystem': 'Power',
        'category': 'Power Management',
        'description': 'Disables specified load groups to conserve power.',
        'inputs': [
            {'name': 'load_mask', 'order': 1, 'data_type': 'UINT8', 'description': 'Bitmask of load groups to shed', 'constraints': 'Bit 0=Payload, Bit 1=Heaters, Bit 2=Comm, Bit 3=Aux'},
        ],
    },
    {
        'name': 'Heater Control',
        'command_id': '0x0401',
        'subsystem': 'Thermal',
        'category': 'Thermal Control',
        'description': 'Enables or disables a specific heater zone and sets the setpoint temperature.',
        'inputs': [
            {'name': 'zone_id', 'order': 1, 'data_type': 'UINT8', 'description': 'Heater zone identifier', 'constraints': '0–7'},
            {'name': 'enable', 'order': 2, 'data_type': 'BOOL', 'description': 'Enable (1) or disable (0) heater', 'constraints': '0 or 1'},
            {'name': 'setpoint_C', 'order': 3, 'data_type': 'INT8', 'description': 'Temperature setpoint in Celsius', 'default_value': '20', 'constraints': '-40 to +60'},
        ],
    },
    {
        'name': 'Payload Power On',
        'command_id': '0x0501',
        'subsystem': 'Payload',
        'category': 'Payload Operations',
        'description': 'Powers on the payload instrument and performs initialization sequence.',
        'inputs': [
            {'name': 'instrument_id', 'order': 1, 'data_type': 'UINT8', 'description': 'Instrument identifier', 'constraints': '0=Imager, 1=Spectrometer'},
            {'name': 'boot_mode', 'order': 2, 'data_type': 'ENUM', 'description': 'Boot mode selection', 'default_value': '0', 'constraints': '0=Normal, 1=Safe, 2=Diagnostic'},
        ],
    },
    {
        'name': 'Start Image Capture',
        'command_id': '0x0502',
        'subsystem': 'Payload',
        'category': 'Payload Operations',
        'description': 'Triggers an image capture with the specified exposure and compression settings.',
        'inputs': [
            {'name': 'exposure_ms', 'order': 1, 'data_type': 'UINT16', 'description': 'Exposure time in milliseconds', 'default_value': '50', 'constraints': '1–5000'},
            {'name': 'gain', 'order': 2, 'data_type': 'UINT8', 'description': 'Detector gain setting', 'default_value': '1', 'constraints': '0–15'},
            {'name': 'compression', 'order': 3, 'data_type': 'ENUM', 'description': 'Compression mode', 'default_value': '1', 'constraints': '0=None, 1=Lossless, 2=Lossy'},
            {'name': 'target_id', 'order': 4, 'data_type': 'UINT16', 'description': 'Target catalog ID (0=manual pointing)', 'default_value': '0', 'constraints': '0–65535'},
        ],
    },
    {
        'name': 'Reboot Processor',
        'command_id': '0x0601',
        'subsystem': 'CDH',
        'category': 'System Control',
        'description': 'Initiates a controlled reboot of the onboard processor. Use with caution.',
        'notes': 'All running tasks will be terminated. State is saved to non-volatile memory before reset.',
        'inputs': [
            {'name': 'confirm_code', 'order': 1, 'data_type': 'UINT32', 'description': 'Safety confirmation code', 'constraints': 'Must equal 0xDEADBEEF'},
            {'name': 'save_state', 'order': 2, 'data_type': 'BOOL', 'description': 'Save state before reboot', 'default_value': '1', 'constraints': '0 or 1'},
        ],
    },
    {
        'name': 'Set Time',
        'command_id': '0x0602',
        'subsystem': 'CDH',
        'category': 'System Control',
        'description': 'Sets the onboard clock to the specified UTC epoch time.',
        'inputs': [
            {'name': 'epoch_seconds', 'order': 1, 'data_type': 'UINT32', 'description': 'Seconds since J2000 epoch'},
            {'name': 'subseconds', 'order': 2, 'data_type': 'UINT16', 'description': 'Sub-second fraction (1/65536 s)', 'default_value': '0'},
        ],
    },
    {
        'name': 'File Download',
        'command_id': '0x0603',
        'subsystem': 'CDH',
        'category': 'File Management',
        'description': 'Queues an onboard file for downlink on the next contact.',
        'inputs': [
            {'name': 'file_id', 'order': 1, 'data_type': 'UINT16', 'description': 'Onboard file identifier'},
            {'name': 'priority', 'order': 2, 'data_type': 'UINT8', 'description': 'Download priority', 'default_value': '5', 'constraints': '1=highest, 10=lowest'},
        ],
    },
    {
        'name': 'Enable Safehold',
        'command_id': '0x0701',
        'subsystem': 'CDH',
        'category': 'Fault Protection',
        'description': 'Manually triggers safehold mode. Spacecraft will transition to sun-safe attitude and minimal power.',
        'notes': 'Recovery requires ground intervention. Use only as last resort.',
        'inputs': [
            {'name': 'reason_code', 'order': 1, 'data_type': 'UINT8', 'description': 'Operator reason code for logs', 'constraints': '1–255'},
        ],
    },
]

SAMPLE_TELEMETRY = [
    {
        'name': 'Battery Temperature',
        'mnemonic': 'BAT_TEMP',
        'apid': '0x0801',
        'subsystem': 'Thermal',
        'description': 'Battery pack temperature from thermistor. Sampled at 1 Hz.',
        'data_type': 'INT16',
        'units': 'degC (x0.1)',
    },
    {
        'name': 'Bus Voltage',
        'mnemonic': 'V_BUS',
        'apid': '0x0802',
        'subsystem': 'Power',
        'description': 'Main 28V power bus voltage.',
        'data_type': 'UINT16',
        'units': 'mV',
    },
    {
        'name': 'Battery State of Charge',
        'mnemonic': 'SOC',
        'apid': '0x0802',
        'subsystem': 'Power',
        'description': 'Estimated battery state of charge as a percentage.',
        'data_type': 'UINT8',
        'units': '%',
    },
    {
        'name': 'Solar Array Current',
        'mnemonic': 'I_SA',
        'apid': '0x0802',
        'subsystem': 'Power',
        'description': 'Total solar array output current.',
        'data_type': 'UINT16',
        'units': 'mA',
    },
    {
        'name': 'Charge Current',
        'mnemonic': 'I_CHG',
        'apid': '0x0802',
        'subsystem': 'Power',
        'description': 'Battery charge current from the BCR.',
        'data_type': 'INT16',
        'units': 'mA',
    },
    {
        'name': 'Reaction Wheel 1 Speed',
        'mnemonic': 'RW1_SPD',
        'apid': '0x0803',
        'subsystem': 'ADCS',
        'description': 'Reaction wheel 1 (X+) current speed.',
        'data_type': 'INT16',
        'units': 'RPM',
    },
    {
        'name': 'Reaction Wheel 2 Speed',
        'mnemonic': 'RW2_SPD',
        'apid': '0x0803',
        'subsystem': 'ADCS',
        'description': 'Reaction wheel 2 (X-) current speed.',
        'data_type': 'INT16',
        'units': 'RPM',
    },
    {
        'name': 'Pointing Error',
        'mnemonic': 'PT_ERR',
        'apid': '0x0803',
        'subsystem': 'ADCS',
        'description': 'Combined 3-axis attitude pointing error magnitude.',
        'data_type': 'FLOAT32',
        'units': 'deg',
    },
    {
        'name': 'Attitude Mode',
        'mnemonic': 'ATT_MODE',
        'apid': '0x0803',
        'subsystem': 'ADCS',
        'description': 'Current ADCS attitude control mode.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'Safe', 'description': 'Minimal control, sun-safe spin'},
            {'value': '1', 'label': 'Detumble', 'description': 'B-dot detumble using magnetorquers'},
            {'value': '2', 'label': 'Nadir', 'description': 'Earth-pointing nadir mode'},
            {'value': '3', 'label': 'Sun-Point', 'description': 'Solar array sun-pointing'},
            {'value': '4', 'label': 'Inertial', 'description': 'Fixed inertial attitude hold'},
            {'value': '5', 'label': 'Target-Track', 'description': 'Ground target tracking'},
        ],
    },
    {
        'name': 'Star Tracker Status',
        'mnemonic': 'ST_STATUS',
        'apid': '0x0803',
        'subsystem': 'ADCS',
        'description': 'Star tracker operational status flags.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'Off', 'description': 'Star tracker powered off'},
            {'value': '1', 'label': 'Initializing', 'description': 'Boot and self-test in progress'},
            {'value': '2', 'label': 'Searching', 'description': 'Searching for star matches'},
            {'value': '3', 'label': 'Tracking', 'description': 'Nominal tracking, valid solution'},
            {'value': '4', 'label': 'Lost', 'description': 'Solution lost, attempting recovery'},
            {'value': '5', 'label': 'Error', 'description': 'Hardware fault detected'},
        ],
    },
    {
        'name': 'RF Transmit Power',
        'mnemonic': 'TX_PWR',
        'apid': '0x0804',
        'subsystem': 'Communications',
        'description': 'Current RF transmitter output power.',
        'data_type': 'UINT16',
        'units': 'mW',
    },
    {
        'name': 'Receiver Lock Status',
        'mnemonic': 'RX_LOCK',
        'apid': '0x0804',
        'subsystem': 'Communications',
        'description': 'Uplink receiver carrier lock indicator.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'No Lock', 'description': 'No carrier detected'},
            {'value': '1', 'label': 'Acquiring', 'description': 'Carrier detected, acquiring lock'},
            {'value': '2', 'label': 'Locked', 'description': 'Full carrier lock established'},
        ],
    },
    {
        'name': 'Downlink Data Rate',
        'mnemonic': 'DL_RATE',
        'apid': '0x0804',
        'subsystem': 'Communications',
        'description': 'Active downlink data rate.',
        'data_type': 'UINT32',
        'units': 'bps',
    },
    {
        'name': 'Panel Temperature North',
        'mnemonic': 'PANEL_N_TEMP',
        'apid': '0x0801',
        'subsystem': 'Thermal',
        'description': 'North-facing solar panel temperature.',
        'data_type': 'INT16',
        'units': 'degC (x0.1)',
    },
    {
        'name': 'Panel Temperature South',
        'mnemonic': 'PANEL_S_TEMP',
        'apid': '0x0801',
        'subsystem': 'Thermal',
        'description': 'South-facing solar panel temperature.',
        'data_type': 'INT16',
        'units': 'degC (x0.1)',
    },
    {
        'name': 'Payload Bay Temperature',
        'mnemonic': 'PL_BAY_TEMP',
        'apid': '0x0810',
        'subsystem': 'Thermal',
        'description': 'Payload compartment internal temperature.',
        'data_type': 'INT16',
        'units': 'degC (x0.1)',
    },
    {
        'name': 'Detector Temperature',
        'mnemonic': 'DET_TEMP',
        'apid': '0x0810',
        'subsystem': 'Payload',
        'description': 'Focal plane detector temperature.',
        'data_type': 'INT16',
        'units': 'degC (x0.01)',
    },
    {
        'name': 'Data Buffer Fill',
        'mnemonic': 'BUF_FILL',
        'apid': '0x0810',
        'subsystem': 'Payload',
        'description': 'Onboard data storage buffer fill percentage.',
        'data_type': 'UINT8',
        'units': '%',
    },
    {
        'name': 'Payload Power Draw',
        'mnemonic': 'PL_PWR',
        'apid': '0x0810',
        'subsystem': 'Payload',
        'description': 'Total payload subsystem power consumption.',
        'data_type': 'UINT16',
        'units': 'mW',
    },
    {
        'name': 'Payload Status',
        'mnemonic': 'PL_STATUS',
        'apid': '0x0810',
        'subsystem': 'Payload',
        'description': 'Payload instrument operational state.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'Off', 'description': 'Instrument powered off'},
            {'value': '1', 'label': 'Standby', 'description': 'Powered but idle'},
            {'value': '2', 'label': 'Warming Up', 'description': 'Thermal stabilization in progress'},
            {'value': '3', 'label': 'Ready', 'description': 'Ready for imaging commands'},
            {'value': '4', 'label': 'Capturing', 'description': 'Image capture in progress'},
            {'value': '5', 'label': 'Processing', 'description': 'Onboard processing active'},
            {'value': '6', 'label': 'Error', 'description': 'Fault condition, check diagnostics'},
        ],
    },
    {
        'name': 'Spacecraft Mode',
        'mnemonic': 'SC_MODE',
        'apid': '0x0801',
        'subsystem': 'CDH',
        'description': 'Top-level spacecraft operational mode.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'Safehold', 'description': 'Minimal operations, sun-safe'},
            {'value': '1', 'label': 'Startup', 'description': 'Post-reset initialization'},
            {'value': '2', 'label': 'Nominal', 'description': 'Normal operations'},
            {'value': '3', 'label': 'Science', 'description': 'Active science collection'},
            {'value': '4', 'label': 'Maintenance', 'description': 'Ground-commanded maintenance window'},
        ],
    },
    {
        'name': 'Onboard Time',
        'mnemonic': 'OBT',
        'apid': '0x0801',
        'subsystem': 'CDH',
        'description': 'Onboard clock time in seconds since J2000 epoch.',
        'data_type': 'UINT32',
        'units': 'seconds',
    },
    {
        'name': 'Reboot Count',
        'mnemonic': 'REBOOT_CNT',
        'apid': '0x0801',
        'subsystem': 'CDH',
        'description': 'Total number of processor reboots since launch.',
        'data_type': 'UINT16',
        'units': 'count',
    },
    {
        'name': 'Propellant Tank Pressure',
        'mnemonic': 'PROP_PRES',
        'apid': '0x0805',
        'subsystem': 'Propulsion',
        'description': 'Propellant tank pressure reading.',
        'data_type': 'UINT16',
        'units': 'kPa',
    },
    {
        'name': 'Thruster Valve Status',
        'mnemonic': 'THR_VALVE',
        'apid': '0x0805',
        'subsystem': 'Propulsion',
        'description': 'Thruster valve open/close status for all thrusters.',
        'data_type': 'ENUM8',
        'units': '',
        'enums': [
            {'value': '0', 'label': 'All Closed'},
            {'value': '1', 'label': 'Thruster 1 Open'},
            {'value': '2', 'label': 'Thruster 2 Open'},
            {'value': '3', 'label': 'Both Open'},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed sample command and telemetry definitions for the C&T Reference Module.'

    def handle(self, *args, **options):
        cmd_count = 0
        inp_count = 0
        for data in SAMPLE_COMMANDS:
            inputs = data.pop('inputs', [])
            notes = data.pop('notes', '')
            cmd, created = CommandDefinition.objects.update_or_create(
                name=data['name'],
                defaults={
                    'command_id': data.get('command_id', ''),
                    'subsystem': data.get('subsystem', ''),
                    'category': data.get('category', ''),
                    'description': data.get('description', ''),
                    'notes': notes,
                },
            )
            if created:
                cmd_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created command: {cmd.name}'))

            for inp_data in inputs:
                _, inp_created = CommandInput.objects.update_or_create(
                    command=cmd,
                    name=inp_data['name'],
                    defaults={
                        'order': inp_data.get('order', 0),
                        'data_type': inp_data.get('data_type', ''),
                        'description': inp_data.get('description', ''),
                        'default_value': inp_data.get('default_value', ''),
                        'constraints': inp_data.get('constraints', ''),
                    },
                )
                if inp_created:
                    inp_count += 1

        tlm_count = 0
        enum_count = 0
        for data in SAMPLE_TELEMETRY:
            enums = data.pop('enums', [])
            tlm, created = TelemetryDefinition.objects.update_or_create(
                name=data['name'],
                defaults={
                    'mnemonic': data.get('mnemonic', ''),
                    'apid': data.get('apid', ''),
                    'subsystem': data.get('subsystem', ''),
                    'description': data.get('description', ''),
                    'data_type': data.get('data_type', ''),
                    'units': data.get('units', ''),
                    'notes': data.get('notes', ''),
                },
            )
            if created:
                tlm_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created telemetry: {tlm.name}'))

            for enum_data in enums:
                _, enum_created = TelemetryEnum.objects.update_or_create(
                    telemetry=tlm,
                    value=enum_data['value'],
                    defaults={
                        'label': enum_data['label'],
                        'description': enum_data.get('description', ''),
                    },
                )
                if enum_created:
                    enum_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'C&T seed complete: {cmd_count} commands, {inp_count} inputs, '
            f'{tlm_count} telemetry points, {enum_count} enums.'
        ))
