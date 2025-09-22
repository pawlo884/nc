import React, { useState, useEffect } from 'react';

const BulkMapping = ({ mappings, onComplete }) => {
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

  return (
    <div style={{ maxWidth: '1200px', margin: '20px auto', padding: '20px' }}>
      <h1>Mapowanie produktów do MPD</h1>
      <p>Wybierz mapowania dla wybranych produktów:</p>
      
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
        {mappings.map((mapping) => (
          <div
            key={mapping.product.id}
            style={{
              border: '1px solid #ddd',
              borderRadius: '8px',
              marginBottom: '20px',
              padding: '20px',
              backgroundColor: '#f9f9f9'
            }}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '15px'
            }}>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontWeight: 'bold',
                  fontSize: '1.1em',
                  color: '#333'
                }}>
                  {mapping.product.name}
                </div>
                <div style={{
                  color: '#666',
                  fontSize: '0.9em',
                  marginTop: '5px'
                }}>
                  ID: {mapping.product.product_id} | 
                  Marka: {mapping.product.brand?.name || 'Brak'} | 
                  Kategoria: {mapping.product.category?.name || 'Brak'}
                </div>
              </div>
            </div>
            
            <div style={{ marginTop: '15px' }}>
              <h4>Sugerowane mapowania:</h4>
              {mapping.suggestions && mapping.suggestions.length > 0 ? (
                mapping.suggestions.map((suggestion) => (
                  <div
                    key={suggestion.id}
                    onClick={() => handleSuggestionClick(mapping.product.id, suggestion.id)}
                    style={{
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
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, color: '#333' }}>
                        {suggestion.name}
                      </div>
                      <div style={{ color: '#666', fontSize: '0.9em' }}>
                        {suggestion.brand}
                      </div>
                    </div>
                    <div style={{
                      color: '#28a745',
                      fontWeight: 'bold',
                      marginLeft: '10px'
                    }}>
                      {suggestion.similarity}%
                    </div>
                  </div>
                ))
              ) : (
                <div style={{
                  color: '#666',
                  fontStyle: 'italic',
                  textAlign: 'center',
                  padding: '20px'
                }}>
                  Brak sugerowanych mapowań
                </div>
              )}
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
          onClick={submitMappings}
          disabled={isLoading}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            margin: '0 10px',
            backgroundColor: '#417690',
            color: 'white',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Zapisywanie...' : 'Zapisz mapowania'}
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

export default BulkMapping;
