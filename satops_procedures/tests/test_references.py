import csv
import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from references.models import ReferenceEntry, Subsystem


class SubsystemModelTest(TestCase):
    def test_str(self):
        sub = Subsystem.objects.create(name="ADCS")
        self.assertEqual(str(sub), "ADCS")

    def test_ordering(self):
        Subsystem.objects.create(name="Power")
        Subsystem.objects.create(name="ADCS")
        names = list(Subsystem.objects.values_list('name', flat=True))
        self.assertEqual(names, ['ADCS', 'Power'])


class ReferenceEntryModelTest(TestCase):
    def setUp(self):
        self.sub = Subsystem.objects.create(name="ADCS")

    def test_str(self):
        entry = ReferenceEntry.objects.create(
            title="ADCS ICD",
            subsystem=self.sub,
            location="https://example.com/adcs-icd",
        )
        self.assertIn("ADCS ICD", str(entry))
        self.assertIn("ADCS", str(entry))

    def test_default_type(self):
        entry = ReferenceEntry.objects.create(
            title="ADCS Ref",
            subsystem=self.sub,
            location="https://example.com",
        )
        self.assertEqual(entry.document_type, ReferenceEntry.TYPE_REFERENCE)

    def test_timestamps(self):
        entry = ReferenceEntry.objects.create(
            title="ADCS ICD",
            subsystem=self.sub,
            location="https://example.com",
        )
        self.assertIsNotNone(entry.created_at)
        self.assertIsNotNone(entry.updated_at)


