# blog/views.py - widoki: lista, szczegóły, CRUD, kontakt
import csv

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ContactForm, ProductForm
from .models import Product


def product_list(request):
    products = Product.objects.order_by('-created_at')
    return render(request, 'myapp/index.html', {'products': products})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'myapp/index2.html', {'product': product})


def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'myapp/create.html', {'form': form})


def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'myapp/edit.html', {'form': form, 'product': product})


def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'myapp/delete.html', {'product': product})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # ścieżka z settings - działa niezależnie od katalogu startowego serwera
            with open(settings.CONTACT_CSV, 'a', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow([
                    data['name'], data['email'], data['phone'],
                    data['subject'], data['message'],
                ])
            return redirect('contact_success')
    else:
        form = ContactForm()
    return render(request, 'myapp/contact.html', {'form': form})


def contact_success(request):
    return render(request, 'myapp/success.html')


def home(request):
    return HttpResponse('Hello, World!')
