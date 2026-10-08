from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('panel/', views.panel_admin, name='panel_admin'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('comprar/<int:producto_id>/', views.comprar_producto, name='comprar_producto'),
]