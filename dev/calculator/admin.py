from django.contrib import admin
from .models import Collection,Slice,Group,BackgroundCalc,Calculation

admin.site.register(Collection)
admin.site.register(Slice)
admin.site.register(Group)
admin.site.register(BackgroundCalc)
admin.site.register(Calculation)
