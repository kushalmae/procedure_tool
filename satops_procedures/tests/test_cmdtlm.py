
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from cmdtlm.models import (
    CommandDefinition,
    CommandInput,
    TelemetryDefinition,
    TelemetryEnum,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class CommandDefinitionModelTest(TestCase):
    def test_str_with_id(self):
        cmd = CommandDefinition.objects.create(
            name='Set Power', command_id='0x0101', subsystem='Power',
        )
        self.assertIn('Set Power', str(cmd))
        self.assertIn('0x0101', str(cmd))

    def test_str_without_id(self):
        cmd = CommandDefinition.objects.create(name='Reboot')
        self.assertEqual(str(cmd), 'Reboot')

    def test_input_count(self):
        cmd = CommandDefinition.objects.create(name='CMD1')
        self.assertEqual(cmd.input_count, 0)
        CommandInput.objects.create(command=cmd, name='arg1', order=1)
        CommandInput.objects.create(command=cmd, name='arg2', order=2)
        self.assertEqual(cmd.input_count, 2)


class CommandInputModelTest(TestCase):
    def test_str(self):
        cmd = CommandDefinition.objects.create(name='CMD1')
        inp = CommandInput.objects.create(command=cmd, name='arg1', order=1)
        self.assertIn('CMD1', str(inp))
        self.assertIn('arg1', str(inp))


class TelemetryDefinitionModelTest(TestCase):
    def test_str_with_mnemonic(self):
        tlm = TelemetryDefinition.objects.create(
            name='Bus Voltage', mnemonic='V_BUS',
        )
        self.assertIn('Bus Voltage', str(tlm))
        self.assertIn('V_BUS', str(tlm))

    def test_str_without_mnemonic(self):
        tlm = TelemetryDefinition.objects.create(name='Bus Voltage')
        self.assertEqual(str(tlm), 'Bus Voltage')

    def test_has_enums(self):
        tlm = TelemetryDefinition.objects.create(name='Mode', mnemonic='MODE')
        self.assertFalse(tlm.has_enums)
        TelemetryEnum.objects.create(telemetry=tlm, value='0', label='Off')
        self.assertTrue(tlm.has_enums)


class TelemetryEnumModelTest(TestCase):
    def test_str(self):
        tlm = TelemetryDefinition.objects.create(name='Mode', mnemonic='MODE')
        enum = TelemetryEnum.objects.create(telemetry=tlm, value='0', label='Off')
        self.assertIn('MODE', str(enum))
        self.assertIn('Off', str(enum))


# ---------------------------------------------------------------------------
# View tests — Commands
# ---------------------------------------------------------------------------

class CommandListViewTest(TestCase):
    def test_loads_empty(self):
        resp = self.client.get(reverse('cmdtlm_command_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Commands')

    def test_lists_commands(self):
        CommandDefinition.objects.create(
            name='Test Cmd', command_id='0xFF', subsystem='Test',
        )
        resp = self.client.get(reverse('cmdtlm_command_list'))
        self.assertContains(resp, 'Test Cmd')
        self.assertContains(resp, '0xFF')

    def test_search(self):
        CommandDefinition.objects.create(name='Alpha', subsystem='Power')
        CommandDefinition.objects.create(name='Beta', subsystem='ADCS')
        resp = self.client.get(reverse('cmdtlm_command_list'), {'q': 'Alpha'})
        self.assertContains(resp, 'Alpha')
        self.assertNotContains(resp, 'Beta')

    def test_filter_subsystem(self):
        CommandDefinition.objects.create(name='A', subsystem='Power')
        CommandDefinition.objects.create(name='B', subsystem='ADCS')
        resp = self.client.get(reverse('cmdtlm_command_list'), {'subsystem': 'Power'})
        self.assertContains(resp, '>A<')
        self.assertNotContains(resp, '>B<')

    def test_clear_filters(self):
        resp = self.client.get(reverse('cmdtlm_command_list'), {'clear': '1'})
        self.assertEqual(resp.status_code, 302)


class CommandDetailViewTest(TestCase):
    def test_detail_loads(self):
        cmd = CommandDefinition.objects.create(
            name='Set Power', command_id='0x01', subsystem='Power',
            description='Sets power level.',
        )
        CommandInput.objects.create(
            command=cmd, name='level', order=1, data_type='UINT8',
        )
        resp = self.client.get(reverse('cmdtlm_command_detail', args=[cmd.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Set Power')
        self.assertContains(resp, 'level')
        self.assertContains(resp, 'UINT8')

    def test_detail_no_inputs(self):
        cmd = CommandDefinition.objects.create(name='NoArgs')
        resp = self.client.get(reverse('cmdtlm_command_detail', args=[cmd.pk]))
        self.assertContains(resp, 'no defined inputs')

    def test_detail_404(self):
        resp = self.client.get(reverse('cmdtlm_command_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# View tests — Telemetry
# ---------------------------------------------------------------------------

class TelemetryListViewTest(TestCase):
    def test_loads_empty(self):
        resp = self.client.get(reverse('cmdtlm_telemetry_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Telemetry')

    def test_lists_telemetry(self):
        TelemetryDefinition.objects.create(
            name='Bus Voltage', mnemonic='V_BUS', subsystem='Power',
        )
        resp = self.client.get(reverse('cmdtlm_telemetry_list'))
        self.assertContains(resp, 'Bus Voltage')
        self.assertContains(resp, 'V_BUS')

    def test_search(self):
        TelemetryDefinition.objects.create(name='Temp', mnemonic='TEMP')
        TelemetryDefinition.objects.create(name='Voltage', mnemonic='VOLT')
        resp = self.client.get(reverse('cmdtlm_telemetry_list'), {'q': 'Temp'})
        self.assertContains(resp, 'Temp')
        self.assertNotContains(resp, 'Voltage')

    def test_clear_filters(self):
        resp = self.client.get(reverse('cmdtlm_telemetry_list'), {'clear': '1'})
        self.assertEqual(resp.status_code, 302)


class TelemetryDetailViewTest(TestCase):
    def test_detail_with_enums(self):
        tlm = TelemetryDefinition.objects.create(
            name='Mode', mnemonic='SC_MODE', subsystem='CDH',
            data_type='ENUM8',
        )
        TelemetryEnum.objects.create(telemetry=tlm, value='0', label='Off')
        TelemetryEnum.objects.create(telemetry=tlm, value='1', label='On')
        resp = self.client.get(reverse('cmdtlm_telemetry_detail', args=[tlm.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SC_MODE')
        self.assertContains(resp, 'Off')
        self.assertContains(resp, 'On')

    def test_detail_no_enums(self):
        tlm = TelemetryDefinition.objects.create(name='Voltage', data_type='UINT16')
        resp = self.client.get(reverse('cmdtlm_telemetry_detail', args=[tlm.pk]))
        self.assertContains(resp, 'No enum definitions')

    def test_detail_404(self):
        resp = self.client.get(reverse('cmdtlm_telemetry_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CSV Import tests
# ---------------------------------------------------------------------------

class CSVImportViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ops', password='ops')
        self.client.login(username='ops', password='ops')

    def test_import_page_loads(self):
        resp = self.client.get(reverse('cmdtlm_csv_import'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Import CSV')

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('cmdtlm_csv_import'))
        self.assertEqual(resp.status_code, 302)

    def _csv_file(self, content):
        return SimpleUploadedFile('test.csv', content.encode('utf-8'), content_type='text/csv')

    def test_import_commands(self):
        csv_data = "name,command_id,subsystem,description,category\nTestCmd,0xAA,Power,A test command,Control\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'commands',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CommandDefinition.objects.filter(name='TestCmd').exists())
        cmd = CommandDefinition.objects.get(name='TestCmd')
        self.assertEqual(cmd.command_id, '0xAA')
        self.assertEqual(cmd.subsystem, 'Power')

    def test_import_command_inputs(self):
        CommandDefinition.objects.create(name='TestCmd')
        csv_data = "command_name,input_name,order,data_type,description\nTestCmd,arg1,1,UINT8,First arg\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'command_inputs',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CommandInput.objects.filter(name='arg1').exists())

    def test_import_command_inputs_missing_parent(self):
        csv_data = "command_name,input_name,order,data_type\nNonExistent,arg1,1,UINT8\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'command_inputs',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CommandInput.objects.count(), 0)

    def test_import_telemetry(self):
        csv_data = "name,mnemonic,apid,subsystem,description,data_type,units\nBusVolt,V_BUS,0x0802,Power,Bus voltage,UINT16,mV\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'telemetry',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(TelemetryDefinition.objects.filter(mnemonic='V_BUS').exists())

    def test_import_telemetry_enums(self):
        TelemetryDefinition.objects.create(name='Mode', mnemonic='SC_MODE')
        csv_data = "mnemonic,value,label,description\nSC_MODE,0,Off,Powered off\nSC_MODE,1,On,Powered on\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'telemetry_enums',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(TelemetryEnum.objects.filter(telemetry__mnemonic='SC_MODE').count(), 2)

    def test_import_no_file(self):
        resp = self.client.post(reverse('cmdtlm_csv_import'), {'action': 'commands'})
        self.assertEqual(resp.status_code, 302)

    def test_import_empty_csv(self):
        csv_data = "name,command_id\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'commands',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)

    def test_import_unknown_action(self):
        csv_data = "name\nfoo\n"
        resp = self.client.post(reverse('cmdtlm_csv_import'), {
            'action': 'bogus',
            'csv_file': self._csv_file(csv_data),
        })
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Seed command test
# ---------------------------------------------------------------------------

class SeedCmdTlmCommandTest(TestCase):
    def test_seed_creates_data(self):
        from django.core.management import call_command
        call_command('seed_cmdtlm')
        self.assertTrue(CommandDefinition.objects.exists())
        self.assertTrue(CommandInput.objects.exists())
        self.assertTrue(TelemetryDefinition.objects.exists())
        self.assertTrue(TelemetryEnum.objects.exists())

    def test_seed_idempotent(self):
        from django.core.management import call_command
        call_command('seed_cmdtlm')
        count1 = CommandDefinition.objects.count()
        call_command('seed_cmdtlm')
        count2 = CommandDefinition.objects.count()
        self.assertEqual(count1, count2)
