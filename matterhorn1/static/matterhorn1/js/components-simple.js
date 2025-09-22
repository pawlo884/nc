// Prosta wersja React komponentów bez webpack
// Używa CDN React i Babel standalone

const { useState, useEffect } = React;

// SingleProductCreate Component
function SingleProductCreate({ productId, productData, onComplete }) {
  const [editedProduct, setEditedProduct] = useState({
    matterhorn_product_id: productData.product_id,
    name: productData.name || '',
    description: productData.description || '',
    brand_name: productData.brand?.name || '',
    variants: productData.variants || []
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const updateProduct = (field, value) => {
    setEditedProduct(prev => ({ ...prev, [field]: value }));
  };

  const updateVariant = (variantIndex, field, value) => {
    setEditedProduct(prev => ({
      ...prev,
      variants: prev.variants.map((variant, j) => 
        j === variantIndex ? { ...variant, [field]: value } : variant
      )
    }));
  };

  const addVariant = () => {
    setEditedProduct(prev => ({
      ...prev,
      variants: [...prev.variants, {
        size_name: '',
        stock: 0,
        ean: '',
        producer_code: ''
      }]
    }));
  };

  const removeVariant = (variantIndex) => {
    setEditedProduct(prev => ({
      ...prev,
      variants: prev.variants.filter((_, j) => j !== variantIndex)
    }));
  };

  const submitProduct = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/admin/matterhorn1/product/bulk-create-mpd/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ products: [editedProduct] })
      });

      const data = await response.json();
      
      if (data.success) {
        showMessage(data.message, 'success');
        setTimeout(() => {
          if (onComplete) onComplete();
          else window.location.reload();
        }, 2000);
      } else {
        showMessage(data.error || 'Wystąpił błąd', 'error');
      }
    } catch (error) {
      console.error('Error:', error);
      showMessage('Wystąpił błąd podczas tworzenia produktu', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return React.createElement('div', {
    style: { marginTop: '20px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#f9f9f9' }
  }, [
    React.createElement('h3', { key: 'title' }, 'Edytuj dane przed utworzeniem w MPD'),
    
    message && React.createElement('div', {
      key: 'message',
      className: `status-message ${messageType}`,
      style: {
        margin: '10px 0',
        padding: '10px',
        borderRadius: '4px',
        backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
        color: messageType === 'success' ? '#155724' : '#721c24',
        border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
      }
    }, message),

    React.createElement('div', { key: 'form' }, [
      // Nazwa produktu
      React.createElement('div', { key: 'name', style: { marginBottom: '15px' } }, [
        React.createElement('label', {
          key: 'label',
          style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
        }, 'Nazwa:'),
        React.createElement('input', {
          key: 'input',
          type: 'text',
          value: editedProduct.name,
          onChange: (e) => updateProduct('name', e.target.value),
          style: {
            width: '100%',
            padding: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }
        })
      ]),

      // Opis produktu
      React.createElement('div', { key: 'description', style: { marginBottom: '15px' } }, [
        React.createElement('label', {
          key: 'label',
          style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
        }, 'Opis:'),
        React.createElement('textarea', {
          key: 'textarea',
          value: editedProduct.description,
          onChange: (e) => updateProduct('description', e.target.value),
          rows: 3,
          style: {
            width: '100%',
            padding: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }
        })
      ]),

      // Marka
      React.createElement('div', { key: 'brand', style: { marginBottom: '15px' } }, [
        React.createElement('label', {
          key: 'label',
          style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
        }, 'Marka:'),
        React.createElement('input', {
          key: 'input',
          type: 'text',
          value: editedProduct.brand_name,
          onChange: (e) => updateProduct('brand_name', e.target.value),
          style: {
            width: '100%',
            padding: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }
        })
      ]),

      // Warianty
      React.createElement('div', { key: 'variants' }, [
        React.createElement('div', {
          key: 'header',
          style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }
        }, [
          React.createElement('h4', { key: 'title' }, 'Warianty:'),
          React.createElement('button', {
            key: 'add',
            onClick: addVariant,
            style: {
              background: '#28a745',
              color: 'white',
              border: 'none',
              padding: '5px 10px',
              borderRadius: '4px',
              cursor: 'pointer'
            }
          }, '+ Dodaj wariant')
        ]),

        editedProduct.variants.map((variant, variantIndex) =>
          React.createElement('div', {
            key: variantIndex,
            style: {
              border: '1px solid #e0e0e0',
              borderRadius: '4px',
              padding: '15px',
              marginBottom: '10px',
              backgroundColor: 'white'
            }
          }, [
            React.createElement('div', {
              key: 'header',
              style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }
            }, [
              React.createElement('h5', { key: 'title' }, `Wariant ${variantIndex + 1}`),
              React.createElement('button', {
                key: 'remove',
                onClick: () => removeVariant(variantIndex),
                style: {
                  background: '#dc3545',
                  color: 'white',
                  border: 'none',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }
              }, 'Usuń')
            ]),

            React.createElement('div', {
              key: 'fields',
              style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }
            }, [
              React.createElement('div', { key: 'size' }, [
                React.createElement('label', {
                  key: 'label',
                  style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                }, 'Rozmiar:'),
                React.createElement('input', {
                  key: 'input',
                  type: 'text',
                  value: variant.size_name,
                  onChange: (e) => updateVariant(variantIndex, 'size_name', e.target.value),
                  style: {
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }
                })
              ]),

              React.createElement('div', { key: 'stock' }, [
                React.createElement('label', {
                  key: 'label',
                  style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                }, 'Stan magazynowy:'),
                React.createElement('input', {
                  key: 'input',
                  type: 'number',
                  value: variant.stock,
                  onChange: (e) => updateVariant(variantIndex, 'stock', parseInt(e.target.value) || 0),
                  style: {
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }
                })
              ]),

              React.createElement('div', { key: 'ean' }, [
                React.createElement('label', {
                  key: 'label',
                  style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                }, 'EAN:'),
                React.createElement('input', {
                  key: 'input',
                  type: 'text',
                  value: variant.ean,
                  onChange: (e) => updateVariant(variantIndex, 'ean', e.target.value),
                  style: {
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }
                })
              ]),

              React.createElement('div', { key: 'producer' }, [
                React.createElement('label', {
                  key: 'label',
                  style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                }, 'Kod producenta:'),
                React.createElement('input', {
                  key: 'input',
                  type: 'text',
                  value: variant.producer_code,
                  onChange: (e) => updateVariant(variantIndex, 'producer_code', e.target.value),
                  style: {
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }
                })
              ])
            ])
          ])
        )
      ])
    ]),

    // Przyciski
    React.createElement('div', {
      key: 'actions',
      style: { marginTop: '15px' }
    }, [
      React.createElement('button', {
        key: 'submit',
        onClick: submitProduct,
        disabled: isLoading,
        style: {
          background: '#28a745',
          color: 'white',
          border: 'none',
          padding: '10px 20px',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          marginRight: '10px',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Tworzenie...' : 'Utwórz w MPD'),
      
      React.createElement('button', {
        key: 'cancel',
        onClick: () => {
          const container = document.getElementById('bulk-create-single-container');
          if (container) container.style.display = 'none';
        },
        disabled: isLoading,
        style: {
          background: '#6c757d',
          color: 'white',
          border: 'none',
          padding: '10px 20px',
          borderRadius: '4px',
          cursor: 'pointer'
        }
      }, 'Anuluj')
    ])
  ]);
}

// ProductMapping Component
function ProductMapping({ productId, isMapped, mappedProductId }) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 3000);
  };

  const uploadImages = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/admin/matterhorn1/product/upload-images/${productId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      showMessage(data.message || data.error || 'Wystąpił nieznany błąd', data.success ? 'success' : 'error');
    } catch (error) {
      console.error('Error:', error);
      showMessage('Wystąpił błąd podczas uploadowania obrazów', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const autoMapVariants = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/admin/matterhorn1/product/auto-map-variants/${productId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      showMessage(data.message || data.error || 'Wystąpił nieznany błąd', data.success ? 'success' : 'error');
      
      if (data.success) {
        setTimeout(() => window.location.reload(), 1500);
      }
    } catch (error) {
      console.error('Error:', error);
      showMessage('Wystąpił błąd podczas mapowania wariantów', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const syncWithMpd = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/admin/matterhorn1/product/sync-with-mpd/${productId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      showMessage(data.message || data.error || 'Wystąpił nieznany błąd', data.success ? 'success' : 'error');
      
      if (data.success) {
        setTimeout(() => window.location.reload(), 1500);
      }
    } catch (error) {
      console.error('Error:', error);
      showMessage('Wystąpił błąd podczas synchronizacji', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isMapped) {
    return null;
  }

  return React.createElement('div', {
    style: { marginTop: '20px', borderTop: '1px solid #ccc', paddingTop: '20px' }
  }, [
    React.createElement('h3', { key: 'title' }, 'Zaawansowane funkcje'),
    
    message && React.createElement('div', {
      key: 'message',
      className: `status-message ${messageType}`,
      style: {
        margin: '10px 0',
        padding: '10px',
        borderRadius: '4px',
        backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
        color: messageType === 'success' ? '#155724' : '#721c24',
        border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
      }
    }, message),
    
    React.createElement('div', {
      key: 'buttons',
      style: { display: 'flex', gap: '10px', flexWrap: 'wrap' }
    }, [
      React.createElement('button', {
        key: 'upload',
        onClick: uploadImages,
        disabled: isLoading,
        style: {
          background: '#28a745',
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Przetwarzanie...' : 'Upload obrazów'),
      
      React.createElement('button', {
        key: 'variants',
        onClick: autoMapVariants,
        disabled: isLoading,
        style: {
          background: '#17a2b8',
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Przetwarzanie...' : 'Auto-mapuj warianty'),
      
      React.createElement('button', {
        key: 'sync',
        onClick: syncWithMpd,
        disabled: isLoading,
        style: {
          background: '#ffc107',
          color: 'black',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Przetwarzanie...' : 'Synchronizuj z MPD')
    ])
  ]);
}

// BulkMapping Component
function BulkMapping({ mappings, onComplete }) {
  const [selectedMappings, setSelectedMappings] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  const showMessage = (text, type) => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const handleSuggestionClick = (productId, mpdId) => {
    setSelectedMappings(prev => ({
      ...prev,
      [productId]: mpdId
    }));
  };

  const submitMappings = async () => {
    const mappingsData = Object.entries(selectedMappings).map(([productId, mpdId]) => ({
      product_id: parseInt(productId),
      mpd_product_id: parseInt(mpdId)
    }));

    if (mappingsData.length === 0) {
      showMessage('Wybierz przynajmniej jedno mapowanie', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/admin/matterhorn1/product/bulk-map-to-mpd/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mappings: mappingsData })
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
      showMessage('Wystąpił błąd podczas zapisywania', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return React.createElement('div', {
    style: { maxWidth: '1200px', margin: '20px auto', padding: '20px' }
  }, [
    React.createElement('h1', { key: 'title' }, 'Mapowanie produktów do MPD'),
    React.createElement('p', { key: 'subtitle' }, 'Wybierz mapowania dla wybranych produktów:'),
    
    message && React.createElement('div', {
      key: 'message',
      className: `status-message ${messageType}`,
      style: {
        margin: '20px 0',
        padding: '15px',
        borderRadius: '4px',
        backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
        color: messageType === 'success' ? '#155724' : '#721c24',
        border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
      }
    }, message),

    React.createElement('div', { key: 'mappings' }, mappings.map((mapping) =>
      React.createElement('div', {
        key: mapping.product.id,
        style: {
          border: '1px solid #ddd',
          borderRadius: '8px',
          marginBottom: '20px',
          padding: '20px',
          backgroundColor: '#f9f9f9'
        }
      }, [
        React.createElement('div', {
          key: 'info',
          style: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '15px'
          }
        }, [
          React.createElement('div', { key: 'details', style: { flex: 1 } }, [
            React.createElement('div', {
              key: 'name',
              style: {
                fontWeight: 'bold',
                fontSize: '1.1em',
                color: '#333'
              }
            }, mapping.product.name),
            React.createElement('div', {
              key: 'meta',
              style: {
                color: '#666',
                fontSize: '0.9em',
                marginTop: '5px'
              }
            }, `ID: ${mapping.product.product_id} | Marka: ${mapping.product.brand?.name || 'Brak'} | Kategoria: ${mapping.product.category?.name || 'Brak'}`)
          ])
        ]),
        
        React.createElement('div', { key: 'suggestions', style: { marginTop: '15px' } }, [
          React.createElement('h4', { key: 'title' }, 'Sugerowane mapowania:'),
          mapping.suggestions && mapping.suggestions.length > 0 
            ? mapping.suggestions.map((suggestion) =>
                React.createElement('div', {
                  key: suggestion.id,
                  onClick: () => handleSuggestionClick(mapping.product.id, suggestion.id),
                  style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px',
                    border: selectedMappings[mapping.product.id] === suggestion.id 
                      ? '2px solid #28a745' 
                      : '1px solid #e0e0e0',
                    borderRadius: '4px',
                    marginBottom: '8px',
                    backgroundColor: selectedMappings[mapping.product.id] === suggestion.id 
                      ? '#f8fff9' 
                      : 'white',
                    cursor: 'pointer',
                    transition: 'all 0.3s'
                  }
                }, [
                  React.createElement('div', { key: 'details', style: { flex: 1 } }, [
                    React.createElement('div', {
                      key: 'name',
                      style: { fontWeight: 500, color: '#333' }
                    }, suggestion.name),
                    React.createElement('div', {
                      key: 'brand',
                      style: { color: '#666', fontSize: '0.9em' }
                    }, suggestion.brand)
                  ]),
                  React.createElement('div', {
                    key: 'similarity',
                    style: {
                      color: '#28a745',
                      fontWeight: 'bold',
                      marginLeft: '10px'
                    }
                  }, `${suggestion.similarity}%`)
                ])
              )
            : React.createElement('div', {
                key: 'no-suggestions',
                style: {
                  color: '#666',
                  fontStyle: 'italic',
                  textAlign: 'center',
                  padding: '20px'
                }
              }, 'Brak sugerowanych mapowań')
        ])
      ])
    )),
    
    React.createElement('div', {
      key: 'actions',
      style: {
        marginTop: '30px',
        textAlign: 'center',
        padding: '20px',
        borderTop: '1px solid #ddd'
      }
    }, [
      React.createElement('button', {
        key: 'submit',
        onClick: submitMappings,
        disabled: isLoading,
        style: {
          padding: '10px 20px',
          border: 'none',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          fontSize: '14px',
          margin: '0 10px',
          backgroundColor: '#417690',
          color: 'white',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Zapisywanie...' : 'Zapisz mapowania'),
      
      React.createElement('button', {
        key: 'cancel',
        onClick: () => window.history.back(),
        disabled: isLoading,
        style: {
          padding: '10px 20px',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
          margin: '0 10px',
          backgroundColor: '#6c757d',
          color: 'white'
        }
      }, 'Anuluj')
    ])
  ]);
}

// BulkCreate Component
function BulkCreate({ productsData, onComplete }) {
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

  return React.createElement('div', {
    style: { maxWidth: '1200px', margin: '20px auto', padding: '20px' }
  }, [
    React.createElement('h1', { key: 'title' }, 'Tworzenie nowych produktów w MPD'),
    React.createElement('p', { key: 'subtitle' }, 'Edytuj dane produktów przed utworzeniem w MPD:'),
    
    message && React.createElement('div', {
      key: 'message',
      className: `status-message ${messageType}`,
      style: {
        margin: '20px 0',
        padding: '15px',
        borderRadius: '4px',
        backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
        color: messageType === 'success' ? '#155724' : '#721c24',
        border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
      }
    }, message),

    React.createElement('div', { key: 'products' }, editedProducts.map((product, productIndex) =>
      React.createElement('div', {
        key: product.matterhorn_product_id,
        style: {
          border: '1px solid #ddd',
          borderRadius: '8px',
          marginBottom: '20px',
          padding: '20px',
          backgroundColor: '#f9f9f9'
        }
      }, [
        React.createElement('h3', { key: 'title' }, `Produkt ID: ${product.matterhorn_product_id}`),
        
        React.createElement('div', { key: 'name', style: { marginBottom: '15px' } }, [
          React.createElement('label', {
            key: 'label',
            style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
          }, 'Nazwa:'),
          React.createElement('input', {
            key: 'input',
            type: 'text',
            value: product.name,
            onChange: (e) => updateProduct(productIndex, 'name', e.target.value),
            style: {
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }
          })
        ]),

        React.createElement('div', { key: 'description', style: { marginBottom: '15px' } }, [
          React.createElement('label', {
            key: 'label',
            style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
          }, 'Opis:'),
          React.createElement('textarea', {
            key: 'textarea',
            value: product.description,
            onChange: (e) => updateProduct(productIndex, 'description', e.target.value),
            rows: 3,
            style: {
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }
          })
        ]),

        React.createElement('div', { key: 'brand', style: { marginBottom: '15px' } }, [
          React.createElement('label', {
            key: 'label',
            style: { display: 'block', marginBottom: '5px', fontWeight: 'bold' }
          }, 'Marka:'),
          React.createElement('input', {
            key: 'input',
            type: 'text',
            value: product.brand_name,
            onChange: (e) => updateProduct(productIndex, 'brand_name', e.target.value),
            style: {
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }
          })
        ]),

        React.createElement('div', { key: 'variants' }, [
          React.createElement('div', {
            key: 'header',
            style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }
          }, [
            React.createElement('h4', { key: 'title' }, 'Warianty:'),
            React.createElement('button', {
              key: 'add',
              onClick: () => addVariant(productIndex),
              style: {
                background: '#28a745',
                color: 'white',
                border: 'none',
                padding: '5px 10px',
                borderRadius: '4px',
                cursor: 'pointer'
              }
            }, '+ Dodaj wariant')
          ]),

          product.variants.map((variant, variantIndex) =>
            React.createElement('div', {
              key: variantIndex,
              style: {
                border: '1px solid #e0e0e0',
                borderRadius: '4px',
                padding: '15px',
                marginBottom: '10px',
                backgroundColor: 'white'
              }
            }, [
              React.createElement('div', {
                key: 'header',
                style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }
              }, [
                React.createElement('h5', { key: 'title' }, `Wariant ${variantIndex + 1}`),
                React.createElement('button', {
                  key: 'remove',
                  onClick: () => removeVariant(productIndex, variantIndex),
                  style: {
                    background: '#dc3545',
                    color: 'white',
                    border: 'none',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }
                }, 'Usuń')
              ]),

              React.createElement('div', {
                key: 'fields',
                style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }
              }, [
                React.createElement('div', { key: 'size' }, [
                  React.createElement('label', {
                    key: 'label',
                    style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                  }, 'Rozmiar:'),
                  React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    value: variant.size_name,
                    onChange: (e) => updateVariant(productIndex, variantIndex, 'size_name', e.target.value),
                    style: {
                      width: '100%',
                      padding: '6px',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }
                  })
                ]),

                React.createElement('div', { key: 'stock' }, [
                  React.createElement('label', {
                    key: 'label',
                    style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                  }, 'Stan magazynowy:'),
                  React.createElement('input', {
                    key: 'input',
                    type: 'number',
                    value: variant.stock,
                    onChange: (e) => updateVariant(productIndex, variantIndex, 'stock', parseInt(e.target.value) || 0),
                    style: {
                      width: '100%',
                      padding: '6px',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }
                  })
                ]),

                React.createElement('div', { key: 'ean' }, [
                  React.createElement('label', {
                    key: 'label',
                    style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                  }, 'EAN:'),
                  React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    value: variant.ean,
                    onChange: (e) => updateVariant(productIndex, variantIndex, 'ean', e.target.value),
                    style: {
                      width: '100%',
                      padding: '6px',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }
                  })
                ]),

                React.createElement('div', { key: 'producer' }, [
                  React.createElement('label', {
                    key: 'label',
                    style: { display: 'block', marginBottom: '5px', fontSize: '0.9em' }
                  }, 'Kod producenta:'),
                  React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    value: variant.producer_code,
                    onChange: (e) => updateVariant(productIndex, variantIndex, 'producer_code', e.target.value),
                    style: {
                      width: '100%',
                      padding: '6px',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }
                  })
                ])
              ])
            ])
          )
        ])
      ])
    )),
    
    React.createElement('div', {
      key: 'actions',
      style: {
        marginTop: '30px',
        textAlign: 'center',
        padding: '20px',
        borderTop: '1px solid #ddd'
      }
    }, [
      React.createElement('button', {
        key: 'submit',
        onClick: submitProducts,
        disabled: isLoading,
        style: {
          padding: '10px 20px',
          border: 'none',
          borderRadius: '4px',
          cursor: isLoading ? 'not-allowed' : 'pointer',
          fontSize: '14px',
          margin: '0 10px',
          backgroundColor: '#28a745',
          color: 'white',
          opacity: isLoading ? 0.6 : 1
        }
      }, isLoading ? 'Tworzenie...' : 'Utwórz produkty w MPD'),
      
      React.createElement('button', {
        key: 'cancel',
        onClick: () => window.history.back(),
        disabled: isLoading,
        style: {
          padding: '10px 20px',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
          margin: '0 10px',
          backgroundColor: '#6c757d',
          color: 'white'
        }
      }, 'Anuluj')
    ])
  ]);
}

// Inicjalizacja komponentów
document.addEventListener('DOMContentLoaded', function() {
  // ProductMapping - dla pojedynczego produktu
  const productMappingContainer = document.getElementById('product-mapping-container');
  if (productMappingContainer) {
    const productId = parseInt(productMappingContainer.dataset.productId);
    const isMapped = productMappingContainer.dataset.isMapped === 'true';
    const mappedProductId = productMappingContainer.dataset.mappedProductId;
    
    ReactDOM.render(
      React.createElement(ProductMapping, {
        productId: productId,
        isMapped: isMapped,
        mappedProductId: mappedProductId
      }),
      productMappingContainer
    );
  }

  // BulkMapping - dla masowego mapowania
  const bulkMappingContainer = document.getElementById('bulk-mapping-container');
  if (bulkMappingContainer) {
    const mappings = JSON.parse(bulkMappingContainer.dataset.mappings || '[]');
    
    ReactDOM.render(
      React.createElement(BulkMapping, {
        mappings: mappings,
        onComplete: () => window.location.href = '/admin/matterhorn1/product/'
      }),
      bulkMappingContainer
    );
  }

  // BulkCreate - dla masowego tworzenia
  const bulkCreateContainer = document.getElementById('bulk-create-container');
  if (bulkCreateContainer) {
    const productsData = JSON.parse(bulkCreateContainer.dataset.productsData || '[]');
    
    ReactDOM.render(
      React.createElement(BulkCreate, {
        productsData: productsData,
        onComplete: () => window.location.href = '/admin/matterhorn1/product/'
      }),
      bulkCreateContainer
    );
  }
});
