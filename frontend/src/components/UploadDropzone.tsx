import { useRef, useState, type DragEvent } from 'react';

const ACCEPTED = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];

interface Props {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export function UploadDropzone({ onFileSelected, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) {
      setError('Use a PDF, JPG, or PNG file.');
      return;
    }
    setError(null);
    setFileName(file.name);
    onFileSelected(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setActive(false);
    if (disabled) return;
    handleFile(e.dataTransfer.files[0]);
  }

  return (
    <div>
      <div
        className={active ? 'dropzone active' : 'dropzone'}
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setActive(true);
        }}
        onDragLeave={() => setActive(false)}
        onDrop={onDrop}
      >
        <p className="dropzone-title">Upload report</p>
        <p className="dropzone-sub">Drop a PDF, JPG, or PNG here, or click to browse.</p>
        {fileName && <div className="dropzone-file">{fileName}</div>}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          disabled={disabled}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
      {error && (
        <p className="error-text" role="alert" style={{ marginTop: 8 }}>
          {error}
        </p>
      )}
    </div>
  );
}
