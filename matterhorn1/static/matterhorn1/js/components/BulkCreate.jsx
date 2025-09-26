import React, { useState, useEffect } from 'react';

const BulkCreate = ({ productsData, onComplete }) => {
  const [editedProducts, setEditedProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  useEffect(() => {
    // Inicjalizuj dane produktów
    setEditedProducts(productsData.map(product => ({
      ...product,
      name: product.name || '',
      description: product.description || '',
      brand_name: product.brand_name || '',
      variants: product.variants || []
    })));
  }, [productsData]);

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const updateProduct = (index, field, value) => {
    setEditedProducts(prev => prev.map((product, i) => 
      i === index ? { ...product, [field]: value } : product
    ));
  };

  const updateVariant = (productIndex, variantIndex, field, value) => {
    setEditedProducts(prev => prev.map((product, i) => 
      i === productIndex 
        ? {
            ...product,
            variants: product.variants.map((variant, j) => 
              j === variantIndex ? { ...variant, [field]: value } : variant
            )
          }
        : product
    ));
  };

  const addVariant = (productIndex) => {
    setEditedProducts(prev => prev.map((product, i) => 
      i === productIndex 
        ? {
            ...product,
            variants: [...product.variants, {
              size_name: '',
              stock: 0,
              ean: '',
              producer_code: ''
            }]
          }
        : product
    ));
  };

  const removeVariant = (productIndex, variantIndex) => {
    setEditedProducts(prev => prev.map((product, i) => 
      i === productIndex 
        ? {
            ...product,
            variants: product.variants.filter((_, j) => j !== variantIndex)
          }
        : product
    ));
  };

  const submitProducts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/admin/matterhorn1/product/bulk-create-mpd/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ products: editedProducts })
      });

      const data = await response.json();
      
      if (data.success) {
        showMessage(data.message, 'success');
        setTimeout(() => {
          if (onComplete) onComplete();
          else window.location.href = '/admin/matterhorn1/product/';
        }, 2000);
      } else {
        showMessage(data.error || 'Wystąpił błąd', 'error');
      }
    } catch (error) {
      console.error('Error:', error);
      showMessage('Wystąpił błąd podczas tworzenia produktów', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '20px auto', padding: '20px' }}>
      <h1>Tworzenie nowych produktów w MPD</h1>
      <p>Edytuj dane produktów przed utworzeniem w MPD:</p>
      
      {message && (
        <div className={`status-message ${messageType}`} style={{
          margin: '20px 0',
          padding: '15px',
          borderRadius: '4px',
          backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
          color: messageType === 'success' ? '#155724' : '#721c24',
          border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
        }}>
          {message}
        </div>
      )}

      <div>
        {editedProducts.map((product, productIndex) => (
          <div
            key={product.matterhorn_product_id}
            style={{
              border: '1px solid #ddd',
              borderRadius: '8px',
              marginBottom: '20px',
              padding: '20px',
              backgroundColor: '#f9f9f9'
            }}
          >
            <h3>Produkt ID: {product.matterhorn_product_id}</h3>
            
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Nazwa:
              </label>
              <input
                type="text"
                value={product.name}
                onChange={(e) => updateProduct(productIndex, 'name', e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              />
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Opis:
              </label>
              <textarea
                value={product.description}
                onChange={(e) => updateProduct(productIndex, 'description', e.target.value)}
                rows="3"
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              />
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                Marka:
              </label>
              <input
                type="text"
                value={product.brand_name}
                onChange={(e) => updateProduct(productIndex, 'brand_name', e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4>Warianty:</h4>
                <button
                  onClick={() => addVariant(productIndex)}
                  style={{
                    background: '#28a745',
                    color: 'white',
                    border: 'none',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  + Dodaj wariant
                </button>
              </div>

              {product.variants.map((variant, variantIndex) => (
                <div
                  key={variantIndex}
                  style={{
                    border: '1px solid #e0e0e0',
                    borderRadius: '4px',
                    padding: '15px',
                    marginBottom: '10px',
                    backgroundColor: 'white'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h5>Wariant {variantIndex + 1}</h5>
                    <button
                      onClick={() => removeVariant(productIndex, variantIndex)}
                      style={{
                        background: '#dc3545',
                        color: 'white',
                        border: 'none',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Usuń
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>
                        Rozmiar:
                      </label>
                      <input
                        type="text"
                        value={variant.size_name}
                        onChange={(e) => updateVariant(productIndex, variantIndex, 'size_name', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '6px',
                          border: '1px solid #ccc',
                          borderRadius: '4px'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>
                        Stan magazynowy:
                      </label>
                      <input
                        type="number"
                        value={variant.stock}
                        onChange={(e) => updateVariant(productIndex, variantIndex, 'stock', parseInt(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '6px',
                          border: '1px solid #ccc',
                          borderRadius: '4px'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>
                        EAN:
                      </label>
                      <input
                        type="text"
                        value={variant.ean}
                        onChange={(e) => updateVariant(productIndex, variantIndex, 'ean', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '6px',
                          border: '1px solid #ccc',
                          borderRadius: '4px'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em' }}>
                        Kod producenta:
                      </label>
                      <input
                        type="text"
                        value={variant.producer_code}
                        onChange={(e) => updateVariant(productIndex, variantIndex, 'producer_code', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '6px',
                          border: '1px solid #ccc',
                          borderRadius: '4px'
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <div style={{
        marginTop: '30px',
        textAlign: 'center',
        padding: '20px',
        borderTop: '1px solid #ddd'
      }}>
        <button
          onClick={submitProducts}
          disabled={isLoading}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            margin: '0 10px',
            backgroundColor: '#28a745',
            color: 'white',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Tworzenie...' : 'Utwórz produkty w MPD'}
        </button>
        
        <button
          onClick={() => window.history.back()}
          disabled={isLoading}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            margin: '0 10px',
            backgroundColor: '#6c757d',
            color: 'white'
          }}
        >
          Anuluj
        </button>
      </div>
    </div>
  );
};

export default BulkCreate;
