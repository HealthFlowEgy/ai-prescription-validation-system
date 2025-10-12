/**
 * Keyboard Navigation Hook
 * Provides accessible keyboard navigation for components
 */

import { useEffect, useCallback } from 'react';

/**
 * Hook for handling keyboard navigation
 * @param {Object} options - Configuration options
 * @param {Function} options.onEscape - Callback for Escape key
 * @param {Function} options.onEnter - Callback for Enter key
 * @param {Function} options.onTab - Callback for Tab key
 * @param {Function} options.onArrowUp - Callback for Arrow Up
 * @param {Function} options.onArrowDown - Callback for Arrow Down
 * @param {Function} options.onArrowLeft - Callback for Arrow Left
 * @param {Function} options.onArrowRight - Callback for Arrow Right
 * @param {boolean} options.enabled - Whether the hook is enabled
 */
export const useKeyboardNavigation = ({
  onEscape,
  onEnter,
  onTab,
  onArrowUp,
  onArrowDown,
  onArrowLeft,
  onArrowRight,
  enabled = true,
} = {}) => {
  const handleKeyDown = useCallback(
    (event) => {
      if (!enabled) return;

      switch (event.key) {
        case 'Escape':
          if (onEscape) {
            event.preventDefault();
            onEscape(event);
          }
          break;

        case 'Enter':
          if (onEnter) {
            event.preventDefault();
            onEnter(event);
          }
          break;

        case 'Tab':
          if (onTab) {
            onTab(event);
          }
          break;

        case 'ArrowUp':
          if (onArrowUp) {
            event.preventDefault();
            onArrowUp(event);
          }
          break;

        case 'ArrowDown':
          if (onArrowDown) {
            event.preventDefault();
            onArrowDown(event);
          }
          break;

        case 'ArrowLeft':
          if (onArrowLeft) {
            event.preventDefault();
            onArrowLeft(event);
          }
          break;

        case 'ArrowRight':
          if (onArrowRight) {
            event.preventDefault();
            onArrowRight(event);
          }
          break;

        default:
          break;
      }
    },
    [
      enabled,
      onEscape,
      onEnter,
      onTab,
      onArrowUp,
      onArrowDown,
      onArrowLeft,
      onArrowRight,
    ]
  );

  useEffect(() => {
    if (enabled) {
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [enabled, handleKeyDown]);

  return { handleKeyDown };
};

/**
 * Hook for focus trap (useful for modals)
 * @param {React.RefObject} containerRef - Reference to the container element
 * @param {boolean} enabled - Whether the focus trap is enabled
 */
export const useFocusTrap = (containerRef, enabled = true) => {
  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    container.addEventListener('keydown', handleTabKey);

    // Focus first element when trap is enabled
    if (firstElement) {
      firstElement.focus();
    }

    return () => {
      container.removeEventListener('keydown', handleTabKey);
    };
  }, [containerRef, enabled]);
};

/**
 * Hook for managing focus restoration
 * Saves the currently focused element and restores it when component unmounts
 */
export const useFocusRestore = () => {
  useEffect(() => {
    const previouslyFocusedElement = document.activeElement;

    return () => {
      if (previouslyFocusedElement && previouslyFocusedElement.focus) {
        previouslyFocusedElement.focus();
      }
    };
  }, []);
};

export default {
  useKeyboardNavigation,
  useFocusTrap,
  useFocusRestore,
};

