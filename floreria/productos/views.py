from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProductoForm, CompraForm
from .models import Producto


def inicio(request):
    productos = Producto.objects.filter(disponible=True)
    return render(request, 'productos/inicio.html', {'productos': productos})


def panel_admin(request):
    productos = Producto.objects.all().order_by('-creado')
    return render(request, 'productos/panel_admin.html', {'productos': productos})


def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')
            return redirect('panel_admin')
    else:
        form = ProductoForm(initial={'disponible': True})

    return render(request, 'productos/crear_producto.html', {'form': form})


def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado correctamente.')
            return redirect('panel_admin')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'productos/editar_producto.html', {'form': form, 'producto': producto})


def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado.')
        return redirect('panel_admin')

    return render(request, 'productos/eliminar_producto.html', {'producto': producto})

def comprar_producto(request, producto_id):
    if request.method != 'POST':
        return redirect('inicio')
    with transaction.atomic():
        producto = get_object_or_404(
            Producto.objects.select_for_update(),
            id=producto_id,
            disponible=True
        )
        form = CompraForm(request.POST, producto=producto)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            if cantidad > 90:
                messages.error(
                    request,
                    'No puedes comprar más de 90 unidades por orden.'
                )
                return redirect('inicio')
            if cantidad > producto.stock:
                messages.error(
                    request,
                    f'No hay suficiente stock. Solo quedan {producto.stock} unidades.'
                )
                return redirect('inicio')
            producto.stock -= cantidad
            producto.save(update_fields=['stock'])
            total = f'{producto.precio * cantidad:,.0f}'.replace(',', '.')
            messages.success(
                request,
                f'Compra realizada: {cantidad} x {producto.nombre} (total ${total}).'
            )
        else:
            for error in form.errors['cantidad']:
                messages.error(request, error)

    return redirect('inicio')