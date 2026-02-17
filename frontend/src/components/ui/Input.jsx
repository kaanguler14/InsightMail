import { forwardRef } from 'react';
import styles from './Input.module.css';

const Input = forwardRef(function Input({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  onKeyDown,
  className = '',
  id,
  ...rest
}, ref) {
  return (
    <div className={`${styles.wrapper} ${className}`}>
      {label && (
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        type={type}
        className={styles.input}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        {...rest}
      />
    </div>
  );
});

export default Input;
