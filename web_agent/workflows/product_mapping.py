"""
Workflow dla mapowania produktów - dodawanie produktów z matterhorn1 do MPD
"""
from typing import Optional
from ..core import Workflow, Action, ActionType


class ProductMappingWorkflow:
    """
    Tworzy workflow do mapowania produktów - przechodzenie przez listę
    i dodawanie produktów po kolei.
    """

    @staticmethod
    def create_product_loop_workflow(
        max_products: int = 10,
        changelist_url: Optional[str] = None
    ) -> Workflow:
        """
        Tworzy workflow do przetwarzania produktów w pętli

        Args:
            max_products: Maksymalna liczba produktów do przetworzenia
            changelist_url: URL do listy produktów (jeśli None, użyje aktualnego URL)

        Returns:
            Workflow do przetwarzania produktów
        """
        workflow = Workflow(name='Product Mapping Loop')

        # 1. Zapisz URL listy produktów
        workflow.add_step(
            name='Zapisz URL listy produktów',
            action=Action(
                ActionType.EVALUATE,
                expression=f'''(() => {{
                    const currentUrl = window.location.href;
                    sessionStorage.setItem('changelist_url', currentUrl);
                    if (!sessionStorage.getItem('products_processed')) {{
                        sessionStorage.setItem('products_processed', '0');
                    }}
                    return {{
                        changelist_url_saved: true,
                        url: currentUrl,
                        max_products: {max_products},
                        products_processed: parseInt(sessionStorage.getItem('products_processed') || '0')
                    }};
                }})()'''
            )
        )

        # 2. Kliknij pierwszy niezmapowany produkt
        workflow.add_step(
            name='Kliknij pierwszy niezmapowany produkt',
            action=Action(
                ActionType.CLICK,
                selector='table.changelist tbody tr:first-child td a, table#result_list tbody tr:first-child td a, table tbody tr:first-child td a',
                timeout=10000
            )
        )

        # 3. Oczekiwanie na stronę produktu
        workflow.add_step(
            name='Oczekiwanie na stronę produktu',
            action=Action(
                ActionType.WAIT_FOR,
                selector='.form-row, fieldset, input[name="name"]',
                timeout=15000
            )
        )

        # 4. Sprawdź czy produkt jest zmapowany
        workflow.add_step(
            name='Sprawdź status mapowania produktu',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const isMappedInput = document.querySelector('input[name="is_mapped"]');
                    const isMappedValue = isMappedInput?.value === 'True' || isMappedInput?.checked === true;
                    const mappedProductUidInput = document.querySelector('input[name="mapped_product_uid"]');
                    const hasMappedUid = mappedProductUidInput?.value && 
                                        mappedProductUidInput.value.trim() !== '' && 
                                        mappedProductUidInput.value.trim() !== '-';
                    const productMapped = isMappedValue || hasMappedUid;
                    
                    if (productMapped) {
                        const productsProcessed = parseInt(sessionStorage.getItem('products_processed') || '0') + 1;
                        sessionStorage.setItem('products_processed', productsProcessed.toString());
                        window.__productMapped = true;
                        return {
                            product_mapped: true,
                            products_processed: productsProcessed,
                            note: 'Produkt jest już zmapowany - przejdź do następnego'
                        };
                    }
                    
                    window.__productMapped = false;
                    return {
                        product_mapped: false,
                        note: 'Produkt nie jest zmapowany - można dodać'
                    };
                })()'''
            )
        )

        # 5. Jeśli produkt nie jest zmapowany, kliknij "Przypisz"
        # (To będzie rozszerzone w przyszłości o pełne wypełnienie formularza)

        # 6. Wróć do listy produktów jeśli produkt był zmapowany
        workflow.add_step(
            name='Wróć do listy jeśli produkt był zmapowany',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const productMapped = window.__productMapped;
                    if (productMapped) {
                        const changelistUrl = sessionStorage.getItem('changelist_url');
                        if (changelistUrl) {
                            return {
                                navigate_to_url: changelistUrl,
                                navigating_back: true
                            };
                        }
                    }
                    return { navigating_back: false };
                })()'''
            )
        )

        return workflow
