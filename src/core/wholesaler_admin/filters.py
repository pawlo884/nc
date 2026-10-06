from django.contrib.admin import SimpleListFilter


class InputFilter(SimpleListFilter):
    """Filtr admina z polem tekstowym zamiast listy wszystkich wartości.

    Do pól o dużej kardynalności (np. `product_uid` w historii stanów - dziesiątki
    tysięcy unikalnych wartości), gdzie zwykły `list_filter` renderuje w bocznym
    pasku link na każdą wartość i strona ładuje się wieczność. Podklasa ustawia
    `parameter_name`, `title` i implementuje `queryset()`.
    """

    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # Musi zwrócić cokolwiek niepustego, żeby filtr się w ogóle pokazał;
        # realne renderowanie robi szablon input_filter.html.
        return ((),)

    def choices(self, changelist):
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


def make_input_filter(*, title, parameter_name, field_name=None, cast=None):
    """Fabryka `InputFilter` filtrującego po dokładnej wartości wpisanej w pole.

    `field_name` - pole modelu (domyślnie = `parameter_name`).
    `cast` - opcjonalna konwersja wpisanego tekstu (np. `int`); przy błędzie
    konwersji filtr zwraca pusty queryset.
    """
    _field = field_name or parameter_name

    class _InputFilter(InputFilter):
        def queryset(self, request, queryset):
            value = self.value()
            if not value:
                return queryset
            if cast is not None:
                try:
                    value = cast(value)
                except (TypeError, ValueError):
                    return queryset.none()
            return queryset.filter(**{_field: value})

    _InputFilter.title = title
    _InputFilter.parameter_name = parameter_name
    _InputFilter.__name__ = f'{parameter_name.title().replace("_", "")}InputFilter'
    return _InputFilter


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
