# blog/tests.py - testy automatyczne (python manage.py test)
import csv
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Product

MEDIA_TMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class ProductTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TMP, ignore_errors=True)

    def image(self, name='test.png'):
        buf = BytesIO()
        Image.new('RGB', (10, 10), 'red').save(buf, 'PNG')
        return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')

    def make(self, name='Pierwszy post'):
        return Product.objects.create(name=name, description='treść', image=self.image())

    def test_list_and_detail(self):
        p = self.make()
        self.assertContains(self.client.get(reverse('product_list')), p.name)
        r = self.client.get(reverse('product_detail', args=[p.slug]))
        self.assertContains(r, p.name)

    def test_detail_missing_returns_404(self):
        r = self.client.get(reverse('product_detail', args=['nie-ma-takiego']))
        self.assertEqual(r.status_code, 404)

    def test_create(self):
        r = self.client.post(reverse('create_product'),
                             {'name': 'Nowy', 'author': 'Jan', 'description': 'x', 'image': self.image()})
        self.assertRedirects(r, reverse('product_list'))
        self.assertTrue(Product.objects.filter(name='Nowy', author='Jan').exists())

    def test_edit_changes_image(self):
        p = self.make()
        old = p.image.name
        r = self.client.post(reverse('edit_product', args=[p.pk]),
                             {'name': 'Zmieniony', 'description': 'y', 'image': self.image('nowy.png')})
        self.assertRedirects(r, reverse('product_list'))
        p.refresh_from_db()
        self.assertEqual(p.name, 'Zmieniony')
        self.assertNotEqual(p.image.name, old)

    def test_delete(self):
        p = self.make()
        self.client.post(reverse('delete_product', args=[p.pk]))
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())

    def test_short_description(self):
        p = Product(description=' '.join(['słowo'] * 35))
        self.assertTrue(p.short_description().endswith('...'))
        self.assertEqual(len(p.short_description().split()), 30)

    def test_slug_unique_and_ordering(self):
        a = self.make('Zażółć gęślą jaźń')
        b = self.make('Zażółć gęślą jaźń')
        self.assertEqual(a.slug, 'zazolc-gesla-jazn')
        self.assertEqual(b.slug, 'zazolc-gesla-jazn-2')
        self.assertEqual(list(Product.objects.all())[0], b)  # najnowszy pierwszy


class ContactTests(TestCase):
    def test_contact_saves_and_redirects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = f'{tmp}/responses.csv'
            with self.settings(CONTACT_CSV=path):
                r = self.client.post(reverse('contact'), {
                    'name': 'Anna', 'email': 'anna@example.com', 'phone': '',
                    'subject': 'Pytanie', 'message': 'Treść wiadomości',
                })
            self.assertRedirects(r, reverse('contact_success'))
            with open(path, encoding='utf-8') as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0][0], 'Anna')
            self.assertEqual(rows[0][3], 'Pytanie')

    def test_contact_invalid_email(self):
        r = self.client.post(reverse('contact'), {
            'name': 'Anna', 'email': 'zly-adres', 'subject': 'x', 'message': 'y'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors.get('email'))
