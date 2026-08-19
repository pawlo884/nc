import React from 'react';
import { createRoot } from 'react-dom/client';
import ProductMapping from './components/ProductMapping';
import BulkMapping from './components/BulkMapping';
import BulkCreate from './components/BulkCreate';

// Inicjalizacja komponentów React
document.addEventListener('DOMContentLoaded', function() {
  // ProductMapping - dla pojedynczego produktu
  const productMappingContainer = document.getElementById('product-mapping-container');
  if (productMappingContainer) {
    const productId = parseInt(productMappingContainer.dataset.productId);
    const isMapped = productMappingContainer.dataset.isMapped === 'true';
    const mappedProductId = productMappingContainer.dataset.mappedProductId;
    
    const root = createRoot(productMappingContainer);
    root.render(
      <ProductMapping 
        productId={productId}
        isMapped={isMapped}
        mappedProductId={mappedProductId}
      />
    );
  }

  // BulkMapping - dla masowego mapowania
  const bulkMappingContainer = document.getElementById('bulk-mapping-container');
  if (bulkMappingContainer) {
    const mappings = JSON.parse(bulkMappingContainer.dataset.mappings || '[]');
    
    const root = createRoot(bulkMappingContainer);
    root.render(
      <BulkMapping 
        mappings={mappings}
        onComplete={() => window.location.href = '/admin/matterhorn1/product/'}
      />
    );
  }

  // BulkCreate - dla masowego tworzenia
  const bulkCreateContainer = document.getElementById('bulk-create-container');
  if (bulkCreateContainer) {
    const productsData = JSON.parse(bulkCreateContainer.dataset.productsData || '[]');
    
    const root = createRoot(bulkCreateContainer);
    root.render(
      <BulkCreate 
        productsData={productsData}
        onComplete={() => window.location.href = '/admin/matterhorn1/product/'}
      />
    );
  }
});
