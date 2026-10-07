from django.db import models
from django.core.validators import MinValueValidator


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    stock = models.PositiveIntegerField(default=0)
    tipo_flor = models.CharField(max_length=50, blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    def borrar_imagen(self):
        """Borra el archivo de la imagen del disco (si existe)."""
        if self.imagen:
            self.imagen.delete(save=False)

    def delete(self, *args, **kwargs):
        # Al eliminar el producto también se elimina su foto del disco
        self.borrar_imagen()
        super().delete(*args, **kwargs)
