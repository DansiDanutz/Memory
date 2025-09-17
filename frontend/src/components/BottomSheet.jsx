import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import './BottomSheet.css';

const BottomSheet = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  height = '50%',
  theme 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [currentY, setCurrentY] = useState(0);
  const [startY, setStartY] = useState(0);
  const sheetRef = useRef(null);
  const backdropRef = useRef(null);
  
  useEffect(() => {
    if (isOpen) {
      // Prevent body scroll when bottom sheet is open
      document.body.style.overflow = 'hidden';
      
      // Animate in
      setTimeout(() => {
        if (sheetRef.current) {
          sheetRef.current.style.transform = 'translateY(0)';
        }
        if (backdropRef.current) {
          backdropRef.current.style.opacity = '1';
        }
      }, 10);
    } else {
      // Re-enable body scroll
      document.body.style.overflow = '';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);
  
  // Handle touch start for drag
  const handleTouchStart = (e) => {
    const touch = e.touches[0];
    setStartY(touch.clientY);
    setIsDragging(true);
  };
  
  // Handle touch move for drag
  const handleTouchMove = (e) => {
    if (!isDragging) return;
    
    const touch = e.touches[0];
    const deltaY = touch.clientY - startY;
    
    // Only allow dragging down
    if (deltaY > 0) {
      setCurrentY(deltaY);
      if (sheetRef.current) {
        sheetRef.current.style.transform = `translateY(${deltaY}px)`;
      }
    }
  };
  
  // Handle touch end for drag
  const handleTouchEnd = () => {
    if (!isDragging) return;
    
    setIsDragging(false);
    
    // If dragged more than 100px down, close the sheet
    if (currentY > 100) {
      handleClose();
    } else {
      // Snap back to position
      if (sheetRef.current) {
        sheetRef.current.style.transform = 'translateY(0)';
      }
      setCurrentY(0);
    }
  };
  
  // Handle close with animation
  const handleClose = () => {
    if (sheetRef.current) {
      sheetRef.current.style.transform = 'translateY(100%)';
    }
    if (backdropRef.current) {
      backdropRef.current.style.opacity = '0';
    }
    
    setTimeout(() => {
      onClose();
      setCurrentY(0);
    }, 300);
  };
  
  if (!isOpen) return null;
  
  return (
    <div className={`bottom-sheet-container ${theme === 'dark' ? 'dark' : ''}`}>
      {/* Backdrop */}
      <div 
        ref={backdropRef}
        className="bottom-sheet-backdrop"
        onClick={handleClose}
      />
      
      {/* Sheet */}
      <div 
        ref={sheetRef}
        className="bottom-sheet"
        style={{ height, transform: 'translateY(100%)' }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Drag Handle */}
        <div className="drag-handle-container">
          <div className="drag-handle" />
        </div>
        
        {/* Header */}
        {title && (
          <div className="bottom-sheet-header">
            <h3 className="bottom-sheet-title">{title}</h3>
            <button 
              className="close-button"
              onClick={handleClose}
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}
        
        {/* Content */}
        <div className="bottom-sheet-content">
          {children}
        </div>
      </div>
    </div>
  );
};

export default BottomSheet;