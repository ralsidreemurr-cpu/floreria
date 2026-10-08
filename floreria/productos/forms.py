import re
from django import forms
from .models import Producto

# 3 o más letras iguales seguidas (ej: "rrrosa", "Roooosas")
REPETIDAS = re.compile(r'([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])\1{2,}', re.IGNORECASE)
# Caracteres NO permitidos en un nombre
NO_PERMITIDOS_NOMBRE = re.compile(r"[^\w\s\-.,'&()/]|_")
SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s\-]+$")

TAMANO_MAX_IMAGEN = 2 * 1024 * 1024  # 2 MB


def limpiar_espacios(texto):
    """Quita espacios al inicio/final y deja un solo espacio entre palabras."""
    return re.sub(r'\s+', ' ', texto or '').strip()


def validar_repetidas(texto, campo):
    m = REPETIDAS.search(texto)
    if m:
        raise forms.ValidationError(
            f'{campo}: hay una letra repetida demasiadas veces seguidas ("{m.group(0)}"). '
            'Revisa que no se haya quedado una tecla apretada.'
        )


class ProductoForm(forms.ModelForm):
    eliminar_imagen = forms.BooleanField(required=False, label='Quitar imagen actual')
    stock = forms.IntegerField(
        label='Stock',
        min_value=0,
        max_value=10000,
        widget=forms.NumberInput(attrs={'min': '0', 'max': '10000'}),
        error_messages={
            'required': 'El stock es obligatorio.',
            'invalid': 'El stock debe ser un número entero.',
            'min_value': 'El stock no puede ser negativo.',
            'max_value': 'El stock no puede superar las 10.000 unidades.',
        },
    )

    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'tipo_flor', 'precio', 'stock', 'imagen', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'maxlength': 100, 'data-sin-repetir': '1'}),
            'descripcion': forms.Textarea(attrs={'maxlength': 500, 'data-sin-repetir': '1'}),
            'tipo_flor': forms.TextInput(attrs={'maxlength': 50, 'data-sin-repetir': '1'}),
            'precio': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'imagen': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
        }
        labels = {
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'tipo_flor': 'Tipo de flor',
            'precio': 'Precio',
            'stock': 'Stock',
            'imagen': 'Imagen',
            'disponible': 'Disponible',
        }
        error_messages = {
            'nombre': {'required': 'El nombre es obligatorio.'},
            'precio': {
                'required': 'El precio es obligatorio.',
                'invalid': 'El precio debe ser un número válido.',
            },
            'stock': {
                'required': 'El stock es obligatorio.',
                'invalid': 'El stock debe ser un número entero.',
            },
        }

    def clean_nombre(self):
        nombre = limpiar_espacios(self.cleaned_data.get('nombre'))
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
        if NO_PERMITIDOS_NOMBRE.search(nombre):
            raise forms.ValidationError('El nombre contiene caracteres no permitidos.')
        if not re.search(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]', nombre):
            raise forms.ValidationError('El nombre debe incluir letras, no solo números.')
        validar_repetidas(nombre, 'Nombre')

        # No permitir nombres duplicados (sin importar mayúsculas)
        repetido = Producto.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError('Ya existe un producto con ese nombre.')
        return nombre

    def clean_descripcion(self):
        descripcion = limpiar_espacios(self.cleaned_data.get('descripcion'))
        if descripcion:
            validar_repetidas(descripcion, 'Descripción')
        return descripcion

    def clean_tipo_flor(self):
        tipo = limpiar_espacios(self.cleaned_data.get('tipo_flor'))
        if tipo:
            if not SOLO_LETRAS.match(tipo):
                raise forms.ValidationError('El tipo de flor solo puede contener letras.')
            validar_repetidas(tipo, 'Tipo de flor')
        return tipo

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None:
            if precio <= 0:
                raise forms.ValidationError('El precio debe ser mayor que cero.')
            if precio > 9999999:
                raise forms.ValidationError('El precio no puede superar $9.999.999.')
        return precio

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None:
            if stock < 0:
                raise forms.ValidationError('El stock no puede ser negativo.')
            if stock > 10000:
                raise forms.ValidationError('El stock no puede superar las 10.000 unidades.')
        return stock

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        # Si no se subió una nueva, imagen puede ser la ya guardada (sin atributo size de upload)
        if imagen and hasattr(imagen, 'content_type'):
            if imagen.size > TAMANO_MAX_IMAGEN:
                raise forms.ValidationError('La imagen no puede pesar más de 2 MB.')
            if imagen.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
                raise forms.ValidationError('Solo se permiten imágenes JPG, PNG o WEBP.')
        return imagen

    def save(self, commit=True):
        producto = self.instance
        imagen_anterior = None
        if producto.pk:
            imagen_anterior = Producto.objects.get(pk=producto.pk).imagen

        nueva = 'imagen' in self.changed_data and self.cleaned_data.get('imagen')
        quitar = self.cleaned_data.get('eliminar_imagen') and not nueva

        producto = super().save(commit=False)
        if quitar:
            producto.imagen = None

        if commit:
            producto.save()
            # Borrar del disco la imagen vieja si fue reemplazada o quitada
            if imagen_anterior and (nueva or quitar):
                imagen_anterior.delete(save=False)
        return producto


class CompraForm(forms.Form):
    """Valida la cantidad de una compra contra el stock disponible."""
    cantidad = forms.IntegerField(
        min_value=1,
        error_messages={
            'required': 'Indica la cantidad a comprar.',
            'invalid': 'La cantidad debe ser un número entero.',
            'min_value': 'La cantidad debe ser al menos 1.',
        },
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        if self.producto is not None and cantidad > self.producto.stock:
            raise forms.ValidationError(
                f'Solo quedan {self.producto.stock} unidades de "{self.producto.nombre}".'
            )
        return cantidad

