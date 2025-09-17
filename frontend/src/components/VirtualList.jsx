import React, { useState, useEffect, useRef, useCallback } from 'react';

const VirtualList = ({ 
  items, 
  itemHeight, 
  containerHeight,
  renderItem,
  buffer = 5 
}) => {
  const [visibleItems, setVisibleItems] = useState([]);
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef(null);
  
  // Calculate visible items based on scroll position
  useEffect(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - buffer);
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + buffer
    );
    
    const visible = [];
    for (let i = startIndex; i <= endIndex; i++) {
      visible.push({
        index: i,
        item: items[i],
        style: {
          position: 'absolute',
          top: i * itemHeight,
          left: 0,
          right: 0,
          height: itemHeight
        }
      });
    }
    
    setVisibleItems(visible);
  }, [scrollTop, items, itemHeight, containerHeight, buffer]);
  
  // Handle scroll with RAF for smooth performance
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    
    requestAnimationFrame(() => {
      setScrollTop(containerRef.current.scrollTop);
    });
  }, []);
  
  // Total height for scrollbar
  const totalHeight = items.length * itemHeight;
  
  return (
    <div
      ref={containerRef}
      className="virtual-list-container"
      style={{
        height: containerHeight,
        overflow: 'auto',
        position: 'relative',
        WebkitOverflowScrolling: 'touch',
        willChange: 'transform'
      }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleItems.map(({ index, item, style }) => (
          <div key={index} style={style}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>
    </div>
  );
};

export default VirtualList;