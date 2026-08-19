import React, { useState, useEffect } from 'react';

const ProductMapping = ({ productId, isMapped, mappedProductId }) => {
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

  return (
    <div style={{ marginTop: '20px', borderTop: '1px solid #ccc', paddingTop: '20px' }}>
      <h3>Zaawansowane funkcje</h3>
      
      {message && (
        <div className={`status-message ${messageType}`} style={{
          margin: '10px 0',
          padding: '10px',
          borderRadius: '4px',
          backgroundColor: messageType === 'success' ? '#d4edda' : '#f8d7da',
          color: messageType === 'success' ? '#155724' : '#721c24',
          border: `1px solid ${messageType === 'success' ? '#c3e6cb' : '#f5c6cb'}`
        }}>
          {message}
        </div>
      )}
      
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button
          onClick={uploadImages}
          disabled={isLoading}
          style={{
            background: '#28a745',
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Przetwarzanie...' : 'Upload obrazów'}
        </button>
        
        <button
          onClick={autoMapVariants}
          disabled={isLoading}
          style={{
            background: '#17a2b8',
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Przetwarzanie...' : 'Auto-mapuj warianty'}
        </button>
        
        <button
          onClick={syncWithMpd}
          disabled={isLoading}
          style={{
            background: '#ffc107',
            color: 'black',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Przetwarzanie...' : 'Synchronizuj z MPD'}
        </button>
      </div>
    </div>
  );
};

export default ProductMapping;
