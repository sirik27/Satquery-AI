/**
 * FileUploader — Drag-and-drop modal for GeoTIFF/TIFF/PNG/JPG upload.
 */

import React, { useState, useRef } from 'react';
import { Upload, X, FileImage, CheckCircle } from 'lucide-react';

const ALLOWED_TYPES = ['.tif', '.tiff', '.geotiff', '.png', '.jpg', '.jpeg'];

export default function FileUploader({ isOpen, onClose, onUpload }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const inputRef = useRef(null);

  if (!isOpen) return null;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateFile = (file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    return ALLOWED_TYPES.includes(ext);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setErrorMessage(null);

    const file = e.dataTransfer.files?.[0];
    if (file && validateFile(file)) {
      console.log('[FileUploader] File selected via drop:', file.name, file.size, file.type);
      setSelectedFile(file);
    } else if (file) {
      setErrorMessage(`Unsupported file format (${file.name}). Allowed: ${ALLOWED_TYPES.join(', ')}`);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    setErrorMessage(null);
    if (file && validateFile(file)) {
      console.log('[FileUploader] File selected via input:', file.name, file.size, file.type);
      setSelectedFile(file);
    } else if (file) {
      setErrorMessage(`Unsupported file format (${file.name}). Allowed: ${ALLOWED_TYPES.join(', ')}`);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    console.log('[FileUploader] Initiating upload for file:', selectedFile.name);
    setUploading(true);
    setProgress(10);
    setErrorMessage(null);

    let progressInterval = null;
    try {
      progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 85));
      }, 400);

      console.log('[FileUploader] Dispatching onUpload to API handler...');
      await onUpload(selectedFile);

      console.log('[FileUploader] Upload and analysis successfully completed!');
      if (progressInterval) clearInterval(progressInterval);
      setProgress(100);

      setTimeout(() => {
        setSelectedFile(null);
        setProgress(0);
        setUploading(false);
        onClose();
      }, 500);
    } catch (err) {
      console.error('[FileUploader] Upload & Analysis failed:', err);
      if (progressInterval) clearInterval(progressInterval);
      setUploading(false);
      setProgress(0);
      const msg = err.response?.data?.detail || err.message || 'Upload failed. Please check network/backend connection.';
      setErrorMessage(`Error analyzing image: ${msg}`);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="modal-overlay" onClick={() => !uploading && onClose()} id="upload-modal">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Satellite Image</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose} disabled={uploading}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div
            className={`drop-zone ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !uploading && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".tif,.tiff,.png,.jpg,.jpeg"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              disabled={uploading}
            />
            {selectedFile ? (
              <div>
                <CheckCircle size={36} color="#22c55e" />
                <p style={{ marginTop: 12, fontWeight: 600 }}>{selectedFile.name}</p>
                <p className="drop-hint">{formatSize(selectedFile.size)}</p>
              </div>
            ) : (
              <div>
                <div className="drop-icon">
                  <FileImage size={36} />
                </div>
                <p>Drag & drop your satellite image here</p>
                <p className="drop-hint">
                  Supports: GeoTIFF, TIFF, PNG, JPG
                </p>
              </div>
            )}
          </div>

          {errorMessage && (
            <div style={{
              marginTop: 12, padding: '10px 14px', borderRadius: 8,
              background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#fca5a5', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8
            }}>
              <span>⚠️</span>
              <span>{errorMessage}</span>
            </div>
          )}

          {uploading && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  height: 4,
                  background: '#334155',
                  borderRadius: 2,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${progress}%`,
                    background: 'linear-gradient(90deg, #2563eb, #22d3ee)',
                    borderRadius: 2,
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 6, textAlign: 'center' }}>
                {progress < 100 ? 'Uploading and analyzing features...' : 'Analysis complete!'}
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? (
              <>
                <div className="spinner" /> Analyzing...
              </>
            ) : (
              <>
                <Upload size={14} /> Upload & Analyze
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