class ReferenceListViewTest(TestCase):
    def test_list_loads(self):
        response = self.client.get(reverse("reference_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Central Reference Page")

    def test_list_with_search(self):
        response = self.client.get(reverse("reference_list"), {"q": "ADCS"})
        self.assertEqual(response.status_code, 200)

    def test_list_with_filters(self):
        sub = Subsystem.objects.create(name="Power")
        response = self.client.get(reverse("reference_list"), {
            "subsystem": sub.id,
            "document_type": "ICD",
        })
        self.assertEqual(response.status_code, 200)

    def test_list_clear_filters(self):
        response = self.client.get(reverse("reference_list"), {"clear": "1"})
        self.assertEqual(response.status_code, 302)

    def test_list_shows_entries(self):
        sub = Subsystem.objects.create(name="ADCS")
        ReferenceEntry.objects.create(
            title="ADCS ICD", subsystem=sub,
            location="https://example.com", document_type="ICD",
        )
        response = self.client.get(reverse("reference_list"))
        self.assertContains(response, "ADCS ICD")


class ReferenceDetailViewTest(TestCase):
    def test_detail_loads(self):
        sub = Subsystem.objects.create(name="ADCS")
        entry = ReferenceEntry.objects.create(
            title="ADCS ICD", subsystem=sub,
            location="https://example.com",
        )
        response = self.client.get(reverse("reference_detail", args=[entry.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ADCS ICD")

    def test_detail_404(self):
        response = self.client.get(reverse("reference_detail", args=[999]))
        self.assertEqual(response.status_code, 404)


class ReferenceCreateViewTest(TestCase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("reference_create"))
        self.assertEqual(response.status_code, 302)

    def test_create_get(self):
        User.objects.create_user("op", password="pass")
        self.client.login(username="op", password="pass")
        response = self.client.get(reverse("reference_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Reference")

    def test_create_post(self):
        User.objects.create_user("op", password="pass")
        self.client.login(username="op", password="pass")
        sub = Subsystem.objects.create(name="Power")
        response = self.client.post(reverse("reference_create"), {
            "title": "Power Manual",
            "document_type": "Manual",
            "subsystem": sub.id,
            "section": "Battery Ops",
            "version": "v1.0",
            "location": "https://example.com/power-manual",
            "user_notes": "Eclipse season reference",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ReferenceEntry.objects.filter(title="Power Manual").exists())

    def test_create_validation(self):
        User.objects.create_user("op", password="pass")
        self.client.login(username="op", password="pass")
        response = self.client.post(reverse("reference_create"), {
            "title": "",
            "subsystem": "",
            "location": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ReferenceEntry.objects.exists())


class ReferenceEditViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("op", password="pass")
        self.sub = Subsystem.objects.create(name="ADCS")
        self.entry = ReferenceEntry.objects.create(
            title="ADCS ICD", subsystem=self.sub,
            location="https://example.com",
        )

    def test_edit_requires_login(self):
        response = self.client.get(reverse("reference_edit", args=[self.entry.id]))
        self.assertEqual(response.status_code, 302)

    def test_edit_get(self):
        self.client.login(username="op", password="pass")
        response = self.client.get(reverse("reference_edit", args=[self.entry.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Reference")

    def test_edit_post(self):
        self.client.login(username="op", password="pass")
        response = self.client.post(reverse("reference_edit", args=[self.entry.id]), {
            "title": "ADCS ICD Updated",
            "document_type": "ICD",
            "subsystem": self.sub.id,
            "location": "https://example.com/v2",
        })
        self.assertEqual(response.status_code, 302)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.title, "ADCS ICD Updated")


class ReferenceDeleteViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("op", password="pass")
        self.sub = Subsystem.objects.create(name="ADCS")
        self.entry = ReferenceEntry.objects.create(
            title="ADCS ICD", subsystem=self.sub,
            location="https://example.com",
        )

    def test_delete_requires_login(self):
        response = self.client.post(reverse("reference_delete", args=[self.entry.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ReferenceEntry.objects.filter(pk=self.entry.pk).exists())

    def test_delete_get_confirmation(self):
        self.client.login(username="op", password="pass")
        response = self.client.get(reverse("reference_delete", args=[self.entry.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure?")

    def test_delete_post(self):
        self.client.login(username="op", password="pass")
        response = self.client.post(reverse("reference_delete", args=[self.entry.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ReferenceEntry.objects.filter(pk=self.entry.pk).exists())


class CSVExportViewTest(TestCase):
    def test_export_csv(self):
        sub = Subsystem.objects.create(name="ADCS")
        ReferenceEntry.objects.create(
            title="ADCS ICD", document_type="ICD", subsystem=sub,
            section="Commands", version="v2.1",
            location="https://example.com", user_notes="Test note",
        )
        response = self.client.get(reverse("reference_csv_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(rows[0], ['Title', 'Document Type', 'Subsystem', 'Section', 'Version', 'Location', 'User Notes'])
        self.assertEqual(rows[1][0], 'ADCS ICD')
        self.assertEqual(rows[1][1], 'ICD')

    def test_export_csv_with_filters(self):
        sub = Subsystem.objects.create(name="ADCS")
        ReferenceEntry.objects.create(
            title="ADCS ICD", subsystem=sub, location="https://example.com",
        )
        ReferenceEntry.objects.create(
            title="ADCS Guide", subsystem=sub, location="https://example.com",
            document_type="Guide",
        )
        response = self.client.get(reverse("reference_csv_export"), {"document_type": "Guide"})
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1 entry


class CSVImportViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("op", password="pass")

    def test_import_requires_login(self):
        response = self.client.post(reverse("reference_csv_import"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_import_csv(self):
        self.client.login(username="op", password="pass")
        Subsystem.objects.create(name="ADCS")

        csv_content = (
            "Title,Document Type,Subsystem,Section,Version,Location,User Notes\n"
            "ADCS ICD,ICD,ADCS,Command Interface,v2.1,https://example.com,Test note\n"
            "New Manual,Manual,NewSub,,v1.0,https://example.com/manual,\n"
        )
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'refs.csv'

        response = self.client.post(
            reverse("reference_csv_import"),
            {'csv_file': csv_file},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReferenceEntry.objects.count(), 2)
        self.assertTrue(Subsystem.objects.filter(name="NewSub").exists())

    def test_import_missing_file(self):
        self.client.login(username="op", password="pass")
        response = self.client.post(reverse("reference_csv_import"))
        self.assertEqual(response.status_code, 302)

    def test_import_invalid_columns(self):
        self.client.login(username="op", password="pass")
        csv_content = "Wrong,Columns\nfoo,bar\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'bad.csv'
        response = self.client.post(
            reverse("reference_csv_import"),
            {'csv_file': csv_file},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReferenceEntry.objects.count(), 0)

    def test_import_skips_incomplete_rows(self):
        self.client.login(username="op", password="pass")
        csv_content = (
            "Title,Document Type,Subsystem,Section,Version,Location,User Notes\n"
            ",ICD,ADCS,,v1.0,,\n"
        )
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'incomplete.csv'
        response = self.client.post(
            reverse("reference_csv_import"),
            {'csv_file': csv_file},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReferenceEntry.objects.count(), 0)


class SeedReferencesCommandTest(TestCase):
    def test_seed_references(self):
        from django.core.management import call_command
        call_command("seed_references")
        self.assertTrue(Subsystem.objects.exists())
        self.assertTrue(ReferenceEntry.objects.exists())

    def test_seed_idempotent(self):
        from django.core.management import call_command
        call_command("seed_references")
        count1 = ReferenceEntry.objects.count()
        call_command("seed_references")
        count2 = ReferenceEntry.objects.count()
        self.assertEqual(count1, count2)
