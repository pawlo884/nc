from django.contrib.admin import SimpleListFilter


def make_scoped_filter(*, title, parameter_name, counterpart_parameter_name,
                        related_model, related_label_field='name'):
    """Fabryka pary krzyżowo filtrujących się SimpleListFilter (np. Brand <-> Category),
    gdzie wybór jednego zawęża listę opcji drugiego.

    `parameter_name`/`counterpart_parameter_name` muszą odpowiadać nazwom pól FK
    na modelu produktu, dla którego filtr jest rejestrowany (np. 'brand'/'category').
    """

    class _ScopedFilter(SimpleListFilter):
        def lookups(self, request, model_admin):
            qs = model_admin.get_queryset(request)
            counterpart_value = request.GET.get(counterpart_parameter_name)
            if counterpart_value:
                try:
                    qs = qs.filter(**{f'{counterpart_parameter_name}_id': int(counterpart_value)})
                except (ValueError, TypeError):
                    pass
            # .order_by() czyści odziedziczone sortowanie z ModelAdmin — inaczej Postgres
            # musi dołączyć kolumnę sortowania do DISTINCT, co zamiast garstki unikalnych
            # wartości zwraca wiersz na każdy produkt.
            ids = list(
                qs.exclude(**{f'{parameter_name}__isnull': True})
                  .order_by()
                  .values_list(f'{parameter_name}_id', flat=True)
                  .distinct()
            )
            if not ids:
                return []
            related_qs = related_model.objects.filter(id__in=ids).order_by(related_label_field)
            return [(str(obj.id), getattr(obj, related_label_field)) for obj in related_qs]

        def queryset(self, request, queryset):
            if self.value():
                try:
                    return queryset.filter(**{f'{parameter_name}_id': int(self.value())})
                except (ValueError, TypeError):
                    return queryset
            return queryset

    _ScopedFilter.title = title
    _ScopedFilter.parameter_name = parameter_name
    _ScopedFilter.__name__ = f'{related_model.__name__}ScopedFilter'
    return _ScopedFilter
